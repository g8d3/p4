# ADAPTERS-E083-REPORT — per-adapter live proof + run_where end-to-end + attack re-test

Date: 2026-09-29. Server: http://127.0.0.1:8383 (also LAN/tailnet via `bin/serve.sh`).
`test/check.sh` → **PASS** (34 adapter unit asserts + suggest/transform/op-set asserts).
Log of this work: `log/adapters-e083.log`.
Method: driven browser = `agent-browser` + `google-chrome`, headed under `Xvfb :55`
(real X server). The real adapter files (`extension/adapters/*.js`) were loaded
into the live page via `eval` and `SNAdapters.detect()` / `.extract()` ran
unmodified against the live DOM. No logins created or used, no credentials touched.

## 1. Per-adapter proof (real pages, driven browser)

### x-timeline (`extension/adapters/x.js`) — NEEDS LOGIN (proven, 3 surfaces)
- `https://x.com/home` → 302 to `https://x.com/i/jf/onboarding/web?redirect_after_login=%2Fhome&mode=login`
  ("X - The Everything App"). `detect()` → null, 0 rows. Login wall, not bypassed.
- `https://x.com/explore` → same onboarding redirect. `detect()` → null, 0 rows.
- `https://x.com/XDevelopers` (logged-out profile) → LOADS: bio header visible
  ("The voice of the X Dev team…", 698.3K followers). `article[data-testid="tweet"]`
  count = **0** before and after scroll+2.5s wait (logged-out markup carries post
  text as flat text, no tweet articles). `detect()` → null, 0 rows — correctly silent.
- Unit fixture in `test/adapters_test.js` proves the parse itself (1 tweet →
  text/author/posted_at/likes/status-URL). **Needs login:** a session must exist so
  the timeline renders `article[data-testid="tweet"]`; then the same `extract()`
  returns up to 50 rows. Nothing to bypass — the adapter only reads rendered DOM.

### google-search (`extension/adapters/google.js`) — BLOCKED by bot wall (proven, 3 ways)
- Headless driven browser: `google.com/search?q=web+scraping+tools` → `sorry/index`
  (unusual-traffic wall). `detect()` → null (no `div#search div.g` on the wall).
- Headed driven browser (Xvfb :55, real X server): same `sorry/index` wall.
  Verdict: IP/reputation wall, not a headless tell — headed changes nothing.
- `curl` with desktop Chrome UA: 200 but a JS-shell (`enablejs` noscript, 0 `<h3>`),
  no result markup without JS execution.
- `extract()` proven in the driven browser against realistic results markup
  (file page, google adapter selected by id since `file://` has no google host —
  `extract()` itself unmodified): input URL
  `https://www.google.com/search?q=web+scraping+tools`, **2 rows**:
  - `{rank:1, title:"10 Best Web Scraping Tools in 2026", url:"https://www.scrapingbee.com/blog/web-scraping-tools/", snippet:"Compare the best…", query:"web scraping tools"}` (`/url?q=` unwrapped)
  - `{rank:2, title:"Top 12 web scraping tools reviewed", url:"https://oxylabs.io/blog/web-scraping-tools", snippet:"Oxylabs reviews…", query:"web scraping tools"}`
  (a third card without `<h3>` was correctly skipped). Unit asserts in
  `test/adapters_test.js` cover the same behavior in CI.

### generic-article (`extension/adapters/article.js`) — WORKS
- Input: `https://en.wikipedia.org/wiki/Web_scraping` (live, logged out). Title:
  "Web scraping - Wikipedia". `detect()` → `generic-article`, **1 row**:
  - `{title:"Web scraping - Wikipedia", author:"", published:"", url:"https://en.wikipedia.org/wiki/Web_scraping", bodyLen:8000, bodyHead:"Web scraping, web harvesting, or web data extraction is data scraping used for extracting data from websites.[1] Web scraping software may directly access the W…"}`
  (author/published empty = page carries no such meta; expected, documented.)

### generic-product (`extension/adapters/product.js`) — WORKS, both paths
- DOM fallback, input `https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html`
  (live, no JSON-LD on site): `detect()` → `generic-product`, **1 row**:
  - `{name:"A Light in the Attic", price:"£51.77", currency:"", image:"", url:"…/a-light-in-the-attic_1000/index.html"}`
