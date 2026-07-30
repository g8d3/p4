#!/bin/bash
# Test: Chrome (baseline) with authenticated profile
set -euo pipefail

BROWSER="Chrome"
RESULT_FILE="output/chrome-result.json"
mkdir -p output

echo "=== $BROWSER: starting test ==="

if ! command -v google-chrome &>/dev/null; then
  echo '{"browser":"Chrome","captcha":null,"search":null,"authenticated":null,"error":"google-chrome not found"}' > "$RESULT_FILE"
  exit 1
fi

# Test via undetected-chromedriver with Chrome + profile
timeout 60 python3 -c "
import json, time, sys, os

RESULT_FILE = '$RESULT_FILE'
result = {'browser': '$BROWSER', 'captcha': None, 'search': None, 'authenticated': None, 'error': None}

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
except ImportError as e:
    result['error'] = f'ImportError: {e}'
    json.dump(result, open(RESULT_FILE, 'w'))
    sys.exit(0)

driver = None
try:
    options = uc.ChromeOptions()
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--window-size=1280,720')
    options.add_argument('--headless=new')

    driver = uc.Chrome(options=options, version_main=150)
    driver.get('https://www.google.com')
    time.sleep(5)

    body_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
    page_url = driver.current_url.lower()

    if 'captcha' in body_text or 'not a robot' in body_text or 'consent.google' in page_url:
        result['captcha'] = True
    else:
        result['captcha'] = False

    if 'sign out' in body_text or 'signout' in body_text:
        result['authenticated'] = True
    else:
        result['authenticated'] = False

    try:
        search_box = driver.find_element(By.NAME, 'q')
        search_box.send_keys('test search')
        search_box.send_keys(Keys.RETURN)
        time.sleep(5)
        results_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
        if 'resultados' in results_text or 'results' in results_text or 'about' in results_text:
            result['search'] = True
        else:
            result['search'] = False
    except Exception:
        result['search'] = False

except Exception as e:
    result['error'] = str(e)
finally:
    if driver:
        try: driver.quit()
        except: pass
    json.dump(result, open(RESULT_FILE, 'w'))
" 2>&1

echo "=== $BROWSER: done ==="
