#!/usr/bin/env python3
"""Forward returns of relative-strength flag rules (paper only, local data).

For every row in data/rs_event_flags.csv, take its timestamp and price, then
look up the same token in data/rs_series.csv at +1h, +4h and +24h. A horizon is
"available" only when the series has a sample within TOL of the target time.
Returns are percent: (price_t / price_flag - 1) * 100.

Baseline: for each flag with an available horizon, draw N random timestamps
from the SAME coin's series that also have that horizon available, and compute
the same forward return. Baseline draws are a reference, not independent
samples; the script reports both the flag sample size and the draw count so a
small flag sample is never mistaken for evidence.

Usage:
  python3 scripts/flag_forward_returns.py [--data-dir DIR] [--draws 200]
                                         [--seed 7] [--horizons 1,4,24]
"""
import argparse
import csv
import hashlib
import os
import random
import statistics
from datetime import datetime, timedelta

HORIZONS_H = (1, 4, 24)
TOL = timedelta(minutes=10)
SMALL_N = 30
# The five VOL_SPIKEs the q79 review says the pre-persist restarts missed
# (coco/paper_scan_review.md, day-4 section). This is the review's list, not a
# re-run of the detector; forwarded here only as a clearly separate sample.
Q79_REPLAY = [
    ("2026-10-25T19:50:00-05:00", "PYTH"),
    ("2026-10-25T19:55:00-05:00", "TRUMP"),
    ("2026-10-25T20:25:00-05:00", "ENA"),
    ("2026-10-25T21:00:00-05:00", "WLFI"),
    ("2026-10-25T21:05:00-05:00", "ORCA"),
]


def parse_ts(s):
    try:
        return datetime.fromisoformat(str(s).strip())
    except (TypeError, ValueError):
        return None


def load_series(path):
    """token -> [(ts, price)] sorted, invalid rows skipped."""
    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            ts, price = parse_ts(r.get("ts")), r.get("price")
            token = (r.get("token") or "").strip().upper()
            if ts is None or not token:
                continue
            try:
                p = float(price)
            except (TypeError, ValueError):
                continue
            if p <= 0:
                continue
            out.setdefault(token, []).append((ts, p))
    for token in out:
        out[token].sort(key=lambda x: x[0])
    return out


def load_flags(path):
    flags = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            ts = parse_ts(r.get("ts"))
            token = (r.get("token") or "").strip().upper()
            rule = (r.get("rule") or "").strip()
            try:
                price = float(r.get("price"))
            except (TypeError, ValueError):
                price = None
            if ts is None or not token or not rule:
                continue
            flags.append({"ts": ts, "token": token, "rule": rule, "price": price})
    return flags


def q79_replay_flags():
    return [{"ts": parse_ts(ts), "token": token, "rule": "VOL_SPIKE_q79_replay", "price": None}
            for ts, token in Q79_REPLAY]


def range_of(items, key):
    vals = [x[key] for x in items if x.get(key)]
    return (min(vals).strftime("%Y-%m-%d %H:%M"), max(vals).strftime("%Y-%m-%d %H:%M")) if vals else ("—", "—")


def forward_at(series, token, start, horizon_h):
    """(price_flag, price_forward, ret_pct) or None if the series cannot answer."""
    pts = series.get(token) or []
    if not pts:
        return None
    # Use the series price at the flag time for both flag and baseline, so the
    # comparison is same-source and same-cadence (the CSV flag price comes from
    # a different snapshot and would add a basis).
    p0 = next((p for t, p in pts if start["ts"] <= t <= start["ts"] + TOL), None)
    if p0 is None:  # flag slightly after the bucket: allow one step back
        p0 = next((p for t, p in reversed(pts) if start["ts"] - TOL <= t <= start["ts"]), None)
    if p0 is None:
        return None
    target = start["ts"] + timedelta(hours=horizon_h)
    p1 = next((p for t, p in pts if target <= t <= target + TOL), None)
    if p1 is None:
        return None
    return p0, p1, (p1 / p0 - 1.0) * 100.0


def valid_random_points(series, token, horizon_h):
    """Timestamps in the same coin's series with a usable forward sample."""
    pts = series.get(token) or []
    out = []
    for i, (t, p) in enumerate(pts):
        target = t + timedelta(hours=horizon_h)
        if any(target <= t2 <= target + TOL for t2, _ in pts[i + 1:]):
            out.append((t, p))
    return out


