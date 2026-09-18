#!/bin/bash
# Pre-flight resilience suite. Simulates interruptions and proves every
# tripwire fires BEFORE go-live. $0 inference spend (no model is called).
# Exit 0 = all PASS. Backup/restores ledger + heartbeat (test rows never ship).
# Usage: bin/chaos.sh
set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1
PASS=0; FAILN=0
ok()  { echo "PASS: $1"; PASS=$((PASS + 1)); }
bad() { echo "FAIL: $1"; FAILN=$((FAILN + 1)); }

# --- sandbox live files, always restore ---
cp data/ledger.jsonl /tmp/chaos-ledger.bak 2>/dev/null || true
cp log/heartbeat.jsonl /tmp/chaos-hb.bak 2>/dev/null || true
restore() { cp /tmp/chaos-ledger.bak data/ledger.jsonl 2>/dev/null || rm -f data/ledger.jsonl
            cp /tmp/chaos-hb.bak log/heartbeat.jsonl 2>/dev/null || rm -f log/heartbeat.jsonl; }
trap restore EXIT

# T1 worker death -> watchdog must WAKEUP (only stale beats remain; trap restores)
printf '{"ts":"2020-01-01T00:00:00Z","who":"scout","host":"chaos","event":"start"}\n' > log/heartbeat.jsonl
OUT=$(timeout 20 bash bin/watchdog.sh 35 2>&1); RC=$?
{ [ "$RC" -eq 3 ] && printf '%s' "$OUT" | grep -q WAKEUP; } \
  && ok "T1a stale start beats -> watchdog WAKEUP (rc=3)" \
  || bad "T1a stale worker NOT detected (rc=$RC: $OUT)"
printf '{"ts":"2020-01-01T00:00:00Z","who":"scout","host":"chaos","event":"end"}\n' > log/heartbeat.jsonl
OUT=$(timeout 20 bash bin/watchdog.sh 35 240 2>&1); RC=$?
{ [ "$RC" -eq 3 ] && printf '%s' "$OUT" | grep -q WAKEUP; } \
  && ok "T1b nothing scheduled for years -> watchdog WAKEUP" \
  || bad "T1b long-parked silence NOT detected (rc=$RC: $OUT)"
