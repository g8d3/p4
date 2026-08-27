#!/usr/bin/env bash
# probe2.sh <port> <profile> <shotsdir> -- <chrome> [flags...]
# Keeps chrome alive; reports GPU via ps, launch log, WebGL unmasked renderer.
set -u
PORT="${1:?port}"; shift
PROFILE="${1:?profile}"; shift
SHOTS="${1:?shots}"; shift
[ "${1:-}" = "--" ] && shift
CHROME="${1:?chrome}"; shift
mkdir -p "${SHOTS}"

FLAGS=("--headless=new" "--ozone-platform=headless" "--no-sandbox"
       "--disable-dev-shm-usage" "--remote-debugging-port=${PORT}"
       "--remote-allow-origins=*" "--user-data-dir=${PROFILE}" "--disable-breakpad" "$@")
LOG="${SHOTS}/launch.log"
echo "### LAUNCH: ${CHROME}" > "${LOG}"
echo "### FLAGS: ${FLAGS[*]}" >> "${LOG}"
"${CHROME}" "${FLAGS[@]}" >>"${LOG}" 2>&1 &
CPID=$!
echo "${CPID}" > "${SHOTS}/keep.pid"
for i in $(seq 1 30); do
  curl -sf "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1 && break
  sleep 0.5
done
echo "### pid=${CPID} port=${PORT}"
echo "### CDP: $(curl -sf http://127.0.0.1:${PORT}/json/version 2>&1 | head -c 120)"

echo
echo "### GPU-ish chrome processes:"
ps aux | grep -iE -- "--type=gpu|--type=utility|viz" | grep -v grep | grep -iE "chrome" | sed 's/  */ /g' | cut -c1-500 || echo "(none)"

echo
echo "### WebGL unmasked renderer (definitive HW vs SW):"
agent-browser connect "${PORT}" >/dev/null 2>&1
agent-browser open "data:text/html,<canvas id=c></canvas><script>var g=document.getElementById('c').getContext('webgl');var d=g&&g.getExtension('WEBGL_debug_renderer_info');window.R=g?('REND='+(d?g.getParameter(d.UNMASKED_RENDERER_WEBGL):'nodbg:'+g.getParameter(g.RENDERER))):'NO_WEBGL';document.title=window.R</script>" >/dev/null 2>&1
sleep 1
echo "  renderer -> $(agent-browser eval 'window.R' 2>&1 | tail -1)"

echo
echo "### chrome://gpu PROBLEM / FEATURE_STATUS region:"
agent-browser open "chrome://gpu" >/dev/null 2>&1; sleep 1
agent-browser eval "var fs=document.querySelector('#feature-status');(fs?fs.innerText:(document.body.innerText||''))" 2>&1 | tr '\n' ' ' | grep -ioE "feature status[^#]{0,600}" | head -c 900
echo
echo "### chrome://gpu raw body len:"
agent-browser eval "document.body.innerText.length" 2>&1 | tail -1

echo
echo "### launch.log grep (errors/vaapi/gpu):"
grep -iE "gpu|vaapi|vulkan|dri|gl_|angle|swiftshader|llvmpipe|error|fail|egl|GL_" "${LOG}" | tail -40 || echo "(no matching log lines)"

echo
echo "### KEEP=1 -> inspecting; kill with: kill \$(cat ${SHOTS}/keep.pid)"
