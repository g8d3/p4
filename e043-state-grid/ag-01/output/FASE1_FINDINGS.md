# e043 — Fase 1: Findings (honest) — 1h BTC, 4y + 5m BTC, 1y

Date: 2026-08. Harness: `ag-01/bin/sim.py` (bar-by-bar, causal, RESTING limit
fills, maker 0.02% fees, lot-based ladder, state regime filter). Sweeps:
`ag-01/bin/sweep.py`. Tables: `output/1h_sweep_small.csv`, `output/5m_sweep_*`.

## 1. Harness is verified

- Accounting hand-checked: one round-trip (long q=$3750, stop −2%) realizes
  exactly −$75.75 (incl. fee). Metrics match.
- Causality: regime state, ATR, and rolling-high anchor all use PAST bars only
  (indicator values shifted one bar). No lookahead.

## 2. Default config says the strategy is broken — because the geometry is

Default (C=[0.5,1,2,3]%, V≈+1%, SL 2%, rolling_high anchor, EMA50/100 enter 1%):

| Dataset | Return | Max DD | Fills | Win rate |
|---|---|---|---|---|
| BTC 5m 1y | **−858%** | −858% | 20,420 | 3.4% |
| BTC 1h 4y | **−240%** | −241% | 4,952 | 4.6% |

Two distinct killers (same as e022's reality check):
1. **Fee + noise churn (5m)**: 20k fills, +1% take-profit is smaller than
   routine adverse 5-min moves.
2. **Asymmetric geometry**: `V (+1%) < SL (−4%)` with a low win rate → the
   average losing round-trip (−2.3%·notional) swamps the average win.

## 3. The dominant control is the regime filter, not the ladders

Tightening `enter_pct` (EMA50/100 slope threshold) rescues losses monotonically:

| enter_pct | c4/v0.05 return | Win rate |
|---|---|---|
| 1.0% | −25.8% | 18% |
| 0.3% | −2.6% | 24% |
| 0.2% | **−1.0%** | 39% |

But it rescues by **almost never trading** (46–82 fills in 4 years; exposure
time ≈ 0.05–0.25%). "Don't lose" ≠ "win".

## 4. The bottleneck is the ENTRY win rate, not tuning

Best of the `small` sweep on 1h, across C-spacing, V, SL-ratio, regime, trailing:

| Config | Return | DD | Fills | Win rate |
|---|---|---|---|---|
| c4 v0.05 SL=2V enter0.2% trail | **−0.88%** | −0.9% | 62 | 42% |

Even at **SL = V (1:1)** — where a symmetric edge needs only ~50% win rate —
win rate stays 19–39%. Buying a dip below the rolling high recovers to +V
before −SL less than half the time. At SL=2V (needs >67%) it's 20–42%.

**Verdict: the raw "buy c% below rolling high → exit +v% / stop −s%" has no
positive edge on real BTC. Best ≈ breakeven while doing almost nothing.** It
does not approach e022's benchmark (+3.6% 5m / +1.7% 1h after fees).

## 5. Fixed `activation_price` anchor is unusable on long datasets

A fixed anchor (never re-anchored) over 4 years of multi-x BTC moves produced
−17,000%, 62k fills, 0.1% win rate (levels sat far from price, infinite
re-churn). Needs periodic re-anchoring — dropped until redesigned.

## 6. What this means for the design (evidence-based pivot options)

The user's ladder (C/V/R/SL + volumes + mirrors + allocation targets) is sound
*infrastructure*, but it rests on an entry that doesn't edge. Options for Fase 2:

- **A. Two-sided range grid (proven).** In RANGE state, run the e022-style
  two-sided ATR-spaced grid (which hit +3.6%/+1.7%) instead of one-sided
  dip-buying; layer the user's R-recycle, multi-volume `Q`, and multi-stop
  `SL`/`V` ladders on top of that positive base. Highest expected value.
- **B. Improve the entry, keep the ladder.** Add dip-recovery confirmation
  (buy only once price stabilizes, not while falling), or a momentum/micro-
  trend filter — test each as a Tier-3 mapping on win rate before trusting it.
- **C. Fee-optimized market-making.** Accept low win rate by capturing spread
  (maker-only, tight) — a different economics, not the same reversion bet.

Recommendation: **A** (build on the base edge that already works), then use the
`allocation_map` targets + adaptive mappings as the risk/state layer on it.

## Files

- `ag-01/bin/sim.py` — simulator (now also logs n_win/n_loss/wins_pnl/losses_pnl)
- `ag-01/bin/sweep.py` — Tier-2 sweeper
- `output/5m_default/metrics.json`, `output/1h_default/metrics.json` — default runs
- `output/1h_sweep_small.csv` — full small sweep table (sorted by return)
- `output/summary.csv` — appended run summary
