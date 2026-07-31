# e020 trail

## 2026-07-30 — Session 1

Created experiment e020 to benchmark undetectable browsers against Google search.

### Setup
- Installed dependencies: undetected-chromedriver, playwright, playwright-stealth, puppeteer-extra + stealth, selenium
- Downloaded Camoufox v152.0.4-beta.28 from daijro/camoufox
- Installed Playwright browsers (chromium, firefox)
- Chrome 150, Firefox 153 (system snap), Playwright Firefox 151

### Results
All 6 browsers tested successfully (no captcha for any):
- Camoufox, Chrome, Firefox, undetected-chromedriver, Playwright+stealth all passed captcha and search
- Puppeteer Extra + stealth passed captcha but search failed (possible detection)
- None had authenticated sessions (fresh profiles)
- Firefox system snap not usable with Selenium/GeckoDriver (snap confinement); used Playwright's bundled Firefox instead
- Camoufox required Playwright (Firefox channel) due to GeckoDriver incompatibility (fork binary not recognized)

### Key finding
All undetectable browsers bypassed Google's captcha in headless mode with fresh profiles. Only Puppeteer Extra failed the actual search (Google may detect the automation layer despite stealth plugin).

## 2026-07-31 — Session 2

Retested with the **main authenticated Chrome profile** (`$HOME/profiles/chrome-main/Profile 1`):
- Confirmed the profile IS logged into Google (auth cookies SID/APISID/HSID/SAPISID/SSID/SIDCC present; accounts.google.com redirects to myaccount.google.com, not ServiceLogin)
- Chrome + main profile: no captcha, search OK, authenticated ✅
- Fixed auth detection in all scripts: now cookie-based instead of text-based ("sign out" text is unreliable)
- Fixed false positives: **NID cookie excluded** (set for every Google visitor, not just logged-in users)
- Added dedicated `test-chrome-authenticated.sh` script
