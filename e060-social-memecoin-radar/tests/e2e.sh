#!/bin/bash
# e060 rung-3 e2e: verifies dashboard, health, rotation JSON shape. Exit nonzero on any failure.
# Usage: tests/e2e.sh [base_url]   (default http://100.102.52.59:8323)
BASE="${1:-http://100.102.52.59:8323}"
fail() { echo "E2E FAIL: $1"; exit 1; }

code=$(curl -s -m 10 -o /tmp/e60_root.html -w "%{http_code}" "$BASE/") || fail "root unreachable"
[ "$code" = "200" ] || fail "root http=$code"
grep -q "rotation radar" /tmp/e60_root.html || fail "dashboard missing title"
grep -q "thumbbar" /tmp/e60_root.html || fail "no bottom thumbbar (mobile thumb zone)"
grep -q 'data-k=movers' /tmp/e60_root.html || fail "thumbbar missing Movers sort"
grep -q '<details>' /tmp/e60_root.html || fail "explainer not collapsed (long-text rule)"
grep -q 'style=float:right' /tmp/e60_root.html && fail "primary control still top-only"
grep -q '<th>pair</th>' /tmp/e60_root.html || fail "table header mislabeled (expected pair, not traders)"
grep -q 'traders</th>' /tmp/e60_root.html && fail "stale traders header still served"
grep -q '%%TOPONE%%\|%%PULSE%%' /tmp/e60_root.html && fail "server card placeholders unreplaced (no first-paint answer)"
grep -q -i "Top now:\|No rotation data" /tmp/e60_root.html || fail "no server-rendered verdict on first paint"
grep -q -i "tokens · sample" /tmp/e60_root.html || fail "no server-rendered data pulse on first paint"
grep -q "grades via live" /tmp/e60_root.html || fail "grade source not surfaced on card (UX law: every number shows its source)"
grep -q "via live" /tmp/e60_root.html || fail "early-move price source not labeled"

health=$(curl -s -m 10 "$BASE/health") || fail "health unreachable"
echo "$health" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('ok') is True and d.get('track')=='e060', d" || fail "health bad: $health"

curl -s -m 20 "$BASE/api/rotation" -o /tmp/e60_rot.json || fail "rotation unreachable"
python3 - <<'EOF' || fail "rotation shape bad"
import json
d = json.load(open("/tmp/e60_rot.json"))
assert isinstance(d.get("rows"), list) and len(d["rows"]) > 0, "empty rows"
assert "stale" in d and "ts" in d, "missing stale/ts"
r0 = d["rows"][0]
for k in ("symbol", "chain", "rotation_score", "heat", "txns_h24", "priceUsd", "token"):
    assert k in r0, f"row missing {k}"
assert isinstance(r0["heat"], (int, float)), "heat not numeric"
print(f"rotation ok: {len(d['rows'])} rows, stale={d['stale']}, heat0={d['rows'][0]['heat']}")
EOF
paper=$(curl -s -m 10 "$BASE/api/paper") || fail "paper unreachable"
echo "$paper" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('ok') is True and 'paper_n' in d, d; assert d.get('grade_src'), 'grade_src missing'; assert (d.get('early') or {}).get('px_src'), 'early px_src missing'; print(f\"paper ok: resolved={d.get('paper_n')} pending-today={d.get('today_logged')} grade_src={d.get('grade_src')}\")" || fail "paper bad: $paper"
out=$(curl -s -m 10 "$BASE/api/version") || fail "version unreachable"
echo "$out" | grep -q '"running"' || fail "version shape bad"
echo "$out" | grep -Eq '"stale": *false' || fail "server STALE - restart after edits"
echo "E2E PASS ($BASE)"
