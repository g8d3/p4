#!/usr/bin/env python3
"""Build site/midterms.json from data/raw/ + elections.json. Monthly resolution.

Definitions (also printed on the page):
- trough = lowest monthly close in [election-4M, election+6M]
- swingA = highest close from Jan of election year to trough ("fear")
- swingB = highest close from trough to trough+12M ("relief")
- a move under 0.5% is not a swing: null with a reason, never a fake number.
"""
import csv
import datetime
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "raw"


def mkey(year, month):
    return year * 12 + (month - 1)


def split_key(k):
    return divmod(k, 12)[0], divmod(k, 12)[1] + 1


def str_key(k):
    y, m = split_key(k)
    return f"{y:04d}-{m:02d}"


def load_shiller():
    import xlrd
    s = xlrd.open_workbook(DATA / "ie_data.xls").sheet_by_name("Data")
    out = {}
    for r in range(8, s.nrows):
        try:
            d = float(s.cell_value(r, 0))
        except (ValueError, TypeError):
            continue
        y, m = int(d), int(round((d - int(d)) * 100))
        if not 1 <= m <= 12:
            continue
        try:
            p = float(s.cell_value(r, 1))
        except (ValueError, TypeError):
            continue
        cape_raw = s.cell_value(r, 12)
        try:
            cape = float(cape_raw)
        except (ValueError, TypeError):
            cape = None
        out[mkey(y, m)] = {"p": p, "cape": cape}
    return out


def load_fred(name):
    out = {}
    with open(DATA / f"fred_{name}.csv") as f:
        for row in csv.DictReader(f):
            d, v = row["observation_date"], row[name.upper()]
            try:
                out[d[:7]] = float(v)
            except (ValueError, TypeError):
                continue
    return out


def pct(a, b):
    return round(100 * (b - a) / a, 2)


def month_diff(a, b):
    return b - a


def swings(hist, elect_key):
    """hist: {mkey: {'p':..,'cape':..}}. Returns (swingA|None, swingB|None, trough_key)."""
    ey, _ = split_key(elect_key)
    lo, hi = elect_key - 4, elect_key + 6
    cands = {k: v for k, v in hist.items() if lo <= k <= hi}
    if not cands:
        return None, None, None
    tk = min(cands, key=lambda k: cands[k]["p"])
    tp = cands[tk]["p"]
    pre = {k: v for k, v in hist.items() if mkey(ey, 1) <= k <= tk}
    pk = max(pre, key=lambda k: pre[k]["p"])
    depth = pct(pre[pk]["p"], tp)
    if depth < -0.5:
        a = {"peak": str_key(pk), "peak_level": round(pre[pk]["p"], 2),
             "trough": str_key(tk), "trough_level": round(tp, 2),
             "depth_pct": depth, "months": month_diff(pk, tk),
             "cape_at_prepeak": pre[pk]["cape"] and round(pre[pk]["cape"], 1)}
    else:
        a = None
    post = {k: v for k, v in hist.items() if tk <= k <= tk + 12}
    qk = max(post, key=lambda k: post[k]["p"])
    height = pct(tp, post[qk]["p"])
    if height > 0.5:
        b = {"trough": str_key(tk), "trough_level": round(tp, 2),
             "peak": str_key(qk), "peak_level": round(post[qk]["p"], 2),
             "height_pct": height, "months": month_diff(tk, qk)}
    else:
        b = None
    return a, b, tk


def stance(funds, ek):
    y, m = split_key(ek)
    now = funds.get(str_key(ek))
    prev = funds.get(f"{y - 1:04d}-{m:02d}")
    if now is None or prev is None:
        return None, "unknown"
    d = now - prev
    return round(now, 2), "hiking" if d > 0.5 else ("cutting" if d < -0.5 else "flat")


def yoy(series, ek):
    y, m = split_key(ek)
    a, b = series.get(str_key(ek)), series.get(f"{y - 1:04d}-{m:02d}")
    if a is None or b is None:
        return None
    return round(100 * (a - b) / b, 2)


def chg(series, ek, n):
    a = series.get(str_key(ek))
    y, m = split_key(ek - n)
    b = series.get(f"{y:04d}-{m:02d}")
    if a is None or b is None:
        return None
    return round(a - b, 2)


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return round((xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2), 2)


