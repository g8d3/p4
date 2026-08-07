"""Download historical Binance klines and write them in the experiment CSV format.

Usage:
    python3 fetch_binance.py --symbol BTCUSDT --interval 5m --start 2026-01-01 \
        --end 2026-08-07 --out ../data/real_btc_5m.csv
"""

from __future__ import annotations

import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://api.binance.com/api/v3/klines"
INTERVALS_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}


def fetch(symbol: str, interval: str, start_ms: int, end_ms: int) -> list[list]:
    rows = []
    cur = start_ms
    while cur < end_ms:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": cur,
            "endTime": end_ms,
            "limit": 1000,
        }
        r = requests.get(BASE, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        rows.extend(data)
        cur = int(data[-1][0]) + INTERVALS_MS[interval]
        time.sleep(0.15)  # stay well under the rate limit
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="5m")
    parser.add_argument("--start", default="2026-01-01")
    parser.add_argument("--end", default="2026-08-07")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "real_btc_5m.csv")
    args = parser.parse_args()

    start_ms = int(datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)

    rows = fetch(args.symbol, args.interval, start_ms, end_ms)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for r in rows:
            ts = datetime.fromtimestamp(r[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00")
            w.writerow([ts, r[1], r[2], r[3], r[4], r[5]])

    prices = [float(r[4]) for r in rows]
    print(f"bars: {len(rows)}  range: {args.start}..{args.end}")
    print(f"close min={min(prices):,.2f} max={max(prices):,.2f} last={prices[-1]:,.2f}")
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
