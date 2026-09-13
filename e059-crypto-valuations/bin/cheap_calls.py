#!/usr/bin/env python3
"""e059 cheap-call paper loop + backtest (offline-first, $0).

Signal: CHEAP = P/Fees <= 0.8x its category median (same threshold the card paints green).
Precision: fraction of cheap calls with ratio still < 1.0 (below median) 7d later.
Multiples move slowly -> 30d resolution window with DISJOINT trailing-30d
windows (call uses fees ending D, resolve uses fees ending D+30). A 7d
window would share 23/30 fee-days with the call and report stickiness,
not signal — verified 1.000 at 7d during build, discarded as autocorrelation.

Mcaps have no free history tier, so mcap is held constant at its latest
value everywhere here (same honesty rule as bin/trend.py, disclosed in
caveats + output). This tests the SALES-trajectory signal, not market prices.

Three jobs, all idempotent:
  backtest : weekly call dates over the trailing 12wk, resolved +7d from
             cached dailyFees series. Writes data/cheap_backtest.json.
  paper    : logs today's live cheap set from output/multiples.json into
             data/cheap_calls.jsonl (1 row/symbol/day) + today's ratios into
             data/daily_ratios.jsonl.
  resolve  : resolves paper calls aged >=7d against the first ratios snapshot
             >= call+7d. Writes output/cheap_calls.json (served statically).

Hooked into bin/refresh.sh (daily). Card shows score from cheap_calls.json.
"""
import json, os
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")

CHEAP = 0.8          # call threshold vs category median
HIT = 1.0            # still-cheap threshold at resolve
RESOLVE_DAYS = 30
BACKTEST_WEEKS = 12
WINDOW = 30          # trailing-30d annualization, mirrors valuations.py
DAY = 86400


def day_ts(dt):
    return int(datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc).timestamp())


def load_chart(slug, dtype="dailyFees"):
    p = os.path.join(DATA, f"fees__{slug}__{dtype}.json")
    if not os.path.exists(p):
        return []
    try:
        d = json.load(open(p))
    except Exception:
        return []
    pts = [(int(ts), float(v or 0)) for ts, v in (d.get("totalDataChart") or []) if v is not None]
    pts.sort()
    return pts


def proto_series(slugs):
    """Merge multi-slug daily fees by calendar day -> sorted [(day_ts, value)]."""
    by_day = {}
    for slug in slugs:
        for ts, v in load_chart(slug):
            d = day_ts(datetime.fromtimestamp(ts, timezone.utc))
            by_day[d] = by_day.get(d, 0) + v
    return sorted(by_day.items())


def ann_at(series, end_ts, window=WINDOW):
    """Annualized fees over trailing `window` days ending end_ts (inclusive)."""
    lo = end_ts - (window - 1) * DAY
    pts = [(t, v) for t, v in series if lo <= t <= end_ts]
    if len(pts) < window // 2:  # thin history -> no call
        return None
    return sum(v for _, v in pts) * 365 / len(pts)


