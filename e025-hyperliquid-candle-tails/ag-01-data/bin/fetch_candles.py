#!/usr/bin/env python3
"""Fetch full available Hyperliquid candle history for the experiment coins.

API: POST https://api.hyperliquid.xyz/info  {"type":"candleSnapshot", ...}
Max 5000 candles per request; the API retains only the most recent ~5000
candles for 5m/1h and full history for 1d/1w. Pagination starts at the
exchange-launch floor (2023-01-01) and advances startTime by interval until
the API returns nothing newer.

Output: output/candles_raw.csv (long format), output/manifest.json
"""
import csv
import json
import sys
import time
import urllib.request

API = "https://api.hyperliquid.xyz/info"
COINS = ["BTC", "ETH", "HYPE", "SOL", "PUMP", "ZEC", "XRP", "LIT", "DOGE",
         "CRV", "AAVE", "XMR"]
TFS = ["5m", "1h", "1d", "1w"]
FLOOR = 1672531200000  # 2023-01-01 UTC

INTERVAL_MS = {"5m": 300_000, "1h": 3_600_000, "1d": 86_400_000, "1w": 604_800_000}


def api(req):
    body = json.dumps(req).encode()
    for attempt in range(4):
        try:
            r = urllib.request.Request(API, data=body,
                                       headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(r, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt == 3:
                return {"_error": f"{type(e).__name__}: {e}"}
            time.sleep(2 * (attempt + 1))
    return {"_error": "unreachable"}


def fetch_coin_tf(coin, tf):
    """Fetch all candles for a coin+tf, paginating forward. Returns (rows, errors)."""
    rows = []
    errors = []
    start = FLOOR
    now = int(time.time() * 1000)
    page = 0
    while True:
        page += 1
        resp = api({"type": "candleSnapshot",
                    "req": {"coin": coin, "interval": tf,
                            "startTime": start, "endTime": now}})
        print(f"=== {coin} {tf} page {page} start={start} got={len(resp) if isinstance(resp, list) else 'ERR'} ===",
              flush=True)
        if not isinstance(resp, list):
            errors.append(f"page {page}: {resp.get('_error', resp)}")
            break
        if not resp:
            break
        rows.extend(resp)
        last_t = resp[-1]["t"]
        # API returns the most recent ~5000 candles of the window; if the page
        # reached the current time, there is nothing newer to paginate to.
        if last_t + INTERVAL_MS[tf] > now:
            break
        if len(resp) < 5000:
            break
        if start == last_t:
            errors.append(f"page {page}: no forward progress")
            break
        start = last_t + INTERVAL_MS[tf]
        time.sleep(0.1)
    return rows, errors


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "output"
    fetch_start = int(time.time() * 1000)
    fetch_start_wall = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    all_rows = {}
    errors = {}
    for coin in COINS:
        for tf in TFS:
            rows, errs = fetch_coin_tf(coin, tf)
            all_rows[(coin, tf)] = rows
            errors[(coin, tf)] = errs
            time.sleep(0.1)
    fetch_end = int(time.time() * 1000)
    fetch_end_wall = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # Dedupe defensively by (coin, tf, t_ms)
    dedup = {}
    for (coin, tf), rows in all_rows.items():
        seen = set()
        for r in rows:
            key = (coin, tf, r["t"])
            if key not in seen:
                seen.add(key)
                dedup.setdefault((coin, tf), []).append(r)

    # Sort by time
    for key in dedup:
        dedup[key].sort(key=lambda r: r["t"])

    with open(f"{out_dir}/candles_raw.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["coin", "tf", "t_ms", "o", "h", "l", "c", "v"])
        for coin in COINS:
            for tf in TFS:
                for r in dedup[(coin, tf)]:
                    w.writerow([coin, tf, r["t"], r["o"], r["h"], r["l"], r["c"], r["v"]])

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
            "pre_launch_volume": "1d/1w candles before the coin's listing have v=0 (synthetic backfill)"
        },
    }
    for coin in COINS:
        for tf in TFS:
            rows = dedup[(coin, tf)]
            real = [r for r in rows if float(r["v"]) > 0]  # v>0 = actually listed/traded
            span = (rows[-1]["t"] - rows[0]["t"]) / INTERVAL_MS[tf] + 1 if rows else 0
            manifest["per_pair"][f"{coin}:{tf}"] = {
                "rows": len(rows),
                "expected": round(span, 1),
                "v0_count": len(rows) - len(real),
                "first_real_t": real[0]["t"] if real else None,
                "first_real_ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(real[0]["t"] / 1000)) if real else None,
                "last_t": rows[-1]["t"] if rows else None,
                "last_ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(rows[-1]["t"] / 1000)) if rows else None,
                "gap_count": _count_gaps(rows, INTERVAL_MS[tf]),
            }
            if errors[(coin, tf)]:
                manifest["api_errors"][f"{coin}:{tf}"] = errors[(coin, tf)]

    with open(f"{out_dir}/manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    total = sum(len(v) for v in dedup.values())
    print(f"DONE: {total} candles written, manifest written")


def _count_gaps(rows, interval):
    """Count missing candles between consecutive timestamps (v>0 region only)."""
    if len(rows) < 2:
        return 0
    gaps = 0
    for a, b in zip(rows, rows[1:]):
        diff = b["t"] - a["t"]
        gaps += max(0, diff // interval - 1)
    return gaps


if __name__ == "__main__":
    main()
