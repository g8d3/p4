# Oracle notes (2026-08-22)

Published strategy snapshots pulled from the TraderDev MCP leaderboard
(`search_strategies`, sort=profit) — see e040 AGENTS.md "The oracle".

## The dominant family (8 of top 15)

All owned by "EMA{V} × VWAP + ATR trail {mult}":

```
ema  = ta.ema(close, V)        // V = 4 or 5
vwap = ta.vwap(close)          // Pine v6 = session-anchored VWAP
atr  = ta.atr(14)
long  = crossover(ema, vwap)
short = crossunder(ema, vwap)
entry long/short at close; every bar: strategy.exit(
  trail_points = atr*mult, trail_offset = atr*mult)
// alternative formulation (ticks): trailUnits = max(1, round(atr*mult/mintick))
```

Variations found in the leaderboard: mult ∈ {0.01, 0.015, 0.02}, EMA len ∈
{4, 5, 9}, TFs ∈ {15m SOL, 30m BTC, 1h BTC, 2h BTC, 4h SOL}. The 15m/30m
variants use `strategy.close("S")` before the opposite entry (explicit
reversal); the 2h variants rely on TV's automatic reversal.

## Reading the numbers with a skeptic's eye

- PF 8-16 with a micro-trail (0.015-0.02 ATR) is *internally consistent*:
  losers are clipped at entry −(ATR×mult) almost immediately (~$8 on 2h BTC),
  winners ride the whole trend until a micro-pullback — avg win >> avg loss.
- The platform quarantines runs whose parity re-run drifts (their own
  quarantine page says so) and keeps martingale/grid off /browse. So the
  public leaderboard is "plausible-looking results only" — survivorship up
  to a point. This is exactly why a local replica is worth building.
- Sharpe ~13-14: computed per-trade, not annualized. Do not compare to a
  yearly Sharpe of 1-2; compare mean/std in the same units.

## Cross-checking plan

1. BTCUSDT 2h identical window (2024-08-01 → 2026-04-30), Bybit klines:
   EMA5/0.02, EMA5/0.015, EMA4/0.015, EMA5/0.01.
2. SOLUSDT family: 15m EMA9/2 (Cash Trail), 4h (Sleeve).
3. If parity holds on Bybit, port the *pattern* to Hyperliquid as an
   extension experiment.
