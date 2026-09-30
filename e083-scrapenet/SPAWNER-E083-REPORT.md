# SPAWNER-E083-REPORT — one button, one business (2026-09-29)

Server: http://127.0.0.1:8383 · LAN http://192.168.0.177:8383 · tailnet
**http://100.102.52.59:8383** (live-resolved). `test/check.sh` → **PASS**
(full suite: signup/token, tiers/metering, growth queue + reject/owner
sections, and the new spawner section). Log: `log/spawner-e083.log`.

## What was built (stdlib only, composition — no new primitives)

`POST /api/businesses/spawn {niche | idea_id}` runs the whole chain
server-side, reusing the existing engines (nothing stubbed):
dataset scaffold (seed rows ingested as the caller, same dedupe as
`/api/ingest`) → recipe (`propose_recipe`, the exact builder behind
`POST /api/generate`, fed a 3-card niche sample so kind detection is real)
→ publish (same free-tier dataset cap as `POST /api/publish` — a capped
owner gets 403+upgrade, not a fleet; recipe+seeds roll back) → default tier
(free quota via the shared metering engine + pro upsell from `tiers_cfg`)
→ 7 niche growth posts (same `_fit`/link/`?ref=<owner code>` scheme as the
growth engine, stored on the business record) → owner's referral code.
Guards: strict token auth (the legacy tokenless carve-out does NOT apply —
a business needs a real account to own it), niche ≤120 chars, duplicate
normalized niche → 409 + existing `business_id`, 3 spawns/hour/owner → 429.
`GET /api/businesses` (live stats per business: records counted from
`records.jsonl`, calls from a counter bumped on every served
`GET /api/public/<dataset>`, signups/revenue from live auth/earnings;
test-owned hidden by default, `?include_test=1` audits — same contract as
earnings/leaderboard). `GET /api/businesses/suggest` (3 niches from live
gaps, each with why + first customer + its spawn call).
`DELETE /api/businesses/<id>` (owner-only token): unpublish + snapshot
delete + recipe delete + owner's seed rows delete + 7 posts dequeued.
`needs.json`: `businesses_path`, `business_spawns_path`,
`business_calls_path`, `spawn_max_per_hour` (+ doc). No hardcoded values.

## Spawn transcripts (both demo businesses, then deleted)

Owners (prod accounts, `test:false`): `demo-owner-alpha-fa0b4c`
(code `9E1B4D`), `demo-owner-beta-85bbc5` (code `028AD7`).
SPAWN 1 (niche text `used bike prices in berlin`) →
`biz-used-bike-prices-in-berlin-2ca809`, dataset `used-bike-prices-in-berlin`,
recipe `used-bike-prices-in-berlin-recipe` (kind price, schema
name/price/currency/url), `growth_posts_queued: 7`, `quota_tier: free`.
Public API served 3 seed rows; dataset share page 200 with title;
duplicate re-spawn → **409**; growth post #1 ends with
`?ref=9E1B4D`; metered read returned `X-Quota-Left: 99`.
SPAWN 2 (`idea_id: product-prices:1` = "Niche job board + alerts") →
`biz-product-prices-449dbc`, dataset auto-de-collided to
`product-prices-cb3e` (slug already published — collision handled, not
clobbered). DELETE 1 → `published/recipe/snapshot true, seed_rows 3,
posts 7`; API 404s, recipe gone from `/api/recipes`, dataset page 404s.
DELETE 2 identical. List now holds 0 businesses. Full JSON in
`log/spawner-e083.log`.

## Suggest output (live data, this run)

1. `Price-drop alerts API (crypto-prices)` — crypto-prices has 1 row from
   1 node, no public API. First customer: indie hacker scraping
   crypto-prices wanting rows as a billable API.
2. `Niche job board + alerts (job-listings)` — same thin-dataset shape.
3. `Niche job board + alerts for product-prices` — 81 referral-attributed
   signups prove distribution; product-prices (144 rows) is the demand pool.

## Browser seat proof (agent-browser, real Chromium)

Rendered `public/spawn-card.html` in a harness cloning the calm shell:
verdict `3 live gaps`, 3 cards × exactly one `Spawn this business` button.
Clicked button 1 as `seat-reviewer-f5eef1` → business
`biz-price-drop-alerts-api-crypto-prices-2a2eaa` live in the public list,
card verdict flipped to `live … 7 posts queued`. Screenshot:
`e083-spawn-seat.png`. Seat business deleted afterwards (list back to 0).
Dashboard `/` seat-checked too: signup, install, refresh/filter, test-row,
publish, both proof buttons all live — no dead controls.
`index.html` was NOT edited (calm agent owns it; it rewrote the file
mid-session and its new conventions — details.card + verdict span,
api/post/esc/pill/ev/tok/nid, tNode/tToken — are all matched by the
snippet; no CALM report exists yet so snippet delivery stands).

## INTEGRATION note (10 lines)

1. Paste `public/spawn-card.html` inside `<main>`, after `secStart`.
2. It needs zero new CSS/JS — calm helpers only.
3. Cards load from `GET /api/businesses/suggest` (public).
4. Each card's button posts its niche to `POST /api/businesses/spawn`.
5. Spawn body: `{node_id, token, niche}` from `tNode`/`tToken` inputs.
6. Auth header alternative: `Authorization: Bearer <token>` works too.
7. Buttons stay disabled until `sn_token`+`sn_node` exist (locked pattern).
8. Success renders `api_url` + `public_url` + quota tier verdict-first.
9. Failures (409 duplicate, 429 rate cap, 403 tier cap) render as plain text.
10. To re-list businesses later, `GET /api/businesses` returns live stats.

## WHAT I STILL DISTRUST

- A spawned business with no audience is inventory, not income: 3 seed
  rows, a recipe, and 7 queued posts earn exactly zero until a stranger
  scrapes, subscribes, or pays. The button manufactures supply; demand is
  still the owner's job (same honesty as the growth loop's void-shouting).
- Free tier = 1 dataset means 1 business per owner: the second spawn
  403s with an upsell. Correct per the paywall, but the "fleet" story
  dies at one free business — say so on the card before someone demos two.
- `calls` counts served reads incl. bots (same exempt traffic the paywall
  lets through free) — vanity-adjacent; signups/revenue are the honest columns.
- `signups`/`revenue` attribute to the OWNER, not the business: two
  businesses by one owner share both numbers. Per-business referral codes
  would fix it but signup only resolves owner codes today.
- Seed rows cite example.com: a stranger's first impression is placeholder
  data. First real scrape should replace them; nothing enforces that.
- Concurrent-agent hazard (lived it): the calm agent rewrote `server/app.py`
  + `index.html` + `check.sh` mid-session and restarted :8383 twice; one of
  my `check.sh` runs failed on a parked growth post from their reject test
  mid-flight, then self-healed. Two writers + one port + shared JSON = flaky
  proofs; my spawner code survived intact, but coordinate restarts and never
  run two `check.sh` at once.
- Rate-cap log (`business_spawns.jsonl`) never expires entries and has no
  endpoint to inspect — fine at this volume, audit it before raising the cap.
