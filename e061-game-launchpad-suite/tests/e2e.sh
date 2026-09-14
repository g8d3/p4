#!/bin/bash
# e061 rung-3 e2e: verifies slice demo servable, fail-closed badge, no secrets.
# Usage: tests/e2e.sh [base_url]   (default http://100.102.52.59:8321)
BASE="${1:-http://100.102.52.59:8321}"
fail() { echo "E2E FAIL: $1"; exit 1; }

code=$(curl -s -m 10 -o /tmp/e61_root.html -w "%{http_code}" "$BASE/") || fail "root unreachable"
[ "$code" = "200" ] || fail "root http=$code"
grep -q "Suite Slice" /tmp/e61_root.html || fail "demo missing title"
grep -q 'id="claim" disabled' /tmp/e61_root.html || fail "claim button not fail-closed disabled"
grep -q 'id="game"' /tmp/e61_root.html || fail "game frame missing"
grep -q 'game/' /tmp/e61_root.html || fail "real game embed missing"
grep -q 'e061-win' /tmp/e61_root.html || fail "win bridge listener missing"
grep -q 'thumbbar' /tmp/e61_root.html || fail "thumbbar missing (mobile thumb zone)"
grep -q 'id="btn-win"' /tmp/e61_root.html || fail "win thumb button missing"
grep -q 'id="winlock"' /tmp/e61_root.html || fail "win lock note missing"
grep -q 'winTap' /tmp/e61_root.html || fail "win thumb tap handler missing (dead-tap fix)"
grep -q 'e061-runs' /tmp/e61_root.html || fail "runs/best loop missing"
grep -q 'id="slip"' /tmp/e61_root.html || fail "paper slip block missing"
grep -q 'id="btn-copy"' /tmp/e61_root.html || fail "slip copy button missing"
grep -q 'id="comeback"' /tmp/e61_root.html || fail "comeback code block missing"
grep -q 'redeemComeback' /tmp/e61_root.html || fail "comeback redeem handler missing"
grep -q 'id="pulse"' /tmp/e61_root.html || fail "server pulse line missing"
grep -q 'api/stats' /tmp/e61_root.html || fail "stats fetch missing"
grep -q 'api/visit' /tmp/e61_root.html || fail "visit ping missing"
grep -q 'e061-visits' /tmp/e61_root.html || fail "day-2 visit tracker missing"
grep -q 'id="daybadge"' /tmp/e61_root.html || fail "day badge missing"
grep -q '<summary>Fees:' /tmp/e61_root.html || fail "fees one-line summary missing"
grep -q '<summary>Warning:' /tmp/e61_root.html || fail "stats one-line summary missing"
code=$(curl -s -m 10 -o /dev/null -w "%{http_code}" "$BASE/game/") || fail "game/ unreachable"
[ "$code" = "200" ] || fail "game/ http=$code"
code=$(curl -s -m 10 -o /dev/null -w "%{http_code}" "$BASE/game/assets/hero.png") || fail "game sprite unreachable"
[ "$code" = "200" ] || fail "sprite http=$code"

curl -s -m 10 "$BASE/status.json" -o /tmp/e61_status.json || fail "status.json unreachable"
python3 - <<'EOF' || fail "status.json not fail-closed"
import json
d = json.load(open("/tmp/e61_status.json"))
assert d.get("pair") == "none deployed", d
assert d.get("anvilRunning") is False, d
assert d.get("disableReason"), "missing disableReason"
print(f"status ok: pair={d['pair']} anvil={d['anvilRunning']}")
EOF

code=$(curl -s -m 10 -X POST -H 'Content-Type: application/json' -d '{"cid":"e2e-probe","ev":"visit"}' "$BASE/api/visit" -o /tmp/e61_visit.json -w "%{http_code}") || fail "visit endpoint unreachable"
[ "$code" = "200" ] || fail "visit http=$code"
code=$(curl -s -m 10 -X POST -H 'Content-Type: application/json' -d '{"cid":"","ev":"bogus"}' "$BASE/api/visit" -o /dev/null -w "%{http_code}") || fail "visit bad-input unreachable"
[ "$code" = "400" ] || fail "visit bad-input http=$code (want 400)"
BASE="$BASE" python3 - <<'EOF' || fail "visit/stats api broken"
import json, os, urllib.request
base = os.environ["BASE"]
d = json.load(open("/tmp/e61_visit.json"))
assert d.get("ok") is True, d
s = json.load(urllib.request.urlopen(base + "/api/stats", timeout=10))
assert s["visits"] >= 1 and "day2" in s and "lastAgeMin" in s, s
print(f"stats ok: visits={s['visits']} players={s['players']} day2={s['day2']}")
EOF

# no secrets in served page (static demo must stay key-free)
grep -qiE "sk-|api[_-]?key|mnemonic|private[_-]?key" /tmp/e61_root.html && fail "possible secret in page"
code=$(curl -s -m 10 "$BASE/version.json" -o /tmp/e61_version.json -w "%{http_code}") || fail "version.json unreachable"
[ "$code" = "200" ] || fail "version.json http=$code"
E2E_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HEAD=$(git -C "$E2E_DIR" log -1 --format=%h -- . ':!demo/version.json' 2>/dev/null || echo "?")
[ -z "$HEAD" ] && HEAD="?"
[ "$HEAD" = "?" ] && fail "cannot resolve track HEAD (run from a git checkout)"
grep -q "$HEAD" /tmp/e61_version.json || fail "version.json stale (run bin/version.sh)"
echo "E2E PASS ($BASE)"
