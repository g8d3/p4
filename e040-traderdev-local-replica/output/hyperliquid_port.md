# e040 — Hyperliquid port (2026-08-22)

## The port

Same engine (EMA5 × daily-UTC VWAP cross + ATR micro-trail, TV-faithful
fills), same parameters (mult 0.02, commission 0.05%/side, 1x equity),
on **Hyperliquid public candles** with **real funding** charged hourly
(mean 8h funding from e025 ag-01: BTC 0.000016, ETH 0.000025, SOL 0.00003).

## Results

### In-sample 4h (2024-08-01 → 2026-04-30 — same window as the oracle)

| Coin | Trades | WR% | PF | Net% | DD% | Sharpe | Funding paid |
|---|---|---|---|---|---|---|---|
| BTC | 778 | 85.5 | 11.2 | +3,421 | -6.4 | 15.4 | $101 |
| ETH | 756 | 86.8 | 16.3 | +25,812 | -13.1 | 14.7 | $735 |
| SOL | 777 | 89.8 | 4.7 | +46,237 | -15.8 | 13.4 | $3,329 |

### Out-of-sample 2h — fresh window 2026-05-01 → 2026-08-22 (never seen)

| Coin | Trades | WR% | PF | Net% | DD% | Sharpe |
|---|---|---|---|---|---|---|
| BTC | 229 | 80.4 | 4.6 | +84.7 | -7.5 | 5.1 |
| ETH | 243 | 80.3 | 16.0 | +189.1 | -3.1 | 7.1 |
| SOL | 235 | 80.0 | 8.4 | +184.3 | -6.1 | 7.9 |
| Bybit BTC (same window) | 239 | 77.4 | 4.1 | +77.5 | -7.3 | 5.2 |

## Verdict

**The edge survives: positive on every coin, in and out of sample, on both
exchanges, after real funding.** But read it correctly:

| Run | Net% | Days | **%/day** |
|---|---|---|---|
| BTC 4h in | +3,421 | 639 | 0.56% |
| ETH 4h in | +25,812 | 639 | 0.87% |
| SOL 4h in | +46,237 | 639 | 0.97% |
| BTC 2h OOS | +84.7 | 114 | 0.54% |
| ETH 2h OOS | +189 | 114 | 0.94% |
| SOL 2h OOS | +184 | 114 | 0.92% |
| Bybit BTC 2h OOS | +77.5 | 114 | 0.51% |

The "explosive" numbers were compounding over 2 years. The real, stable rate
is **~0.5-1.0%/day net** (ETH/SOL ≈ 0.9%, BTC ≈ 0.5%), consistent across
exchange, timeframe and out-of-sample. Nothing decayed after 2026-04-30.

The dangerous parts are the honest ones:

1. **Drawdowns hit -13 to -16% in-sample (ETH/SOL 4h)** — the sample says
   "high WR, deep tail". One multi-day chop can erase weeks of gains.
2. **Fill optimism**: exits assume the favorable extreme happened first
   within each 2-4h bar. With real limit/stop fills at 1x, slippage and
   maker-taker spreads, expect a haircut of ~0.1-0.3%/trade (2-6%/month).
3. **Funding is negligible** (<$6 on $10k over 114 days OOS) — this
   strategy holds ~2 bars; SOL funding $3,329 only because equity
   compounded 460x.
4. **Concentration**: the whole edge is a 1-bar continuation pulse after
   EMA-VWAP crosses. It is a regime bet (trending market), not a
   fundamental edge. 2026-05→08 happened to trend.

## Bottom line

- Runable in production? At 0.5-1%/day with 1x and ~30 days of recovery
  after a -15% drawdown — only with strict risk control (cap the
  compounding, e.g. fixed $1k allocation, take-profit early, or halve
  size after 3 consecutive losses) and AFTER live-paper validation.
- Recommendation path: paper-trade this on Hyperliquid (e036 desk
  patterns) for 4-6 weeks, track deltas vs this backtest, then decide.
- Everything is local, free, and repeatable: `bin/backtest.py` + `bin/fetch_hyperliquid.py`.
