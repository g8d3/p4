# ag-06 — Session log

Per e025 A/B conventions: start/end timestamps, command count, every problem
hit and how it was solved, anything that consumed context.

## Start

- Start: 2026-08-13 ~20:37 UTC
- End: 2026-08-13 ~21:00 UTC
- Window: 25-6 (per self-command)

## Inputs

- `../ag-01-data/output/candles_raw.csv` (135,232 rows; v>0 drop → 132,057;
  1d subset = 10,262)
- `../ag-05-seasonality/output/report.md` (the finding being validated)
- Read: e000-fundamentals, e025, ag-05, ag-02 AGENTS.md (inherits)

## Method

- Verified Python + pandas + numpy + scipy + matplotlib present system-wide.
- Verified the ag-05 weekday finding reproduces on the shared CSV:
  `median ret_next` by open-day weekday matches the ag-05 report exactly
  (Mon −0.42, Wed −0.60, Thu +0.20, Sun +0.28).
- **Critical discovery (context consumed):** the strategy P&L `(c−o)/o`
  (same-day intraday) does NOT equal ag-05's `ret_next` (next candle's
  close-to-close). Empirically `ret_next[w] ≈ intraday[w+1]` — the finding
  describes the day AFTER the candle's open day. This one-day shift is the
  root cause of the honest "strategy fails" verdict and is documented in
  `backtest_report.md` and `beginners_guide.md`.

## Steps

1. Wrote `bin/analyze.py` (single script):
   - Permutation test (pooled + per-coin), metric = tilt
     `(median ret_next Thu+Sun)/2 − (median Mon+Wed)/2`, plus max-min spread;
     10,000 shuffles, weekday labels shuffled per coin.
   - Strategy backtest (Rule A/B/C) on the second half of each coin's 1d
     series (t_ms > coin median). P&L = (c−o)/o for long, (o−c)/o for short.
   - Fees: taker 0.045%/side (0.09% RT), maker 0.018%/side (0.036% RT).
   - Pooled (equal-weight per coin per day) + per-coin metrics: total return,
     expectancy, win rate, max drawdown, Sharpe-style (daily, √365).
   - Charts: `permutation_null.png`, `backtest_equity.png`.
2. Ran the script (backgrounded + self-wake). First run produced all
   deliverables; added an OOS weekday diagnostic table to the script (second
   run) to prove the one-day shift directly, then re-ran.
3. Verified outputs: `file` on PNGs (valid PNGs), `wc -l backtest.csv`
   (13,192 rows), JSON results intact.
4. Wrote `permutation_test.md`, `strategy_spec.md`, `backtest_report.md`,
   `beginners_guide.md`, this log, and `done.txt`.

## Results

- **Permutation test (pooled):** tilt observed +0.749%, spread +0.873%,
  p < 0.0001 for both (0 of 10,000 shuffles reached the observed value).
- **Per coin:** 9/12 pass at p<0.05, 6/12 at p<0.01. Failing coins (LIT, XMR,
  ZEC) are the short-history coins (234/210/315 1d candles).
- **Backtest (OOS, net taker):** Rule A total −85.4%, expectancy −0.430%/trade
  (gross −0.340%/trade); Rule B −48.5%, −0.083%/trade; Rule C −66.2%,
  −0.094%/trade; buy-and-hold pooled −6.9%.
- **Verdict:** pattern is statistically real but the strategy as specified
  loses money even before fees, because it trades the same-day intraday while
  the finding describes the next-day move.

## Problems hit

1. **return-definition mismatch (the big one):** `ret_next` vs same-day
   `(c−o)/o` are shifted by one weekday. Not an error — it is the honest
   scientific result — but required the diagnostic table (STEP 3d) to prove
   it, and it shaped the entire report narrative.
2. **Chart lib warning:** matplotlib Axes3D import warning (harmless,
   non-fatal).
3. **Nothing else:** no data issues, no fee rounding issues, no crashes.

## Command count

~15 commands total (data inspection, verification, script runs, output
checks). No downloads (shared CSV only).
