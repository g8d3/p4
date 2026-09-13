#!/usr/bin/env python3
"""e059 trend patch (offline, $0): price-to-sales THROUGH TIME.

Owner ask 2026-09-12: comparables must read through category AND through
time. Reads cached DefiLlama dailyFees series in data/ (no network) +
mcaps already in output/multiples.json, then appends per-protocol:
  p_fees_trend : 6 trailing weekly P/Fees values (oldest→newest)
  trend_spark  : unicode sparkline of those 6 values (▁▂▃▄▅▆▇)
  trend_dir    : -1 multiple falling (cheaper) / 0 flat / +1 rising
Honesty rule: mcap history is NOT available on free tiers, so mcap is held
constant at its latest value — the trend shows the SALES (fees) trajectory
behind the multiple. Disclosed in caveats. Idempotent; safe to re-run.
Hooked into bin/refresh.sh so daily rebuilds keep the trend.
"""
import json, os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
WEEKS = 6
BARS = "▁▂▃▄▅▆▇"

TREND_CAVEAT = ("Trend holds market cap constant at its latest value (free tiers "
                "have no mcap history) — it shows the sales/fees trajectory "
                "behind each multiple, not past market prices.")


def load_chart(slug):
    p = os.path.join(DATA, f"fees__{slug}__dailyFees.json")
    if not os.path.exists(p):
        return []
    try:
        d = json.load(open(p))
    except Exception:
        return []
    pts = [(int(ts), float(v or 0)) for ts, v in (d.get("totalDataChart") or []) if v is not None]
    pts.sort()
    return pts


def main():
    cfg = json.load(open(os.path.join(ROOT, "config.json")))
    mp = os.path.join(OUT, "multiples.json")
    out = json.load(open(mp))
    by_symbol = {r["symbol"]: r for r in out["protocols"]}
    n_ok = 0
    for p in cfg["protocols"]:
        row = by_symbol.get(p["symbol"])
        if not row:
            continue
        mc = row.get("market_cap_usd")
        # merge multi-slug daily fees by day, trailing 42d → 6 weeks
        by_day = {}
        for slug in p["llama"]:
            for ts, v in load_chart(slug)[-WEEKS * 7:]:
                day = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
                by_day[day] = by_day.get(day, 0) + v
        days = sorted(by_day)[-WEEKS * 7:]
        weeks = [days[i:i + 7] for i in range(0, len(days), 7)]
        trend, vals = [], []
        for wk in weeks:
            s = sum(by_day[d] for d in wk)
            ann = s * 365 / max(len(wk), 1) if wk else 0
            vals.append(ann)
            trend.append(round(mc / ann, 2) if mc and ann else None)
        nums = [t for t in trend if t is not None]
        if nums and max(nums) > min(nums):
            lo, hi = min(nums), max(nums)
            spark = "".join(BARS[min(int((t - lo) / (hi - lo) * 6), 6)] if t is not None else "·"
                            for t in trend)
        else:
            spark = ("▄" * len(trend)) if nums else ""
        if len(nums) >= 4 and nums[0]:
            first = sum(nums[:2]) / 2
            last = sum(nums[-2:]) / 2
            direction = -1 if last < first * 0.9 else (1 if last > first * 1.1 else 0)
        else:
            direction = None
        row["p_fees_trend"] = trend
        row["trend_spark"] = spark or None
        row["trend_dir"] = direction
        if trend and any(t is not None for t in trend):
            n_ok += 1
        print(f"  {p['symbol']}: trend={trend} spark={spark} dir={direction}")
    if TREND_CAVEAT not in out.get("caveats", []):
        out["caveats"] = out.get("caveats", []) + [TREND_CAVEAT]
    json.dump(out, open(mp, "w"), indent=1)
    print(f"trend ok: {n_ok}/{len(out['protocols'])} protocols → output/multiples.json")


if __name__ == "__main__":
    main()
