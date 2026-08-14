#!/usr/bin/env python3
"""Backfill full funding-rate history for a set of coins from Hyperliquid.

Endpoint: POST /info {"type":"fundingHistory","coin":X,"startTime":MS,"endTime":MS}
- Returns up to 500 entries per request (hourly funding payments since
  exchange launch ~May 2023).
- Paginate forward: next startTime = last entry time + 1ms.
- No API key needed (public endpoint).

Usage: python3 bin/backfill_funding.py [out_dir] [coins...]
  out_dir  default: output
  coins    default: the 12 e025 coins (BTC ETH HYPE SOL PUMP ZEC XRP LIT DOGE CRV AAVE XMR)
"""
import json
import sys
import time
import urllib.request
import csv

URL = "https://api.hyperliquid.xyz/info"
LAUNCH = 1682900000000  # ~2023-05-01 UTC, exchange launch floor
DEFAULT_COINS = ["BTC", "ETH", "HYPE", "SOL", "PUMP", "ZEC",
                 "XRP", "LIT", "DOGE", "CRV", "AAVE", "XMR"]


def fetch(coin, start, end, retries=3):
    payload = json.dumps({"type": "fundingHistory", "coin": coin,
                          "startTime": start, "endTime": end}).encode()
    req = urllib.request.Request(URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if attempt == retries - 1:
                print(f"  ERR {coin} {start}->{end}: {e}", file=sys.stderr)
                return None
            time.sleep(1 + attempt)
    return None


def backfill(coin):
    rows, start = [], LAUNCH
    while True:
        chunk = fetch(coin, start, int(time.time() * 1000))
        if not chunk:
            break
        rows.extend(chunk)
        if len(chunk) < 500:
            break
        start = chunk[-1]["time"] + 1  # next window after last entry
        print(f"  {coin}: {len(rows)} entries so far, last={start}")
    return rows


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    coins = sys.argv[2:] or DEFAULT_COINS
    path = f"{out_dir}/funding_raw.csv"
    total = 0
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["coin", "time_ms", "fundingRate", "premium"])
        for coin in coins:
            rows = backfill(coin)
            for r in rows:
                w.writerow([coin, r["time"], r["fundingRate"], r["premium"]])
            print(f"=== {coin}: {len(rows)} funding entries")
            total += len(rows)
    print(f"DONE: {len(coins)} coins, {total} rows -> {path}")


if __name__ == "__main__":
    main()
