#!/usr/bin/env python3
"""Download Yahoo v8 weekly+daily series for tickers in needs.json."""
import json, urllib.request, os, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
needs = json.load(open(os.path.join(ROOT, "needs.json")))
UA = {"User-Agent": "Mozilla/5.0"}

def get(symbol, interval, rng):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={rng}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)

os.makedirs(os.path.join(ROOT, "data", "raw"), exist_ok=True)
for t in needs["tickers"]:
    for interval, rng in [("1wk", needs["weekly_range"]), ("1d", needs["daily_range"])]:
        try:
            data = get(t, interval, rng)
            out = os.path.join(ROOT, "data", "raw", f"{t}_{interval}.json")
            json.dump(data, open(out, "w"))
            print(f"ok {t} {interval}: {out}")
        except Exception as e:
            print(f"FAIL {t} {interval}: {e}")
        time.sleep(2)
