# ag-10 — Cross-sectional: relative strength & co-movement

Phase 5c. Everything so far is single-coin. This compares the 12 coins to each
other: does relative performance persist (momentum) or reverse? And when an
event hits, do the coins move together (systematic) or independently?

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-02-dist/AGENTS.md](../ag-02-dist/AGENTS.md) — derived columns
- [../ag-06-backtest/AGENTS.md](../ag-06-backtest/AGENTS.md) — OOS discipline

Single agent, never downloads. Beginner-explain requirement applies.

## Inputs

- `../ag-01-data/output/candles_raw.csv` — 12 coins × 4 tfs.
- Cross-sectional work is strongest on 1d (12 coins × ~1300 days each).

## Questions (the declared grid)

1. **Relative strength**: each day, rank the 12 coins by trailing N-day return
   (N = 5 and 20). Bucket by rank (top 3 / middle / bottom 3). What is the
   next-day and next-5-day return of each bucket? Momentum predicts top beats
   bottom; reversion predicts the opposite.
2. **Long-short portfolio**: the money test. Each day, long the top-3 coins by
   trailing N-day return, short the bottom-3, equal weight, hold one day.
   Backtest out-of-sample on the second half (same walk-forward discipline as
   ag-08: rank on first-half data only for the rule, trade the second half).
   Report net of taker fees 0.045% per side (short = borrow-fee-free on perps,
   but 2× taker for two legs).
3. **Co-movement**: on days when one coin has a 3σ 1d move, what fraction of
   the other 11 coins move the same direction that day? Is there a "market
   factor" in the tails — do crashes hit everything at once?

## Method & rigor

- 12 coins is a small cross-section: report the caveat prominently (a 3-coin
  portfolio has high idiosyncratic risk).
- Split-sample replication on all claims (first/second half).
- No lookahead: ranking uses returns up to t, positions from t.

## Deliverables

| File | Contents |
|---|---|
| `output/relative_strength.csv` | Per (N, bucket, horizon): n, mean/median return, split halves |
| `output/co_movement.csv` | Per tf: % of coins co-moving on event days (up vs down events) |
| `output/long_short.csv` | Per day per leg: P&L %, fees |
| `output/charts/*.png` | RS bucket bars + long-short equity curve (~4) |
| `output/report.md` | Answers to the 3 questions, OOS verdict, honest nulls |
| `output/beginners_guide.md` | Relative strength, long-short, cross-section, for a beginner |
| `output/session-log.md` | Per e025 conventions |

## Honest expectations

- Crypto cross-sectional momentum is a real, documented effect (winners keep
  winning over weeks). It may show on 1d.
- The long-short portfolio is where "does it survive fees" really matters —
  taker costs on 2 legs eat thin edges fast.

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-10 "Self-wake: check progress. Files? errors? done?" Enter ) &
```

Window: `25-10`. Write `done.txt` with the 3 verdicts when done.

## Notify (mandatory)
In addition to writing `done.txt`, agents MUST notify on completion:
`notify.sh done "<agent> finished: <headline>"` (from `../../e000-fundamentals/bin/notify.sh`)
On an unrecoverable failure, before giving up: `notify.sh error "<agent> failed: <cause>"`

