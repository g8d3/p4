# ag-08 — Backtest: daily crash reversion

Phase 5a. Backtest the ONE robust directional finding of the experiment
(ag-07): after a daily 3σ down candle ("crash"), the next 5 days have positive
expected return. Test it out-of-sample, net of fees, with controls.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-06-backtest/AGENTS.md](../ag-06-backtest/AGENTS.md) — backtest rigor + the alignment lesson (ag-06: the weekday pattern lived one day to the side of the spec)
- [../ag-07-event-study/AGENTS.md](../ag-07-event-study/AGENTS.md) — the crash-reversion finding + event definition

Single agent, never downloads. Beginner-explain requirement applies (Plain
English sections + `beginners_guide.md`).

## The finding being tested (from ag-07)

Daily down events (`|ret| < −3σ`, σ = global stdev of 1d `ret` per coin) are
followed by positive 5-day cumulative returns: mean +2.5%, median +3.07% vs
+0.68% baseline; 6/6 coins same sign; both time halves (+3.04/+2.17).

## Strategy under test

- **Rule A (the finding)**: for each coin, at the **close of a 1d crash candle**
  (`ret < −3σ`), buy at that close. Hold **5 daily candles**, sell at close.
  No leverage. Equal notional per coin. No re-entry while a position is open.
- **Rule B (control — buy rallies)**: same but for `ret > +3σ`. Proves the
  asymmetry is real and the effect is specific to crashes.
- **Rule C (baseline)**: always long every day (buy at close, sell at next
  close). Is the crash strategy better than just being long?
- **Sensitivity** (report, don't optimize): hold 3 and 10 days for Rule A.

## Out-of-sample discipline (the core)

- Compute σ **only on the first half** of each coin's 1d series. Use that
  first-half σ to detect events in the **second half**. The second half has
  never influenced the rule — this is the honest test (walk-forward).
- State the exact OOS date range and number of trades in the report.
- Do NOT tune the rule after seeing OOS results (data snooping — the ag-06
  lesson). The grid above is final.

## Metrics

- Total return, **expectancy** (mean P&L per trade), win rate, **max
  drawdown**, Sharpe-style ratio — gross AND **net of fees**: taker 0.045%
  each side (0.09% round trip); also show maker 0.018%.
- Per-coin results + a market-pooled view (equal weight per day). Caveat: the
  12 coins are correlated — effective sample is smaller than 12× trades.
- Risk caveat in plain words: statistical exercise on history, not advice.

## Deliverables

| File | Contents |
|---|---|
| `output/backtest.csv` | One row per (coin, trade): entry/exit dates, P&L %, fees |
| `output/backtest_report.md` | Rules, OOS window, metrics table (A/B/C, gross/net), verdict |
| `output/equity.png` | Equity curves A vs B vs C, net of fees |
| `output/beginners_guide.md` | Backtest + OOS + expectancy + drawdown for a beginner |
| `output/session-log.md` | Per e025 conventions |

## Pitfalls

- Entry P&L = `(close[t+5] − close[t]) / close[t]` — cumulative 5-day from
  crash close. State the exact return definition.
- Crash candle = the day you enter; its own return is NOT part of the trade.
- Don't let positions overlap across the same coin (single position rule).
- If the OOS window has <30 trades, say so and downgrade the conclusion.

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-8 "Self-wake: check progress. Files? errors? done?" Enter ) &
```

Window: `25-8`. Write `done.txt` with net expectancy and the verdict when done.

## Notify (mandatory)
In addition to writing `done.txt`, agents MUST notify on completion:
`notify.sh done "<agent> finished: <headline>"` (from `../../e000-fundamentals/bin/notify.sh`)
On an unrecoverable failure, before giving up: `notify.sh error "<agent> failed: <cause>"`

