# MAKEITREAL-2 REPORT — honest counters (test/agent exhaust out of public counts, 2026-09-30)

`bash test/check.sh` → **PASS** (extended with 8 honest-counter asserts, all observed passing).
Log of this work: `log/makeitreal.log` (appended: BEFORE/AFTER curl tables, retro-flag transcript).
Server restarted twice via `bin/serve.sh` from exact `ss -tlnp` PID (1568601 → 1591771 → 1592696).

## Problem (live, confirmed before the fix)

Public counters mixed agent exhaust with real data: `/api/records?dataset=product-prices`
returned **225 rows** of test junk, `/api/public/product-prices` served a **224-row**
snapshot of it, `/api/ideas?dataset=product-prices` claimed `rows: 225`, and
`/api/last-capture` showcased test node `check-bot-ccdbbf` as the product proof.
(Earnings/leaderboard/growth-stats were already honest — old patterns covered the
record node_ids; the junk lived in records/public/publish/ideas/last-capture/brief.)

## Fix

1. **Default-honest reads + `?include_test=1` audit toggle everywhere.**
   `/api/records`, `/api/public/<ds>`, `/api/ideas` (GET), `/api/last-capture`,
   `/api/last-payout`, `/dataset/<id>` pages, and `/api/brief` now exclude
   test/agent rows by default and reveal them with `?include_test=1` (rows carry
   `test:true`). Verified the toggle pre-existed on earnings/leaderboard/growth-stats/
   published/funnel/gaps/businesses; added it where missing (the six above).
   `?agent` sessions: `/api/events` already stamps `synthetic:true` for
   agent-tagged browsers; `growth_stats` visits and `brief` visits now also check
   the `agent` field explicitly (defense in depth for legacy rows).
2. **Retro-flag.** `needs.json:test_node_patterns` extended with `check-*`,
   `growth-*`, `adapters-*`, `probe-*`, `*-probe` (old patterns kept). One-off pass:
   **70 auth accounts** newly stamped `test:true`; **all 280 record rows** stamped
   `test:true/false` → **269 test / 11 prod**. Prod survivors (must stay public):
   8× `crypto-spot` + 3× `usd-fx`, all `real-collector-10b278` (now 10+3 after a
   scheduled collector tick during the suite). Backups in `/tmp/*.pre-honest`.
   Test-node inventory (by dataset): product-prices 225 (node-check 85,
   ~80× check-bot-*, node-demo-*, node-tester spill), tester-overnight 17
   (node-tester), news-ycombinator-com-lists 20 (adapters-proof*), proof-ds 2
   (bob-proof), product-prices-7daa 3 (check-bot-spawner), crypto-prices 1 +
   job-listings 1 (hands-proof-*).
3. **Snapshots rebuilt honest-only.** `/api/publish` now ships honest rows only
   (+ `test_rows_hidden` meta); all 3 snapshots rebuilt: product-prices
   honest **0** / hidden 225, crypto-spot 10/0, usd-fx 3/0. `/api/public/<ds>`
   404s by default for test-published datasets (with audit hint), serves on
   `?include_test=1`. New ingests stamp `test` at write time.
4. **e082 play-money: no change needed.** `/api/proof` already returns
   `simulated:true` + note, and the board already labels tick spend "simulated"
   next to the number in 5 places (receipt line, budget input, ledger card,
   calm-status, tick detail). Code-verified; e082 server left untouched (out of scope).

## Counters before → after (curl, in log/makeitreal.log)

| Counter | Before | After (default) | After (?include_test=1) |
|---|---|---|---|
| records product-prices | 225 | **0** | 225–231, all test:true |
| public product-prices | 224 rows (HTTP 200) | **404 honest-zero** + audit hint | 200, count 0 + test_rows_hidden |
| public crypto-spot | 8 | 8–10 (collector ticks on) | same (all honest) |
| earnings nodes | real-collector 11 | real-collector 11–13 | 90+ nodes, 280+ rows |
| leaderboard leaders | 0 | 0 | 0 (no referral volume — honest) |
| growth visits/signups | 36 / 0 | 36 / 0, agent beacon adds 0 | signups 77 (test-inclusive) |
| ideas product-prices rows | 225 | **0** | — (audit via GET flag) |
| ideas crypto-spot rows | n/a | 8–10, real fields | same |
| last-capture node | check-bot-* (test) | **real-collector** | Raw Proof test row |
| last-payout equation | real-collector (luck) | **real-collector, 13 rec** | same shape |
| brief headline | 280-row world | **13 rows live on the hub** | — |
| dataset page product-prices | 225-row table | **0 rows + audit link** | 231-row audit table |
| dataset page crypto-spot | real banner | real banner, 10 rows | same |

## Seat check (I opened the pages)

- `/dataset/product-prices`: "0 contributed rows · 0 nodes", audit link, Copy API
  link, Subscribe copy-curl, Install extension, Sign up, Go Pro — every control acts.
- `/dataset/product-prices?include_test=1`: 231-row audit table (Raw Proof/Legacy
  Check/Check Widget visible, flagged context).
- `/dataset/crypto-spot`: REAL DATA banner (coinbase, latest fetch), 10-row sample
  table, copy/subscribe/install/signup all present. No dead page.

## WHAT I STILL DISTRUST

- **Honest zeros look empty, and empty looks broken.** product-prices now 404s on
  the public API and shows "No rows yet" — truthful, but a stranger can't tell
  "no real data yet" from "dead project". The audit hint carries that weight alone.
- **The audit toggle is undiscoverable.** Nothing on the dashboard links
  `?include_test=1`; only dataset pages mention it. An auditor must read this report.
- **`check-*` now matches every future check node by design** — including any
  human who names themselves "check-…". Prod names must avoid the patterns
  (documented in needs.json); no guard rails the signup form.
- **Snapshots no longer contain test rows even for audit.** `/api/public/<ds>?include_test=1`
  un-hides the dataset but serves the honest-only file; full audit lives in
  `/api/records?include_test=1`. Two doors, one truth — confusing.
- **brief/visits honesty rests on the `synthetic` stamp.** Pre-convention event rows
  with agent traffic but no flag would leak into visits; the explicit `agent` check
  covers known shape only.
- **e082 "simulated" verified in code, not live.** Its server wasn't running and
  starting a sibling experiment's server was out of scope; first e082 restart
  should curl `/api/proof` for `simulated:true`.