def ratios_at(protos, series_map, mcaps, end_ts):
    """{symbol: ratio vs category median} at end_ts; None where uncomputable."""
    pfees = {}
    for p in protos:
        a = ann_at(series_map.get(p["symbol"], []), end_ts)
        mc = mcaps.get(p["symbol"])
        pfees[p["symbol"]] = (mc / a) if (mc and a) else None
    cats = {}
    for p in protos:
        cats.setdefault(p.get("category", "Other"), []).append(p["symbol"])
    out = {}
    for cat, syms in cats.items():
        vals = sorted(v for s in syms if (v := pfees.get(s)) is not None)
        if not vals:
            continue
        med = (vals[len(vals) // 2] + vals[~(len(vals) // 2)]) / 2
        for s in syms:
            out[s] = (pfees[s] / med) if (pfees.get(s) is not None and med) else None
    return out


def main():
    cfg = json.load(open(os.path.join(ROOT, "config.json")))
    protos = cfg["protocols"]
    live = json.load(open(os.path.join(OUT, "multiples.json")))
    mcaps = {r["symbol"]: r.get("market_cap_usd") for r in live["protocols"]}
    today = datetime.now(timezone.utc).date().isoformat()

    series_map = {}
    for p in cfg["protocols"]:
        slugs = [s for s in p["llama"]]
        series_map[p["symbol"]] = proto_series(slugs)

    # ---- BACKTEST: weekly calls, trailing BACKTEST_WEEKS, resolve +7d ----
    now_ts = int(datetime.now(timezone.utc).timestamp())
    bt_calls, bt_hits = 0, 0
    bt_rows = []
    for w in range(1, BACKTEST_WEEKS + 1):
        call_ts = day_ts(datetime.now(timezone.utc) - timedelta(days=w * 7 + RESOLVE_DAYS))
        res_ts = call_ts + RESOLVE_DAYS * DAY
        if res_ts > now_ts - DAY:
            continue  # outcome not yet observable
        r0 = ratios_at(protos, series_map, mcaps, call_ts)
        r1 = ratios_at(protos, series_map, mcaps, res_ts)
        for p in protos:
            s = p["symbol"]
            if r0.get(s) is None or r1.get(s) is None:
                continue
            if r0[s] <= CHEAP:
                hit = r1[s] < HIT
                bt_calls += 1
                bt_hits += 1 if hit else 0
                bt_rows.append({"symbol": s, "call": datetime.fromtimestamp(call_ts, timezone.utc).date().isoformat(),
                                "ratio_call": round(r0[s], 2),
                                "ratio_resolve": round(r1[s], 2), "hit": hit})
    bt_prec = round(bt_hits / bt_calls, 3) if bt_calls else None
    json.dump({"as_of": today, "method": f"weekly calls trailing {BACKTEST_WEEKS}wk, mcap held constant at latest",
               "cheap_le": CHEAP, "hit_lt": HIT, "resolve_days": RESOLVE_DAYS,
               "n": bt_calls, "hits": bt_hits, "precision": bt_prec, "calls": bt_rows},
              open(os.path.join(DATA, "cheap_backtest.json"), "w"), indent=1)
    print(f"backtest: {bt_hits}/{bt_calls} stayed cheap = {bt_prec} (mcap-constant, sales-trajectory)")

    # ---- PAPER: log today's live cheap set (idempotent per date) ----
    meds = live.get("category_medians", {})
    logged_path = os.path.join(DATA, "cheap_calls.jsonl")
    have = set()
    if os.path.exists(logged_path):
        for line in open(logged_path):
            try:
                r = json.loads(line)
                have.add((r["date"], r["symbol"]))
            except Exception:
                pass
    n_new = 0
    with open(logged_path, "a") as f:
        for r in live["protocols"]:
            m = meds.get(r.get("category", ""), {})
            mp = m.get("median_p_fees")
            if not r.get("p_fees") or not mp:
                continue
            ratio = r["p_fees"] / mp
            if ratio <= CHEAP and (today, r["symbol"]) not in have:
                f.write(json.dumps({"date": today, "symbol": r["symbol"],
                                    "category": r.get("category"), "ratio_call": round(ratio, 3),
                                    "p_fees": r.get("p_fees"), "resolved": None, "hit": None}) + "\n")
                n_new += 1
    # today's ratio snapshot for future resolution
    snap_path = os.path.join(DATA, "daily_ratios.jsonl")
    snap_have = set()
    if os.path.exists(snap_path):
        for line in open(snap_path):
            try:
                snap_have.add(json.loads(line)["date"])
            except Exception:
                pass
    if today not in snap_have:
        snap = {"date": today, "ratios": {}}
        for r in live["protocols"]:
            m = meds.get(r.get("category", ""), {})
            mp = m.get("median_p_fees")
            if r.get("p_fees") and mp:
                snap["ratios"][r["symbol"]] = round(r["p_fees"] / mp, 3)
        with open(snap_path, "a") as f:
            f.write(json.dumps(snap) + "\n")
    print(f"paper: +{n_new} cheap calls logged for {today}")

    # ---- RESOLVE: calls aged >=RESOLVE_DAYS vs first snapshot >= call+7d ----
    snaps = []
    if os.path.exists(snap_path):
        for line in open(snap_path):
            try:
                snaps.append(json.loads(line))
            except Exception:
                pass
    snaps.sort(key=lambda s: s["date"])
    calls = []
    if os.path.exists(logged_path):
        for line in open(logged_path):
            try:
                calls.append(json.loads(line))
            except Exception:
                pass
    n_res = 0
    for c in calls:
        if c.get("resolved"):
            continue
        due = (datetime.fromisoformat(c["date"]) + timedelta(days=RESOLVE_DAYS)).date().isoformat()
        fut = next((s for s in snaps if s["date"] >= due and c["symbol"] in s.get("ratios", {})), None)
        if fut:
            c["resolved"] = fut["date"]
            c["hit"] = fut["ratios"][c["symbol"]] < HIT
            n_res += 1
    with open(logged_path, "w") as f:
        for c in calls:
            f.write(json.dumps(c) + "\n")
    res = [c for c in calls if c.get("resolved")]
    pen = [c for c in calls if not c.get("resolved")]
    hits = sum(1 for c in res if c.get("hit"))
    paper_prec = round(hits / len(res), 3) if res else None
    summary = {"as_of": today, "resolve_days": RESOLVE_DAYS,
               "backtest": {"n": bt_calls, "hits": bt_hits, "precision": bt_prec},
               "paper": {"n_resolved": len(res), "hits": hits, "precision": paper_prec,
                         "n_pending": len(pen)},
               "pending": [{"symbol": c["symbol"], "date": c["date"],
                            "ratio_call": c.get("ratio_call")} for c in pen[-12:]]}
    json.dump(summary, open(os.path.join(OUT, "cheap_calls.json"), "w"), indent=1)
    print(f"resolve: +{n_res} newly resolved; paper {hits}/{len(res)} = {paper_prec} ({len(pen)} pending)")


if __name__ == "__main__":
    main()
