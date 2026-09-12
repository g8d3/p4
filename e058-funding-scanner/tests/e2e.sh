#!/bin/bash
# e058 rung-3 e2e: verifies root UI, /api/table shape (live data), /api/status freshness, secret-clean. Exit nonzero on any failure.
# Usage: tests/e2e.sh [base_url]   (default http://100.102.52.59:8320)
BASE="${1:-http://100.102.52.59:8320}"
fail() { echo "E2E FAIL: $1"; exit 1; }

code=$(timeout 15 curl -s -m 10 -o /tmp/e58_root.html -w "%{http_code}" "$BASE/") || fail "root unreachable"
[ "$code" = "200" ] || fail "root http=$code"
grep -qi "funding scanner" /tmp/e58_root.html || fail "page missing title"

timeout 15 curl -s -m 15 "$BASE/api/table" -o /tmp/e58_table.json || fail "api/table unreachable"
python3 - <<'EOF' || fail "api/table shape bad"
import json
d = json.load(open("/tmp/e58_table.json"))
rows = d.get("rows")
assert isinstance(rows, list) and len(rows) > 0, "empty rows"
r0 = rows[0]
for k in ("coin", "apy", "spread_bps", "n_legs"):
    assert k in r0, f"missing {k}"
assert d.get("count", len(rows)) > 0, "count bad"
print(f"table ok: {len(rows)} rows, top={r0['coin']} apy={r0['apy']}")
EOF

timeout 15 curl -s -m 15 "$BASE/api/status" -o /tmp/e58_status.json || fail "api/status unreachable"
python3 - <<'EOF' || fail "api/status shape/freshness bad"
import json, datetime
d = json.load(open("/tmp/e58_status.json"))
snaps = d.get("snapshots")
assert isinstance(snaps, list) and len(snaps) > 0, "no snapshots"
last = snaps[-1]["ts"]
ts = datetime.datetime.fromisoformat(last.replace("Z", "+00:00"))
age_min = (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds() / 60
assert age_min < 120, f"data stale: last snapshot {last} ({age_min:.0f} min ago)"
print(f"status ok: {len(snaps)} snapshots, coins={d.get('coins')}, last={last} ({age_min:.0f} min ago)")
EOF

# fail-closed on secrets: served files must not contain keys/tokens
grep -riE "sk-|api[_-]?key\s*[:=]\s*['\"][a-z0-9]{8}|-----BEGIN .*PRIVATE KEY" /tmp/e58_root.html /tmp/e58_table.json 2>/dev/null && fail "possible secret in served content"

echo "E2E PASS ($BASE)"
