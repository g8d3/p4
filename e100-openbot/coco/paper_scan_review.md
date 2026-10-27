# Paper scan review — relative-strength scanner, first live day
By Mango Z · 2026-10-25 22:45 Bogotá (UTC-5). Paper only — no wallets, no keys, no real trades.
Sources: `e101-hummingbot/data/rstrength_flags.csv`, `data/rs_event_flags.csv`, live CoinGecko API (timestamps cited inline). All numbers below come from those files/API responses.

## What the scanner flagged

**Daily scan (rstrength_scan.py, 2026-10-25, `data/rstrength_flags.csv`, 2 rows):**

| Token | Flagged (Bogotá) | Price at flag | 7d / 30d at flag (vs SOL −0.48% / −16.61%) | Price now (CoinGecko `last_updated` 2026-10-25T22:41:51Z) | Change since flag |
|---|---|---|---|---|---|
| GRASS | 2026-10-25 (morning scan) | $0.715863 | +22.34% / +26.40% | $0.733699 | **+2.49%** (≈12 h) |
| ORE | 2026-10-25 (morning scan) | $160.02 | +51.33% / +107.68% | $164.66 | **+2.90%** (≈12 h) |

**Event listener (rs_event_flags.csv, 17 flags on 2026-10-25):**
- 5 STRONG/RUG_RISK flags at 16:05 were the known thin-pair false positives (EURC, INJ, MET, ORCA, RENDER) — fixed in commit `0c259c2`, verified by Coco.
- After the 16:09 restart: 12 flags, **all VOL_SPIKE or LIQ_ADD** (CBBTC, USDE, USDC, WSOL, ENA, USDG, JITOSOL, JUP, JLP, RAY, + ORE STRONG at 17:15 rank 108, USDE LIQ_ADD). Zero thin-pair false positives since the fix — the volume floor, avg-baseline floor and ±2% liquidity-trend gate held (ORE's 17:15 STRONG came with real volume above the $5k floor, not the earlier $155 spike).

## What happened since (honest read)

- Both daily-scan picks are up since the flag (+2.5% GRASS, +2.9% ORE in ~12 hours). That is **far too little data to call the rule good**: 2 picks, 1 day, and both were strong momentum coins on a day SOL itself was down.
- The listener produced no actionable paper signal after the fix — only VOL_SPIKE notes (by design, these do not notify) on mostly large caps and stablecoin-ish assets where a 4–14× 5-minute volume burst is routine noise.

## Lessons

1. **Flag volume ≠ signal quality.** 6,318 orders and 17 flags in a day produced zero tradeable paper events; the two daily-scan picks (quiet, slow rule) are the only ones with follow-up value. Slow rules with floors beat event fireworks.
2. **Absolute floors are mandatory.** Every false positive traced to a missing absolute threshold (volume, liquidity trend, warm-up). Relative multipliers alone ("x800 the average") are meaningless on thin pairs.
3. **12 hours is not a verdict.** +2.5%/+2.9% since flag proves nothing; the +7d/+30d result columns in `rstrength_flags.csv` are the real test — first meaningful reads land 2026-11-01 (GRASS/ORE 7d) and 2026-11-24 (30d). Do not judge the rule before then.

## Day 2 re-run — 2026-10-25 18:30 Bogotá (paper only)

Re-ran `python3 scripts/rstrength_scan.py` in `e101-hummingbot` (watchlist 20 + Solana top 50; 7 near-zero-volume coins skipped by the $10k floor). Result: **0 new daily flags, 2 open rows** (same-day GRASS/ORE are deduped by date+token, so the re-run does not append duplicates). No orders, no wallets, no real trades.

CoinGecko snapshot used for the comparison (`last_updated` **2026-10-25T23:29:51Z** = 18:29:51 Bogotá):

| Token | Flag price (morning) | Price now | Since flag | 7d / 30d now | SOL now | 7d / 30d spread vs SOL | vs first review (17:41, 22:41:51Z) |
|---|---|---|---|---|---|---|---|
| GRASS | $0.715863 | **$0.723485** | **+1.06%** | +27.19% / +39.79% | −0.51% / −16.06% | +27.70 / +55.85 pp | $0.733699 → **−1.39%** |
| ORE | $160.02 | **$160.87** | **+0.53%** | +55.42% / +110.01% | −0.51% / −16.06% | +55.93 / +126.08 pp | $164.66 → **−2.30%** |

**Stayed strong / faded:** both daily picks still clear the rule (7d and 30d each beat SOL by >15 pp while SOL 30d is negative), and their spreads widened slightly versus the morning. Both faded a little from the 17:41 snapshot (−1.4% GRASS, −2.3% ORE), so the first review's +2.5%/+2.9% "since flag" numbers did not keep rising. No new daily candidate replaced or joined them.

**Event listener:** `data/rs_event_flags.csv` now has **18 flags today** (17 at the first review). The only new one is ORE `VOL_SPIKE` at **18:20:59** ($160.88, rank 83, 6.24× 5-minute volume, 1h −0.56%) — a volume note, not a STRONG/RUG signal, and no notification by design. No new STRONG/RUG flags and no thin-pair false positives since the 16:09 fix.

**Read:** same conclusion as day 1, one hour later — the quiet daily rule is still the only thing with follow-up value, and 48 minutes of drift is noise, not a verdict. The 7d/30d result columns remain the real test: first reads 2026-11-01 (7d) and 2026-11-24 (30d).

### Re-run check — 2026-10-25 18:32 Bogotá

q36 re-sent; re-ran the scan. Still **0 new daily flags, 2 open rows**. CoinGecko `last_updated` **2026-10-25T23:31:47Z** (18:31:47 Bogotá): GRASS **$0.719496**, ORE **$160.92**, SOL **$100.87**. Both picks still clear the rule; moves versus the 18:29 snapshot are under 0.6%, so nothing material changed. No new lesson.

## Day-3 check — 2026-10-25 19:35 Bogotá (third scan pass, CSVs only)

Read `data/rstrength_flags.csv`, `data/rs_series.csv` and `data/rs_event_flags.csv` only. No API prices, no trades/wallets.

- **No new daily flags.** `rstrength_flags.csv` still has exactly the two 2026-10-25 rows (GRASS $0.715863, ORE $160.02); the `result_7d`/`result_30d` columns are still empty, so the rule's 7d/30d spread cannot be re-measured yet.
- **Price path from the paper series** (latest sample 19:35:59):
  - GRASS $0.7145 → **−0.19% vs flag**, +0.08% since the series' first 15:50 sample (WSOL −0.06% over the same window) — flat.
  - ORE $160.24 → **+0.14% vs flag**, +0.53% since 15:50 — still slightly ahead of SOL, but only fractionally.
- **What held:** both day-1/day-2 picks are roughly flat at their flag levels and did not lose their absolute price; ORE stayed marginally ahead of WSOL over the series window.
- **What reversed:** ORE's event stream flipped from `STRONG` (17:15) / `VOL_SPIKE` (18:20) to **`RUG_RISK` at 19:30:59** — price $160.19 (−0.12% 1h) with liquidity −2.71% in 30m and **−3.72% in 1h** while 5-minute volume was 5.26× baseline. That is the first liquidity-side reversal on the name, not a price breakout. No new STRONG flags.
- **Listener noise:** 4 new flags since the day-2 note (EURC, PYUSD, SYRUPUSDC VOL_SPIKE; ORE RUG_RISK) → 22 total for the day. The three stablecoin/stable-ish volume spikes are the same routine noise; only ORE's risk flag matters.
- **Verdict:** the signal is **not yet supported**. The picks held flat rather than extending relative strength, and ORE's first reversal is a liquidity warning. Keep the paper rule running until the 7d/30d columns fill (2026-11-01 / 2026-11-24); do not treat the flat day as confirmation and do not add positions. The quiet daily scan still looks more useful than the event fireworks, but it has not earned a keep decision yet.

## Day-3 evening — 2026-10-25 21:27 Bogotá (CSVs only, paper only)

Read `data/rstrength_flags.csv` (still exactly the 2 morning rows, result columns empty), `data/rs_series.csv` (69 samples/token, 15:50:59 → 21:25:59) and `data/rs_event_flags.csv` (22 rows, last 19:30:59). No API prices, no trades/wallets.

**Picks vs first scan (flag prices from the CSV):**

| Pick | Flag | Latest (21:25:59) | Since flag |
|---|---|---|---|
| GRASS | $0.715863 | $0.7049 | **−1.53%** |
| ORE | $160.02 | $150.53 | **−5.93%** |

**Same-window baselines from the series (15:50:59 → 21:25:59, real rows):**

| Baseline | First | Last | Window |
|---|---|---|---|
| CBBTC (BTC proxy — wrapped BTC, tracks spot; assumption, not spot BTC) | $80,342 | $79,474.50 | **−1.08%** |
| WBTC (second BTC proxy) | $80,203.80 | $79,284.40 | **−1.15%** |
| WSOL (SOL context) | $101.41 | $100.69 | **−0.71%** |
| ETH | — | — | **not in the CSVs — no ETH baseline available** |

- GRASS (−1.53% since flag; −1.26% over the series window) is roughly in line with the market (BTC-proxy −1.1%, SOL −0.7%): flat-to-soft, no edge either way.
- ORE (−5.93% since flag; −5.56% over the window) is now **~4.8 pp worse than the BTC proxy**. The damage is concentrated in one move: **21:10 → 21:15, $156.79 → $151.51 (−3.37% in 5 min)** on $24,254 5-minute volume (~5× its recent baseline), with liquidity roughly flat (~$235–239k, no liq collapse) — a sell burst, not a drain.
- That 21:15 drop produced **no flag**: ORE's RUG_RISK (19:30:59) cools that rule until ~22:30 and its VOL_SPIKE (18:20:59) cools that rule until ~21:20, so both candidate rules were plausibly muted by the 180-minute per-(coin,rule) cooldown. Plausible, not proven — and if cooldowns swallow a −3.4%-in-5-min move on a flagged name, that is itself a design question for the listener.
- Wider gap: `rs_event_flags.csv` has **nothing after 19:30:59** while series sampling ran to 21:25:59. Cooldowns may explain it (most active pairs were recently flagged), but a silent writer would look identical from the CSVs. Open question, flagged not claimed.

**Sample size:** n = 2 picks, ~1 day. That is not enough data for any verdict on the rule — and the first directional read is adverse (ORE −5.9% vs BTC-proxy −1.1%). The 7d/30d columns remain the real test (2026-11-01 / 2026-11-24). No positions, no change to the plan: keep the paper rule running.

## Day-4 — 2026-10-25 ~22:18 Bogotá (q79: the 19:30→21:30 flag gap, paper only)

q66 asked whether the 2-hour gap in `rs_event_flags.csv` (last row 19:30:59, next 21:30:59) meant the writer died. Verdict from code + CSVs + `logs/rstrength.log`: **the writer was healthy; the evaluator was blind. Two restarts each wiped the in-memory sample history, and `coin_rules` needs 12 five-minute samples — so no rule could fire for most of the gap.**

Evidence (all local, nothing traded):

- **Sampling never stopped.** `rs_series.csv` has continuous 5-minute buckets 15:50:59 → 22:10:59 (78 buckets; one 11-minute hole 20:40:59 → 20:51:59 during a Binance DNS outage, `WebSocketAddressException` in the log). Row counts per bucket stay at the full 43–44 tokens.
- **Two restarts in the log** (`listening; 53 coins` lines): **19:44:29** (minutes after the q48 stablecoin-filter commit landed) and **20:33:54** (mid-DNS-outage, systemd `Restart=always`). `Engine.hist` lived only in memory, so each restart reset the 1-hour warm-up: blind until ~20:40, then blind again until 21:30.
- **Replay with the real `coin_rules`:** ignoring restarts, 5 VOL_SPIKEs should have fired in the gap (PYTH 19:50, TRUMP 19:55, ENA 20:25, WLFI 21:00, ORCA 21:05) — cooldowns do not cover any of them. Honoring the two restarts (history wiped, 12-sample warm-up), **zero** rules could fire in the gap. The first post-warm flag lands exactly on the 12th post-restart bucket: **STONK VOL_SPIKE at 21:30:59**, then JLP at 21:50. Cooldown is innocent; warm-up amnesia explains 100% of the gap.
- **Correction to q66:** the 21:15 ORE −3.37% sell burst was attributed to cooldowns (RUG_RISK cooled till ~22:30, VOL_SPIKE till ~21:20). The replay shows it fell 9 samples after the 20:33 restart — inside the blind window, same root cause, not cooldowns.
- **Side findings (not bugs, no action):** the `USDC RUG_RISK` log lines at ~19:44 never hit the CSV because they came from the q48 gate test writing to a temp dir; the `GOOD/MEME/GRAD` lines at 19:44:29 are a `--simulate` run, same story. The pre-19:44 code had no pegged-asset filter, so a whole-day replay is not comparable — only the gap window was tested.

**Fix (local branch `q79-hist-persist`, commit `f8044b6`, unpushed):** the engine now persists the last 13 samples per token in `rs_listener_state.json` (same file as the cooldowns) and restores them on start; corrupt/legacy state boots empty, never crashing the loop. Replaying the gap *with* persistence restores all 5 missed detections. Tests: new `tests/test_hist_persist.py` PASS (restart keeps samples → STRONG fires on the 12th sample; corrupt state ignored; capped at 13), plus existing `--simulate` and `test_stable_filter.py` still PASS. Paper only; no timers touched.

## Forward returns by rule — 2026-10-25 22:40 Bogotá (q81, paper only)

Question: do the relative-strength flag rules predict price? Read-only analysis of the real CSVs: `data/rs_event_flags.csv` (24 flags, 16:05:59 → 21:50:59) and `data/rs_series.csv` (43 tokens, 15:50:59 → 22:35:59). No API calls, wallets or orders.

Method: for each flag, forward return = series price at flag time → series price at +1h/+4h/+24h, percent. A horizon counts only when the same token has a series sample within ±10 min of the target. Baseline = random same-coin timestamps that also have that horizon, 200 draws per flag/horizon, fixed seed; baseline draws are not independent samples. Hit rate = share of forward returns > 0. Script: `e101-hummingbot/scripts/flag_forward_returns.py` (branch `q81-forward-returns` `890a266`), fixture test `tests/test_flag_forward_returns.py` 3/3 PASS.

| Rule | Horizon | Flags n | Median | Mean | Hit rate | Baseline median | Baseline mean | Baseline hit | Sample |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| LIQ_ADD | +1h | 1 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 20.00% | too small |
| RUG_RISK | +1h | 3 | −0.44% | −0.61% | 0.00% | −0.27% | −0.31% | 37.80% | too small |
| STRONG | +1h | 4 | 0.29% | 0.49% | 50.00% | 0.00% | −0.33% | 18.80% | too small |
| VOL_SPIKE | +1h | 15 | −0.02% | −0.35% | 26.70% | 0.00% | −0.20% | 27.30% | too small |
| ALL | +1h | 23 | 0.00% | −0.22% | 26.10% | 0.00% | −0.23% | 26.90% | too small |
| LIQ_ADD | +4h | 1 | 0.00% | 0.00% | 0.00% | 0.00% | −0.01% | 23.00% | too small |
| RUG_RISK | +4h | 2 | −0.64% | −0.64% | 50.00% | −1.01% | −0.76% | 37.80% | too small |
| STRONG | +4h | 4 | 0.00% | −1.48% | 0.00% | −0.58% | −1.11% | 9.80% | too small |
| VOL_SPIKE | +4h | 11 | −0.52% | −1.03% | 9.10% | −0.43% | −0.78% | 16.20% | too small |
| ALL | +4h | 18 | −0.19% | −1.03% | 11.10% | −0.39% | −0.81% | 17.60% | too small |
| all rules | +24h | 0 | — | — | — | — | — | — | no data |

`+24h` is unavailable for every flag: the series ends 22:35:59, only ~6.75 hours after the first flag; nothing can be concluded at that horizon until tomorrow's data exists.

**q79 replay (separate, clearly labelled):** the day-4 review lists five VOL_SPIKEs the pre-persist restarts missed (PYTH 19:50, TRUMP 19:55, ENA 20:25, WLFI 21:00, ORCA 21:05). Using that documented list — not a re-run of the detector — +1h gives n=5, median **−1.07%**, mean −0.98%, hit rate **0/5 (0%)**, vs baseline median −0.15% and hit 25.1%. Too small to conclude, and the direction is adverse.

**Verdict:** no rule shows evidence of predictive edge in this dataset, and no rule can be judged from it: every per-rule sample is under 30 flags, the whole file is one 5.75-hour window, and the ±10-min matching plus overlapping 5-minute series makes the baseline a reference rather than a significance test. The only read is weak and adverse — VOL_SPIKE at +4h has hit rate 9.1% vs 16.2% baseline, and the five replayed misses at +1h were 0/5 positive vs a 25.1% baseline — but with n=11–15 and one day, that is not a conclusion. Keep the paper collector running and re-run this script after 24h of series data exists; only then do +24h and a larger +1h/+4h sample become meaningful.

_Sources: `data/rs_event_flags.csv` (24 rows), `data/rs_series.csv` (43 tokens), q79 day-4 replay list in this file; generated with `python3 scripts/flag_forward_returns.py --data-dir data --replay-q79 --draws 200 --seed 7`. Paper only; no positions, timers or services touched._

## Forward returns by rule — 2026-10-26 16:20 Bogotá (q81 re-run, 24h+, paper only)

First run after the series reached 24h. Branch `q81-forward-returns` @ 890a266, worktree `/tmp/opencode/q81-rerun`, same command and seed as the first run. Data read-only from the shared checkout.

**Coverage check:** first flag **2026-10-25 16:05** (-05), last series point **2026-10-26 16:15** (-05) — exactly **24h10m**, i.e. only just past the gate, so `+24h` can still be answered only for flags in the first 10 minutes. Flags: 88 rows over 24h; series: 43 tokens, 15:50 → 16:15.

| Rule | Horizon | Flags n | Median | Mean | Hit rate | Baseline median | Baseline mean | Baseline hit | Sample |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| LIQ_ADD | +1h | 3 | 0.00% | 0.00% | 0.00% | 0.00% | 0.08% | 19.00% | too small |
| LIQ_DRAIN | +1h | 2 | -0.06% | -0.06% | 0.00% | 0.00% | -0.02% | 19.00% | too small |
| RUG_RISK | +1h | 8 | -0.07% | -0.11% | 12.50% | 0.00% | 0.08% | 39.60% | too small |
| STRONG | +1h | 8 | 0.81% | 0.65% | 62.50% | 0.00% | 0.17% | 36.20% | too small |
| VOL_SPIKE | +1h | 63 | 0.00% | 0.17% | 39.70% | 0.00% | 0.04% | 39.10% | usable n |
| ALL | +1h | 84 | 0.00% | 0.17% | 36.90% | 0.00% | 0.06% | 37.70% | usable n |
| LIQ_ADD | +4h | 3 | 0.00% | 0.00% | 0.00% | 0.00% | 0.12% | 31.30% | too small |
| LIQ_DRAIN | +4h | 1 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | too small |
| RUG_RISK | +4h | 6 | 0.01% | -2.01% | 50.00% | 0.00% | 0.51% | 42.90% | too small |
| STRONG | +4h | 7 | 0.00% | -1.36% | 14.30% | 0.00% | 0.21% | 38.40% | too small |
| VOL_SPIKE | +4h | 54 | 0.00% | 0.43% | 46.30% | 0.00% | 0.18% | 43.20% | usable n |
| ALL | +4h | 71 | 0.00% | 0.03% | 40.80% | 0.00% | 0.20% | 41.60% | usable n |
| LIQ_ADD | +24h | 0 | — | — | — | — | — | — | no data |
| LIQ_DRAIN | +24h | 0 | — | — | — | — | — | — | no data |
| RUG_RISK | +24h | 2 | 2.77% | 2.77% | 50.00% | 2.93% | 2.85% | 50.00% | too small |
| STRONG | +24h | 3 | -0.89% | -1.27% | 0.00% | -0.89% | -1.37% | 0.00% | too small |
| VOL_SPIKE | +24h | 0 | — | — | — | — | — | — | no data |
| ALL | +24h | 5 | -0.50% | 0.35% | 20.00% | -0.50% | 0.32% | 20.00% | too small |

Flags rows: 88 · series tokens: 43 · horizons: +1h, +4h, +24h.
Baseline: random same-coin timestamps, 200 draws per flag/horizon where data exists; draws are not independent. Hit rate = forward return > 0.

**Stale/flat series check (the director's +1h≈0.00% concern), measured on this data:** 6,694 of 12,728 consecutive series steps (**53%**) repeat the previous price exactly, and **20% of +1h** and **21% of +4h** flag returns are exactly 0.00%. All 3 LIQ_ADD +1h and +4h returns are zero. So the zero medians are mostly a price-refresh artefact, not a market fact: a flag whose price did not tick has no +1h move to measure, and that dilutes every median toward 0.

### q79 replay — five VOL_SPIKEs from the day-4 review (list, not re-derived; paper only)
| Rule | Horizon | Flags n | Median | Mean | Hit rate | Baseline median | Baseline mean | Baseline hit | Sample |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| VOL_SPIKE_q79_replay | +1h | 5 | -1.07% | -0.98% | 0.00% | 0.00% | 0.01% | 34.30% | too small |
| ALL | +1h | 5 | -1.07% | -0.98% | 0.00% | 0.00% | 0.01% | 34.30% | too small |
| VOL_SPIKE_q79_replay | +4h | 5 | -0.61% | -0.79% | 0.00% | 0.00% | -0.02% | 45.20% | too small |
| ALL | +4h | 5 | -0.61% | -0.79% | 0.00% | 0.00% | -0.02% | 45.20% | too small |
| VOL_SPIKE_q79_replay | +24h | 0 | — | — | — | — | — | — | no data |
| ALL | +24h | 0 | — | — | — | — | — | — | no data |

Flags rows: 5 · series tokens: 43 · horizons: +1h, +4h, +24h. These five rows are the documented day-4 review list, not a re-run of the detector.

**Verdict:** still no evidence of predictive edge, and the first 24h does not settle it. `+1h` and `+4h` now have usable n for VOL_SPIKE only (63 and 54), and both land on baseline (hit 39.7% vs 39.1% at +1h; 46.3% vs 43.2% at +4h) with 0.00% medians driven by the 53% flat-price share. Every other rule is under 30 flags and too small to judge. `+24h` has just n=5 because coverage is exactly 24h10m — the sample cannot grow until the series is several days long. Before any horizon comparison is trusted, the collector's price refresh needs fixing: near-half of steps are stale, which biases medians to zero and makes hit rates coin-flip-like by construction.

_Sources: `~/code/p4/e101-hummingbot/data/rs_event_flags.csv` (88 rows, 2026-10-25 16:05 → 2026-10-26 16:05), `rs_series.csv` (43 tokens, 2026-10-25 15:50 → 2026-10-26 16:15), q79 day-4 replay list in this file; generated with `python3 e101-hummingbot/scripts/flag_forward_returns.py --data-dir ~/code/p4/e101-hummingbot/data --replay-q79 --draws 200 --seed 7` on branch q81-forward-returns @ 890a266. Paper only; no positions, orders, timers or services touched._
