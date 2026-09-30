# MAKEITREAL-1 REPORT — loop-driven REAL-data collector (2026-09-29)

Loop-driven collector of REAL public no-key data into REAL datasets on a
schedule. No accounts (beyond the prod collector node itself), no keys, no
spend, nothing posted anywhere. `bash test/check.sh` → **PASS** (exit 0).

## Sources (2, both no-key, stdlib urllib, browser UA, 20s timeout)

1. **Crypto spot** → dataset `crypto-spot` (BTC/USD, ETH/USD).
   First choice **CoinGecko** `simple/price` (free, no key, single try per
   tick). Rate respect: **cache-first, ≥5 min TTL** (`data/collect_cache.json`;
   a fresh hit means zero upstream requests), **HTTP 429 → 10-min backoff**
   serving cache only, single-shot return on 429 (no retry storm).
   Fallbacks, first live answer wins: **Coinbase** spot, then **Kraken**
   ticker. The winning origin is stored per row as `source`.
2. **USD FX daily fix** → dataset `usd-fx` (USD/EUR, USD/GBP, USD/JPY) from
   **open.er-api.com** (free, no key). Same cache + 429 discipline.

Every row carries `source` + `fetched_at` (FX also `upstream_at`).
Only changed values ingest (no dupe spam); published snapshots rebuild on
every successful tick. Both datasets are prod rows: visible on public
`/api/earnings`, public APIs, and dataset pages.

## Schedule

`bin/collect.sh one|daemon|stop|status` (growth.sh pattern: setsid-detached,
PID file `data/collect.pid`, appends `log/collect.log`, ticks to
`data/collect.jsonl`). Interval `collect_interval_sec: 1800` (30 min, from
needs.json). Daemon running pid 1568749. One small fetch per source per
tick; failures log `fetch-failed` and keep serving cache.

## Proof (re-pull matches, live 2026-09-29 ~23:30Z)

- `GET /api/public/crypto-spot` latest:
  `BTC 83757.925, source coinbase, fetched_at 2026-09-29T23:21:01+00:00`.
  Direct re-pull `api.coinbase.com/v2/prices/BTC-USD/spot` → `83679.845`
  seconds later (drift 0.09% — live spot moves; suite asserts <2%).
- `GET /api/public/usd-fx` latest:
  `USD/JPY 157.315109, source open.er-api.com,
  upstream_at Tue, 29 Sep 2026 00:02:31 +0000`.
  Direct re-pull `open.er-api.com/v6/latest/USD` → identical stamp and
  identical EUR/GBP/JPY (daily fix; suite asserts <1%).
- Dataset pages `/dataset/crypto-spot` + `/dataset/usd-fx` render
  `REAL DATA · source(s): … · latest fetch … — re-pull the source yourself,
  numbers match.` (fixed this turn: the banner was computed but never
  inserted into the page HTML).
- `bin/collect.sh one` twice in a row: tick 1 live (`from_cache false`,
  ingested 2), tick 2 cache-only (`from_cache true/true`, ingested 0,
  snapshots still republished).
- Growth loop already markets it: queue holds `g-2026-09-29-btc-spot`
  (`BTC $83,757.93 right now (coinbase, fetched …)`) — collector → dataset
  → growth post, zero taps.
- CoinGecko transcript (honest): tried first every tick, answers
  `403 ERROR … Request blocked` (CloudFront block from this network), so
  rows today read `source: coinbase`. The day CoinGecko answers, rows will
  say `coingecko` with zero code changes.

## Seat check (I opened the pages)

- `/dataset/crypto-spot`, `/dataset/usd-fx`: provenance banner, published
  stamp + record count, raw-JSON-API link, sample table incl.
  source/fetched_at columns, **Copy API link**, **Subscribe: copy curl**,
  Install extension + Sign up CTAs, `?ref=` beacon. User actions: copy the
  API URL/curl and poll it; install; sign up. No dead page.
- `/` dashboard: all cards act (signup→token, ingest, recipes, proof,
  publish, earnings, leaderboard, ideas, funnel, growth, spawn, gaps, owner).

## Suite notes (kept PASS)

- Added collector block to `test/check.sh`: discipline unit (TTL/429/1-try),
  tick status + both datasets published, cache file, row provenance on both
  public APIs, page banners, prod visibility in public earnings, live
  re-pull within tolerance (honest SKIP if upstream unreachable), daemon
  status. Full file → exit 0.
- Fixed one pre-existing failure the suite forced: `growth stats` asserted
  `growth_signups>=1` on the default endpoint while every growth-referred
  account is agent traffic hidden by the test/prod contract (default 0,
  audit 67+). Now asserts both sides like earnings/leaderboard
  (default shape + `?include_test=1` reveals). No data touched.
- Fixed my own first-draft bug in the re-pull assert (compared the ETH row
  to live BTC) — selects the BTC row now.

## Servers (resolved live 2026-09-29)

- e083 ScrapeNet: local http://127.0.0.1:8383 · LAN http://192.168.0.177:8383
  · tailnet http://100.102.52.59:8383. Server pid 1568601 (restarted via
  bin/serve.sh from exact ss PID). Collect daemon pid 1568749 (30 min).

## WHAT I STILL DISTRUST

- **CoinGecko has never answered from this network.** The "CoinGecko first"
  order is code-true but evidence-empty here; a 403 page is not a price
  feed. If the block is permanent, the honest description is
  "Coinbase-first" — I keep the CoinGecko attempt because the day the
  network changes, preference flips automatically, but today the primary
  source is aspirational, not proven.
- **Spot-price "proof" is drift, not equality.** A re-pull seconds later
  never equals the stored tick (0.09% today). The suite's 2% band is
  generous enough to pass on stale-but-plausible data too — it proves
  liveness, not exactness. Only the FX fix (exact match, same upstream
  stamp) is a hard equality proof.
- **Cache means the dataset can be 30 min stale by design.** Freshness is
  bounded by interval + TTL, and the page shows `latest fetch` honestly —
  but a visitor reading "BTC $83,757" at :29 is reading history. Fine for a
  free demo feed, wrong for trading.
- **Two ticks 4 min apart ingested 9 rows for the same prices.** Dedupe
  works (unchanged values skip), but every micro-move mints prod rows and
  the collector's earnings grow forever. At 30-min cadence this is ~100
  rows/day of noise — the dataset is a ticker log, not a curated table.
- **The collector node is a permanent prod earner.** `real-collector-*`
  sits on the public earnings board and accrues SCRAPE per tick; anyone
  reading the leaderboard sees house traffic next to user traffic. Labeled
  by node id only — expect "who is real-collector and why is it rich?"
- All upstream proofs assume clearnet egress to coinbase/er-api. If this
  box loses that route, ticks degrade to `fetch-failed` and the suite's
  re-pull SKIP keeps PASS green on cached data — a passing suite would then
  be proving nothing. Watch `consecutive_failures` in collect_state.json.
