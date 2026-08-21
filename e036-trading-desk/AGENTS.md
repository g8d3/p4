# e036 — Trading Desk

Mobile-friendly dashboard for the e025 paper-trading desk: one glance shows
open positions, closed trades, equity curve, and a live Hyperliquid price
ticker — from the phone, no SSH.

## What it serves

Reads (never modifies) e025's live outputs:

| File | Producer | Used for |
|---|---|---|
| `e025-hyperliquid-candle-tails/ag-16-live-monitor/output/paper_trades.csv` | ag-16 monitor | closed trades table |
| `e025-hyperliquid-candle-tails/ag-16-live-monitor/output/paper_state.json` | ag-16 monitor | open positions |
| `e025-hyperliquid-candle-tails/ag-16-live-monitor/output/monitor.log` | ag-16 monitor | recent activity feed |
| `EXECUTIVE_SUMMARY.md` | e025 | strategy context (static) |

Plus live Hyperliquid public API (`POST /info`, `allMids` + `candleSnapshot`)
for prices and the equity curve overlay. No API keys, read-only, no trading.

## Run

```bash
bin/desk.sh            # starts server on :8088 (background, logs to output/desk.log)
```

Then open `http://<machine-ip>:8088` from the phone.

## Agents

- **ag-01**: the desk (Flask + single-page UI, auto-refresh every 60s).

## Constraints

- Read-only over e025 outputs. If a file is missing/stale, show a warning
  badge instead of guessing.
- Mobile-first (the user browses from Android), dark theme, no JS framework —
  plain HTML/CSS/JS served by Flask.
- Live prices are fetched per request with a 5s cache; if Hyperliquid is
  unreachable the page must still render (stale badge).
