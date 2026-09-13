#!/usr/bin/env bash
# e059 daily refresh: rebuild multiples.json/csv (DefiLlama free + CoinGecko public, keyless).
# Cron-friendly. Page shows LIVE/STALE badge from multiples.json as_of (>49h = STALE).
cd "$(dirname "$0")/.." || exit 1
echo "=== refresh $(date -Is)" >> refresh.log
cp page.html output/index.html
git log -1 --format=%h -- . > output/.commit 2>/dev/null
python3 -c "import json,time; print(json.dumps({'track':'e059','commit':open('output/.commit').read().strip(),'date':time.strftime('%Y-%m-%d %H:%M')}))" > output/version.json 2>/dev/null
rm -f output/.commit
timeout 1200 python3 bin/valuations.py >> refresh.log 2>&1
# keep the 6-week sales trend (offline, cached series only) after every rebuild
timeout 300 python3 bin/trend.py >> refresh.log 2>&1
echo "=== done $(date -Is) rc=$?" >> refresh.log
