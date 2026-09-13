#!/bin/bash
# e059 rung-3 e2e: verifies static site, multiples.json shape, csv, no secrets. Exit nonzero on any failure.
# Usage: tests/e2e.sh [base_url]   (default http://100.102.52.59:8324)
BASE="${1:-http://100.102.52.59:8324}"
fail() { echo "E2E FAIL: $1"; exit 1; }

code=$(timeout 15 curl -s -m 10 -o /tmp/e59_root.html -w "%{http_code}" "$BASE/") || fail "root unreachable"
[ "$code" = "200" ] || fail "root http=$code"
grep -q "crypto multiples" /tmp/e59_root.html || fail "page missing title"
# mobile hard rules: thumb-zone bar, inner-scroll wrap, 1-line caveats
 grep -q 'id="thumbbar"' /tmp/e59_root.html || fail "no bottom thumbbar"
 grep -q 'position:fixed' /tmp/e59_root.html || fail "thumbbar not fixed-bottom"
 grep -q 'class="twrap"' /tmp/e59_root.html || fail "table not in inner-scroll wrap"
 grep -q '<details>' /tmp/e59_root.html || fail "caveats not collapsed to 1-line summary"
 grep -q 'vs cat' /tmp/e59_root.html || fail "missing vs-category signal"
 grep -q 'cheapbtn' /tmp/e59_root.html || fail "missing cheap-first toggle"
 grep -q 'sales 6wk' /tmp/e59_root.html || fail "missing sales-through-time column"
 grep -q 'simplebtn' /tmp/e59_root.html || fail "missing simple/full view toggle"
 grep -q 'body.simple' /tmp/e59_root.html || fail "simple view CSS missing"
 grep -q 'id="verdict"' /tmp/e59_root.html || fail "missing one-line cheapest verdict"
 grep -q 'id="metasum"' /tmp/e59_root.html || fail "meta jargon not collapsed to 1-line summary"
 grep -q 'copybtn' /tmp/e59_root.html || fail "missing copy-top-3 slip button" 
 grep -q 'copy top 3' /tmp/e59_root.html || fail "copy slip button mislabeled"

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
assert all(p.get("trend_spark") for p in protos), "missing trend_spark (6-week sales trend)"
assert all(isinstance(p.get("p_fees_trend"), list) and len(p["p_fees_trend"]) >= 4 for p in protos), "bad p_fees_trend"
print(f"multiples ok: {len(protos)} protocols, cats={sorted(d['category_medians'])}, as_of={d['as_of']}")
EOF

code=$(timeout 15 curl -s -m 10 -o /tmp/e59_mult.csv -w "%{http_code}" "$BASE/multiples.csv") || fail "csv unreachable"
[ "$code" = "200" ] || fail "csv http=$code"
[ -s /tmp/e59_mult.csv ] || fail "csv empty"

# fail-closed on secrets: served files must not contain keys/tokens
grep -riE "sk-|api[_-]?key\s*[:=]\s*['\"][a-z0-9]{8}|-----BEGIN .*PRIVATE KEY" /tmp/e59_root.html /tmp/e59_mult.json 2>/dev/null && fail "possible secret in served content"

code=$(curl -s -m 10 "$BASE/version.json" -o /tmp/e59_version.json -w "%{http_code}") || fail "version.json unreachable"
[ "$code" = "200" ] || fail "version.json http=$code"
HEAD=$(git log -1 --format=%h -- e059-crypto-valuations 2>/dev/null || echo "?")
grep -q "$HEAD" /tmp/e59_version.json || fail "version.json stale (refresh.sh stamps it)"
echo "E2E PASS ($BASE)"
