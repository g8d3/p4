#!/usr/bin/env python3
"""Test: undetected-chromedriver"""
import json
import os
import sys
import time

RESULT_FILE = "output/undetected-chromedriver-result.json"
os.makedirs("output", exist_ok=True)

result = {
    "browser": "undetected-chromedriver",
    "captcha": None,
    "search": None,
    "authenticated": None,
    "error": None,
}

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
except ImportError as e:
    result["error"] = f"ImportError: {e}"
    json.dump(result, open(RESULT_FILE, "w"))
    sys.exit(0)

driver = None
try:
    options = uc.ChromeOptions()
    options.binary_location = "/opt/google/chrome/chrome"
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--headless=new")

    driver = uc.Chrome(options=options, version_main=150)
    driver.get("https://www.google.com")
    time.sleep(5)

    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    page_url = driver.current_url.lower()

    # Captcha check
    if "captcha" in body_text or "not a robot" in body_text or "consent.google" in page_url:
        result["captcha"] = True
    else:
        result["captcha"] = False

    # Authenticated check via cookies
    auth_cookies = [c["name"] for c in driver.get_cookies() if c["name"] in ("SID","SAPISID","HSID","SIDCC","SSID","APISID","__Secure-1PSID","__Secure-3PSID")]
    result["authenticated"] = bool(auth_cookies)

    # Try search
    try:
        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys("test search")
        search_box.send_keys(Keys.RETURN)
        time.sleep(5)
        results_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "resultados" in results_text or "results" in results_text or "about" in results_text:
            result["search"] = True
        else:
            result["search"] = False
    except Exception:
        result["search"] = False

except Exception as e:
    result["error"] = str(e)
finally:
    if driver:
        try:
            driver.quit()
        except Exception:
            pass
    json.dump(result, open(RESULT_FILE, "w"))