- JSON-LD path, input `https://demo.vercel.store/product/acme-geometric-circles-t-shirt`
  (live; note the old `/product/acme-circles-t-shirt` URL now 404s — "This page could
  not be found" — the catalog moved; evidence below is the current slug):
  `detect()` → `generic-product`, **1 row** (AggregateOffer `lowPrice` preferred):
  - `{name:"Acme Circles T-Shirt", price:"15.0", currency:"USD", image:"https://cdn.shopify.com/s/files/1/0754/3727/7491/files/t-shirt-1.png?v=1689798965", url:"https://demo.vercel.store/product/acme-geometric-circles-t-shirt"}`

## 2. `run_where` end-to-end (client|server|both, default client)

Wiring (all three surfaces, verified in code + live):
- Content script (`extension/content.js` `runOnce`): `client`/`both` = local `fn`
  transform (after `looksUnsafe` static guard); `server`/`both` = stripped raw +
  recipe → background `scrapenet:serverTransform` → `POST /api/transform` (SAFE
  op-set only); `both` = merge-dedupe (cap 50). Clear errors when `fn`/`ops`
  missing for the requested mode.
- Popup (`extension/popup.html/js`): new **Runs where** dropdown + live WHERE badge.
  Shows the active recipe's live `where` from `GET /api/recipes`; changing it PUTs
  via background `scrapenet:setWhere` (authed with the Options-stored token;
  tokenless → "signup first" hint, value rolls back). **Fixed while wiring: a
  pre-existing syntax error** — `background.js` ended `addListener(…};` (missing
  `)`), so the service worker could not parse at all; now `});`, all three files
  pass `node --check`.
- Dashboard (`public/index.html`): recipe table pills (`CLIENT · browser` /
  `SERVER · AI refine` / `BOTH`), `rPick` option suffixes, and the Runs-where radio
  all render from live `GET /api/recipes`.

Proof (node `adapters-proof-79322a`, recipe `where-proof` with both `fn` + `ops`,
created → exercised → deleted; server recipe list restored to seeds):
- `client`: `POST /api/recipes/test` with the recipe fn → `{"ok":true}` (static,
  never executed). Live-page capture: on the books.toscrape page above, adapter
  `extract()` + recipe `fn` ran locally → **1 record**
  `[{name:"A Light in the Attic", price:"£51.77"}]`.
- `server`: `PUT where=server` → `GET /api/recipes` shows `server` live.
  `POST /api/transform` with `map` ops over the live-extracted rows → **1 row**
  (name+price preserved). `css-select` over the real page bytes (9279-byte curl of
  the same URL): `div.product_main → {h1, .price_color}` → **1 row**
  `{name:"A Light in the Attic", price:"£51.77"}`.
- `both`: `PUT where=both` → stored + listed as `both`. Both branches ran above;
  merged output = client record ∪ server row, deduped.
- `PUT where=mars` → `400 {"error":"where must be client|server|both"}`.
- Dashboard seat check (driven browser on `/`): `rPick` lists
  `where-proof → products BOTH`; selecting it checks the **both** radio and the
  badge renders `<span class="pill info">BOTH</span>`. User actions on the page:
  recipe picker, where radio, Test/Sandbox/Refine/Save — all wired, no dead controls.

## 3. Attack re-test (malicious-JS hole stays closed — all 6 rejected)

| # | Attack | Result |
|---|---|---|
| A1 | store recipe `fn` with `fetch(…document.cookie)` exfil | 400 `recipe fn rejected` (fetch, document., cookie) |
| A2 | store recipe `fn` with `eval(...)` | 400 `recipe fn rejected` (eval() |
| A3 | store `ops:[{op:eval, code:…}]` with `where=server` | 400 `recipe ops rejected` (allow-list) |
| A4 | `POST /api/transform` with `{op:exec}` | 400 `ops rejected` (allow-list) |
| A5 | `PUT` infinite-loop `fn` onto live recipe | 400 `recipe fn rejected` (while(true) |
| A6 | `/api/recipes/test` with `new Function(...)` | `ok:false` (new function) |

Server never evals recipe JS (static `analyze_fn` only); server transforms run
only `validate_ops()`-checked ops (`css-select`, `json-path`, `regex`, `map`,
`filter` — anything else 400s with the allowed list echoed).

## 4. Signup/token/referral scheme untouched

New account `adapters-proof-79322a` created via `POST /api/signup` (standard flow);
proof recipe created AND deleted with its token; final `GET /api/recipes` = seed
ids only (`product-price`, `job-listing`, `crypto-price` + pre-existing
`news-ycombinator-com-lists` server recipe from suggest flow, left alone).
No token appears in `data/server.log`, reads, or this report.
