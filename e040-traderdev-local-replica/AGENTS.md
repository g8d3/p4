# e040 — TraderDev Local Replica

**Goal**: replicate the trader.dev leaderboard's dominant strategy pattern
(EMA×VWAP cross + ATR trailing stop) on this machine, using public
exchange data, and validate parity against the platform's published metrics.

Why: the platform's top strategies are trivial in structure (see
`bin/README-oracle.md`). If a local replica reproduces the published
PF/Sharpe/drawdown within a sane band, the edge is real and fully ours —
no credits, unlimited iterations. If it does not, the platform numbers are
engine artifacts (their own engine quarantines "unreal" runs).

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, notifications
- [../e025-hyperliquid-candle-tails/AGENTS.md](../e025-hyperliquid-candle-tails/AGENTS.md) — background only (Hyperliquid vs Bybit data; e025's candles are for other experiments — do NOT reuse them here beyond sanity comparisons)

## The oracle (published, 2026-08-22)

| Name | Symbol | TF | net% | PF | SR | WR% | DD% | trades | window |
|---|---|---|---|---|---|---|---|---|---|
| EMA4-VWAP ATR0.015 Ticks TF0 | BTCUSDT | 2h | 16194 | 8.65 | 14.40 | 65.0 | 2.30 | 1805 | 2024-08-01 → 2026-04-30 |
| EMA5-VWAP ATR0.02 LS | BTCUSDT | 2h | 16331 | 14.20 | 13.66 | 67.0 | 3.50 | 1731 | 2024-08-01 → 2026-04-30 |
| EMA5-VWAP ATR0.015 LS | BTCUSDT | 2h | 15645 | 14.30 | 13.57 | 66.9 | 3.50 | 1727 | 2024-08-01 → 2026-04-30 |
| Cash Trail 2 LS (EMA9-VWAP) | SOLUSDT | 15m | 15943 | 3.68 | 15.22 | 57.1 | 5.04 | 3292 | (see notes) |
| Sleeve 4h SOL | SOLUSDT | 4h | 14434 | 6.32 | 5.62 | 69.9 | 6.74 | 727 | (see notes) |

Bar count sanity: 2024-08-01 → 2026-04-30 at 2h = 7644 bars ≈ their
`barsEvaluated` 7651 for the 2h runs. Frame the same window for parity.

## Engine semantics (from their own codegen rules — this IS the spec)

The strategy Pine v6 (from `get_strategy`):

```pinescript
//@version=6
strategy(..., pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  initial_capital=10000, default_qty_type=strategy.percent_of_equity,
  default_qty_value=100, margin_long=100, margin_short=100)
ema = ta.ema(close, N)        // N=4 or 5
vwap = ta.vwap(close)         // Pine v6: session-anchored (daily reset)
atr  = ta.atr(14)
longCondition  = ta.crossover(ema, vwap)
shortCondition = ta.crossunder(ema, vwap)
entry Long/Short on each cross; exits re-issued EVERY bar with
  trail distance = atr * mult (mult = 0.01 / 0.015 / 0.02)
```

Their codegen rules state the exit MUST be trail/stop based (never a
`low <= trail → strategy.close` hand-rolled flatten — that fills at bar
close, not at the stop, and their engine hard-rejects it). The canonical
form their engine promises parity with is the **adaptive ATR ratchet
trail**:

```
longTrail := max(longTrail, close - atr*mult)   // per bar, re-issued
exit at stop=longTrail  (fill intrabar when low <= longTrail)
```

Local-replica translation (bar-close data, no intrabar feed):

- Signals computed on bar close; entry filled at that bar's close (POC).
- Opposite cross **reverses**: close existing position at bar close,
  enter the other side same bar.
- Trail state (long): on each bar after entry,
  `stop = max(prev_stop, high_bound)` where the ratchet is seeded at
  `entry_close - atr*mult` and raised per bar by `close - atr*mult`
  clamped to not decrease; exit if `low <= stop` → fill at `stop` unless
  the bar gapped below (gap fill at `open`).
- Sizing: notional = 10 × equity (100% equity × margin 100, the broker
  profile their API hard-forces), commission 0.05% of notional per side,
  no slippage (platform default).
- Metrics: net profit %, profit factor, Sharpe (trades-based + equity),
  win rate %, max drawdown % (equity), trade count. Report BOTH raw and
  fee-less variants when diagnosing.

## Data (local, public, no keys)

Bybit public klines — the strategies were published ON Bybit perps
(`BYBIT:BTCUSDT.P`), so use the exact symbol + window for parity:

```
GET https://api.bybit.com/v5/market/kline
  ?category=linear&symbol=BTCUSDT&interval=120&start=<ms>&end=<ms>&limit=1000
```

- interval strings: 15, 60, 120, 240 (minutes).
- Public endpoint, no auth, ~1000 candles/request → paginate by `start =
  last_t + interval_ms`. Rate limit is generous; 200ms between pages.
- Interval 120 over 2 years ≈ 8.8k candles ≈ 9 pages.
- Alternative/additional: Hyperliquid `candleSnapshot` (see e025) — but
  note its 5m/1h history is capped at ~5000 candles; 2h/4h go back further
  and 1d/1w are full. Bybit is still the true parity source.

## Deliverables

| File | Contents |
|---|---|
| `output/btcusdt_2h.csv` | Bybit klines (ts,o,h,l,c,v) full fetched range |
| `output/trades_<variant>.csv` | Per-trade log: entry/exit time, dir, entry/exit price, PnL% |
| `output/equity_<variant>.csv` | Equity curve per bar |
| `output/metrics.json` | All metrics for every variant in one file |
| `output/report.md` | Parity verdict vs oracle, deltas explained, honest conclusion |
| `done.txt` | Final state |

## Success criteria

1. On BTCUSDT 2h, same window (2024-08-01 → 2026-04-30), Ema5/ATR0.02:
   PF within 3× of 14.2, Sharpe same order (≥5), net% positive ≥ 500%,
   trade count within 2× of 1731. Ratcheting the replicas to exact parity
   is the point of the diagonal band — document direction of each delta.
2. If margins hold for the EMA-family family across SYMBOLS too (SOL),
   the pattern is robust; if only BTC 2h reproduces, that is the finding.

## Pitfalls

- **VWAP anchor**: Pine v6 `ta.vwap(close)` with no anchor = daily-session
  cumulative VWAP (resets 00:00 UTC on 24/7 markets). A rolling N-bar VWAP
  is a DIFFERENT strategy — do not silently substitute. Make the anchor
  configurable (`daily` vs `weekly` vs `rolling_N`) and report which was
  used; default `daily`.
- **EMA warmup**: first ~50 bars (EMA 5 + ATR 14) must have concrete values
  before any signal; start backtest at the oracle window start.
- **Candle timezone**: Bybit kline `start` is epoch ms (UTC). UTC day
  boundary for VWAP reset = midnight UTC.
- **Known honest limits vs true TV parity**: no intrabar feed → trailing
  stop fill uses bar high/low extremes; TV would use its own tick data.
  Expect (and document) a parity gap that should shrink as mult grows
  (larger trails = less intrabar sensitivity). This gap IS the experiment's
  second question, not a bug.
- **The engine quarantines "unreal" runs** and removes martingale/grid from
  /browse — the oracle numbers are filtered, not exhaustive. Use `notes.md`
  to record anything weird (e.g. a strategy with suspicious PF > 20).

## Commands

```bash
python3 bin/fetch_bybit.py --symbol BTCUSDT --interval 120 --start 2024-07-01 > output/fetch.log 2>&1 &
python3 bin/backtest.py --csv output/btcusdt_2h.csv --ema 5 --mult 0.02 \
  --window 2024-08-01:2026-04-30 --tag ema5_atr002
```

The backtester is pure pandas/numpy — takes seconds, no GPU, no network.

## Read-only platform usage (sparingly, one version)

The TraderDev MCP key (`pk_…`, 1000 credits/week) stays for oracle
queries only — reads (get_strategy, search_strategies) have not consumed
credits in testing. Backtests/optimizations on their side DO consume
credits: never auto-run them; use them only to double-check a local result
and note the credit cost. Key is kept in `~/secrets/` if present, otherwise
read from the session note — NEVER commit it to git.

## Cadence / automation

This experiment runs as short orchestrator-led py runs (seconds). If
spawned as tmux agents later, give each a 60-min deadline, window `40-<n>`,
and self-wake after every command (see baseline pattern in
[../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md)).


## Paper-trading monitors (live)

### TSMR vol-targeting monitor (current, live)

`bin/paper_tsmr.py` — runs daily at 00:30 via cron
(`bin/paper_tsmr_cron.sh`, installed). $30k paper, BTC/ETH/SOL/XRP/DOGE:
- weekly rebalance at the last CLOSED daily candle; signal per coin: 30d
  return > 0 -> long at vol-targeted weight (20% annualized, 30d realized
  vol, capped 1.0), else flat; equal allocation; 0.035% taker fee per side.
- daily mark-to-market at closes; state in output/tsmr_paper_state.json,
  log output/tsmr_paper.log, phone notification on each rebalance.
- **Auto-commit/push**: the cron wrapper commits any output changes and
  pushes to GitHub (same pattern as
  `e025/ag-16-live-monitor/bin/paper_trade_cron.sh`) — check `tsmr_paper.log`
  for `auto-push OK`. If a change sits uncommitted, the cron didn't push.

### 1-day EMA×VWAP monitor (superseded)

`bin/paper_1d.py` — replaced by the TSMR monitor; no longer in crontab.
For BTC/ETH/SOL with $10k paper each:
- signal: EMA5 x weekly-anchored VWAP cross on the last CLOSED daily candle
  (same as backtest), entry at that close.
- exit: trail only (arm at high >= entry + ATR*0.02, stop = best - T,
  gap -> open) or reversal at close. NO stop loss (by design — MC showed
  worst realized trade < 2% of equity).
- fees 0.05% per side, 1x sizing, notifications via notify.sh on every
  open/close, state in output/paper_state.json, log output/paper_trades_1d.csv.

Purpose: compare live drift vs the 0.15-0.29%/day backtest expectation and
catch a regime change (the one risk Monte Carlo cannot test). Check weekly.


## Notification discipline for monitors (learned 2026-08-22)

- A monitor script that can notify the phone MUST be validated with a FULL
  end-to-end run (not only dry-run) before being enabled; dry-runs that
  happen to have no open position do NOT exercise the trading arithmetic.
- Error notifications: at most ONE per day per monitor (dedupe via state),
  all details only in the local log.
- Never notify errors for a code path that hasn't been exercised by a test.
