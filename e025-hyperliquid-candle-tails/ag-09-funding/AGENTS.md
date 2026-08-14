# ag-09 — Funding analysis: sentiment edge

Phase 5b. The funding-rate history was backfilled (118K rows, `funding_raw.csv`).
Funding is the perp sentiment gauge: **extreme positive funding = the crowd is
long**. Test whether crowding predicts returns, and whether it explains the
patterns already found (weekday, daily-crash reversion).

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-02-dist/AGENTS.md](../ag-02-dist/AGENTS.md) — derived columns
- [../ag-05-seasonality/AGENTS.md](../ag-05-seasonality/AGENTS.md) — split-sample + per-coin replication pattern

Single agent, never downloads. Beginner-explain requirement applies.

## Inputs

- `../ag-01-data/output/funding_raw.csv` — `coin, time_ms, fundingRate, premium`
  (hourly payments since ~May 2023; XMR is empty — delisted, skip)
- `../ag-01-data/output/candles_raw.csv` — candles
- Funding convention: positive = longs pay shorts (crowd long).

## Questions (the declared grid)

1. **Crowding → reversal?** Compute per-coin funding z-scores (per coin, over
   its own history). Bucket: extreme negative (<−1.5σ), normal, extreme
   positive (>+1.5σ). What is the next-day and next-5-day return of each
   bucket? (Hypothesis: extreme positive funding → negative forward returns.)
2. **Funding and the weekday pattern** (ag-05/ag-06): average funding by
   weekday. Is Mon/Wed down correlated with funding being high those days?
   Does controlling for funding change the weekday return?
3. **Funding before daily crashes** (ag-07): for 1d crash events, was funding
   extreme in the days before? Do crashes with extreme pre-funding revert
   differently than crashes with neutral funding?
4. **Funding itself**: does funding mean-revert? How long does an extreme
   funding spell last (half-life)?

## Method & rigor

- Join funding to candles on the daily timeframe (use the funding payment at
  the day's open — define and state it). No lookahead: features from t and
  before, targets from t+1 onward.
- Split-sample 50/50 by time per coin; replication required on both halves.
- Per-coin replication rate (fraction of 12 coins same sign).
- If the funding buckets have <100 obs per bucket per tf, report as
  insufficient data.

## Deliverables

| File | Contents |
|---|---|
| `output/funding_patterns.csv` | Per (coin, tf, bucket): n, mean/median next-return, split halves |
| `output/weekday_funding.csv` | Avg funding by weekday + the weekday-return controlling analysis |
| `output/crash_funding.csv` | Crash events × pre-funding bucket → next-5-day returns |
| `output/charts/*.png` | Bucket bar charts + funding mean-reversion chart (~5) |
| `output/report.md` | Answers to the 4 questions, replication verdicts, honest nulls |
| `output/beginners_guide.md` | Funding, sentiment, crowd-positioning, for a beginner |
| `output/session-log.md` | Per e025 conventions |

## Honest expectations

- Crowding-reversal is a real, documented perp phenomenon — it may show.
- The weekday and crash findings may be funding-independent (fine — that's a
  result too).
- Funding may just be a proxy for vol/regime already covered. Say so if so.

## Pitfalls

- fundingRate is a **string** — cast to float.
- XMR has 0 funding rows — skip, note it.
- Hourly funding vs daily candles: aggregate carefully; state the convention.
- Funding z-scores need each coin's own history; don't pool raw rates across
  coins (levels differ wildly).

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-9 "Self-wake: check progress. Files? errors? done?" Enter ) &
```

Window: `25-9`. Write `done.txt` with the 4 verdicts when done.

## Notify (mandatory)
In addition to writing `done.txt`, agents MUST notify on completion:
`notify.sh done "<agent> finished: <headline>"` (from `../../e000-fundamentals/bin/notify.sh`)
On an unrecoverable failure, before giving up: `notify.sh error "<agent> failed: <cause>"`

