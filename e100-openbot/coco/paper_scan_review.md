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
