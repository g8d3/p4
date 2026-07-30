#!/bin/bash
# Install all dependencies for undetectable browser benchmarks
set -euo pipefail

echo "=== Installing dependencies ==="

# Python packages
echo "--- Installing Python packages ---"
pip3 install undetected-chromedriver 2>&1 | tail -3 || echo "undetected-chromedriver failed"
pip3 install playwright 2>&1 | tail -3 || echo "playwright failed"
pip3 install playwright-stealth 2>&1 | tail -3 || echo "playwright-stealth failed"
pip3 install selenium 2>&1 | tail -3 || echo "selenium failed"

# Install Playwright browsers (chromium only, no need for all)
python3 -m playwright install chromium 2>&1 | tail -3 || echo "playwright install chromium failed"

# Node.js packages
echo "--- Installing Node.js packages ---"
npm install -g puppeteer-extra puppeteer-extra-plugin-stealth 2>&1 | tail -3 || echo "puppeteer-extra failed"

# Create Firefox profile directory
mkdir -p "$HOME/profiles/firefox-main"

# Camoufox: check if installed, otherwise download
CAMOFOX_DIR="/opt/camoufox"
if [ ! -x "$CAMOFOX_DIR/camoufox" ]; then
  echo "--- Camoufox not found, checking if we can download ---"
  echo "Camoufox is a Firefox-based undetectable browser."
  echo "Download from: https://github.com/camoufox/camoufox/releases"
  echo "Or via: curl -L https://github.com/camoufox/camoufox/releases/latest/download/camoufox-linux64.tar.xz | tar xJ -C /opt/"
  echo "Skipping auto-download (requires manual approval)."
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "IMPORTANT: Playwright browsers may need system deps:"
echo "  python3 -m playwright install-deps chromium"
echo ""
