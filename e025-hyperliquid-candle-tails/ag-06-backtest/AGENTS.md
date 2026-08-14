# ag-06 — Weekday edge: rigor + strategy backtest

Phase 3 of e025. Two jobs, done in order, every deliverable explained for a
**beginner** (the user is learning): (1) prove the 1d weekday pattern is real,
not chance; (2) turn it into a concrete strategy and backtest it on data the
pattern has never seen.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-05-seasonality/AGENTS.md](../ag-05-seasonality/AGENTS.md) — the weekday finding this builds on
- [../ag-02-dist/AGENTS.md](../ag-02-dist/AGENTS.md) — derived column definitions

## Inputs

- `../ag-01-data/output/candles_raw.csv` — shared candle CSV (never download)
- `../ag-05-seasonality/output/report.md` — the finding being validated:
  **1d weekday direction: Mon −0.42%, Wed −0.60% down; Thu +0.20%, Sun +0.28%
  up. Replicated in both split halves and in 10–12/12 coins.**

## The beginner-explain requirement (absolute)

The user is a beginner. Every deliverable MUST contain plain-English
explanations of the concepts it uses — what the test does, why it matters,
what the numbers mean, in simple language with analogies where useful. Do NOT
assume the reader knows: p-value, permutation test, backtest, expectancy,
drawdown, fees, out-of-sample. Each deliverable gets a "Plain English" section
at the top, and a combined `beginners_guide.md` explains the whole pipeline
in order.

## Part 1 — Permutation test (does the weekday pattern survive chance?)

The pattern was found by looking at the data. Real patterns must survive a
test where we break the association:

- **Method**: shuffle the weekday labels on the 1d candles (per coin, to keep
  the series structure), recompute the pattern-strength metric (e.g. Spearman
  rho of weekday → median `ret_next`, or the max-minus-min day spread, or
  consistency of sign), repeat ~10,000 times, and count how often the shuffled
  data produces a pattern as strong as the real one.
- **p-value** = fraction of shuffles ≥ observed. p < 0.01 = the pattern would
  appear by chance <1% of the time.
- Report the observed metric, the null distribution (histogram chart), and the
  p-value. Also report the per-coin permutation result (how many of 12 coins
  pass individually).
- **Plain English**: "we scramble which day each candle belongs to. If the
  weekday pattern still shows up after scrambling, it was never real — it was
  just luck. We repeat 10,000 times and count how often luck produces what we
  saw."

## Part 2 — Strategy spec (one concrete, testable rulebook)

Spec a strategy from the finding. Keep it dead simple — this is a research
test, not a production system:

- **Rule A (weekday tilt)**: for each coin, on Mon/Wed open a SHORT at the day
  open, close at the day close. On Thu/Sun open a LONG, close at day close.
  No leverage. Equal notional per coin.
- **Rule B (control — the opposite)**: trade the *other* days (Tue/Fri/Sat
  long, Mon/Wed/Thu/Sun short... define exactly) — this shows the pattern is
  specific and not some generic daily drift.
- **Rule C (baseline)**: buy-and-hold each coin (or long every day) for
  comparison.
- State the exact rules in `strategy_spec.md` as plain language + one short
  pseudocode block. Include the fee model: **taker 0.045% each side** (0.09%
  round trip) and the maker rate 0.018% (report both).

## Part 3 — Backtest (test on data the pattern never saw)

- **Out-of-sample rule**: the pattern was discovered using ALL 1d data
  (ag-05's halves were for replication, not profit testing). The backtest must
  run on **only the second half** of each coin's 1d series (by time) — the
  portion never used to decide the rules. This is what makes the test honest.
  State the exact date range used.
- Compute per rule: total return, **expectancy** (mean P&L per trade),
  **win rate**, **max drawdown**, a Sharpe-style ratio, and the same **net of
  fees** (taker and maker variants). Also report the same metrics for Rule B
  and Rule C so the reader sees the contrast.
- Report per-coin results too, and a "market-pooled" view (equal weight across
  coins per day) — with the honest caveat that the 12 coins are correlated, so
  the effective independent sample is much smaller than 12× the trades.
- **Fees decide it**: with medians of ~0.2–0.6% per day and 0.09% round-trip
  cost, the net result may be thin or negative. Report that honestly. The
  experiment's job is to measure, not to make the strategy look good.
- Risk caveat: this is a statistical exercise on historical data, not trading
  advice, and past results don't predict the future. State it plainly.

## Deliverables

| File | Contents |
|---|---|
| `output/permutation_test.md` | Method, metric, null-distribution chart, p-value (pooled + per coin) |
| `output/permutation_null.png` | Histogram of shuffled pattern strengths + the observed value marked |
| `output/strategy_spec.md` | Exact rules (plain language + pseudocode), fee model |
| `output/backtest.csv` | One row per (coin, day, rule): entry, exit, P&L %, fees |
| `output/backtest_report.md` | Metrics table per rule, gross vs net, drawdown chart path, verdict |
| `output/backtest_equity.png` | Equity curve: Rule A vs B vs C, net of fees |
| `output/beginners_guide.md` | Whole pipeline explained for a beginner |
| `output/session-log.md` | Per e025 conventions |

## Pitfalls

- 1d candles: `ret` uses `c[t−1]`→`c[t]`; for a strategy entering at day open
  and exiting at day close, P&L = `(c − o)/o` — the *intraday* return, not the
  close-to-close return. Make sure spec and backtest use the same definition
  and say which one.
- The weekdays Mon/Wed/Thu/Sun refer to the candle's OPEN day (UTC).
- Correlated coins: report the market-pooled result and warn about inflated
  sample size.
- Split halves by TIME per coin, then use only the second half for P&L. Never
  look at second-half P&L while deciding rules.
- Fees: taker 0.045% (0.045/100) each side; round trip 0.09%.

## Command execution

- Python + pandas + numpy + matplotlib (system-wide, verified in ag-04/ag-05).
  Run backgrounded with `timeout 600` + self-wake per fundamentals.
- Verify every deliverable exists and non-trivial before `done.txt`.

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-6 "Self-wake: check progress. Files produced? errors? done?" Enter ) &
```

Window: `25-6`. On wake: check outputs, fix errors, iterate. When all
deliverables exist, write `done.txt` with the p-value, the net expectancy, and
the verdict.
