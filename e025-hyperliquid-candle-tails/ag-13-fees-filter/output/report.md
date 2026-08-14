# ag-13 — Fees filter: which edges survive real costs?

Date: 2026-08-14
Input: reports from ag-02, ag-03, ag-05, ag-06, ag-07 (all exist).
ag-08 (OOS crash backtest), ag-09 (funding), ag-10 (relative strength),
ag-11 (vol model), ag-12 (regime drift) — **all pending, no output yet**.
The daily-crash-reversion row therefore uses ag-07's numbers and is flagged
provisional until ag-08 confirms it out-of-sample.

## Plain English

Every edge found so far in this experiment was measured **gross** — as if
trading cost nothing. This report applies the **hype filter**: subtract the
real cost of trading (exchange fees + slippage) and ask which edges still have
money left over.

The **fee model**: on Hyperliquid, a market order (taker) costs **0.045% per
side** = **0.09% round trip** (buy + sell). A limit order (maker) costs
0.018% per side = 0.036% round trip. On top of fees, big orders move the
price — **slippage** — which we assume at **1 basis point per side (0.02%
round trip) on the deep top coins (BTC/ETH)** and **5 bps per side (0.10%
round trip) on small caps**. So a realistic round trip is **0.11% (top coins,
taker) to 0.19% (small caps, taker)**.

**The breakeven rule**: a strategy only survives if its gross edge per trade
is **bigger than the round-trip cost** — 0.09% minimum, realistically 0.11%+
with slippage. Anything below that loses money no matter how "statistically
real" it is.

## The edge ledger

| Edge | Timeframe | Gross edge (source) | Round-trip cost | Net edge | Verdict |
|---|---|---|---|---|---|
| Daily crash reversion | 1d | ag-07: mean **+2.47%**, median **+3.07%** over 5d (n=46, 6/6 coins, both halves; re-verified here) | 0.09% taker (1 leg) | **+2.38% mean, +2.98% median** | **REAL AND NET-POSITIVE** (~26× the fee) — OOS confirm (ag-08) pending |
| Weekday tilt | 1d | ag-06: pattern real (perm p<0.0001, tilt +0.749%) BUT Rule A OOS **−0.34%/trade gross** | 0.09% taker | **−0.43%/trade** | Real statistically, **NOT tradeable** as spec'd (traded the wrong day; corrected version deliberately untested) |
| 1h post-crash bounce | 1h | ag-03: p50 next **+0.208%**, mean **+0.300%** after `ret<−3σ` | 0.09% taker | **+0.12%** (p50) | Real but **NOT robust** (split-half h1 −0.14 / h2 +0.85) — marginal, not sizeable |
| 5m post-crash bounce | 5m | ag-03: p50 next **+0.049%** | 0.09% / 0.19% (small-cap slippage) | **−0.04%** | Real but tiny → **killed by fees** |
| 1h body-position reversion | 1h | ag-05: upper-wick −0.032% vs lower-wick +0.010% median_next (~0.04% spread) | 0.09% taker | **−0.05%** | Real but **sub-fee → untradeable** |
| Volatility clustering | all | ag-03/05: `\|ret_next\|` 1.5–3.4× after extremes (vol_pct 2.4–3.4×, range_top1 2.1–2.5×, cooloff 2.0–2.2×) | n/a unless traded | n/a | REAL, robust — **sizing input only**, no directional leg |
| Hour-of-day volatility | 5m/1h | ag-05: US-open bump, `\|ret_next\|` 1.75× (5m) / 1.58× (1h), 12/12 coins | n/a unless traded | n/a | REAL, robust — **sizing input only**, direction flat |
| Relative strength long-short | 1d | ag-10 (PENDING — no numbers yet) | **0.18%** taker × 2 legs daily | ? | **PENDING** — must beat 0.18%/day to matter |
| Fat tails (unconditional) | all | ag-02: kurtosis 9.3–13.8, p99.9 4.9–6.7σ | 0 | 0 | Descriptive; informs **tail-risk sizing**, not a direct edge |

## Breakeven edge sizes (what survives what)

| Cost model (round trip) | Breakeven gross edge per trade |
|---|---|
| Taker 0.09% | **0.090%** |
| Maker 0.036% | **0.036%** |
| Taker + slippage, top coins (0.11%) | **0.110%** |
| Taker + slippage, small caps (0.19%) | **0.190%** |

**Intuition**: a 5m scalp that earns 0.05% gross is dead — it must earn 0.09%+
just to break even, and more than that with slippage. A daily position that
earns 2.5% gross is alive — the fee is 3% of its profit, not its death.

## Edge-by-edge verdicts

