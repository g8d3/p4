# e025 — Executive Summary

*What we asked, what we tested, what we found, and what survives.*
Written for a beginner. Every claim below comes from an agent report in this
directory (each has its own `report.md` + `beginners_guide.md` + `session-log.md`).

**Date**: 2026-08-14 · **Data**: 12 top Hyperliquid perps (by volume+OI) × 4
timeframes (5m/1h/1d/1w), max available history (135,232 candles) + full
funding history (118K rows) + a live OI collection now running hourly.

---

## What we did

| Phase | Question | Agent |
|---|---|---|
| 1–2 | Are returns distributed like a normal curve, and does 1 agent work as well as 3? | ag-01…04 |
| 3 | Do calendar/volume conditions predict the next move? | ag-05 |
| 4 | What happens around 3σ extreme moves? (event study) | ag-06, ag-07 |
| 5 | Is the daily-crash reversion real, and what else is out there? (funding, cross-section, vol model, regime, fees) | ag-08…13 |
| 6 | Does volume confirm price moves? | ag-14 |
| 7 | Combine the surviving signals into one strategy | ag-15 |

Every directional claim was validated three ways: **split-sample** (replicates
on the second half of the data), **per-coin** (holds in a majority of coins),
and **net of fees** (survives 0.09% round-trip taker cost). Anything that
failed a check was reported as noise — there was no cherry-picking.

---

## The honest verdicts

### 1. Returns are extremely fat-tailed
Crypto candles are NOT normal. Kurtosis 9–14 everywhere; a "1-in-1000" move
happens far more often than statistics would predict. Extreme events are
routine, not black swans. → **Volatility sizing is mandatory, not optional.**

### 2. Volatility clusters (the most robust finding)
After an extreme move, volatility stays elevated ~2× for several candles and
decays slowly. Volume percentile, hour-of-day (US open ~13–16 UTC), and
time-since-extreme-move all predict next-candle volatility, replicating in
every coin. → **Not tradeable directly, but the core input for position
sizing.** A GARCH(1,1) model beats simple rules by 31 points at forecasting
it (ag-11).

### 3. Direction: almost nothing works
- **Hour of day, day of month, volume change, VWAP distance, funding
  extremes**: all null for direction.
- **Weekday effect** (Mon/Wed down, Thu/Sun up on 1d): statistically real
  (p<0.0001) but **unstable over time** (5/15 quarters) and the naive trade
  lost out-of-sample.
- **Funding** is highly persistent but has no predictive power for price.
- **OBV divergence**: real but dies at fees.

### 4. The ONE tradeable family: daily reversion of declines
Three independent analyses converged on the same thing:

> **Daily crashes (3σ down days) revert over the next 5 days.**

- Event study (ag-07): +2.5% mean next-5, 6/6 coins, both halves.
- Backtest (ag-08): +1.24%/trade net, 68% win — but only 28 trades.
- Volume twist (ag-14): the effect is *not* stronger on quiet crashes; the
  crash edge actually lived in normal/high-volume crashes.
- **Combined (ag-15)**: crash OR low-volume-down → **312 out-of-sample
  trades, +0.55%/trade net of fees, Sharpe 0.44, +16.3% total**. The two
  signals are mostly independent (only 4.2% overlap), so pooling genuinely
  enlarges the sample.

By contrast, simply being long every day lost −67% net over the same window.
The reversion edge exists relative to a weak long-only baseline.

### 5. Cross-sectional momentum (real, but dangerous)
Top-3 coins by trailing return beat bottom-3 by 0.2–0.4%/day; a long-short
portfolio made +341% out-of-sample (Sharpe 1.28) — but with −66% max
drawdown. Crashes are **systemic**: on down 3σ days, 96% of coins fall
together. Diversification evaporates in tails.

### 6. The fees filter (the "hype filter")
At 0.09% round trip, **almost every statistical edge dies**. The ledger
(ag-13) lists each finding with its gross edge, cost, and net verdict. Only
the daily-reversion family survives with real margin.

---

## What survives — the edge ledger

| Edge | Gross | Net (0.09% RT) | Verdict |
|---|---|---|---|
| Crash OR low-volume-down reversion, 5d hold | +0.64%/trade | **+0.55%** | **Only tradeable candidate** (312 OOS trades) |
| Daily crash reversion alone | +1.33% | +1.24% | Real but thin (28 trades) |
| Cross-sectional long-short | ~+0.34%/day | +0.28% | Real but −66% DD, 12 coins only |
| Weekday tilt | real pattern | −0.43% | Not tradeable |
| OBV divergence | −0.10% | +0.01% | Dies at fees |
| Vol clustering / hour-of-day vol | — | — | Sizing inputs only |
| Funding, VWAP, volume-chg, day-of-month | null | null | No edge |

---

## Honest limitations

- **Sample**: only ~2.3 years of daily data (and 5m/1h only ~17 days/7 months
  — Hyperliquid retention). One bear regime dominates the crash sample.
- **Correlated coins**: 12 coins are not 12 independent tests; effective
  sample is much smaller.
- **Regime drift**: volatility cycles; the weekday effect is unstable. The
  reversion finding is stable (8/10 quarters) but future regimes may differ.
- **Not advice**: this is a statistical exercise on history. Paper-trade it
  before risking anything.

---

## What's running now

- **Live OI collection**: e021 captures funding+OI+markPx for all coins every
  hour — building the OI history that no endpoint provides.
- **Paper-trading monitor** (ag-16): checks daily for triggers and logs live
  forward trades, pushing a phone notification when one fires — the real
  out-of-sample test going forward.

## Read next

- This summary → `STRATEGY.md` (the tradeable spec) → `ag-15-combined/output/`
- `e000-fundamentals/bin/notify.sh` — the notification contract every agent
  now follows (log + tmux + phone push).
