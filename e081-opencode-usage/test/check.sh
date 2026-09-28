#!/bin/bash
# Smoke test: script runs, prints all 3 windows, --json is valid.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
fail(){ echo "FAIL: $1"; exit 1; }
OUT=$(bash "$DIR/bin/usage.sh" 2>&1) || fail "usage.sh exit nonzero: $OUT"
echo "$OUT" | grep -q "rolling .*%" || fail "missing rolling: $OUT"
echo "$OUT" | grep -q "weekly .*%" || fail "missing weekly: $OUT"
echo "$OUT" | grep -q "monthly .*%" || fail "missing monthly: $OUT"
bash "$DIR/bin/usage.sh" --json | python3 -c "import json,sys; d=json.load(sys.stdin); u=d['usage']; assert 'rolling' in u and 'weekly' in u and 'monthly' in u, d; print('json OK')" || fail "--json shape"
echo "PASS"
echo "$OUT"
