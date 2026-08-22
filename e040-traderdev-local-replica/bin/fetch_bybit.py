#!/usr/bin/env python3
"""Fetch Bybit public klines (linear perps) into a CSV.

API: GET https://api.bybit.com/v5/market/kline?category=linear&symbol=X&interval=120&start=<ms>&end=<ms>&limit=1000
Public, no auth. ~1000 candles/request, paginate forward from --start.

Output: <out> CSV with header ts,o,h,l,c,v (ts = open time epoch ms).
"""
import argparse
import csv
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.bybit.com/v5/market/kline"
PAGE = 1000


def fetch(symbol, interval, start_ms, end_ms):
    """Paginate BACKWARD: the API returns the most recent ~1000 candles of
    the [start, end] window, so step `end` down page by page."""
    step = interval * 60_000
    rows = []
    seen = set()
    window_end = end_ms
    while window_end > start_ms:
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": str(interval),
            "start": str(start_ms),
            "end": str(window_end),
            "limit": str(PAGE),
        }
        url = API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json_loads(r.read().decode())
                break
            except Exception as e:
                if attempt == 2:
                    print(f"ERROR {symbol} {interval} end={window_end}: {e}", flush=True)
                    return rows
                time.sleep(2 * (attempt + 1))
        else:
            break
        if data.get("retCode") != 0:
            print(f"API error {symbol} {interval}: {data.get('retMsg')}", flush=True)
            break
        batch = data["result"]["list"]
        if not batch:
            break
        page_min_t = min(int(k[0]) for k in batch)
        for k in batch:  # API returns newest first
            t = int(k[0])
            if t not in seen:
                seen.add(t)
                rows.append((t, float(k[1]), float(k[2]),
                             float(k[3]), float(k[4]), float(k[5])))
        if page_min_t <= start_ms or len(batch) < PAGE:
            break
        window_end = page_min_t - step
        print(f"  page: {len(rows)} rows, window_end={page_min_t}", flush=True)
        time.sleep(0.2)
    return rows


def json_loads(s):
    import json
    return json.loads(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--interval", type=int, default=120, help="minutes")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD (UTC)")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD (UTC)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    import datetime as dt
    start_ms = int(dt.datetime.fromisoformat(args.start).replace(
        tzinfo=dt.timezone.utc).timestamp() * 1000)
    if args.end:
        end_ms = int(dt.datetime.fromisoformat(args.end).replace(
            tzinfo=dt.timezone.utc).timestamp() * 1000)
    else:
        end_ms = int(time.time() * 1000)

    print(f"=== fetch {args.symbol} {args.interval}m {args.start} -> {args.end or 'now'} ===", flush=True)
    rows = fetch(args.symbol, args.interval, start_ms, end_ms)
    rows.sort(key=lambda r: r[0])
    out = args.out or f"{args.symbol.lower()}_{args.interval}m.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "o", "h", "l", "c", "v"])
        w.writerows(rows)
    print(f"=== wrote {len(rows)} rows -> {out} ===")


if __name__ == "__main__":
    main()
