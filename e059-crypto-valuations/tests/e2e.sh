#!/bin/bash
# e059 rung-3 e2e: verifies static site, multiples.json shape, csv, no secrets. Exit nonzero on any failure.
# Usage: tests/e2e.sh [base_url]   (default http://100.102.52.59:8324)
BASE="${1:-http://100.102.52.59:8324}"
fail() { echo "E2E FAIL: $1"; exit 1; }

code=$(timeout 15 curl -s -m 10 -o /tmp/e59_root.html -w "%{http_code}" "$BASE/") || fail "root unreachable"
[ "$code" = "200" ] || fail "root http=$code"
grep -q "crypto multiples" /tmp/e59_root.html || fail "page missing title"

timeout 15 curl -s -m 15 "$BASE/multiples.json" -o /tmp/e59_mult.json || fail "multiples.json unreachable"
python3 - <<'EOF' || fail "multiples shape bad"
import json, datetime
d = json.load(open("/tmp/e59_mult.json"))
protos = d.get("protocols")
assert isinstance(protos, list) and len(protos) > 0, "empty protocols"
assert "as_of" in d, "missing as_of"
p0 = protos[0]
assert isinstance(p0, dict) and len(p0) > 0, "bad proto row"
assert all(p.get("category") for p in protos), "missing category"
assert isinstance(d.get("category_medians"), dict) and d["category_medians"], "missing category_medians"
assert all(p.get("fees_momentum") is not None for p in protos), "missing fees_momentum"
print(f"multiples ok: {len(protos)} protocols, cats={sorted(d['category_medians'])}, as_of={d['as_of']}")
EOF

code=$(timeout 15 curl -s -m 10 -o /tmp/e59_mult.csv -w "%{http_code}" "$BASE/multiples.csv") || fail "csv unreachable"
[ "$code" = "200" ] || fail "csv http=$code"
[ -s /tmp/e59_mult.csv ] || fail "csv empty"

# fail-closed on secrets: served files must not contain keys/tokens
grep -riE "sk-|api[_-]?key\s*[:=]\s*['\"][a-z0-9]{8}|-----BEGIN .*PRIVATE KEY" /tmp/e59_root.html /tmp/e59_mult.json 2>/dev/null && fail "possible secret in served content"

echo "E2E PASS ($BASE)"
