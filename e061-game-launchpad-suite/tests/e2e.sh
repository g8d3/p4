#!/bin/bash
# e061 rung-3 e2e: verifies slice demo servable, fail-closed badge, no secrets.
# Usage: tests/e2e.sh [base_url]   (default http://100.102.52.59:8321)
BASE="${1:-http://100.102.52.59:8321}"
fail() { echo "E2E FAIL: $1"; exit 1; }

code=$(curl -s -m 10 -o /tmp/e61_root.html -w "%{http_code}" "$BASE/") || fail "root unreachable"
[ "$code" = "200" ] || fail "root http=$code"
grep -q "Suite Slice" /tmp/e61_root.html || fail "demo missing title"
grep -q 'id="claim" disabled' /tmp/e61_root.html || fail "claim button not fail-closed disabled"
grep -q 'id="game"' /tmp/e61_root.html || fail "game canvas missing"

curl -s -m 10 "$BASE/status.json" -o /tmp/e61_status.json || fail "status.json unreachable"
python3 - <<'EOF' || fail "status.json not fail-closed"
import json
d = json.load(open("/tmp/e61_status.json"))
assert d.get("pair") == "none deployed", d
assert d.get("anvilRunning") is False, d
assert d.get("disableReason"), "missing disableReason"
print(f"status ok: pair={d['pair']} anvil={d['anvilRunning']}")
EOF

# no secrets in served page (static demo must stay key-free)
grep -qiE "sk-|api[_-]?key|mnemonic|private[_-]?key" /tmp/e61_root.html && fail "possible secret in page"
echo "E2E PASS ($BASE)"
