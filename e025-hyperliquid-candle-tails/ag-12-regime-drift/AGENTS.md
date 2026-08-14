# ag-12 — Regime drift: are the patterns stable over time?

Phase 5e. All findings so far assume the data is stationary. Check whether
volatility, tails, event frequency, and the key patterns actually stayed
stable across time — if they drift, the edges may not hold going forward.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../ag-02-dist/AGENTS.md](../ag-02-dist/AGENTS.md) — derived columns

Single agent, never downloads. Beginner-explain requirement applies.

## Inputs

- `../ag-01-data/output/candles_raw.csv` (1d and 1w have full history since
  2023; 5m/1h only have recent windows — note that limitation).

## Method

Split the history of each coin into **quarters** (or halves if the series is
short). Per quarter, compute:

1. **Volatility level**: σ of `ret`, and median `range`.
2. **Tail shape**: kurtosis, p99, p99.9.
3. **Event frequency**: count of 3σ days per quarter.
4. **Pattern stability**:
   - The weekday effect (ag-06): does Mon/Wed-down / Thu/Sun-up persist in
     each quarter?
   - The daily-crash reversion (ag-07): does "buy crash, next-5 positive"
     hold in each quarter?
5. **Trend test**: is vol rising or falling over the quarters (e.g. simple
   linear trend / rank correlation vs time)?

## Deliverables

| File | Contents |
|---|---|
| `output/quarters.csv` | Per (coin, tf, quarter): σ, kurtosis, p99.9, 3σ-event count |
| `output/pattern_stability.csv` | Per quarter: weekday effect size, crash-reversion next-5 return |
| `output/charts/*.png` | Vol and kurtosis over time per tf; event frequency over time (~5) |
| `output/report.md` | Is the data stationary? Which patterns are time-stable? |
| `output/beginners_guide.md` | What "regime drift" and "stationary" mean, for a beginner |
| `output/session-log.md` | Per e025 conventions |

## Honest expectations

- Crypto vol is known to be regime-driven (2024 quiet, 2025 active). Expect
  real drift in volatility level — the interesting question is whether the
  *relative* patterns (weekday, crash-reversion) survive regime changes.
- 1w has only ~190 candles/coin — quarters there are thin; note it.

## Self-command

```bash
( sleep 60; tmux send-keys -t 25-12 "Self-wake: check progress. Files? errors? done?" Enter ) &
```

Window: `25-12`. Write `done.txt` with the stability verdict when done.
