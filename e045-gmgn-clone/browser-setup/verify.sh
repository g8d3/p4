#!/usr/bin/env bash
# verify.sh <name> <port> <profile> <shotsdir> -- <chrome> [flags...]
# Launch headless chrome, verify it drives the live app, report GPU/stealth/VAAPI.
set -u
NAME="${1:?name}"; shift
PORT="${1:?port}"; shift
PROFILE="${1:?profile}"; shift
SHOTS="${1:?shots}"; shift
[ "${1:-}" = "--" ] && shift
CHROME="${1:?chrome}"; shift
mkdir -p "${SHOTS}"

FLAGS=("--headless=new" "--ozone-platform=headless" "--no-sandbox"
       "--disable-dev-shm-usage" "--remote-debugging-port=${PORT}"
       "--remote-allow-origins=*" "--user-data-dir=${PROFILE}" "$@")
LOG="${SHOTS}/launch.log"
echo "### ${NAME} :: ${CHROME}" > "${LOG}"
echo "### FLAGS: ${FLAGS[*]}" >> "${LOG}"
"${CHROME}" "${FLAGS[@]}" >>"${LOG}" 2>&1 &
CPID=$!
echo "${CPID}" > "${SHOTS}/keep.pid"
for i in $(seq 1 30); do
  curl -sf "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1 && break
  sleep 0.5
done
echo "### [$NAME] pid=${CPID} port=${PORT}"
echo "### CDP: $(curl -sf http://127.0.0.1:${PORT}/json/version 2>&1 | grep -i browser | head -1)"

echo "### [$NAME] gpu-process + viz processes:"
ps aux | grep -iE "chrome" | grep -iE -- "--type=gpu|--type=utility|viz" | grep -v grep | sed 's/  */ /g' | cut -c1-320 || echo "(none)"

echo "### [$NAME] connect + open app"
agent-browser connect "${PORT}" >/dev/null 2>&1
agent-browser open "http://127.0.0.1:8338/" >/dev/null 2>&1; sleep 2
echo "  title -> $(agent-browser eval 'document.title' 2>&1 | tail -1)"
echo "  url   -> $(agent-browser eval 'location.href' 2>&1 | tail -1)"
echo "  body-len-> $(agent-browser eval 'document.body.innerText.length' 2>&1 | tail -1)"
echo "  h1    -> $(agent-browser eval '(document.querySelector("h1")||{innerText:\"(no h1)\"}).innerText' 2>&1 | tail -1)"

echo "### [$NAME] WebGL unmasked renderer (HW vs SW):"
agent-browser open "data:text/html,<canvas id=c></canvas><script>var g=document.getElementById('c').getContext('webgl');var d=g&&g.getExtension('WEBGL_debug_renderer_info');window.rend=g?(d?g.getParameter(d.UNMASKED_RENDERER_WEBGL):'nodbg:'+g.getParameter(g.RENDERER)):'NO_WEBGL';document.body.textContent=window.rend;</script>" >/dev/null 2>&1; sleep 1
echo "  -> $(agent-browser eval 'window.rend||document.body.textContent' 2>&1 | tail -1)"
echo "  webgl2 -> $(agent-browser open "data:text/html,<canvas id=c></canvas><script>var g=document.getElementById('c').getContext('webgl2');var d=g&&g.getExtension('WEBGL_debug_renderer_info');window.rend=g?(d?g.getParameter(d.UNMASKED_RENDERER_WEBGL):'nodbg:'+g.getParameter(g.RENDERER)):'NO_WEBGL2';document.body.textContent=window.rend;</script>" >/dev/null 2>&1; sleep 1; agent-browser eval 'window.rend' 2>&1 | tail -1)"

echo "### [$NAME] chrome://gpu feature-status (wait 1.5s):"
agent-browser open "chrome://gpu" >/dev/null 2>&1; sleep 1.5
agent-browser eval "(document.querySelector('#feature-status')||{}).innerText||''" 2>&1 | tr '\n' ' ' | grep -ioE "feature status[^<]{0,700}" | head -c 900 || echo "(empty)"

echo "### [$NAME] screenshot app:"
agent-browser open "http://127.0.0.1:8338/" >/dev/null 2>&1; sleep 2
agent-browser screenshot "${SHOTS}/${NAME}.png" 2>&1 | tail -2
ls -la "${SHOTS}/${NAME}.png" 2>&1

echo "### [$NAME] launch.log GPU/VAAPI lines:"
grep -iE "vaapi|vulkan|angle|egl|swiftshader|llvmpipe|gpu process|viz|dri|GL_|UseGpu|video.*decode|Fallback|exiting gpu" "${LOG}" | tail -30 || echo "(no informative lines)"

echo "### [$NAME] done."
