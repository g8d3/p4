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
| Camoufox | No | ✅ | No | Firefox fork, Playwright |
| Chrome | No | ✅ | No | Headless via undetected-chromedriver |
| Firefox | No | ✅ | No | Playwright's bundled Firefox |
| Playwright + stealth | No | ✅ | No | `playwright-stealth` not found as separate pkg |
| Puppeteer Extra + stealth | No | ❌ | No | Search failed, possible bot detection |
| undetected-chromedriver | No | ✅ | No | Chrome 150, headless |

All tests used **fresh profiles** (no authenticated Google session). To test with authentication, use the main Chrome profile at `$HOME/profiles/chrome-main/Profile 1` with `--user-data-dir`.

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
