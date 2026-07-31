# e020 — Undetectable Browser Benchmark

Benchmark undetectable browsers against Google search with an authenticated session, measuring captcha blocking, search success, and setup complexity.

## Browsers Tested

| # | Browser | Type | Approach |
|---|---------|------|----------|
| 1 | Chrome (baseline) | Full browser | Real profile with Google session |
| 2 | Firefox (baseline) | Full browser | Real profile with Google session |
| 3 | Camoufox | Full browser (Firefox fork) | Anti-fingerprint patches |
| 4 | undetected-chromedriver | Python library | Patches ChromeDriver to avoid detection |
| 5 | Playwright + playwright-stealth | Python library | Stealth patches on Playwright |
| 6 | Puppeteer Extra + stealth-plugin | Node.js library | Stealth patches on Puppeteer |

## Results

| Browser | Captcha | Search | Authenticated | Notes |
|---------|---------|--------|---------------|-------|
| Chrome (main profile) | No | ✅ | ✅ | `$HOME/profiles/chrome-main/Profile 1` |
| Camoufox | No | ✅ | No | Firefox fork, Playwright |
| Chrome | No | ✅ | No | Fresh profile via undetected-chromedriver |
| Firefox | No | ✅ | No | Playwright's bundled Firefox |
| Playwright + stealth | No | ✅ | No | `playwright-stealth` not found as separate pkg |
| Puppeteer Extra + stealth | No | ❌ | No | Search failed, possible bot detection |
| undetected-chromedriver | No | ✅ | No | Chrome 150, headless |

### What the "Authenticated" column means

`Authenticated` tells whether the browser is **logged into a Google account** during the test.

- **Chrome (main profile) = YES**: it used the real profile `chrome-main/Profile 1`, which contains the Google session cookies (SID, APISID, etc.), so it was logged in.
- **All others = NO**: they used **fresh/temporary profiles** (empty), so there was no Google session — they are not failing, they simply start from zero.

This matters because Google is more likely to show captchas to anonymous or unusual sessions. The finding: even logged out (fresh profiles), no browser hit a captcha. Only the real profile was actually authenticated.

Auth detection is **cookie-based** (SID/SAPISID/HSID/APISID/SSID/SIDCC/`__Secure-1PSID`/`__Secure-3PSID`). **NID is excluded** — Google sets it for every visitor, logged in or not.

**Key finding**: Chrome with the main authenticated profile works without captcha and searches successfully. All undetectable browsers also bypass captcha with fresh profiles. Only Puppeteer Extra failed the actual search (possible bot detection despite stealth plugin).

### ⚠️ Risk: reusing the real profile's cookies in other browsers

**Do NOT copy the real profile's cookies into other browsers (Camoufox, Playwright, etc.) to test authentication.** The session cookies would not match the new browser's fingerprint, which Google can interpret as **session theft** and flag the account (bot-marked, possibly locked). If authenticated tests in other browsers are ever needed, use a **throwaway test account**, never the real one.

## Automation Protocols

| Protocol | Browsers | Used by | Notes |
|----------|----------|---------|-------|
| **CDP** (Chrome DevTools Protocol) | Chrome, Chromium, Edge, Firefox | Puppeteer, Playwright (Chrome), CDP clients | Native to Chrome; Firefox implements a subset for compatibility |
| **Marionette** | Firefox | GeckoDriver, Selenium | Firefox's WebDriver protocol; GeckoDriver translates W3C WebDriver commands to Marionette |
| **Juggler** | Firefox | Playwright (Firefox) | Custom protocol developed by Puppeteer team before Firefox had CDP; Camoufox patches it to sandbox Playwright's interactions |
| **WebDriver BiDi** (BiDirectional) | Chrome, Firefox (partial) | Emerging standard | W3C standard designed to replace CDP; bidirectional communication |

## Methodology

1. Launch browser with fresh profile (or authenticated if testing profile-based)
2. Navigate to `https://www.google.com`
3. Check for captcha / bot detection page
4. Perform a search query
5. Check if search results are returned (vs. blocked/captcha)
6. Record: captcha shown? search succeeded? authenticated session present?

## Agents

- `ag-01/` — Run benchmarks, collect results, produce comparison table

## Output

- `ag-01/output/results.csv` — comparison table
- `ag-01/output/summary.md` — human-readable summary
- `ag-01/output/*-result.json` — raw per-browser results

## Test scripts (`ag-01/bin/`)

- `test-chrome-authenticated.sh` — Chrome with the main authenticated profile
- `test-chrome.sh` — Chrome with fresh profile (undetected-chromedriver)
- `test-firefox.sh` — Playwright's bundled Firefox
- `test-camoufox.sh` — Camoufox via Playwright (Firefox channel)
- `test-undetected-chromedriver.py` — undetected-chromedriver
- `test-playwright-stealth.py` — Playwright (+ stealth if available)
- `test-puppeteer-stealth.js` — Puppeteer Extra + stealth plugin
- `run-all.sh` — run the full suite
- `compile-results.py` — aggregate results into table
