#!/bin/bash
# Daily live refresh: S&P daily + weekly bars, recompute, snapshot tracking log.
# No agents, no audits, no gates. ~1-2 min CPU.
set -e
cd "$(dirname "$0")/.."
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
curl -s -m 90 "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500" -o data/raw/fred_sp500.csv
curl -s -m 120 -A "$UA" "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?period1=0&period2=9999999999&interval=1wk&events=div" -o data/raw/yahoo_spx_weekly.json
.venv/bin/python bin/compute.py
.venv/bin/python -c "
import json, datetime
d = json.load(open('site/midterms.json'))
l = d['live']
line = f\"{datetime.date.today().isoformat()} spx={l['spx']} asof={l['asof']} days_to_2026={l['days_to']}\"
open('data/tracking.log', 'a').write(line + chr(10))
print(line)
"
