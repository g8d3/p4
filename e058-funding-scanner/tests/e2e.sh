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

# report-config: GET returns schedule + thresholds; POST round-trips a valid patch
timeout 15 curl -s -m 15 "$BASE/api/report-config" -o /tmp/e58_cfg.json || fail "api/report-config unreachable"
python3 - <<'EOF' || fail "api/report-config shape bad"
import json
c = json.load(open("/tmp/e58_cfg.json"))
for k in ("report_hour_utc", "threshold_bps", "last_n", "top_n", "urgent_mult"):
    assert k in c, f"missing {k}"
assert 0 <= c["report_hour_utc"] <= 23, "hour out of range"
print(f"report-config ok: hour={c['report_hour_utc']} thr={c['threshold_bps']} top_n={c['top_n']}")
EOF
code=$(timeout 15 curl -s -m 15 -o /tmp/e58_cfg_post.json -w "%{http_code}" -X POST "$BASE/api/report-config" -H 'Content-Type: application/json' -d '{"top_n":10}') || fail "api/report-config POST unreachable"
[ "$code" = "200" ] || fail "api/report-config POST http=$code"
# invalid patch must fail closed (400, config unchanged)
code=$(timeout 15 curl -s -m 15 -o /dev/null -w "%{http_code}" -X POST "$BASE/api/report-config" -H 'Content-Type: application/json' -d '{"report_hour_utc":99}') || fail "api/report-config bad-POST unreachable"
[ "$code" = "400" ] || fail "api/report-config bad-POST http=$code (want 400)"

# signals history endpoint (may be empty on fresh DB, must be well-shaped)
timeout 15 curl -s -m 15 "$BASE/api/signals?limit=5" -o /tmp/e58_sig.json || fail "api/signals unreachable"
python3 - <<'EOF' || fail "api/signals shape bad"
import json
d = json.load(open("/tmp/e58_sig.json"))
assert isinstance(d.get("rows"), list), "rows not a list"
print(f"signals ok: {d.get('count', 0)} logged")
EOF

# mobile hard rules (owner law): thumb-zone controls, inner-scroll tables,
# one-line summary + expand for config, top persistent card (saved data to work)
for pat in "thumbbar" "twrap" "topcard" "details class=cfg" "loadTop" "Top persistent spreads"; do
  grep -q "$pat" /tmp/e58_root.html || fail "mobile/power pattern missing: $pat"
done
echo "mobile ok: thumbbar + twrap + topcard + cfg-summary live"

timeout 15 curl -s -m 15 "$BASE/api/persistence?threshold_bps=20&last_n=4" -o /tmp/e58_persist.json || fail "api/persistence unreachable"
python3 - <<'EOF' || fail "api/persistence shape bad"
import json
d = json.load(open("/tmp/e58_persist.json"))
rows = d.get("rows")
assert isinstance(rows, list) and len(rows) > 0, "no survivors"
r0 = rows[0]
for k in ("coin", "median_apy", "persist", "long", "short", "verdict", "paper"):
    assert k in r0, f"missing {k}"
print(f"persistence ok: {len(rows)} survivors, top={r0['coin']} med={r0['median_apy']}%")
EOF

# run #28: filter collapses to one line, signal history closed by default,
# copy-slip in thumbbar + topcard (simplify + paper power)
for pat in "copySlip" "fltGo" "f-sum" "copy slip"; do
  grep -q "$pat" /tmp/e58_root.html || fail "run28 pattern missing: $pat"
done
grep -q '<details open>' /tmp/e58_root.html && fail "signal history must ship closed (long-text rule)"
python3 - <<'EOF' || fail "verdict/paper content bad"
import json
rows = json.load(open("/tmp/e58_persist.json"))["rows"]
assert any(r.get("verdict") == "STEADY" for r in rows), "no STEADY verdict"
assert all(r.get("paper", "").startswith("PAPER e058") for r in rows), "paper slip malformed"
print("verdict ok: STEADY present, paper slips well-formed")
EOF

echo "E2E PASS ($BASE)"
