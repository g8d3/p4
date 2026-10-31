#!/bin/bash
# resume-worker — deliver queued session-resume prompts, then exit.
# Triggered BY systemd itself (pi-web-resume.service: PartOf + After
# pi-web-sessiond), never by a timer: when the daemon restarts for any
# reason, this runs right after it. No sleeps, no guessing — it polls the
# daemon's health and delivers the instant it answers.
#
# Queue: ~/.pi-web/resume-queue/<session-id>.json
#   {"sid": "...", "cwd": "/home/vuos/code/p4", "message": "..."}
# Delivered entries are deleted. Undeliverable ones are kept for the next run.
set -u
QUEUE="$HOME/.pi-web/resume-queue"
BASE="http://127.0.0.1:8504/api/machines/local"
LOG="/tmp/pi-web-resume-worker.log"
LOCK="$QUEUE/.lock"

mkdir -p "$QUEUE"
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date -u +%FT%TZ) another worker holds the lock, exiting" >> "$LOG"
  exit 0
fi

log() { echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }

shopt -s nullglob
entries=("$QUEUE"/*.json)
[ "${#entries[@]}" -eq 0 ] && exit 0

# Readiness, not a timer: exit the instant the daemon answers.
ready=""
for _ in $(seq 1 240); do
  if curl -sf -m 3 "$BASE/sessions?cwd=%2Fhome%2Fvuos%2Fcode%2Fp4" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.5
done
if [ -z "$ready" ]; then
  log "ERROR: daemon not healthy after 120s, keeping ${#entries[@]} queued"
  exit 1
fi

urlenc() { printf '%s' "$1" | sed 's|/|%2F|g'; }

# Build the POST body with python (quote-safe for any message text).
# Prints shell assignments on stdout; writes body to $1.payload on success.
build_payload() {
  python3 - "$1" <<'PYEOF'
import json, shlex, sys
try:
    q = json.load(open(sys.argv[1], encoding='utf-8'))
except Exception:
    print('MALFORMED=1')
    raise SystemExit
sid, cwd, msg = q.get('sid', ''), q.get('cwd', ''), q.get('message', '')
if not (sid and cwd and msg):
    print('MALFORMED=1')
    raise SystemExit
print('MALFORMED=0')
print('psid=' + shlex.quote(sid))
print('ppayload=' + shlex.quote(sys.argv[1] + '.payload'))
open(sys.argv[1] + '.payload', 'w', encoding='utf-8').write(
    json.dumps({'cwd': cwd, 'text': msg}))
PYEOF
}

delivered=0
for f in "${entries[@]}"; do
  unset MALFORMED psid ppayload
  eval "$(build_payload "$f")"
  if [ "${MALFORMED:-1}" != "0" ]; then
    log "skipping malformed queue file $f"
    continue
  fi
  resp=$(curl -s -m 15 -X POST "$BASE/sessions/$(urlenc "$psid")/prompt" \
    -H 'Content-Type: application/json' \
    --data @"$ppayload")
  rm -f "$ppayload"
  if echo "$resp" | grep -q '"accepted":true'; then
    rm -f "$f"
    delivered=$((delivered + 1))
    log "resumed $psid"
  else
    log "ERROR: resume NOT accepted for $psid, keeping queued: $resp"
  fi
done
log "done, delivered $delivered/${#entries[@]}"
exit 0
