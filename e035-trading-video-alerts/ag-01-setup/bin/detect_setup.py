#!/usr/bin/env python3
"""Detect S/R proximity setups on Hyperliquid and emit the video payload.

Reads live 1h candles (public REST, no key), finds fractal-pivot S/R levels
(same method as e022), and fires when price sits within PROXIMITY_PCT of a
confirmed level. Writes output/setup.json or output/no_setup.json.
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.hyperliquid.xyz/info"
COINS = ["BTC", "ETH", "SOL"]
TF = "1h"
TF_MS = 3_600_000
HISTORY_BARS = 336          # ~14 days
PIVOT_WINDOW = 5            # fractal window (e022 default)
CLUSTER_TOL_PCT = 0.30      # cluster pivots within 0.3%
MIN_TOUCHES = 2             # confirmed level needs >= 2 clustered pivots
PROXIMITY_PCT = 0.35        # fire when within 0.35% of a level
CANDLES_IN_PAYLOAD = 72     # last 72 candles embedded for the video

OUT_DIR = Path(__file__).resolve().parent.parent / "output"


def post(payload):
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_candles(coin):
    end = int(time.time() * 1000)
    start = end - HISTORY_BARS * TF_MS
    rows = post({"type": "candleSnapshot",
                 "req": {"coin": coin, "interval": TF,
                         "startTime": start, "endTime": end}})
    out = []
    for c in rows:
        out.append({"t": int(c["t"]), "o": float(c["o"]), "h": float(c["h"]),
                    "l": float(c["l"]), "c": float(c["c"]), "v": float(c["v"])})
    out.sort(key=lambda x: x["t"])
    return out


def atr_pct(candles, period=14):
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["h"], candles[i]["l"], candles[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if not trs:
        return 0.0
    atr = sum(trs[-period:]) / min(period, len(trs))
    return atr / candles[-1]["c"] * 100.0


def find_levels(candles):
    """Fractal pivots -> clustered levels with touch counts."""
    pivots = []
    w = PIVOT_WINDOW
    for i in range(w, len(candles) - w):
        win = candles[i - w:i + w + 1]
        if candles[i]["h"] == max(c["h"] for c in win):
            pivots.append(candles[i]["h"])
        if candles[i]["l"] == min(c["l"] for c in win):
            pivots.append(candles[i]["l"])
    pivots.sort()
    clusters = []
    for p in pivots:
        if clusters and abs(p - clusters[-1]["px"]) / p * 100 <= CLUSTER_TOL_PCT:
            c = clusters[-1]
            c["touches"] += 1
            c["px"] = (c["px"] * (c["touches"] - 1) + p) / c["touches"]
        else:
            clusters.append({"px": p, "touches": 1})
    return [c for c in clusters if c["touches"] >= MIN_TOUCHES]


def detect_coin(coin, force=False):
    candles = fetch_candles(coin)
    if len(candles) < 60:
        raise RuntimeError(f"{coin}: only {len(candles)} candles")
    price = candles[-1]["c"]
    px_24h = candles[-25]["c"] if len(candles) > 25 else candles[0]["c"]
    change_24h = (price - px_24h) / px_24h * 100.0
    levels = find_levels(candles)
    best = None
    for lv in levels:
        dist = abs(price - lv["px"]) / price * 100.0
        if not force and dist > PROXIMITY_PCT:
            continue
        cand = {
            "setup": "support_test" if lv["px"] < price else "resistance_test",
            "level": round(lv["px"], 2),
            "distance_pct": round(dist, 3),
            "touches": lv["touches"],
        }
        key = (cand["distance_pct"], -cand["touches"])
        if best is None or key < (best["distance_pct"], -best["touches"]):
            best = cand
    result = {
        "coin": coin,
        "price": round(price, 2),
        "change_24h_pct": round(change_24h, 2),
        "tf": TF,
        "atr_pct": round(atr_pct(candles), 3),
        "levels_all": [{"px": round(l["px"], 2), "touches": l["touches"]}
                       for l in sorted(levels, key=lambda x: -x["touches"])][:8],
        "candles": candles[-CANDLES_IN_PAYLOAD:],
    }
    if best:
        result.update(best)
        return result, True
    return result, False


def main():
    force = "--force" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = []
    for coin in COINS:
        try:
            res, fired = detect_coin(coin, force=force)
            candidates.append((fired, res))
            state = f"{res.get('setup', 'no setup')}" if fired else "quiet"
            print(f"{coin}: {state} price={res['price']} "
                  f"levels={len(res['levels_all'])}")
        except Exception as e:
            print(f"{coin}: ERROR {e}", file=sys.stderr)
    fired = [r for f, r in candidates if f]
    ts = datetime.now(timezone.utc).isoformat()
    if fired:
        fired.sort(key=lambda r: (r["distance_pct"], -r["touches"]))
        winner = dict(fired[0])
        if force:
            winner["forced"] = True
        winner["generated_at"] = ts
        winner["runners_up"] = [
            {k: r[k] for k in ("coin", "price", "setup", "level", "distance_pct")}
            for r in fired[1:]]
        (OUT_DIR / "setup.json").write_text(json.dumps(winner, indent=2))
        print(f"ALERT -> {winner['coin']} {winner['setup']} @ {winner['level']}")
        return 0
    quiet = {"generated_at": ts, "setup": None,
             "scanned": [{k: r[k] for k in ("coin", "price", "change_24h_pct")}
                         for _, r in candidates]}
    (OUT_DIR / "no_setup.json").write_text(json.dumps(quiet, indent=2))
    (OUT_DIR / "setup.json").unlink(missing_ok=True)
    print("No setup fired.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
