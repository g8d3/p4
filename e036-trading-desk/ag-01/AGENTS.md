# ag-01 — the desk

Flask app serving the e025 paper-trading desk as a mobile dashboard.

## Run

```bash
bin/desk.sh        # starts on :8088 if not already running (idempotent)
```

Open `http://192.168.0.93:8088` from the phone.

## Files

- `bin/desk.py` — server: reads e025 outputs (read-only), fetches live
  Hyperliquid mids (5s cache), computes equity + unrealized P/L.
- `bin/index.html` — single-page dark UI, auto-refresh 60s, SVG equity curve.
- `output/desk.log` — server log.

## Notes

- Equity model: $1,000 start, cumulative net% of closed trades + live
  unrealized% of open positions (equal-weight per-trade, matching e025's
  paper desk convention).
- `day_close()`: today → live mid; past days → Hyperliquid daily candle.
  Entry-day close is fetched from the candle at the entry day's timestamp.
- If Hyperliquid is unreachable: page renders with `STALE PRICES` badge.
- Server must be launched detached (`setsid`) — see e000 rule on background
  + self-wake; a shell timeout kills the process group otherwise.

## Self-command

```bash
tmux send-keys -t 36-1 "check desk: curl -s http://127.0.0.1:8088/api/data | head -c 200; tail -5 output/desk.log" Enter
```
