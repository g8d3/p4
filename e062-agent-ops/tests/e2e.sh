#!/bin/bash
# e062 rung-3 e2e: verifies fleet board root + /api/board JSON shape. Exit nonzero on any failure.
# Usage: tests/e2e.sh [base_url]   (default http://100.102.52.59:8322)
BASE="${1:-http://100.102.52.59:8322}"
fail() { echo "E2E FAIL: $1"; exit 1; }

code=$(curl -s -m 10 -o /tmp/e62_root.html -w "%{http_code}" "$BASE/") || fail "root unreachable"
[ "$code" = "200" ] || fail "root http=$code"
grep -q "fleet board" /tmp/e62_root.html || fail "board missing title"
grep -q "run fleet now" /tmp/e62_root.html || fail "run-fleet button missing"
grep -q 'id=runs' /tmp/e62_root.html || fail "activity runs table missing"
code=$(curl -s -m 10 -o /tmp/e62_runstate.json -w "%{http_code}" "$BASE/api/runstate") || fail "runstate unreachable"
[ "$code" = "200" ] || fail "runstate http=$code"
python3 -c "import json; d=json.load(open('/tmp/e62_runstate.json')); assert d.get('ok') and 'running' in d, 'runstate shape'" || fail "runstate shape bad"
# token fail-closed: wrong/missing token must NOT run, must guide owner to token button
out=$(curl -s -m 10 -X POST "$BASE/api/run" -H 'Content-Type: application/json' -H 'X-Token: wrong' -d '{"scope":"fleet"}') || fail "run API unreachable"
echo "$out" | grep -q '"ok":false' || fail "wrong token not rejected: $out"
echo "$out" | grep -qi 'token button' || fail "wrong-token error lacks guidance: $out"
out=$(curl -s -m 10 -X POST "$BASE/api/run" -H 'Content-Type: application/json' -d '{"scope":"fleet"}') || fail "run API unreachable (no token)"
echo "$out" | grep -q '"ok":false' || fail "missing token not rejected"
echo "token gate ok: wrong/missing token rejected with guidance, no run spawned"

curl -s -m 15 "$BASE/api/board" -o /tmp/e62_board.json || fail "board API unreachable"
python3 - <<'EOF' || fail "board shape bad"
import json
d = json.load(open("/tmp/e62_board.json"))
tracks = d.get("tracks")
assert isinstance(tracks, list) and len(tracks) >= 5, "tracks < 5"
names = {t["track"] for t in tracks}
assert {"e058", "e059", "e060", "e061", "e062"} <= names, f"missing tracks: {names}"
for t in tracks:
    assert "rung" in t and "beat" in t, f"track {t.get('track')} missing rung/beat"
rw = d.get("runway", {})
for k in ("spent", "earned", "left"):
    assert k in rw, f"runway missing {k}"
assert isinstance(d.get("runs"), list), "runs missing"
for r in d["runs"]:
    for k in ("tokens", "tok_s", "cost_usd", "started"):
        assert k in r, f"runs row missing {k}"
print(f"runs ok: {len(d['runs'])} rows with tokens/tok-s/cost")
assert isinstance(d.get("runner"), dict) and "running" in d["runner"], "runner missing"
assert isinstance(d.get("leg_tail"), str), "leg_tail missing"
print(f"board ok: {len(tracks)} tracks, runway left=${rw['left']:.2f}")
EOF
echo "E2E PASS ($BASE)"
