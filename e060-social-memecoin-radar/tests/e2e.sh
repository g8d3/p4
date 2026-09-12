#!/bin/bash
# e060 rung-3 e2e: verifies dashboard, health, rotation JSON shape. Exit nonzero on any failure.
# Usage: tests/e2e.sh [base_url]   (default http://100.102.52.59:8323)
BASE="${1:-http://100.102.52.59:8323}"
fail() { echo "E2E FAIL: $1"; exit 1; }

code=$(curl -s -m 10 -o /tmp/e60_root.html -w "%{http_code}" "$BASE/") || fail "root unreachable"
[ "$code" = "200" ] || fail "root http=$code"
grep -q "rotation radar" /tmp/e60_root.html || fail "dashboard missing title"

health=$(curl -s -m 10 "$BASE/health") || fail "health unreachable"
echo "$health" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('ok') is True and d.get('track')=='e060', d" || fail "health bad: $health"

curl -s -m 20 "$BASE/api/rotation" -o /tmp/e60_rot.json || fail "rotation unreachable"
python3 - <<'EOF' || fail "rotation shape bad"
import json
d = json.load(open("/tmp/e60_rot.json"))
assert isinstance(d.get("rows"), list) and len(d["rows"]) > 0, "empty rows"
assert "stale" in d and "ts" in d, "missing stale/ts"
r0 = d["rows"][0]
for k in ("symbol", "chain", "rotation_score"):
    assert k in r0, f"row missing {k}"
print(f"rotation ok: {len(d['rows'])} rows, stale={d['stale']}")
EOF
echo "E2E PASS ($BASE)"
