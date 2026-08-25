# Benchmarks — putting the e022 v2 baseline in context

Plain-language summary for the course. The baseline numbers (+3.64% / +1.71%)
mean almost nothing until compared with what you could get elsewhere.

## Comparison table (same data, same time windows)

| Strategy | Period | Return | Max DD | Sharpe (ann.) |
|---|---|---|---|---|
| **e022 v2 grid** | BTC 5m, 1y (2025-08 → 2026-08) | **+3.64%** | −7.16% | 1.42 |
| Buy & hold BTC | same | **−44.01%** | −53.84% | −1.05 |
| DCA BTC monthly (30d) | same | −21.12% | — | — |
| T-bills (approx. 4-5%/yr) | same | ≈ +4% | ~0 | — |
| | | | | |
| **e022 v2 grid** | BTC 1h, 4y | **+1.71%** | −7.55% | 0.66 |
| Buy & hold BTC | same | **+181.00%** | −53.74% | 0.79 |
| DCA BTC monthly (30d) | same | +47.48% | — | — |
| T-bills (approx. 4-5%/yr) | 4y | ≈ +17-20% | ~0 | — |

## What this actually means

1. **The grid is a market-neutral, defensive machine, not a return machine.**
   In the one bear year (5m window) it made +3.64% while BTC dumped −44% — it
   beat buy-and-hold by ~47 points **because it mostly sits in cash and only
   trades the calm part of the market**.
2. **In the 4-year window it is embarrassingly weak on absolute return** (+1.7%
   vs +181% B&H). Its only defense: max drawdown −7.6% vs BTC's −53.7%, and it
   is *positive after fees* (most grid families lose after fees).
3. **Risk-adjusted, it is respectable in the bear window** (Sharpe 1.42 vs
   −1.05 for B&H) and mediocre in the bull window (0.66 vs 0.79).
4. **An investor choosing this portfolio allocation should ask**: why not
   T-bills? On the 5m window the grid barely beats cash (≈+4% vs +3.64%) but
   holds market risk; on 1h 4y T-bills crush it. The grid's ONLY credible
   claim today: *positive, low-drawdown alternative to being fully long in
   calm/bear markets*.

## Consequence for the e043 mission

The user's ladder features (NAUTILUS_A_PLAN Test 3) will be judged against
v2's +3.64%/+1.71%, but the *true* goal for the product/course framing is:
can the ladder family beat this benchmark AND make the +1.71% (4y) respectably
closer to or above T-bills? A "win" that stays at +2% over 4 years is not a
sellable edge; we keep that explicit in every verdict.
