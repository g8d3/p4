#!/usr/bin/env python3
"""Test: Playwright + playwright-stealth"""
import json
import os
import sys
import time

RESULT_FILE = "output/playwright-stealth-result.json"
os.makedirs("output", exist_ok=True)

result = {
    "browser": "Playwright + stealth",
    "captcha": None,
    "search": None,
    "authenticated": None,
    "error": None,
}

try:
    from playwright.sync_api import sync_playwright
except ImportError as e:
    result["error"] = f"ImportError: {e}"
    json.dump(result, open(RESULT_FILE, "w"))
    sys.exit(0)

try:
    from playwright_stealth import stealth_sync
except ImportError:
    # playwright-stealth may not be installed; run without it
    stealth_available = False
else:
    stealth_available = True

pw = None
browser = None
page = None

try:
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=[
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1280,720",
    ])

    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/150.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()

    if stealth_available:
        stealth_sync(page)

    page.goto("https://www.google.com", wait_until="load", timeout=30000)
    time.sleep(3)

    body_text = page.inner_text("body").lower()
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
            results_text = page.inner_text("body").lower()
            if "resultados" in results_text or "results" in results_text or "about" in results_text:
                result["search"] = True
            else:
                result["search"] = False
        else:
            result["search"] = False
    except Exception:
        result["search"] = False

    result["stealth_available"] = stealth_available

except Exception as e:
    result["error"] = str(e)
finally:
    if browser:
        try:
            browser.close()
        except Exception:
            pass
    if pw:
        try:
            pw.stop()
        except Exception:
            pass
    json.dump(result, open(RESULT_FILE, "w"))
