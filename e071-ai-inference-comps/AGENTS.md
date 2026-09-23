# e071 — AI Inference Comps (P/S, P/E, FDV/S, PEG + venues, all numeric)

Live comparables for the AI-inference coin universe from 3 X threads
(2026-09-19/21): `@Shawred0` tier list, `@sal_ash_` RH-chain scan (11 names
>$100k), `@entyper` SQUIRE/Pod deep-dive. ~21 unique assets, Solana + Base +
RH chain + majors (TAO, VVV).

## Inherits
- [../e000-fundamentals/TABLE_FIRST.md](../e000-fundamentals/TABLE_FIRST.md) — table-first rule + table_check.py
- [../e068-tablelib/AGENTS.md](../e068-tablelib/AGENTS.md) — tables via tablelib (no hand-rolled HTML)

## Objective: the most complete taker/maker decision table for AI-inference tokens

Consumers (human or agent) decide per venue and side from numbers alone:
- **Taker** (buy/sell now): `taker_fee_bps` + `slip_1k/10k_bps` at size + `trader_depth`
  + `volume_24h` on each `venues` row, split by `venue_type` (amm/clob/rfq).
- **Maker/LP** (quote or provide depth): `lp_apr_proxy_pct` on deployed depth +
  `lp_turnover` + `vol_to_liq` + drawdown context (`drop_from_ath`, `rise_from_siglow`).
- Token-level comps (P/S, FDV/S, shares, supply, unlocks) pick *what*; venues pick *where*.

## Rule: every cell numeric or numeric list. No prose in cells.

- Main table = one row per token, one fact per column, numbers as numbers.
- "Best venue to trade / to LP" is NEVER a name in a cell. It is a
  separate `venues` table: one row per (token, venue) with
  `fee_bps`, `spread_bps`, `depth_2pct_usd`, `volume_24h_usd`,
  `liquidity_usd`, `trades_24h`, `lp_score`, `trader_score`. Best = max/min
  over scores, computed, not asserted.
- Same for unlocks / supply events / history: separate tables, epoch dates,
  numeric amounts. The main row only carries aggregates
  (`unlock_next_ts`, `unlock_next_pct_float`, `supply_minted_pct`, ...).

## Pipeline (keyless, cron-friendly)

- `bin/refresh.sh` — ONLY blessed refresh: fetch → comps → venues → inject → version.
- `bin/fetch.py` — DexScreener (solana/base contracts) + CoinGecko public
  (majors: TAO/VVV/ROUTER/DOT) + tweet-seed quotes for RH-chain names not on
  either feed yet. All responses cached in `data/`.
- `bin/comps.py` — pure math from cache: P/S, P/E, FDV/S, PEG-style,
  market_share, ATH/ATL draws + dates, sig-low (see below), supply
  mint/burn/net, TVL/S, sparklines. Never fetches.
- `output/` — `comps.json`, `comps.csv`, `venues.json`, `unlocks.json`,
  `version.json`, `index.html` (SSR via tablelib, real `<tr>` rows).
- Page polls `comps.json` + `version.json` every 60s and re-renders the
  badge; `refresh.sh` via cron keeps data fresh. Freshness badge shows
  OLDEST `through` (STALE_MASK rule).

## Significant-low definition (deterministic, coded in comps.py)

Daily (1d) closes, sequence: initial_price → ATL → ATH → sig_low → current.
- `sig_low` = lowest daily close AFTER `ath_ts` and at least 7d before now,
  with drawdown ≥20% from ATH (`(ath-sig_low)/ath >= 0.20`). If no post-ATH
  close meets the 20% cut, `sig_low = lowest close after ath_ts`, flagged
  `sig_low_weak=1`. All fields numeric + epoch dates; `*_pct` as floats.

## Status (2026-09-22)

- v1: universe locked (22 rows), all rows live, stale=0 everywhere.
  RH chain resolved as DexScreener/GeckoTerminal `robinhood` (Uniswap v4):
  ORBIO/MANY/CEREBRO/SABLE kept their 0x mints; ARIA, DARK, FAB, DAM, ACU,
  CEST, ASKR contracts resolved via DexScreener search 2026-09-22 (see
  `universe.json` notes; DARK=Darkwoods and DAM=Modam need a thread-side
  re-verify; CEST has a ~10x smaller secondary pool). CREDIT relisted live
  on pumpswap ($2.2k mcap). 18 venue rows. GeckoTerminal day-OHLCV fills
  ATH/ATL/spark/supply/born for all DEX rows; sig-low stays null where
  post-ATH history is <7d old (rule working as coded, not missing data).
- Next: per-venue spread/depth from pool books, inference-revenue feeds per
  project (tokens_processed, credit mint/burn) → real P/S instead of proxy.
- v2 (2026-09-22): majors age filled from curated genesis_date (TAO
  2021-01-09, VVV 2025-01-27, DOT 2020-05-26; CG genesis_date is null;
  ROUTER stays null — uncertain row). New `cg`/`cmc` link columns so majors
  have external review (slugs verified). Page now has tabs: Comps | Venues
  (18 rows) | Sources (13-entry directory: 10 live feeds, Dune +
  explorers + vesting docs marked planned).
- v3 (2026-09-22): quote caches TTL 3h -> 15min so the 15min cron really
  refreshes prices (detail/history keep long TTL). Per-row website/X/
  Telegram/Discord links (CG detail for majors, DexScreener info for DEX
  rows; site 22/22, X 21/22). CG page links for all GT-mapped DEX tokens
  (16/22); CMC only where listings exist (5/22: 4 majors + ORBIO — rest
  unlisted, verified via CG search + CMC 404s). `through` label -> latest
  sync. Frozen panes (sticky title row + first column) via tablelib.
- v4 (2026-09-23): ROUTER/DOT collision resolved via X bios — ROUTER =
  @SolRouterAI solana `6SjVTj1VGwFSXn7wEjwFm77LvACeTqB7sQUebYKX8Ds5`
  (Solrouter, solrouter.com), DOT = @usedotai base
  `0x23A2847d772803f9EFC64B4277b782b06296FE51` (Dot, usedot.xyz).
  Both now DEX rows (DexScreener verified); majors shrink to TAO/VVV.
  No uncertain rows left.
- v5 (2026-09-23): CG/CMC link sweep (contract-verified per token).
  CG 16/22: DOT `dot` is the Dot listing (base contract + usedot.xyz
  match), NOT Polkadot — earlier block removed. Unlisted: MINI, CEST
  (CG cestus-network tracks secondary mint 0x1258..., not ours), DARK,
  AILE, CREDIT, ACU. CMC: only TAO/VVV/ORBIO listed — 19 microcaps
  verified unlisted (near-misses mini/credit/sable-finance/aria-ai
  rejected by contract). Nulls stay null, never guessed.
  Collateral: `ORBIO.b` relabeled `DOLPHIN` — DexScreener/GT/CG unanimous
  the base mint is Dolphin/POD (dphn.ai), not an Orbio leg.
