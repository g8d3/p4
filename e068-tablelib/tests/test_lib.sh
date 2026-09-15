#!/bin/bash
# e068 automated test: the verifier IS this library's test suite.
# Tier 1 must PASS and Tier 2 must print zero WARNs on the demo page.
cd "$(dirname "$0")/.." || exit 1
python3 example/build.py || exit 1
OUT=$(python3 ../e000-fundamentals/bin/table_check.py e068-tablelib --served example/index.html)
RC=$?
echo "$OUT"
WARNS=$(echo "$OUT" | grep -c "^WARN")
if [ "$RC" -ne 0 ]; then echo "LIB TEST: Tier 1 FAIL"; exit 1; fi
if [ "$WARNS" -ne 0 ]; then echo "LIB TEST: $WARNS Tier 2 WARN(s) — library must comply by construction"; exit 1; fi
echo "LIB TEST: PASS (Tier 1 ok, 0 WARNs)"
