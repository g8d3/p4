# ag-15 — Session log

## Start / end
- Start: 2026-08-14 10:55 (UTC-5) — window 25-15, opencode-go/deepseek-v4-flash
- End: 2026-08-14 (UTC-5)

## Declared test grid + definitions — BEFORE running (no post-hoc changes)

Pooled OOS backtest of the COMBINED reversion strategy on the shared candles:
**T1 (crash, from ag-08) OR T2 (low-volume down, from ag-14)**.

### Trigger definitions (exact, replicated from prior agents)

**T1 — crash** (ag-08): per coin, `ret[t] = (c[t]-c[t-1])/c[t-1]` on the 1d
series (v>0 only). `sigma` = stdev of `ret` computed on the FIRST half only
(walk-forward, ddof=1, same as ag-08/backtest.py). T1 on candle `t` iff
`ret[t] < -3*sigma`.

**T2 — low-volume down** (ag-14, signal 5 "vol_adj down_q5"): per coin,
`median_v` = median of `v` on the FIRST half (ag-14 used the full series
median; we move it to the first half for walk-forward — stated choice).
`rel_vol[t] = v[t] / median_v`, `vol_adj[t] = ret[t] / rel_vol[t]`
(ret in %, matching ag-14's analyze.py: `sr / rel_vol`). The quintile is of
`|vol_adj|` **within down moves only** (ag-14's report describes the bucket
as "quintiles of |vol_adj| per (coin,tf) within each sign"; the code pooled
signs but with ~50/50 split the two definitions coincide — stated choice).
`q5_thresh` = 80th percentile of `|vol_adj|` over FIRST-half down moves
(i.e. the top-quintile cutoff). T2 on candle `t` iff `ret[t] < 0` AND
`|vol_adj[t]| >= q5_thresh`.

Both σ and the vol_adj quintile threshold come ONLY from the first half of
each coin's 1d series; triggers are detected and traded on the **second half
only** (the ag-08 walk-forward rule). No lookahead.

### Rules (the FULL declared grid — no additions after results)

| Rule | Trigger | Entry / Exit |
|---|---|---|
| A | T1 only | buy close of trigger day, sell close of day+5 |
| B | T2 only | same |
| C | T1 OR T2 | same |
| D | T1 AND T2 | same |
| E | always long (baseline) | buy close, sell next close |

- Hold = 5 daily candles for A/B/C/D; 1 for E.
- One position per coin at a time (no re-entry while open); equal notional per
  coin; no leverage.
- P&L per trade = `(c[exit] - c[entry]) / c[entry]`; the trigger candle's own
  return is NOT part of the trade.
- Fees: taker 0.045% per side (0.09% round trip), maker 0.018% per side
  (0.036% round trip); applied multiplicatively:
  `net = (1+gross)*(1-fee)*(1-fee) - 1`.

### OOS discipline
- First half: compute σ, median_v, q5_thresh. Second half: detect + trade.
- Pooled OOS window = union of per-coin second halves (ag-08: 2024-11-19 →
  2026-08-13).
- Grid final; no tuning after results.

### Metrics (for every rule)
- Total return, expectancy (mean P&L per trade), win rate, max drawdown,
  Sharpe-style (mean/std of pooled daily returns × √365), gross AND net
  (taker + maker).
- Per-coin + market-pooled (equal weight per day over coins alive; correlated
  coins caveat).

### Questions to answer
1. Sample gain: C vs A trade counts; edge preserved?
2. Volume refines crash: D vs A (expectancy, n).
3. T2 independence: fraction of T2 triggers that are also T1.
4. Net expectancy / win rate / max DD / Sharpe for every rule.

### Validation target (replication check, not tuning)
Rule A alone should reproduce ag-08: 28 OOS trades, net-taker expectancy
~+1.24%, win ~68%. If the machinery doesn't reproduce that, fix the machinery.

## Pitfalls (from AGENTS.md + inherited)
- Drop v=0 (3,175 synthetic pre-listing candles) before computing.
- σ / median_v / q5 thresholds from FIRST half only — never the full series.
- Triggers detected only in SECOND half; trades must complete their hold.
- Never pool timeframes — 1d only here.
- Single-position rule per coin.

## Command count
- Reads/ls/head/file checks: 6
- Python runs: backtest 3x, metrics 2x, chart 1x, verification one-offs 6

## What was done
1. Read AGENTS.md + all Inherits (fundamentals, e025 scope, ag-08 crash
   backtest, ag-14 volume-price). Read ag-08's backtest.py/metrics.py/chart.py
   and ag-14's analyze.py to replicate EXACT definitions.
2. Declared the full grid + trigger definitions in this log BEFORE running.
3. `bin/backtest.py` — walk-forward triggers (T1: first-half σ; T2: first-half
   q5 of |vol_adj| among down moves with causal rolling median_v), rules
   A/B/C/D/E, one position per coin, net-of-fees → backtest.csv, oos_windows.csv,
   trigger_overlap.csv.
4. `bin/metrics.py` — pooled daily equity (ag-08 convention) + metrics →
   metrics.json, per_coin.csv, equity_daily.csv.
5. `bin/chart.py` — equity curves A/B/C/D/E net of taker → equity.png.
6. Verified Rule A == ag-08 exactly (28 trades, +1.24% net, +3.58%, Sharpe
   0.22) and Rule E == ag-08 baseline (−67.24%, −75.62% DD). Written
   backtest_report.md, beginners_guide.md, done.txt.

## Problems hit + solutions
- **Stale-baseline bug (the big one)**: first attempt used a static FIRST-half
  median_v as the volume baseline. Volumes grew 10–20× over the sample (BTC
  1.4k→29k/candle), so second-half |vol_adj| was ~10× smaller than first-half
  and the q5 threshold caught ~0 T2 for BTC/ETH/SOL/XRP/AAVE — a baseline
  artifact, not a signal result. Fixed with a causal trailing 101-candle rolling
  median (the same window ag-14 used for its causal volume percentile);
  calibration now 19.8% of down moves = quintile target. Stated in report.
- **Rule E every-other-day bug**: the generic single-position scan blocked
  re-entry for hold=1, so the baseline only traded every other day (2,565 vs
  the expected 5,123). Fixed by giving E its own daily loop (no blocking —
  sell close[i+1] and immediately re-buy at the same close is one clean round
  trip, matching ag-08's rule_c_trades). After fix, E matches ag-08 exactly.
- **Transient print mismatch**: backtest.py summary showed Rule B win 62.3%
  once while metrics.py showed 48.1% — a stale CSV read during a chained run;
  re-running backtest.py gave 48.1% everywhere. No logic change needed.

## Key findings (for the report)
- C (union) = 312 trades vs A = 28 → 11.1×, 155 distinct days vs 8.
- D (intersection) = 20 trades, net −0.54% (negative) → volume does NOT refine
  the crash. Crash edge sat in the 8 high-volume crashes (+5.68%, 8/8 wins).
- T2 largely independent of T1: 4.2% of T2 triggers are also T1.
- Verdict: pooling credible (n=312, +0.55%/trade net, Sharpe 0.44); quiet-crash
  refinement contradicted.

## Verification
- Rule A matches ag-08 byte-for-byte on the same 28 trades / 8 crash days.
- Rule E matches ag-08's baseline (5,123 trades, −67.24% net, −75.62% DD).
- T2 calibration: 19.8% of second-half down moves flagged (target 20%).
- D verified to be exactly A's T1+T2 subset; C ⊇ 19/28 A trades + 305/308 B
  trades (single-position rule makes the union non-additive by design).

## Context consumed
- Full e000 AGENTS.md, e025 scope, ag-08 + ag-14 AGENTS.md and bin scripts,
  ag-08 report + signals/report from ag-14. No downloads, no API calls, no
  sudo, no extra tmux windows created.
