#!/bin/bash
# Test: Firefox (baseline) via Playwright
set -euo pipefail

BROWSER="Firefox"
RESULT_FILE="output/firefox-result.json"
mkdir -p output

echo "=== $BROWSER: starting test ==="

timeout 60 python3 << 'PYEOF' 2>&1
import json, time, sys

RESULT_FILE = "output/firefox-result.json"
result = {"browser": "Firefox", "captcha": None, "search": None, "authenticated": None, "error": None}

try:
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
    browser = pw.firefox.launch(headless=True)
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

    if "sign out" in body_text or "signout" in body_text:
        result["authenticated"] = True
    else:
        result["authenticated"] = False

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