1. **Daily crash reversion (1d) — THE survivor.** After a daily 3σ down
   candle, the next 5 days average +2.47% (median +3.07%). One round trip
   costs 0.09–0.19%; the edge is **~26× the cost**. Even at the harshest
   assumption (taker + 5bp small-cap slippage) the net is +2.28% mean.
   Only ~46 trades over 3.5 years pooled across 10 coins → it's rare, so it
   is a **low-frequency, high-margin edge**, not a steady income. **Provisional:
   ag-08's out-of-sample walk-forward test is pending and is the proper
   confirmation.** Capacity is fine — a top-10 perp absorbs daily notional with
   ease; this trade needs no leverage and one position at a time.
2. **Weekday tilt (1d) — statistically real, financially dead as specified.**
   The pattern passes a 10,000-shuffle permutation test (p<0.0001) but the
   strategy built from it lost **−0.34%/trade even gross** out-of-sample: the
   spec traded the *same-day* open→close while the finding described the
   *next-day* close-to-close move, so it systematically took the wrong side.
   Fees are irrelevant to this failure — it lost 3.8× the fee cost *before*
   fees. The corrected version is deliberately untested (would be data
   snooping). Honest verdict: **pattern real, strategy untradeable as written.**
3. **1h post-crash bounce — borderline.** The +0.208% p50 next-candle bounce
   survives the taker fee (+0.118% net) but the effect fails split-half
   replication (h1 −0.14% / h2 +0.85%), so it is not a reliable edge. With
   small-cap slippage it thins to ~+0.02%. **Not sizeable; treat as noise.**
4. **5m post-crash bounce & 1h body-position reversion — both killed by fees.**
   Gross edges of 0.05% and ~0.04% are *below* the 0.09% breakeven. These are
   the canonical case of this report: **statistically real, financially dead.**
   The 5m case is even worse with small-cap slippage (0.19% breakeven).
5. **Volatility clustering & hour-of-day vol — real, robust, and useful, but
   as sizing inputs, not trades.** They predict the *size* of the next move
   (2–3.4×), not its direction. The tradeable translation is **vol-targeted
   position sizing**: when a candle is extreme or it's US-open hours, cut size
   or expect wider swings. Fees apply only if you rebalance to target
   frequently — every rebalance leg costs 0.09% taker.
6. **Relative strength (ag-10) — pending.** A daily long-top-3 / short-bottom-3
   needs **0.18%/day** (two legs × 0.09%) just to break even before slippage.
   Whatever ag-10 measures must clear that bar. Not yet measured.

## Ranking by net tradeability

1. **Daily crash reversion (1d)** — real, robust, net-positive; the only edge
   whose margin is an order of magnitude above costs.
2. **Volatility clustering / hour-of-day vol** — real, robust, and free to use
   as sizing inputs (no fee unless rebalancing).
3. **Relative strength (ag-10)** — unmeasured; feasibility unknown.
4. **1h post-crash bounce** — net-positive in the median but not robust; too
   unreliable to rank higher.
5. **Weekday tilt, 5m bounce, 1h body reversion** — real statistics, negative
   or sub-fee money.

## Capacity notes

- **Top coins (BTC/ETH)** have deep books; 1 bps/side slippage is generous for
  reasonable sizes. The crash-reversion trade is a daily-scale, one-position
  trade on these — negligible capacity constraint.
- **Small caps (DOGE, XRP, HYPE, PUMP, LIT, ZEC…)** pay more slippage — 5 bps
  per side is our working assumption on the 5m/1h scalps. This is precisely
  why intraday small-cap strategies have the hardest time: 0.19% breakeven
  versus typical 5m edges under 0.1%.
- The 12 coins are correlated (all move with BTC), so "12× trades" overstates
  independent evidence. The crash-reversion's 46 events are more like a single
  time series's worth of rare observations — treat the edge as directional
  evidence, not a sized position.

## Final experiment verdict

**Of everything measured in e025, exactly one edge is both real AND net of
costs: buying after a daily 3σ crash and holding ~5 days (+2.38% net mean per
trade vs 0.09–0.19% cost).** It is rare (≈13 trades/year across the coin set),
so it is a low-frequency high-conviction trade, not a system to run daily.

Everything else falls into three honest buckets:

- **Real but untradeable**: weekday tilt (wrong-day spec, gross-negative),
  5m post-crash bounce (0.05% < 0.09% breakeven), 1h body-position reversion
  (~0.04% < 0.09%).
- **Real, robust, but not a trade**: volatility clustering and hour-of-day
  volatility — powerful *sizing* inputs with no directional leg.
- **Not yet measured**: relative strength (ag-10 pending).

The experiment's statistical headline — **crypto tails are fat, volatility
clusters, direction is near-unpredictable** — is fully confirmed. The
commercial headline is harsher: at 0.09% round trip, **most statistically real
edges in this dataset are too small to survive real costs.** Fees and slippage
are the hype filter, and they filtered out almost everything but the daily
crash.

**Caveat**: this is a statistical exercise on historical data, not trading
advice; past results do not predict the future. The crash-reversion verdict is
provisional until ag-08's out-of-sample backtest lands.

Files: `edge_ledger.csv` (machine-readable), this report, `beginners_guide.md`,
`session-log.md`. Verdict also in `done.txt`.