def stats(vals):
    if not vals:
        return {"n": 0, "median": None, "mean": None, "hit": None}
    return {
        "n": len(vals),
        "median": round(statistics.median(vals), 2),
        "mean": round(statistics.fmean(vals), 2),
        "hit": round(100.0 * sum(1 for v in vals if v > 0) / len(vals), 1),
    }


def summarize(flags, series, horizons=HORIZONS_H, draws=200, seed=7):
    """Rows per (rule, horizon) plus an ALL aggregate."""
    rules = sorted({f["rule"] for f in flags})
    rows = []
    for horizon in horizons:
        per_rule = {r: {"flag": [], "base": []} for r in rules}
        for idx, f in enumerate(flags):
            got = forward_at(series, f["token"], f, horizon)
            if got is None:
                continue
            per_rule[f["rule"]]["flag"].append(got[2])
            cand = valid_random_points(series, f["token"], horizon)
            if not cand:
                continue
            rng = random.Random(seed + int(hashlib.sha256(
                ("%s|%s|%s" % (f["token"], f["ts"].isoformat(), horizon)).encode()).hexdigest()[:8], 16))
            for _ in range(draws):
                t, _p = cand[rng.randrange(len(cand))]
                start = {"ts": t, "token": f["token"], "price": None}
                g = forward_at(series, f["token"], start, horizon)
                if g is not None:
                    per_rule[f["rule"]]["base"].append(g[2])
        all_flag, all_base = [], []
        for r in rules:
            fs, bs = stats(per_rule[r]["flag"]), stats(per_rule[r]["base"])
            all_flag += per_rule[r]["flag"]
            all_base += per_rule[r]["base"]
            rows.append({"rule": r, "horizon": horizon, "flag": fs, "base": bs,
                         "verdict": "no data" if fs["n"] == 0 else ("too small" if fs["n"] < SMALL_N else "usable n")})
        fs, bs = stats(all_flag), stats(all_base)
        rows.append({"rule": "ALL", "horizon": horizon, "flag": fs, "base": bs,
                     "verdict": "no data" if fs["n"] == 0 else ("too small" if fs["n"] < SMALL_N else "usable n")})
    return rows


def fmt(x, suffix="%"):
    return "—" if x is None else f"{x:.2f}{suffix}"


def markdown(rows, flags_n, series_n, horizons):
    lines = ["| Rule | Horizon | Flags n | Median | Mean | Hit rate | Baseline median | Baseline mean | Baseline hit | Sample |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in rows:
        f, b = r["flag"], r["base"]
        lines.append("| {rule} | +{h}h | {n} | {med} | {mean} | {hit} | {bmed} | {bmean} | {bhit} | {v} |".format(
            rule=r["rule"], h=r["horizon"], n=f["n"], med=fmt(f["median"]), mean=fmt(f["mean"]),
            hit=fmt(f["hit"]), bmed=fmt(b["median"]), bmean=fmt(b["mean"]), bhit=fmt(b["hit"]),
            v=r["verdict"]))
    lines += ["", f"Flags rows: {flags_n} · series tokens: {series_n} · horizons: {', '.join('+%dh' % h for h in horizons)}.",
              "Baseline: random same-coin timestamps, 200 draws per flag/horizon where data exists; draws are not independent. Hit rate = forward return > 0."]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Forward returns of RS flag rules (paper only)")
    ap.add_argument("--data-dir", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
    ap.add_argument("--draws", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--horizons", default="1,4,24")
    ap.add_argument("--replay-q79", action="store_true",
                    help="also print the five missed VOL_SPIKEs listed in the q79 review (not re-derived)")
    args = ap.parse_args()
    horizons = tuple(int(h) for h in args.horizons.split(",") if h.strip())
    flags_path = os.path.join(args.data_dir, "rs_event_flags.csv")
    series_path = os.path.join(args.data_dir, "rs_series.csv")
    flags = load_flags(flags_path)
    series = load_series(series_path)
    rows = summarize(flags, series, horizons=horizons, draws=args.draws, seed=args.seed)
    fr, sr = range_of(flags, "ts"), range_of([{"ts": t} for pts in series.values() for t, _ in pts], "ts")
    print(f"Flags: {len(flags)} rows, {fr[0]} → {fr[1]} · Series: {len(series)} tokens, {sr[0]} → {sr[1]}")
    print(markdown(rows, len(flags), len(series), horizons))
    if args.replay_q79:
        replay = q79_replay_flags()
        rrows = summarize(replay, series, horizons=horizons, draws=args.draws, seed=args.seed)
        print("\n### q79 replay — five VOL_SPIKEs from the day-4 review (list, not re-derived; paper only)")
        print(markdown(rrows, len(replay), len(series), horizons))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
