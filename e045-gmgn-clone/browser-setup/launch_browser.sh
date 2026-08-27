#!/usr/bin/env bash
# launch_browser.sh — Headless Chromium + GPU(VAAPI) + stealth, CDP for agent-browser.
#
# Usage:
#   launch_browser.sh [port] [profile-dir]
#   PORT       default 9222   (remote-debugging-port; agent-browser connect <port>)
#   PROFILE    default ./stealth-profile
#
# Env overrides:
#   CHROME_BIN   default /home/vuos/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome
#   KEEP=0       leave running in background (prints pid); default 0
#   EXTRA_FLAGS  additional flags, appended
#
# This script is the final, verified recipe. It:
#   - runs headless (--headless=new, --ozone-platform=headless, no X dependence)
#   - keeps the GPU process ALIVE with SwiftShader for GL/WebGL (hardware GL is
#     impossible on this box in headless — --enable-gpu/--use-angle=gl crash it)
#   - enables hardware VAAPI video decode/encode (Radeon VCN) for encode/decode
#   - exposes a stable CDP endpoint for agent-browser connect
#   - applies browser stealth flags so it is less detectable than vanilla headless
# It does NOT touch port 8338 or any running web app.
set -euo pipefail

CHROME_BIN="${CHROME_BIN:-/home/vuos/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome}"
PORT="${1:-${PORT:-9222}}"
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILE="${2:-${PROFILE:-${BASE_DIR}/stealth-profile}}"
mkdir -p "${PROFILE}"

# Browser version -> realistic non-headless UA. chromium-1234 = Chrome for Testing 151.
UA="${STEALTH_UA:-Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36}"

# Run without an X display: headless has its own ozone platform and the REAL
# reason --enable-gpu/--use-angle=gl crashes here is that ANGLE tries to open
# the default X display (which this session has no permission for).
unset DISPLAY WAYLAND_DISPLAY
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

FLAGS=(
  --headless=new
  --ozone-platform=headless
  --no-sandbox
  --disable-dev-shm-usage
  --disable-breakpad
  --remote-debugging-port="${PORT}"
  --remote-allow-origins=*
  --user-data-dir="${PROFILE}"

  # --- GPU: keep GPU process alive (SwiftShader GL) + hardware VAAPI video ---
  # NOTE: do NOT pass --enable-gpu or --use-angle=gl here — in headless on this
  # box they make ANGLE try to open the (denied) X display and the GPU process
  # exits ("Could not open the default X display"), breaking WebGL/page render.
  --enable-unsafe-swiftshader            # allow software WebGL (auto-fallback deprecated in M151+)
  --enable-features=VaapiVideoDecoder,VaapiVideoEncoder,VaapiVideoDecodeLinuxGL,VaapiIgnoreDriverChecks

  # --- Stealth (less detectable than vanilla headless) ---
  --disable-blink-features=AutomationControlled   # navigator.webdriver -> false
  --lang=en-US
  --no-first-run
  --no-default-browser-check
  --disable-infobars
  --window-size=1440,900
  --user-agent="${UA}"                    # strip "HeadlessChrome" from UA
)

if [ -n "${EXTRA_FLAGS:-}" ]; then
  read -r -a _extra <<< "${EXTRA_FLAGS}"
  FLAGS+=("${_extra[@]}")
fi

echo "[launch_browser] CHROME=${CHROME_BIN}"
echo "[launch_browser] port=${PORT} profile=${PROFILE}"
# Redirect chrome output to a log so it does NOT hold the caller's stdout pipe.
LOG="${BASE_DIR}/browser.log"; : > "${LOG}"
echo "[launch_browser] LOG=${LOG}"
"${CHROME_BIN}" "${FLAGS[@]}" >> "${LOG}" 2>&1 &
CPID=$!
echo "${CPID}" > "${BASE_DIR}/browser.pid"
echo "[launch_browser] pid=${CPID}"

# Wait for the CDP endpoint.
for _ in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then break; fi
  sleep 0.5
done
if curl -sf "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
  echo "[launch_browser] CDP READY: http://127.0.0.1:${PORT}/json/version"
  curl -s "http://127.0.0.1:${PORT}/json/version" | grep -i '"Browser"' || true
else
  echo "[launch_browser] CDP NOT READY in 20s — check ${BASE_DIR}/browser.log"
  exit 1
fi
