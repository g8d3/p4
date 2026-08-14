# ag-13 — Fees filter: which edges survive real costs?

Phase 5f. Every edge so far was measured gross. This agent is the "hype
filter": it re-evaluates every candidate edge net of Hyperliquid fees and a
slippage assumption, and produces the experiment's final **edge ledger**.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-06-backtest/AGENTS.md](../ag-06-backtest/AGENTS.md) — fee model, backtest rigor
- [../ag-08-crash-backtest/AGENTS.md](../ag-08-crash-backtest/AGENTS.md) — the OOS crash backtest (if its output exists; if not, use ag-07 numbers)

Single agent, never downloads. Beginner-explain requirement applies.

## Inputs (read-only, whatever exists)

- Reports from ag-02, ag-03, ag-05, ag-06, ag-07 (all exist)
- ag-08 crash backtest output if present (note if pending)
- Fee model: **taker 0.045% per side** (0.09% round trip), maker 0.018%,
  slippage assumption 1 bps (top coins BTC/ETH) to 5 bps (small caps) — state
  and justify assumptions.

## Task

Build the **edge ledger**: one row per candidate edge found across the whole
experiment:

| Edge | Timeframe | Gross edge (source) | Round-trip cost | Net edge | Verdict |
|---|---|---|---|---|---|
| Daily crash reversion | 1d | ag-07 (+2.5% mean, 5d) | taker 0.09% | ? | ? |
| Weekday tilt | 1d | ag-06 (real pattern, spec failed) | 0.09% | ? | ? |
| Vol clustering | all | ag-03/05 (not tradeable directly) | — | sizing input | ? |
| Hour-of-day vol | 5m/1h | ag-05 | — | sizing input | ? |
| Relative strength | 1d | ag-10 (if exists) | 0.09% × 2 legs | ? | ? |

For each: is the gross edge large enough that fees cannot kill it? What edge
size is required to survive costs (breakeven expectancy)? Rank by net
tradeability. Include capacity notes (top-10 coins are deep; 5m scalps on
small caps will pay more slippage).

## Deliverables

| File | Contents |
|---|---|
| `output/edge_ledger.csv` | The table above, one row per edge, all numbers |
| `output/report.md` | Which edges are real AND net-positive; which are real but untradeable; final experiment verdict |
| `output/beginners_guide.md` | Fees, slippage, breakeven, why costs kill edges, for a beginner |
| `output/session-log.md` | Per e025 conventions |

## Honest expectations

- Most "real" statistical edges die at 0.09% round trip on intraday
  timeframes. The daily-crash reversion is the candidate most likely to
  survive (its edge is ~20× the fee).
- The ledger is the experiment's conclusion: it separates "statistically
  interesting" from "tradeable".

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-13 "Self-wake: check progress. Files? errors? done?" Enter ) &
```

Window: `25-13`. Write `done.txt` with the final ledger verdict when done.
