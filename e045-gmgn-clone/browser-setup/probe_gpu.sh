#!/usr/bin/env bash
# probe_gpu.sh <port> <profile-dir> <screenshot-dir> -- <chrome-binary> [flags...]
# Launches chrome headless, connects via agent-browser, and reports GPU status
# from chrome://gpu, plus the actual chrome process command lines.
set -u
PORT="${1:?port}"; shift
PROFILE="${1:?profile}"; shift
SHOTS="${1:?shots}"; shift
[ "${1:-}" = "--" ] && shift
CHROME="${1:?chrome}"; shift

SHOTDIR="${SHOTS}"; mkdir -p "${SHOTDIR}"

FLAGS=("--headless=new" "--ozone-platform=headless" "--no-sandbox"
       "--disable-dev-shm-usage"
       "--remote-debugging-port=${PORT}"
       "--remote-allow-origins=*"
       "--user-data-dir=${PROFILE}"
       "--disable-breakpad"
       "$@")
LOG=$(mktemp)
echo "### LAUNCH: ${CHROME} ${FLAGS[*]}"
"${CHROME}" "${FLAGS[@]}" >"${LOG}" 2>&1 &
CPID=$!
echo "### chrome pid=${CPID} (log=${LOG})"

for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then break; fi
  sleep 0.5
done
echo "### CDP reachable: $(curl -sf http://127.0.0.1:${PORT}/json/version 2>&1 | tr -d '\n' | head -c 300)"
echo

echo "### ALL chrome processes (cmdlines) on this port:"
ps aux | grep -iE "chrome" | grep "${PORT}" | grep -v grep | sed 's/  */ /g' | cut -c1-500 || echo "(none)"
echo

echo "### agent-browser connect ${PORT}"
agent-browser connect "${PORT}" 2>&1 | head -40
echo
echo "### open chrome://gpu"
agent-browser open "chrome://gpu" 2>&1 | head -20
sleep 2
echo
echo "### chrome://gpu text via eval:"
agent-browser eval "document.body.innerText" > "${SHOTDIR}/gpu_dump.txt" 2>/dev/null
echo "dump line count: $(wc -l < "${SHOTDIR}/gpu_dump.txt" 2>/dev/null)"
echo "--- key status lines ---"
grep -iE "feature status|problem|software|hardware|vaapi|vulkan|opengl|d3d|video decode|webgl|gpu compositing|canvas|raster|acceleration|swiftshader|llvmpipe|radeon|amd|disabled|angle" "${SHOTDIR}/gpu_dump.txt" | head -90

if [ "${KEEP:-0}" = "1" ]; then
  echo "### KEEP=1 -> chrome left running pid=${CPID} on port ${PORT}"
  echo "${CPID}" > "${SHOTDIR}/keep.pid"
else
  agent-browser close --all 2>&1 | head -5
  sleep 1
  kill "${CPID}" 2>/dev/null; pkill -f "remote-debugging-port=${PORT}" 2>/dev/null
  echo "### cleaned up"
fi
