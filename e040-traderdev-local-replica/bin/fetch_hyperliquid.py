#!/usr/bin/env python3
"""Fetch Hyperliquid candles (candleSnapshot) into CSV.

API: POST https://api.hyperliquid.xyz/info
  {"type":"candleSnapshot","req":{"coin":"BTC","interval":"4h","startTime":ms,"endTime":ms}}
Public, no auth, ~5000 candles per request (history retention caps:
~5000 for 2h/4h, full for 1d+). One request usually suffices.

Output: CSV header ts,o,h,l,c,v
"""
import argparse
import datetime as dt
import json
import time
import urllib.request

API = "https://api.hyperliquid.xyz/info"


def api(req):
    body = json.dumps(req).encode()
    r = urllib.request.Request(API, data=body,
                               headers={"Content-Type": "application/json",
                                        "User-Agent": "e040-replica/1.0"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch(coin, interval, start_ms, end_ms):
    rows = []
    cursor = start_ms
    step = INTERVAL_MS[interval]
    while cursor < end_ms:
        resp = api({"type": "candleSnapshot",
                    "req": {"coin": coin, "interval": interval,
                            "startTime": cursor, "endTime": end_ms}})
        if not isinstance(resp, list) or not resp:
            break
        rows.extend(resp)
        last_t = resp[-1]["t"]
        if last_t + step > end_ms or len(resp) < 5000:
            break
        cursor = last_t + step
        time.sleep(0.15)
    rows.sort(key=lambda r: r["t"])
    return rows


INTERVAL_MS = {"1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
               "30m": 1_800_000, "1h": 3_600_000, "2h": 7_200_000,
               "4h": 14_400_000, "8h": 28_800_000, "12h": 43_200_000,
               "1d": 86_400_000, "1w": 604_800_000}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coin", default="BTC")
    ap.add_argument("--interval", default="4h")
    ap.add_argument("--start", default="2024-06-01")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    start_ms = int(dt.datetime.fromisoformat(args.start).replace(
        tzinfo=dt.timezone.utc).timestamp() * 1000)
    end_ms = int(time.time() * 1000)
    print(f"=== fetch HL {args.coin} {args.interval} from {args.start} ===",
          flush=True)
    rows = fetch(args.coin, args.interval, start_ms, end_ms)
    out = args.out or f"output/hl_{args.coin.lower()}_{args.interval}.csv"
    import csv
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "o", "h", "l", "c", "v"])
        for r in rows:
            w.writerow([r["t"], r["o"], r["h"], r["l"], r["c"], r["v"]])
    first = dt.datetime.fromtimestamp(rows[0]["t"]/1000, tz=dt.timezone.utc)
    last = dt.datetime.fromtimestamp(rows[-1]["t"]/1000, tz=dt.timezone.utc)
    print(f"=== wrote {len(rows)} rows -> {out} ({first} -> {last}) ===")


if __name__ == "__main__":
    main()
