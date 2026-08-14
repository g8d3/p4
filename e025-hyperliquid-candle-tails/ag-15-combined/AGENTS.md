# ag-15 — Combined reversion strategy: crash OR low-volume down move

Phase 7. The experiment's thesis so far: **daily mean-reversion of unconfirmed
declines**. Two independent analyses found the same family:
- ag-07/ag-08: 1d crashes (`ret < −3σ`) revert over the next 5 days (+1.24%/trade net, but only 28 OOS trades)
- ag-14: down moves on **unusually low volume for their size** also revert (+1.18pp net next-5d)

This agent pools the two triggers into ONE strategy to enlarge the sample and
answer: is the combined signal bigger, and does the volume filter strengthen
or dilute the crash signal?

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-08-crash-backtest/AGENTS.md](../ag-08-crash-backtest/AGENTS.md) — OOS/walk-forward discipline + the T1 definition
- [../ag-14-volume-price/AGENTS.md](../ag-14-volume-price/AGENTS.md) — the T2 definition (volume-adjusted return)

Single agent, never downloads. Beginner-explain requirement applies.

## Inputs

- `../ag-01-data/output/candles_raw.csv` (drop v=0)
- `../ag-08-crash-backtest/output/backtest.csv` and
  `../ag-14-volume-price/output/signals.csv` — reference the EXACT definitions
  the previous agents used; re-implement the same definitions here (do not
  invent new ones).

## Trigger definitions (exact, from prior agents)

- **T1 — crash**: 1d `ret < −3σ` (σ = stdev of 1d `ret` per coin, computed on
  the FIRST half only, applied to both halves — the ag-08 walk-forward rule).
- **T2 — low-volume down**: 1d down move (`ret < 0`) whose **volume-adjusted
  return** `vol_adj = ret / (v / median_v)` is in the lowest-volume quintile
  of down moves for its `(coin, tf)` (ag-14's q5-of-down-sign definition).
  Re-read ag-14's report to replicate the exact bucket; if ambiguous, define
  it as: down moves with `v / median_v` in the bottom quintile, and state the
  choice.

## Rules (the FULL declared grid — no additions after results)

| Rule | Trigger | Entry / Exit |
|---|---|---|
| A | T1 only | buy at close of trigger day, sell at close of day+5 |
| B | T2 only | same |
| C | **T1 OR T2** (the combined strategy) | same |
| D | T1 AND T2 (intersection — purest?) | same |
| E | always long (baseline) | buy close, sell next close |

All: no leverage, equal notional per coin, one position per coin at a time.
Net of taker 0.045% per side (also report maker 0.018%).

## OOS discipline (the core, from ag-08)

- σ and the vol_adj quintile thresholds computed on the **first half** of each
  coin's 1d series; triggers detected and traded on the **second half only**.
- The grid above is final — no tuning after seeing OOS numbers (data
  snooping, the ag-06 lesson).
- Report exact OOS date range and trade counts per rule.

## Questions to answer

1. **Sample gain**: how many more trades does C (union) give vs A alone? Is
   the edge preserved (expectancy, win rate) at the larger sample?
2. **Does volume refine the crash?** Compare D (crash ∧ low-volume) vs A:
   if D has higher expectancy with enough trades, "unconfirmed crashes revert
   strongest" is supported. If D is tiny/n≤10, report as insufficient.
3. **Is T2 independent of T1?** What fraction of T2 triggers are also T1?
   If B is mostly C without crashes, the two analyses are one phenomenon.
4. Net-of-fees expectancy, win rate, max drawdown, Sharpe-style for every
   rule, per-coin + market-pooled (with the correlated-coins caveat).

## Deliverables

| File | Contents |
|---|---|
| `output/backtest.csv` | One row per (coin, trade, rule): entry/exit, P&L %, fees, trigger (T1/T2/both) |
| `output/backtest_report.md` | The 4 answers, metrics table, OOS window, honest verdict |
| `output/equity.png` | Equity curves A/B/C/D/E, net of fees |
| `output/trigger_overlap.csv` | T1∩T2 overlap stats per coin |
| `output/beginners_guide.md` | Combined signals, sample size, why pooling matters — beginner |
| `output/session-log.md` | Per e025 conventions |

## Honest expectations

- The two triggers are the same family, so C may barely beat A on quality but
  with a bigger sample — that is itself the win (more trustworthy numbers).
- If C's OOS net expectancy stays positive at n≥50 trades, the thesis gains
  real credibility. If not, the honest verdict is "insufficient evidence".
- D (intersection) will likely be tiny. Report it, don't force it.

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-15 "Self-wake: check progress. Files? errors? done?" Enter ) &
```

Window: `25-15`. Write `done.txt` with the 4 answers when done.

## Notify (mandatory)
In addition to writing `done.txt`, agents MUST notify on completion:
`notify.sh done "<agent> finished: <headline>"` (from `../../e000-fundamentals/bin/notify.sh`)
On an unrecoverable failure, before giving up: `notify.sh error "<agent> failed: <cause>"`

