# e040 — Parity verdict (2026-08-22)

## TL;DR

**The pattern is real and locally reproducible.** A bar-level pandas replica of
the trader.dev leaderboard's top strategy (EMA×VWAP cross + ATR micro-trail)
run on public Bybit klines over their exact window reproduces the same
phenomenon: +16,000 → +672,000% net, PF 6-19, WR 81-87%, DD 2-6%, trades
lasting ~2 bars. Their numbers are NOT an engine hallucination, but the
exact values are engine-flavored.

## Head-to-head (BTCUSDT 2h, 2024-08-01 → 2026-04-30)

| Variant | Source | Trades | WR% | PF | Net% | DD% | Sharpe |
|---|---|---|---|---|---|---|---|
| EMA5 ATR×0.02 | **their engine** | 1729 | 66.7 | 14.21 | 16,324 | 3.50 | 13.5 |
| EMA5 ATR×0.02 | local replica | 1439 | 81.0 | 6.46 | 22,025 | 5.53 | 19.3 |
| EMA5 ATR×0.01 | local replica | 1439 | 82.9 | 12.63 | 30,709 | 2.14 | 21.4 |
| EMA5 ATR×0.002 | local replica | 1439 | 83.8 | 18.52 | 36,078 | 2.14 | 22.1 |
| EMA4 ATR×0.015 | **their engine** | 1805 | 65.0 | 8.65 | 16,194 | 2.30 | 14.4 |
| EMA4 ATR×0.015 | local replica | 1491 | 81.8 | 9.45 | 29,848 | 2.25 | 24.6 |
| EMA5 ATR×0.02 (ETH) | local replica | 1382 | 87.0 | 14.96 | 672,423 | 6.16 | 20.1 |

Criteria from AGENTS.md (PF within 3×, Sharpe same order, net positive ≥500%,
trades within 2×): **MET** on every row. DD is the only metric that lands
tighter in their engine (3.5 vs 5.5) and on EMA4 it matches nearly exactly
(2.30 vs 2.25).

## What the forensics proved (1 credit — ground truth trade list)

Full trade-level fixture from their engine (`01M0NHGBJ5T0879XD2BY473T63`):

1. **Sizing**: qty = equity / price (1x, no leverage) — the broker profile
   hard-forced by their API is `percent_of_equity 100` + `margin 100`, i.e.
   1x effective, NOT the 10x I first assumed.
2. **Trail math**: clean trades confirm `exit = best ± ATR×0.02` with a
   ratchet, e.g. seq 2 short: entry 63395.7, best low 63295.1, exit
   63301.73 = best + 6.62 (= ATR 331 × 0.02) — exact.
3. **Signal parity**: their entry sequence matches my daily-anchored VWAP
   cross sequence almost bar-for-bar (same trades from 2024-08-02 onward),
   including the midnight-UTC session-reset whipsaws. ~17% trade-count delta
   comes from (a) their session anchor hour and (b) their engine's
   double-exit artifact.
4. **The engine's double-exit quirk**: on ~2% of rows the SAME entry has TWO
   exits (e.g. qty 0.032 + qty 0.169) because both `strategy.exit` lines
   (`Long Exit`, `Short Exit`) are executed every bar and their engine
   applies both to the open position sometimes (mirror trail: arm when the
   adverse extreme is revisited past the entry, exit at the bounce's
   extreme − T). Real TradingView would ignore the order with no matching
   entry id. Their avg loss (-$215) is 7× smaller than the TV-faithful
   replica's (-$1,478): **the quirk caps some losing trades** — part of their
   PF 14 vs my PF 6.5 is this accident, not the strategy.
5. **Effective trail distance is smaller than it looks**: their exit prices
   imply T ≈ $1.4-6.6 (ATR × 0.002-0.01 effective, not 0.02) — consistent
   with the mintick-tick conversion in their own EMA4 variant code
   (`round(atr*mult/syminfo.mintick)`). The smaller T, the tighter the
   winning tail; my grid reproduces their family best at mult 0.002
   (PF 18.5/DD 2.1/SR 22.1).
6. **Warmup**: engine backtests from 2024-07-07 (25d before the requested
   window) — indicator warmup is outside `fromTs`; barsEvaluated 7938 vs
   window bars 7644. Their first trade printed at 00:00 of window start.

## Honest limits (what local cannot claim yet)

- Intrabar sequence: fills assume the favorable extreme occurred before the
  retracement within the bar (same assumption TV's bar engine makes; the
  optimistic tail of this strategy lives in 1-bar moves).
- The "mirror exit" model I coded as a first hypothesis (both exits at
  conservative worst fill) collapses (PF 0.07) — the real artifact fires
  rarely. NOT included in final runs.
- VWAP anchor: midnight UTC matched their signals best; their exact session
  hour remains unverified (they run a private engine, no fixture for it).
- Hyperliquid port: NOT yet done (Bybit was tested for parity).

## Bottom line for the user

- You CAN backtest this locally forever with public data: zero credits,
  unlimited iterations, ~seconds per run. `bin/backtest.py` is the engine.
- The platform's remaining value: strategy discovery + their engine as an
  occasional second opinion. Each backtest there ≈ 1 credit; we spent 1.
- The real research question is NOT "does the backtest work" (it does) but
  "does a 1-bar micro-trail harvest survive on Hyperliquid with real fills
  and funding". That is the next experiment.

## Suggested next steps

1. Port to Hyperliquid (same EMA5/ATR×0.01 + daily-UTC VWAP), add funding
   cost + taker fee, compare BTC/ETH/SOL.
2. Out-of-sample: 2026-05-01 → now on Bybit (data already fetched).
3. Sensitivity: ema len 3-9, TFs 1h/4h, mul 0.001-0.05 — cheapest on local.
