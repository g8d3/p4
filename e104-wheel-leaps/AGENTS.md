# e104-wheel-leaps

Wheel → LEAPS tracker for the MarketMovesMatt $10k→$100k system: one page that
checks the system's own entry rules live and backtests them.

## What it is

Static page + 2-step pipeline. No keys, no framework, English everywhere.

- `needs.json` — port, tickers, Yahoo endpoints, RSI parameters. No hardcodes.
- `bin/fetch.py` — Yahoo v8 chart (weekly 5y + daily 1y) → `data/raw/<T>.json`.
- `bin/compute.py` — weekly RSI-14, red-day flag, RSI<30 history + 6/12mo
  forward returns → `site/data.json`.
- `site/` — `index.html` + `app.js` + `style.css`, reads `data.json`.
  Includes a wheel-income calculator (the page's user action).
- `bin/serve.sh` — review server on port from `needs.json`, logs to `output/server.log`.

## Refresh

```bash
python3 bin/fetch.py && python3 bin/compute.py
bin/serve.sh
```

## Rules

- Data cells carry source (Yahoo) + timestamp; missing = null with reason.
- LEAPS options history is NOT available free — forward underlying returns
  are shown as a proxy and labeled as such. Never present proxy as option P&L.
