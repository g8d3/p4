# e025 — Strategy Spec: Daily Decline Reversion (CRASH / LOW-VOLUME-DOWN)

The one strategy the experiment's evidence supports. **Research spec, not
financial advice.** Validated out-of-sample (ag-15) but on limited history —
paper-trade it first (ag-16 live monitor does exactly this).

## Thesis

Daily declines are temporary: a big down day, or a down day that volume did
not confirm, tends to be followed by positive returns over the next ~5 days.
Two independent signals, only 4% overlapping, combine into one rule.

## Universe

The 12 e025 coins (BTC, ETH, HYPE, SOL, PUMP, ZEC, XRP, LIT, DOGE, CRV, AAVE,
XMR). Optionally extend to any liquid perp with ≥1 year of daily history.

## Signals (evaluated daily, on the **closed** 1d candle)

- **T1 — Crash**: 1d close-to-close return `ret < −3 × σ`, where σ is the
  standard deviation of daily returns computed on the **trailing 365 days**
  (live analog of the walk-forward first-half σ used in ag-08/15).
- **T2 — Low-volume down**: 1d `ret < 0` AND `v / median_v < q20`, where
  `median_v` is the causal trailing median of daily volume over the last 101
  candles (min 30) and `q20` is the 20th percentile of that ratio over the
  same window. (Live analog of ag-14's "bottom quintile of down moves".)

Both use **causal** statistics only (past data). No lookahead.

## Trade rules

| Rule | Value |
|---|---|
| Entry | At the **close** of the day either trigger fires |
| Side | LONG only |
| Exit | At the close of the 5th day after entry (5 daily candles held) |
| Leverage | None |
| Sizing | Equal notional per coin × vol scaling (below) |
| Overlap | One position per coin at a time; if a coin triggers while in a position, skip |
| Fees assumed | Taker 0.045%/side (0.09% round trip); maker 0.018% |

## Position sizing (from ag-11 GARCH vol model)

Scale the base allocation inversely to forecast volatility. Using the
GARCH-forecast σ percentile for the timeframe you size on (1d):

| Forecast vol percentile | Multiplier |
|---|---|
| 10th (very calm) | ~1.14× base |
| 50th (median) | 1.00× base |
| 90th | ~0.74× base |
| 95th | ~0.64× base |
| 99th (extreme) | ~0.51× base |

Rationale: entries happen after crashes, which are *by construction* high-vol
moments — the vol scaling is what keeps the strategy's risk-per-trade flat.
A crash day is usually ~99th percentile vol → start from ~0.5× base and scale
up as vol normalizes.

## Risk management (lessons from ag-10)

- Crashes are **systemic** (96% co-movement): multiple coins trigger the same
  day and fall together. Treat same-day triggers across coins as ONE risk
  unit, not N independent trades.
- Expect −30%+ drawdowns on the pooled strategy (ag-15 max DD −32%).
- The long-only baseline lost −67% over the same window — this strategy is a
  *relative* edge, not a free lunch.

## Validation status (honest)

| Metric (OOS second half, net taker) | Value |
|---|---|
| Trades | 312 (155 distinct days) |
| Expectancy | +0.55%/trade |
| Win rate | 48.7% |
| Total return | +16.3% |
| Sharpe | 0.44 |
| Max drawdown | −32.4% |

Limitations: ~2.3y of history, one bear regime dominates the crash sample;
crash-only variant has just 28 trades. Regime drift is real (ag-12). Numbers
may not reproduce.

## Operation

The **ag-16-live-monitor** runs the signals daily against live candles, logs
paper trades, and pushes a phone notification when a trigger fires or a trade
closes. It accumulates forward out-of-sample evidence — the honest next test.

## Explicitly NOT this strategy

- Shorting rallies (tested, loses)
- Buying every crash regardless of size (weak alone)
- Intraday (5m/1h) versions of any reversion (all died at fees)
- Any weekend/weekday filter (unstable over time)