def main():
    elect = json.load(open(ROOT / "elections.json"))
    hist = load_shiller()
    funds = load_fred("fedfunds")
    cpi = load_fred("cpiaucsl")
    unrate = load_fred("unrate")
    gs10 = load_fred("gs10")
    out = []
    for e in elect["elections"]:
        y, m, d = int(e["date"][:4]), int(e["date"][5:7]), e["date"]
        ek = mkey(y, m)
        a, b, tk = swings(hist, ek)
        ba = round(b["height_pct"] / abs(a["depth_pct"]), 2) if a and b else None
        rate, st = stance(funds, ek)
        macro = {"fed_rate": rate, "fed_stance": st,
                 "cpi_yoy": yoy(cpi, ek), "unrate": unrate.get(str_key(ek)),
                 "unrate_chg6m": chg(unrate, ek, 6), "gs10": gs10.get(str_key(ek)),
                 "gs10_chg6m": chg(gs10, ek, 6),
                 "cape_at_prepeak": (a or {}).get("cape_at_prepeak")}
        missing = [k for k, v in macro.items()
                   if v is None and k not in ("fed_stance",)]
        macro_note = ("full macro from 1954+; " if not missing else
                      "no " + ", ".join(missing) + " this far back (series starts later); ") + \
            "monthly resolution, nominal index"
        path = [{"m": str_key(ek + k), "k": k,
                 "v": round(100 * hist[ek + k]["p"] / hist[ek]["p"], 2)}
                for k in range(-12, 13) if ek + k in hist and ek in hist]
        if a is None:
            areason = "no pre-election dip"
        else:
            areason = None
        out.append({**{k: e[k] for k in ("id", "date", "president", "party",
                                        "term", "divided_after", "recession", "note")},
                    "swingA": a, "swingA_note": areason,
                    "swingB": b, "swingB_note": None if b else "no relief rally",
                    "ba_ratio": ba, "macro": macro, "macro_note": macro_note,
                    "trough_offset_m": month_diff(ek, tk) if tk else None,
                    "path": path})
    depths = [x["swingA"]["depth_pct"] for x in out if x["swingA"]]
    heights = [x["swingB"]["height_pct"] for x in out if x["swingB"]]
    bas = [x["ba_ratio"] for x in out if x["ba_ratio"] is not None]
    hits = [x for x in out if x["trough_offset_m"] is not None
            and abs(x["trough_offset_m"]) <= 2]
    stats = {"n": len(out),
             "hit_rate_2m": round(100 * len(hits) / len(out), 1),
             "median_depth": median(depths), "median_height": median(heights),
             "median_ba": median(bas),
             "share_relief_beats_fear":
                 round(100 * sum(1 for x in bas if x and x > 1) / len(bas), 1) if bas else None,
             "median_ba_hiking": median([x["ba_ratio"] for x in out
                                         if x["ba_ratio"] is not None and x["macro"]["fed_stance"] == "hiking"]),
             "median_ba_cutting": median([x["ba_ratio"] for x in out
                                          if x["ba_ratio"] is not None and x["macro"]["fed_stance"] == "cutting"])}
    with open(DATA / "fred_sp500.csv") as f:
        rows = [(r["observation_date"], r["SP500"]) for r in csv.DictReader(f) if r["SP500"] not in ("", ".")]
    last_day, last_val = rows[-1]
    today = datetime.date.today()
    target = datetime.date(2026, 11, 3)
    result = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
              "elections": out, "stats": stats,
              "live": {"asof": last_day, "spx": float(last_val),
                       "next_election": "2026-11-03",
                       "days_to": (target - today).days},
              "method": ("Monthly S&P composite (Shiller, nominal) for swings; "
                         "trough = lowest close in [election-4M, election+6M]; "
                         "fear = high since Jan of election year to trough; "
                         "relief = trough to high in next 12M; moves under 0.5% are dashes, not swings; "
                         "macro monthly from FRED; hit = trough within 2 months of election month.")}
    dest = ROOT / "site" / "midterms.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    json.dump(result, open(dest, "w"), indent=1)
    print("wrote", dest, "elections:", len(out), "stats:", stats)


if __name__ == "__main__":
    main()
