# UX-E083-REPORT — action-first overhaul + telemetry

Server: http://127.0.0.1:8383 · LAN http://192.168.0.177:8383 · tailnet
**http://100.102.52.59:8383** (live-resolved, `needs.json:public_url`).
`test/check.sh` → **PASS** (extended: events + funnel + generate + proof asserts).
Log of this work: `log/ux-e083.log`. Signup/token/referral scheme untouched
(same `POST /api/signup` → once-shown token → sha256 0600 → Bearer/token gate).

## Before / after (real browser, agent-browser + screenshots)

BEFORE (`/tmp/e083-before-top.png`): hero was a 4-line paragraph + numbered
text steps; a full-width Install card with 3 verbose steps pushed everything
down; tables were `at|dataset|node|record` with 300-char raw JSON blobs, no
row actions; no proof, no prefill, no WHERE, no telemetry, no funnel.
AFTER (`/tmp/e083-after-hero.png`, `-proof.png`, `-funnel.png`): 2-line hero +
3 buttons above the fold; compact Get-token strip; Live records open, the
rest (`Recipes`, `Proof`, `Publish`, `Earnings`, `Leaderboard`, `Ideas`,
`Stuck users`, `Install`) collapsed `<details>`; every table is
STATUS pill | name | result | expandable details with per-row action buttons.

## Each charge, with proof

1. **Action-first layout.** Hero is now 2 lines
   ("ScrapeNet — turn any website into a paid API." / "Scrape pages you
   visit, publish the data, earn 0.01 SCRAPE per record.") + 3 primary
   buttons above the fold: `Install extension` (zip download), `Publish
   dataset` (opens+scrolls to Publish), `See earnings` (opens+scrolls to
   Earnings). Everything else collapsed. Proof: after-hero screenshot +
   `curl /` contains all three button ids above the first `<details>`.
2. **AI-prefill, never a blank box.** Recipe editor ships prefilled sample
   HTML + `Generate from sample` → `POST /api/generate {html|url}` →
   rule-based kind detection (price/job/crypto/generic signals) fills id,
   name, dataset, fn + one-line explanation; URL mode fetches the page
   server-side (urllib, 10s, 200KB cap, http(s) only); LLM slot documented
   (`llm_available` + `llm_prompt`, same pattern as `/api/refine`). Idea
   cards each carry `Use this idea`: authed → creates the recipe scaffold
   via API + jumps to Publish; tokenless → prefills editor + publish box +
   scrolls to signup. Browser proof: clicked Generate → "PROPOSED (price):
   found 1 price tags + 1 product/card/item blocks"; clicked Use-this-idea
   (authed) → `product-prices-starter` scaffold created (deleted after to
   keep seeds clean). `check.sh` asserts kind=price + fn + 400s.
3. **PROOF buttons.** `Show last capture` → `GET /api/last-capture`
   (newest row, prefers rows carrying `raw`; `POST /api/ingest` accepts
   optional `raw`, extension content+background now forward a raw excerpt)
   renders RAW vs TRANSFORMED side by side + recipe fn. `Show last payout
   math` → `GET /api/last-payout` renders the equation. Browser proof:
   raw→record columns rendered; equation shown verbatim:
   `2 records x 0.01 SCRAPE - 10.0% commission (0.002 SCRAPE) = 0.018 SCRAPE`.
   `check.sh` asserts `has_raw=true`, recipe fn present, equation substrings.
4. **One-click token.** Signup strip: one field + green `Get token` →
   node id + referral code + show-once token in dashed box + `Copy token`
   button; token/node cached for locked buttons. `Ingest`/`Publish`/`Save`
   are disabled with `🔒 Locked — get a token (signup above) to unlock`
   until a token exists, then auto-unlock. Browser proof: signed up as
   `browser-ux-tester-0d9d2f`, copied token, all three buttons flipped
   `disabled=false`. Scheme unchanged (same endpoint, same 401 hints;
   old `check.sh` auth asserts still pass).
5. **Aligned tables everywhere.** Records, recipes, earnings, leaderboard
   all render `STATUS pill | name | result | details▸`. Every row is
   actionable: records → Retest in recipe / Republish / Copy link; recipes
   → Load in editor / Copy id; earnings → Copy node id / View records;
   leaderboard → Copy referral link. Verified in-browser (details expanded,
   buttons clicked: Retest loaded the record into the recipe sample,
   Republish jumped to Publish, Use-idea scaffolded).
6. **Transform location.** Every recipe shows a WHERE badge
   (`CLIENT · browser` / `SERVER · AI refine` / `BOTH`) in the picker and
   the recipes table, plus a per-recipe Client/Server/Both radio switch.
   One-line tradeoff sits next to the switch: "CLIENT = raw page never
   leaves your browser (private, fastest). SERVER = raw is sent to the
   collector for AI refine (smarter transforms, less private). Both = try
   client first, fall back to server." Semantics are real: extension
   branches on `recipe.where` (server mode sends raw untransformed),
   `where` validates `client|server|both` on create+update (400 otherwise),
   seeds default `client`. `check.sh` asserts badge field + bad-where 400
   + `both` roundtrip.

## Telemetry (same schema as e082)

- Client snippet POSTs `/api/events {v:1, session, ts, page, event,
  detail?, ms?}`: `page_view` on load, `click:<button-id>` delegation,
  `download` on zip click, `signup` on success, `proof`+`first_proof_seen`
  on proof render, `js_error` via `window.onerror`, `idle_45s` after 45 s
  with no action. Session id = random hex in `sessionStorage`.
- Server: `data/events.jsonl` (needs.json `events_path`); `GET /api/funnel
  → {views, downloads, signups, publishes, stuck_sessions[]}`
  (publishes from server-truth audit log); dashboard `Stuck users` card
  with pills + stuck session list. No IPs anywhere (never stored).
- Verified: browser session produced `page_view/click/signup/generate/
  proof` events in `events.jsonl`; funnel read `{views:3+, downloads,
  signups, publishes:25, stuck_sessions:['check-sess-2']}` with the active
  browser session correctly NOT stuck; `check.sh` asserts all 7 event
  kinds + 3 validation 400s + funnel keys + stuck attribution.

## Remaining gaps (honest)

- `SERVER` mode sends raw for *refine suggestions* — the collector still
  never executes recipe JS (by design), so "server transform" today means
  AI-assisted, not server-executed. The tradeoff line says exactly this.
- Stuck-session list is raw session ids; no per-session drill-down page.
- `idle_45s` fires once per page load; returning tabs don't re-arm.
- Extension `where=server` path is code-reviewed only — not load-tested on
  a live shop page (needs `chrome://extensions` + human clicks).
- Funnel `publishes` counts audit events (server truth) while the rest
  counts client events — documented, but a purist funnel would use one source.
