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
#
# System-format delivery (no core edits): the only wake path core exposes for
# an existing idle session is POST /prompt, which core renders as an OWNER
# bubble. So we relay: create a throwaway session, prompt IT (owner bubble
# stays hidden in the throwaway), and its agent calls send_session_message
# into the target — that path is a custom message with display:true, i.e. a
# SYSTEM bubble, and it starts/continues the target's run. The throwaway is
# archived afterwards. If the relay fails at any point we fall back to a
# direct /prompt on the target (owner format) so a resume is never lost.
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

# message_count <sid> <cwd> — prints messageCount or empty on error.
message_count() {
  curl -s -m 10 "$BASE/sessions/$(urlenc "$1")/status?cwd=$(urlenc "$2")" \
    | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("messageCount",""))
except Exception: print("")'
}

# deliver_system <target-sid> <cwd> <message> — relay path. Returns 0 on
# system-format delivery, 1 otherwise (caller falls back to direct prompt).
deliver_system() {
  local target="$1" cwd="$2" msg="$3" oldpid="$4" queuedat="$5" relay="" resp="" before="" after="" newpid="" banner=""
  newpid="$(systemctl --user show pi-web-sessiond.service -p MainPID --value 2>/dev/null || true)"
  banner="$(python3 - "$msg" "$oldpid" "$newpid" "$queuedat" <<'PYEOF'
import sys
rmsg, old, new, queued = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
if old and new:
    head = ("**System restart notice** — the session daemon restarted as planned "
            f"(`old pid {old}` -> `current pid {new}`). ")
elif new:
    head = ("**System restart notice** — the session daemon restarted as planned "
            f"(`current pid {new}`). ")
else:
    head = "**System restart notice** — the session daemon restarted as planned. "
tail = ("Your transcript, workspace files and settings are intact. Continue the work "
        "you were doing before the restart from where it stopped, then report briefly "
        "what you did and current status.")
note = ("\n\n> Resume note: " + rmsg.replace("\n", "\n> ")) if rmsg else ""
print(head + tail + note)
PYEOF
)"
  before="$(message_count "$target" "$cwd")"
  resp="$(curl -s -m 15 -X POST "$BASE/sessions" \
    -H 'Content-Type: application/json' \
    --data "$(python3 -c 'import json,sys; print(json.dumps({"cwd": sys.argv[1]}))' "$cwd")")"
  relay="$(printf '%s' "$resp" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    raise SystemExit
for k in ("id","sessionId"):
    if d.get(k): print(d[k]); break
else:
    s = d.get("session") or {}
    print(s.get("id","") if isinstance(s, dict) else "")')"
  [ -n "$relay" ] || { log "relay: create failed for $target: $(printf '%s' "$resp" | head -c 200)"; return 1; }
  local instruction
  instruction="$(python3 - "$target" "$banner" <<'PYEOF'
import json, sys
target, rmsg = sys.argv[1], sys.argv[2]
print("You are a resume relay. This is a SYSTEM restart notice, not a user request. Call send_session_message with sessionId="
      + json.dumps(target) + " and message=" + json.dumps(rmsg)
      + " exactly. No other tool calls, no other action. "
      + "After the tool result, reply with exactly: done")
PYEOF
)"
  resp="$(curl -s -m 15 -X POST "$BASE/sessions/$(urlenc "$relay")/prompt" \
    -H 'Content-Type: application/json' \
    --data "$(python3 -c 'import json,sys; print(json.dumps({"cwd": sys.argv[1], "text": sys.argv[2]}))' "$cwd" "$instruction")")"
  echo "$resp" | grep -q '"accepted":true' || {
    log "relay $relay: prompt not accepted for $target: $(printf '%s' "$resp" | head -c 200)"
    archive_relay "$relay" "$cwd"
    return 1
  }
  # Wait for the relay turn to finish (bounded): it calls one tool then idles.
  local i st
  for i in $(seq 1 60); do
    st="$(curl -s -m 10 "$BASE/sessions/$(urlenc "$relay")/status?cwd=$(urlenc "$cwd")")"
    if printf '%s' "$st" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: raise SystemExit(1)
raise SystemExit(0 if (not d.get("isStreaming") and not d.get("isCompacting")) else 1)'; then
      break
    fi
    sleep 2
  done
  after="$(message_count "$target" "$cwd")"
  archive_relay "$relay" "$cwd"
  if [ -n "$before" ] && [ -n "$after" ] && [ "$after" -gt "$before" ] 2>/dev/null; then
    return 0
  fi
  log "relay $relay: target messageCount did not move for $target (before=$before after=$after)"
  return 1
}

# archive_relay <relay-sid> <cwd> — best effort, never fails the resume.
archive_relay() {
  local resp
  resp="$(curl -s -m 15 -X POST "$BASE/sessions/bulk/archive" \
    -H 'Content-Type: application/json' \
    --data "$(python3 -c 'import json,sys; print(json.dumps({"sessions":[{"id": sys.argv[1], "cwd": sys.argv[2]}]}))' "$1" "$2")" 2>&1)" || true
  echo "$resp" | grep -q '"archived"' || log "relay $1: archive response (non-fatal): $(printf '%s' "$resp" | head -c 200)"
}

delivered=0
for f in "${entries[@]}"; do
  unset MALFORMED psid ppayload
  eval "$(build_payload "$f")"
  if [ "${MALFORMED:-1}" != "0" ]; then
    log "skipping malformed queue file $f"
    continue
  fi
  # shellcheck disable=SC2154
  cwd="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("cwd",""))' "$f")"
  # shellcheck disable=SC2154
  rmsg="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("message",""))' "$f")"
  oldpid="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("oldPid",""))' "$f")"
  queuedat="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("queuedAt",""))' "$f")"
  if deliver_system "$psid" "$cwd" "$rmsg" "$oldpid" "$queuedat"; then
    rm -f "$f" "$ppayload"
    delivered=$((delivered + 1))
    log "resumed $psid via relay (system format)"
    continue
  fi
  # Fallback: direct prompt (owner format) so the resume is never lost.
  resp="$(curl -s -m 15 -X POST "$BASE/sessions/$(urlenc "$psid")/prompt" \
    -H 'Content-Type: application/json' \
    --data @"$ppayload")"
  rm -f "$ppayload"
  if echo "$resp" | grep -q '"accepted":true'; then
    rm -f "$f"
    delivered=$((delivered + 1))
    log "resumed $psid via fallback direct prompt (owner format)"
  else
    rm -f "$ppayload"
    log "ERROR: resume NOT accepted for $psid, keeping queued: $resp"
  fi
done
log "done, delivered $delivered/${#entries[@]}"
exit 0
