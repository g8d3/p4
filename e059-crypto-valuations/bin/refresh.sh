#!/usr/bin/env bash
# e059 daily refresh: rebuild multiples.json/csv (DefiLlama free + CoinGecko public, keyless).
# Cron-friendly. Page shows LIVE/STALE badge from multiples.json as_of (>49h = STALE).
cd "$(dirname "$0")/.." || exit 1
echo "=== refresh $(date -Is)" >> refresh.log
timeout 1200 python3 bin/valuations.py >> refresh.log 2>&1
# keep the 6-week sales trend (offline, cached series only) after every rebuild
timeout 300 python3 bin/trend.py >> refresh.log 2>&1
echo "=== done $(date -Is) rc=$?" >> refresh.log
