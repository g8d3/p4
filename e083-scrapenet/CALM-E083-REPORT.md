# CALM-E083-REPORT — Spawn card wired, Owner drawer proven (2026-09-29)

Server: http://127.0.0.1:8383 · LAN http://192.168.0.177:8383 · tailnet
**http://100.102.52.59:8383** (resolved live). `test/check.sh` → **PASS**
(incl. 13 new UI asserts). Restart: `bin/serve.sh restart` only
(killed exact PID 1482386 from `ss -tlnp`, started 1496092). Log:
`log/calm-e083.log`.

## What changed (2 files)

- `public/index.html` — pasted ONE Spawn card (`secSpawn`, after Start,
  snippet conventions kept): `suggest→spawn`, 3 niche cards × one
  `Spawn this business` button each (disabled + 🔒 until token), result
  line with **API URL + page URL**, plus a `bizList` live-business table
  (LIVE pill, API/page links, per-row **Delete**, token-gated).
- `test/check.sh` — 13 new asserts: `secSpawn`, spawn-button text,
  `businesses/suggest` + `businesses/spawn` fetch wiring, `bizList`,
  `data-biz-del`, `secOwner`, `oXKey`, `oChannel`, `oFreeCalls`,
  `oProPrice`, `data-act=intent-ok/payout-ok`, suggest==3.
- Owner drawer: **already existed and already covered everything**
  (X paste, dryrun/x_api flip, tier edits, growth OK/Park, intent +
  bonus review) — verified, not rebuilt.

## Cold-browser proofs (agent-browser, real Chromium, cleared storage)

Seat `calm-seat-ana-4b4169` (prod-sounding name so it shows publicly):

1. Suggest renders **3 niches** (`Price-drop alerts API (crypto-prices)`…),
   3 buttons, locked pre-token.
2. Page signup → 3 buttons enabled → **Spawn fires**:
   `live Price-drop alerts API… API: …/api/public/price-drop-alerts-api-crypto-prices
   · page: …/dataset/… · 7 posts queued · tier free`.
3. Business in list with **API + page links**; public API served 3 seed rows.
4. Page **Delete** → `deleted biz-…-69b966 cleaned up`, list empty,
   API 404s, `GET /api/businesses` count 0.
5. Owner unlock via page → X-key paste (field cleared, status `X key set`),
   channel **dryrun→x_api→dryrun** (status confirms each),
   tier **100→111 / $9→$10 live** in `/api/config` then restored,
   dry-run test post `WOULD POST (dryrun)`,
   growth **Park g-2026-10-03-published → OK** (queue back to 1 posted + 6 queued),
   **2 page-made intents → Approve #22** (seat quota bar flips to PRO 10000)
   **+ Reject #23** (22 wait = 24−2 decided). Zero shell for all of it.
6. Secrets: fixture `xbro_page_fixture_2108` + `sk_test_page_fixture_2108`
   appear in **no** GET (`/api/config`, `/brief`, `/owner/status`,
   `/growth/stats`, `/health`), not in POST responses, `secrets.json`
   stays `0600`; both cleared afterwards (status: bearer False, stripe False).

## WHAT I STILL DISTRUST

- **Bonus-payout Approve/Reject is unflippable today**: `payouts_pending`
  is empty (no referrer ≥5.0 SCRAPE), so the buttons never render. Control
  exists, endpoint is suite-covered, but no human has clicked it — first
  real credit will be the first test.
- **Keys can be set but not cleared from the page** (`bSaveX`/`bSaveDeal`
  skip empty fields). Clearing is curl-only; the drawer should grow a
  Clear button before keys rotate.
- Spawn buttons enable via 3s poll after signup — a fast clicker sees
  locked buttons until reload/poll; acceptable, slightly ragged.
- Seat names matching `test_node_patterns` vanish from the public list:
  a reviewer signing up as e.g. `node-demo-*` spawns into the audit
  surface only and thinks the button is broken. The card should say so.
- 22 stale `intents_pending` from past sessions still sit in the owner
  queue — every unlock screams "22 payments wait" at an owner who has
  nothing to do. Stale intents need expiry or a bulk-dismiss.

## 2026-09-29 — per-card refresh isolation (anonymous quota exhausted)

Bug (from e082 HANDS-REPORT distrust #2, live at fix time): anon bucket at
101/100, so browser-UA `GET /api/records` 429s; `api()` resolved the error
body, `loadRecords` threw on `rows.map`, and the sequential `refresh()`
chain died — logged-out visitors saw Data/Friends/Auto-posts/Gaps stuck at
"loading…" with `…` verdicts (proven in headless Chromium, cleared storage).

Fix (`public/index.html` only, server untouched): `api()` now rejects on
HTTP error (status + body attached); new `step(fn)` wraps every `refresh()`
card so one failure never kills the others; `loadRecords` catches 429-quota
into an honest card ("sign in for live records -- free quota is full
(101/100 today, resets …). Your key gets its own quota; the rest of this
page still works.", verdict `Quota full -- sign in`); `loadEarnings` /
`loadPublished` / `loadLeader` / `loadRecipes` / `health` got own fallbacks.
Restart: killed exact PID 1505083 (`ss -tlnp`), `bin/serve.sh` → 1520433.
URLs: http://127.0.0.1:8383 · http://192.168.0.177:8383 ·
http://100.102.52.59:8383. Log: `log/calm-e083.log`.

Proofs: browser-UA curl still 429s with the quota body pre+post (paywall
intact, bots still exempt); logged-out Chromium AFTER shows the honest
records card while growth/gaps/earn/leader/funnel all render live data.
`test/check.sh` → **PASS exit 0** (extended: `api()`-rejects grep, 3×
`step()` greps, quota-message grep, gaps+queue serve while anon throttled,
throwaway-bucket HTTP-429 shape incl. `quota_used`+`upgrade`, token reads
survive anon exhaustion). Two suite races with the live e082-loop daemon
fixed along the way: growth asserts now use the server's `loop_drafts`
accounting / ignore `source==loop` rows, and the hands-draft fixture clears
pending unposted loop drafts (any node token may, server rule) before
posting its own. No blockers — nothing went silent.

[2026-09-30T00:18:47Z] HERO-CLARITY: hero now static money sentence + one Install-extension link + buyer APIs-$9 line.
[2026-09-30T00:18:47Z] Zero JS dependency: curl first paint contains full sentence, no loading placeholders in hero.
[2026-09-30T00:18:47Z] Cold tailnet read: stranger learns browse-normally-get-paid + buyer APIs within first 20 words.
[2026-09-30T00:18:47Z] check.sh read-only FAIL free-tier-publish is server consent rule (sibling area), untouched.
[2026-09-30T00:18:47Z] Old JS ids kept hidden+empty in hero block only; no restart; log at log/hero.log.