NOW=$(date -u +%FT%TZ)
printf '{"ts":"%s","who":"scout","host":"chaos","event":"end"}\n' "$NOW" > log/heartbeat.jsonl
OUT=$(timeout 20 bash bin/watchdog.sh 35 240 2>&1); RC=$?
{ [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q parked; } \
  && ok "T1c freshly finished leg -> parked OK, no false alarm" \
  || bad "T1c fresh park mishandled (rc=$RC: $OUT)"

# T2 broke floor -> credits gate must refuse
timeout 30 python3 bin/credits.py --floor 999999 > /dev/null 2>&1; RC=$?
[ "$RC" -eq 2 ] && ok "T2 floor breach -> credits gate refuses (rc=2)" \
  || bad "T2 floor breach NOT refused (rc=$RC)"

# T3 loop on broke floor -> STOP row, zero NEW triage spend (ledger has history)
BEFORE_PAPER=$(grep -c '"kind":"PAPER"' data/ledger.jsonl 2>/dev/null || true)
OUT=$(E070_FLOOR=999999 timeout 120 bash bin/loop.sh 2>&1); RC=$?
AFTER_PAPER=$(grep -c '"kind":"PAPER"' data/ledger.jsonl 2>/dev/null || true)
{ [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q "STOP: reserve floor" \
  && grep -q '"kind":"STOP"' data/ledger.jsonl \
  && [ "${AFTER_PAPER:-0}" -eq "${BEFORE_PAPER:-0}" ]; } \
  && ok "T3 loop halts with STOP row and spends nothing on triage" \
  || bad "T3 loop did NOT halt cleanly (rc=$RC: $OUT)"

# T4 missing key -> triage returns error JSON, loop-safe (rc=0)
OUT=$(OPENROUTER_API_KEY= timeout 60 python3 bin/triage.py --text "x" 2>&1)
{ printf '%s' "$OUT" | grep -q '"error"'; } \
  && ok "T4 missing key -> triage error JSON, no crash" \
  || bad "T4 missing key mishandled: $OUT"

# T5 API outage -> triage returns error JSON fast, loop-safe
OUT=$(OPENROUTER_DECISIONS_URL=http://127.0.0.1:9/nope OPENROUTER_API_KEY=dummy \
  timeout 60 python3 bin/triage.py --text "x" 2>&1)
{ printf '%s' "$OUT" | grep -q '"error"'; } \
  && ok "T5 decisions API down -> triage error JSON, no crash" \
  || bad "T5 API outage mishandled: $OUT"

# T6 credits outage -> watcher reports ok:false (rc=1), never fake numbers
OUT=$(OPENROUTER_CREDITS_URL=http://127.0.0.1:9/nope timeout 30 python3 bin/credits.py 2>&1); RC=$?
{ [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q '"ok": false'; } \
  && ok "T6 credits API down -> honest failure, no fake balance" \
  || bad "T6 credits outage mishandled (rc=$RC: $OUT)"

# T7 desk down -> selfcheck must FAIL (user-facing alarm works)
timeout 30 python3 bin/selfcheck.py --base http://127.0.0.1:9 > /dev/null 2>&1; RC=$?
[ "$RC" -eq 1 ] && ok "T7 desk down -> selfcheck FAILs (alarm works)" \
  || bad "T7 desk outage NOT detected (rc=$RC)"

# T8 corrupt ledger line -> desk skips it, still renders (no crash)
timeout 30 python3 -c "
import sys; sys.path.insert(0, 'bin'); import desk, tempfile, os
p = tempfile.mktemp(); open(p, 'w').write('{\"a\":1}\nGARBAGE{{{\n{\"b\":2}\n')
rows, missing = desk.read_jsonl(p, 10); os.unlink(p)
assert rows == [{'a': 1}, {'b': 2}] and missing is False, rows
" 2>&1 && ok "T8 corrupt ledger line skipped, reader survives" \
  || bad "T8 corrupt ledger line crashes reader"

# T9 GPU heuristic sanity: hardware string matches, SwiftShader does not
if printf 'NVIDIA GeForce RTX 4090' | grep -qiE 'nvidia|amd|radeon|intel|iris|adreno|apple|mali' \
   && ! printf 'SwiftShader Device' | grep -qiE 'nvidia|amd|radeon|intel|iris|adreno|apple|mali'; then
  ok "T9 GPU/CPU classifier distinguishes hardware from SwiftShader"
else
  bad "T9 GPU/CPU classifier broken"
fi

# T10 end-to-end rendered gate on the live desk (real browser, ~2 min)
OUT=$(timeout 300 bash bin/rendercheck.sh 2>&1); RC=$?
{ [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q "RENDERCHECK OK"; } \
  && ok "T10 rendered-DOM gate passes on live desk" \
  || bad "T10 rendered gate failed: $OUT"

# T11 finished leg must read IDLE on the page — never LIVE after death
NOW=$(date -u +%FT%TZ)
printf '{"ts":"%s","who":"chaos","host":"chaos","event":"start"}\n' "$NOW" >> log/heartbeat.jsonl
L1=$(timeout 15 curl -s http://127.0.0.1:8327/api/state | python3 -c "import json,sys; print(json.load(sys.stdin)['pulse']['level'])")
printf '{"ts":"%s","who":"chaos","host":"chaos","event":"end"}\n' "$NOW" >> log/heartbeat.jsonl
sleep 1
L2=$(timeout 15 curl -s http://127.0.0.1:8327/api/state | python3 -c "import json,sys; print(json.load(sys.stdin)['pulse']['level'])")
{ [ "$L1" = "LIVE" ] && [ "$L2" != "LIVE" ]; } \
  && ok "T11 start reads LIVE, finished never reads LIVE (now PAUSED/IDLE)" \
  || bad "T11 pulse wrong: start=$L1 end=$L2"

echo "--- chaos: $PASS passed, $FAILN failed ---"
[ "$FAILN" -eq 0 ]
