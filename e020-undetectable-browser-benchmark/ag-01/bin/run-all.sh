#!/bin/bash
# Run all undetectable browser benchmarks
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  Undetectable Browser Benchmark Suite"
echo "============================================"
echo ""

# Run each test sequentially
TESTS=(
  "test-chrome.sh"
  "test-firefox.sh"
  "test-undetected-chromedriver.py"
  "test-playwright-stealth.py"
  "test-puppeteer-stealth.js"
  "test-camoufox.sh"
)

for test in "${TESTS[@]}"; do
  if [ -f "$test" ] && [ -x "$test" ]; then
    echo ""
    echo "--- Running: $test ---"
    timeout 90 "$test" 2>&1 || echo "Test failed or timed out: $test"
    echo "--- Done: $test ---"
  else
    echo "Skipping (not found/executable): $test"
  fi
done

echo ""
echo "=== Compiling results ==="
python3 compile-results.py 2>&1 || python3 "$SCRIPT_DIR/../compile-results.py" 2>&1 || echo "compile-results failed"

echo ""
echo "=== Results ==="
cat "$SCRIPT_DIR/../output/results.csv" 2>/dev/null || cat "$SCRIPT_DIR/../output/summary.md" 2>/dev/null || echo "No output files found"
