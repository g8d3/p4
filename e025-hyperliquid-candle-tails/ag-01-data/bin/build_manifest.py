#!/usr/bin/env python3
"""Build manifest.json from an existing candles_raw.csv (no re-fetch)."""
import csv
import json
import sys
import time
from collections import defaultdict

COINS = ["BTC", "ETH", "HYPE", "SOL", "PUMP", "ZEC", "XRP", "LIT", "DOGE",
         "CRV", "AAVE", "XMR"]
TFS = ["5m", "1h", "1d", "1w"]
INTERVAL_MS = {"5m": 300_000, "1h": 3_600_000, "1d": 86_400_000, "1w": 604_800_000}


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    fetch_start_wall = sys.argv[2] if len(sys.argv) > 2 else "unknown"
    fetch_end_wall = sys.argv[3] if len(sys.argv) > 3 else "unknown"

    rows = defaultdict(list)
    with open(f"{out_dir}/candles_raw.csv") as f:
        r = csv.DictReader(f)
        for line in r:
            rows[(line["coin"], line["tf"])].append(line)

    # Dedupe by (coin, tf, t_ms) and sort
    dedup = {}
    for key, ls in rows.items():
        seen = set()
        for row in ls:
            k = (key[0], key[1], row["t_ms"])
            if k not in seen:
                seen.add(k)
                dedup.setdefault(key, []).append(row)
        dedup[key].sort(key=lambda x: int(x["t_ms"]))

    manifest = {
        "fetch_start": fetch_start_wall,
        "fetch_end": fetch_end_wall,
        "coins": COINS,
        "timeframes": TFS,
        "history_floor": "2023-01-01T00:00:00+00:00",
        "per_pair": {},
        "api_errors": {},
        "notes": {
            "retention": {
                "5m": "API retains ~most recent 5000 candles (~17 days for BTC)",
                "1h": "API retains ~most recent 5000 candles (~7 months for BTC)",
                "1d": "full history since exchange launch",
                "1w": "full history since exchange launch",
            },
            "pre_launch_volume": "1d/1w candles before the coin's listing have v=0 (synthetic backfill)",
        },
    }
    for coin in COINS:
        for tf in TFS:
            rows_key = dedup.get((coin, tf), [])
            if not rows_key:
                manifest["per_pair"][f"{coin}:{tf}"] = {"rows": 0, "expected": 0,
                                                        "error": "MISSING"}
                continue
            real = [r for r in rows_key if float(r["v"]) > 0]
            span = (int(rows_key[-1]["t_ms"]) - int(rows_key[0]["t_ms"])) / INTERVAL_MS[tf] + 1
            manifest["per_pair"][f"{coin}:{tf}"] = {
                "rows": len(rows_key),
                "expected": round(span, 1),
                "v0_count": len(rows_key) - len(real),
                "first_real_t": real[0]["t_ms"] if real else None,
                "first_real_ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(int(real[0]["t_ms"]) / 1000)) if real else None,
                "last_t": rows_key[-1]["t_ms"],
                "last_ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(int(rows_key[-1]["t_ms"]) / 1000)),
                "gap_count": _count_gaps(rows_key, INTERVAL_MS[tf]),
            }

    with open(f"{out_dir}/manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"manifest written for {sum(len(v) for v in dedup.values())} rows")


def _count_gaps(rows, interval):
    if len(rows) < 2:
        return 0
    gaps = 0
    for a, b in zip(rows, rows[1:]):
        diff = int(b["t_ms"]) - int(a["t_ms"])
        gaps += max(0, diff // interval - 1)
    return gaps


if __name__ == "__main__":
    main()
