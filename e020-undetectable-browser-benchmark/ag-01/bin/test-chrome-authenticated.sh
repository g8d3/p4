#!/bin/bash
# Test: Chrome with the main authenticated profile ($HOME/profiles/chrome-main)
set -euo pipefail

BROWSER="Chrome (authenticated profile)"
RESULT_FILE="output/chrome-authenticated-result.json"
mkdir -p output

echo "=== $BROWSER: starting test ==="

if [ ! -d "$HOME/profiles/chrome-main/Profile 1" ]; then
  echo '{"browser":"Chrome (authenticated profile)","captcha":null,"search":null,"authenticated":null,"error":"Main profile not found"}' > "$RESULT_FILE"
  exit 1
fi

timeout 90 python3 -c "
import json, time, sys

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
    options.binary_location = '/opt/google/chrome/chrome'
    options.user_data_dir = '$HOME/profiles/chrome-main'
    options.add_argument('--profile-directory=Profile 1')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--window-size=1280,720')
    options.add_argument('--headless=new')

    driver = uc.Chrome(options=options, version_main=150)
    driver.get('https://www.google.com')
    time.sleep(8)

    body_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
    page_url = driver.current_url.lower()

    if 'captcha' in body_text or 'not a robot' in body_text or 'consent.google' in page_url:
        result['captcha'] = True
    else:
        result['captcha'] = False

    auth_cookies = [c['name'] for c in driver.get_cookies() if c['name'] in ('SID','SAPISID','HSID','SIDCC','SSID','APISID','__Secure-1PSID','__Secure-3PSID')]
    result['authenticated'] = bool(auth_cookies)
    result['auth_cookies'] = auth_cookies

    try:
        search_box = driver.find_element(By.NAME, 'q')
        search_box.send_keys('test search')
        search_box.send_keys(Keys.RETURN)
        time.sleep(8)
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
    print(json.dumps(result))
" 2>&1

echo "=== $BROWSER: done ==="
