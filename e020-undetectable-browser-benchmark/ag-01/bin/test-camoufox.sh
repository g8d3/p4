#!/bin/bash
# Test: Camoufox - Firefox fork with anti-fingerprinting patches
set -euo pipefail

BROWSER="Camoufox"
RESULT_FILE="output/camoufox-result.json"
mkdir -p output

echo "=== $BROWSER: starting test ==="

CAMOFOX_BIN=""
for p in /opt/camoufox/camoufox camoufox ./camoufox ~/.local/bin/camoufox/camoufox; do
  if [ -x "$p" ]; then
    CAMOFOX_BIN="$p"
    break
  fi
done

if [ -z "$CAMOFOX_BIN" ]; then
  echo '{"browser":"Camoufox","captcha":null,"search":null,"authenticated":null,"error":"Camoufox binary not found"}' > "$RESULT_FILE"
  exit 0
fi

echo "Found Camoufox at: $CAMOFOX_BIN"

timeout 60 python3 << 'PYEOF' 2>&1
import json, time, sys

RESULT_FILE = "output/camoufox-result.json"
result = {"browser": "Camoufox", "captcha": None, "search": None, "authenticated": None, "error": None}
CAMOFOX_BIN = "/home/vuos/.local/bin/camoufox/camoufox"

try:
    # Use Playwright with Camoufox binary
    from playwright.sync_api import sync_playwright
except ImportError as e:
    result["error"] = f"playwright not installed: {e}"
    json.dump(result, open(RESULT_FILE, "w"))
    sys.exit(0)

pw = None
browser = None
page = None

try:
    pw = sync_playwright().start()
    browser = pw.firefox.launch(
        headless=True,
        executable_path=CAMOFOX_BIN,
        args=["--headless"],
    )
    context = browser.new_context(no_viewport=True)
    page = context.new_page()
    page.goto("https://www.google.com", wait_until="load", timeout=30000)
    time.sleep(5)

    body_text = page.evaluate("document.body.innerText").lower()
    page_url = page.url.lower()

    if "captcha" in body_text or "not a robot" in body_text or "consent.google" in page_url:
        result["captcha"] = True
    else:
        result["captcha"] = False

    auth_cookies = [c["name"] for c in context.cookies() if c["name"] in ("SID","SAPISID","HSID","SIDCC","SSID","APISID","__Secure-1PSID","__Secure-3PSID")]
    result["authenticated"] = bool(auth_cookies)

    try:
        search_box = page.query_selector("textarea[name='q']") or page.query_selector("input[name='q']")
        if search_box:
            search_box.fill("test search")
            search_box.press("Enter")
            page.wait_for_timeout(5000)
            results_text = page.evaluate("document.body.innerText").lower()
            if "resultados" in results_text or "results" in results_text or "about" in results_text:
                result["search"] = True
            else:
                result["search"] = False
        else:
            result["search"] = False
    except Exception:
        result["search"] = False

except Exception as e:
    result["error"] = str(e)
finally:
    if browser:
        try: browser.close()
        except: pass
    if pw:
        try: pw.stop()
        except: pass
    json.dump(result, open(RESULT_FILE, "w"))
PYEOF

echo "=== $BROWSER: done ==="
