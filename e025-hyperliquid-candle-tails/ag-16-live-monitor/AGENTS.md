# ag-16 — Live paper-trading monitor

The forward test of the e025 Daily Decline Reversion strategy. A cron job
runs `bin/paper_trade.py` daily at 00:15 UTC; it reads live 1d candles,
fires the two triggers (T1 crash, T2 low-volume down), logs paper trades,
and pushes phone notifications (via `e000-fundamentals/bin/notify.sh`) when a
trade opens or closes.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, notifications contract
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../STRATEGY.md](../STRATEGY.md) — the strategy being monitored (authoritative rules)
- [../ag-15-combined/AGENTS.md](../ag-15-combined/AGENTS.md) — validation results the monitor extends

## What the monitor does (do not change the rules)

- Reads live 1d candles (trailing 420 days) for the 12 coins from
  `candleSnapshot`.
- Causal statistics only: σ = stdev of trailing-365 daily returns;
  `v/median_v` = current volume vs 101-candle causal rolling median; `q20` =
  20th percentile of that ratio over the window.
- **T1** `ret < −3σ` · **T2** `ret < 0` AND `v/median_v < q20`, evaluated on
  the latest **closed** daily candle.
- Opens a paper trade (entry close, hold 5 days), closes it on exit day,
  P&L **net of taker fees** (0.045% per side).
- **Notifications**: `notify.sh done` on open and close. This is the point of
  the monitor — the user gets a phone push when a trigger fires.
- Idempotent per day (state in `output/paper_state.json`). `--dry-run`
  evaluates without writing state or notifying.

## Files

```
ag-16-live-monitor/
├── AGENTS.md
├── bin/paper_trade.py      # the monitor (stdlib only)
└── output/
    ├── paper_state.json    # idempotency state + pending trades
    ├── paper_trades.csv    # every paper trade, open and closed
    └── monitor.log         # cron output
```

## Verify the monitor is working

After the daily run (or a manual `zsh -c 'cd ... && python3 bin/paper_trade.py'`):

- `output/monitor.log` shows `monitor done: last_day=YYYY-MM-DD` for each run.
- `output/paper_trades.csv` accumulates rows; `paper_state.json` has the
  processed day and pending trades.
- On any trigger: a phone push arrives, and the pending trade appears in
  state. If the cron never fires (new machine), reinstall:
  `crontab -l | { cat; echo "15 0 * * * /usr/bin/zsh -c 'cd /home/vuos/code/p4/e025-hyperliquid-candle-tails/ag-16-live-monitor && python3 bin/paper_trade.py >> output/monitor.log 2>&1'"; } | crontab -`
- **PC off at run time**: cron does not run missed jobs. A `@reboot` entry
  re-runs the wrapper on next boot (it is idempotent per day and safe to
  re-run). Consequences: a missed trigger day is NOT backfilled (the
  monitor evaluates only the newest closed day — honouring the
  no-fake-trades rule and the forward-test design); pending exits DO catch
  up because they close by date (`exit_day <= today`). The daily auto-push
  is also a heartbeat: no commit on a date = the PC was off.

## Integrity rules

- Do not change the trigger thresholds, hold period, or universe without
  updating STRATEGY.md and ag-15 — the monitor is a forward validation of a
  frozen spec, not a tuning playground.
- Never backfill fake trades to make the log look active.
- `paper_trades.csv` is a research record — every row is real, dated, and
  auditable.

## Honest expectation

The historical edge is small and thin-sampled. The monitor may run for weeks
with no trigger and may produce losing streaks. That is the honest test.
When the CSV has 50+ closed trades, compare the realized expectancy to
ag-15's +0.55%/trade — that comparison IS the experiment's conclusion.
