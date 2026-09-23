# e071 data dictionary — every cell numeric, every prose claim decomposed

## Main table `comps.json` / `comps.csv` (one row per token, 41 atomic columns)

| Your metric | Column(s) (all numeric) | Source today → target |
|---|---|---|
| Price to sales | `p_sales` = mcap/sales_ann | SQUIRE live (1100 SOL × SOLpx); others null until per-project revenue feed |
| Price to earnings | `p_earnings` = mcap/earnings_ann | null v0 (needs protocol-vs-holder split per project) |
| FDV to sales | `fdv_to_sales` | same sales proxy as P/S |
| PEG | `peg_proxy` = P/S ÷ revenue_growth_30d_pct | null v0 except where growth exists; formula locked |
| Comparables | whole table + `mcap_share_pct`, `mcap_to_vol_24h` | live |
| Capital share (NOT dominance) | `mcap_share_pct` = mcap ÷ universe mcap × 100 | live |
| Trader-attention share | `volume_share_pct` = vol24h ÷ universe vol24h × 100 | live |
| Depth share | `liquidity_share_pct` = liq ÷ universe liq × 100 | live |
| True market share | `sales_share_pct` = inference revenue ÷ universe revenue | null until revenue feeds land |
| Product dominance | `usage_share_pct` = tokens/calls ÷ universe total | null until usage feeds land (SQUIRE: 1.5B tokens, 23k payments) |
| Taker cost (per venue) | `taker_fee_bps` (static schedule; `fee_variable`=1 where dynamic, never faked) + `slip_1k/10k_bps` CPMM impact proxy | live |
| Maker economics (per venue) | `lp_apr_proxy_pct` = vol×fee/liq×365 + `lp_turnover` | live where fee known |
| Venue kind | `venue_type` = amm/clob/rfq | short code (routing, not prose) |
| Token age | `age_days` = days since oldest pool creation (`born_ts` epoch); DEX rows from pairCreatedAt, majors from curated `genesis_date` in universe.json (CG genesis_date is null) | live for all rows except ROUTER (uncertain row, no fabrication) |
| DEX review | `dex_url` → DexScreener pair page (first pool; majors null) | link column, opens new tab |
| External review | `gmgn_url` → gmgn.ai token page (sol/base mints only); `coingecko_url` + `cmc_url` → CoinGecko/CoinMarketCap pages (majors; slugs verified 2026-09-22) | link columns, open new tab |
| Project links | `site_url` (first website), `x_url`, `tg_url`, `discord_url` → per-row homepage + socials (majors from CoinGecko detail, DEX rows from DexScreener pair info; null where the feed lists none — never guessed) | link columns, open new tab |
| Freshness | `through` (label: latest sync) = date the row's numbers were last refreshed from the feeds; page badge uses the oldest one | date column |
| % drop ATH→now | `drop_from_ath_pct` | CG majors live; microcaps null until GeckoTerminal day-OHLCV lands |
| ATH date | `ath_ts` (epoch) | same |
| % rise ATL→now | `rise_from_atl_pct` | same |
| ATL date | `atl_ts` (epoch) | same |
| % rise sig-low→now | `rise_from_siglow_pct` | majors weak-proxy (atl-if-post-ath, weak=1); full 1d-candle algo coded |
| Sig-low date | `sig_low_ts` (epoch) + `sig_low_weak` (0/1) | deterministic rule in AGENTS.md |
| % minted | `supply_minted_pct` | CG totals where available |
| % burned | `supply_burned_pct` | null v0 (needs mint/burn event feed) |
| % net supply change | `supply_net_pct`, `circ_pct_of_max`, `fdv_to_mcap` | live where CG gives max/total |
| Next unlock | `unlock_next_ts` + `unlock_next_pct` | null v0; `unlocks.json` rows schema ready |
| TVL to sales | `tvl_to_sales` | null v0 (no TVL feed for inference credits yet) |
| Liquidity over time + exchange | `liquidity_usd` + `price_hist_30d` spark + `venues.json` rows | snapshot live; history per-pool next |
| Volume over time + exchange | `volume_24h_usd`, `volume_ann_proxy_usd`, venues rows | snapshot live |
| Best venue to LP | NOT a cell → `venues.json`: `lp_turnover` = vol/liq (max wins) | live ranking; `fee_bps` lands with pool-book feed |
| Best venue to trade | NOT a cell → `venues.json`: `trader_depth` = liquidity (max wins) | live ranking; `spread_bps`+`depth_2pct_usd` next |
| Trend in one cell? | sparklines only (`price_hist_30d` list), never mixed strings | TABLE_FIRST atomic rule |

## Venues table `venues.json` (one row per token×pool — the numeric breakup you asked for)

`volume_24h_usd`, `liquidity_usd`, `trades_24h`, `buys_24h`, `sells_24h`,
`fee_bps` (v1), `spread_bps` (v1), `depth_2pct_usd` (v1),
`lp_turnover` (=vol/liq → LP wants HIGH), `trader_depth` (=liq → trader wants HIGH depth + LOW fee/spread).
Best = argmax/argmin over scores, computed in the open, never a name typed by hand.

## Auto-update

- `bin/refresh.sh` (fetch→comps→inject→version) is the only writer; cron every 3h.
- Page shows `LIVE <as_of>` + `oldest-through` (fail-closed STALE_MASK rule), a server-time clock (HH:MM:SS in the viewer's local timezone + tz name, offset-calibrated from `server_ts` each poll, UTC in tooltip, proving connectivity), and polls `comps.json` every 30s: only changed cells are patched in place (green flash = up, red = down, blue = other) with an `updated HH:MM:SS · N cells flashed` receipt — never a full reload.
- API: `output/comps.json`, `venues.json`, `unlocks.json`, `comps.csv`, `version.json` — same files the page renders, so page and API can never drift.
