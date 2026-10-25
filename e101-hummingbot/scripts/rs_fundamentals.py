#!/usr/bin/env python3
"""Daily fundamentals time series (slow event source; free APIs only, no invented data).

Per coin, one row per day in data/rs_fundamentals.csv:
  fees / revenue / holders revenue (DefiLlama overview: 24h, 7d, prior 7d, 30d, prior 30d),
  TVL (DefiLlama /protocols), is_meme (CoinGecko meme-token category membership),
  has_llama (protocol listed on DefiLlama), buyback_burn_30d (null: no free generic source),
  team / roadmap / revenue_plan from scripts/rs_fundamentals_manual.json (null when unknown).
Trends: rev_trend_7d / rev_trend_30d = % change vs the prior window (from DefiLlama's own
prior-window totals). score 0..100 and class: PROJECT_IMPROVING / PROJECT / PROJECT_WEAKENING /
MEME / UNKNOWN.
"""
import csv, json, os
from datetime import datetime
import rstrength_scan as scan
import rs_sources

# Judgment labels (config, not data): platform tokens that earn fees from OTHER coins
# trading on them, and hybrids (lottery/mining + real revenue + buybacks).
PLATFORM = {"PUMP", "STONK", "PONS"}
HYBRID = {"ORE"}
# external_share thresholds (config): > BIZ real_business, >= HYB hybrid, else casino
BIZ = float(os.environ.get('RS_SHARE_BIZ', 0.70)); HYB = float(os.environ.get('RS_SHARE_HYB', 0.30))
SELF_CATS = {"memes", "meme"}  # DefiLlama categories whose fees are trading on the coin itself

BASE = scan.BASE
OUT = os.path.join(BASE, "data", "rs_fundamentals.csv")
MANUAL = os.path.join(BASE, "scripts", "rs_fundamentals_manual.json")
F = ["date", "token", "cg_id", "is_meme", "has_llama", "tvl",
     "fees_24h", "fees_30d", "rev_24h", "rev_7d", "rev_7d_prior", "rev_30d", "rev_30d_prior",
      "holders_rev_30d", "buyback_burn_30d", "team", "roadmap", "revenue_plan",
      "rev_trend_7d", "rev_trend_30d", "llama_category", "taxonomy", "coin_type", "auto_class",
     "real_revenue_30d", "self_trading_revenue_30d", "external_revenue_30d",
     "external_share", "business_class", "external_share_trend_7d", "revenue_is_self_trading", "has_real_revenue", "score", "klass"]
LL = "https://api.llama.fi/overview/fees?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"


def _ov(dt):
    d = scan.get_json(LL + (f"&dataType={dt}" if dt else ""))
    return {str(p.get("defillamaId")): p for p in d.get("protocols", [])}


def _sum(rows, k):
    v = [r.get(k) for r in rows if r.get(k) is not None]
    return round(sum(v), 2) if v else None


def chg(a, b):
    return round((a / b - 1) * 100, 1) if a is not None and b else None


def score_of(r):
    if r.get("coin_type") == "launchpad_meme":
        return 10, "MEME"
    if not r["has_llama"]:
        return None, "UNKNOWN"
    s = 40
    if r.get("has_real_revenue"): s += 20
    t7, t30 = r["rev_trend_7d"], r["rev_trend_30d"]
    for t in (t7, t30):
        if t is not None: s += 10 if t > 5 else (-10 if t < -5 else 0)
    if (r["holders_rev_30d"] or 0) > 0: s += 10
    if r["tvl"]: s += 5
    if r["is_meme"]: s -= 15
    s = max(0, min(100, s))
    if (t7 or 0) > 5 and (t30 or 0) > 5: k = "PROJECT_IMPROVING"
    elif (t7 or 0) < -5 and (t30 or 0) < -5: k = "PROJECT_WEAKENING"
    else: k = "PROJECT"
    return s, k


def refresh(coins):
    """coins: {SYMBOL: coingecko_id}. Appends today's rows once per day; returns {SYM: row}."""
    today = datetime.now(scan.BOG).strftime("%Y-%m-%d")
    have = latest()
    if have and set(coins) <= set(have) and all(have[k]["date"] == today for k in coins):
        return have
    protos = scan.get_json("https://api.llama.fi/protocols")
    by_g, by_parent = {}, {}
    for p in protos:
        if p.get("parentProtocol"):
            by_parent.setdefault(p["parentProtocol"], []).append(p)
        if p.get("gecko_id"):
            by_g.setdefault(p["gecko_id"], []).append(p)
    for pp in scan.get_json("https://api.llama.fi/lite/protocols2").get("parentProtocols", []):
        if pp.get("gecko_id"):
            by_g.setdefault(pp["gecko_id"], []).append({"id": pp["id"], "parent": True})
    fees, rev, hold = _ov(None), _ov("dailyRevenue"), _ov("dailyHoldersRevenue")
    memes = {c["id"] for c in scan.markets(category="meme-token")}
    manual = json.load(open(MANUAL)) if os.path.exists(MANUAL) else {}
    out = {}
    for sym, cid in coins.items():
        ps = list(by_g.get(cid, []))
        for p in list(ps):
            key = p["id"] if p.get("parent") else (p.get("parentProtocol") or "")
            ps += [c for c in by_parent.get(key, []) if c not in ps]
        ids = {str(p["id"]) for p in ps} | {p["parentProtocol"] for p in ps if p.get("parentProtocol")}
        fr = [fees[i] for i in ids if i in fees]
        rr = [rev[i] for i in ids if i in rev]
        hr = [hold[i] for i in ids if i in hold]
        m = manual.get(sym, {})
        r = {"date": today, "token": sym, "cg_id": cid, "is_meme": cid in memes, "has_llama": bool(ps),
             "tvl": _sum(ps, "tvl"), "fees_24h": _sum(fr, "total24h"), "fees_30d": _sum(fr, "total30d"),
             "rev_24h": _sum(rr, "total24h"), "rev_7d": _sum(rr, "total7d"),
             "rev_7d_prior": _sum(rr, "total14dto7d"), "rev_30d": _sum(rr, "total30d"),
             "rev_30d_prior": _sum(rr, "total60dto30d"), "holders_rev_30d": _sum(hr, "total30d"),
             "buyback_burn_30d": m.get("buyback_burn_30d"), "team": m.get("team"),
             "roadmap": m.get("roadmap"), "revenue_plan": m.get("revenue_plan")}
        r["rev_trend_7d"] = chg(r["rev_7d"], r["rev_7d_prior"])
        r["rev_trend_30d"] = chg(r["rev_30d"], r["rev_30d_prior"])
        cats = {(p.get("category") or "").lower() for p in ps if p.get("category")}
        r["llama_category"] = ",".join(sorted(cats)) or None
        r["taxonomy"] = rs_sources.taxonomy(rs_sources.cg_meta(cid))
        if r["taxonomy"] == "meme": r["is_meme"] = True
        self_only = bool(cats) and cats <= SELF_CATS
        if not ps:
            # no product on DefiLlama: any income is fees on its own pair (or unknown)
            r["revenue_is_self_trading"] = True if r["is_meme"] else None
            r["real_revenue_30d"] = None
        else:
            r["revenue_is_self_trading"] = self_only
            r["real_revenue_30d"] = None if self_only else r["rev_30d"]
        # external = DefiLlama product revenue; self = fees from trading the coin itself
        # (DefiLlama self-only categories, or manual self_trading_revenue_30d). Unknown -> null.
        ext = r["real_revenue_30d"]
        slf = m.get("self_trading_revenue_30d")
        if self_only: slf, ext = r["rev_30d"], 0.0
        elif ps and ext is not None and slf is None:
            # DefiLlama exposes a product-revenue breakdown here (fees vs revenue overviews),
            # and it reports no self-trading revenue for this protocol -> 0, not a guess.
            slf = 0.0
        r["external_revenue_30d"], r["self_trading_revenue_30d"] = ext, slf
        if ext is not None and slf is not None and (ext + slf) > 0:
            sh = round(ext / (ext + slf), 3)
            r["external_share"] = sh
            r["business_class"] = "real_business" if sh > BIZ else ("hybrid" if sh >= HYB else "casino")
        else:
            r["external_share"] = r["business_class"] = None
        r["external_share_trend_7d"] = share_trend(sym, r["external_share"], today)
        r["has_real_revenue"] = bool(r["real_revenue_30d"]) and not r["revenue_is_self_trading"]
        if sym in HYBRID and r["has_real_revenue"]: r["coin_type"] = "hybrid"
        elif sym in PLATFORM and r["has_real_revenue"]: r["coin_type"] = "launchpad_platform_token"
        elif r["has_real_revenue"]: r["coin_type"] = "revenue_project"
        elif r["is_meme"]: r["coin_type"] = "launchpad_meme"
        elif r["taxonomy"] == "l1": r["coin_type"] = "l1"
        else: r["coin_type"] = None
        # Auto business class for coins the fixed rules leave unclassified:
        # CoinGecko categories + the DefiLlama product-revenue fact only.
        auto = rs_sources.business_class(rs_sources.cg_meta(cid), r["is_meme"],
                                         bool(r["has_real_revenue"]))
        if r["coin_type"] is None and auto: r["coin_type"] = auto
        r["auto_class"] = auto
        # taxonomy file: record the derived class (None stays as null = n/a);
        # never touches human-curated keys in the same entry.
        manual.setdefault(sym, {})["auto_class"] = auto
        json.dump(manual, open(MANUAL, "w"), indent=1)
        r["score"], r["klass"] = score_of(r)
        out[sym] = r
    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=F)
        if new: w.writeheader()
        w.writerows(out.values())
    scan.log(f"[fundamentals] {today} rows={len(out)}")
    return out


def share_trend(sym, cur, today):
    """external_share now minus its value 6-9 days ago in our own daily series."""
    if cur is None or not os.path.exists(OUT):
        return None
    from datetime import date
    t = date.fromisoformat(today); best = None
    for r in csv.DictReader(open(OUT)):
        if r["token"] == sym and r.get("external_share") not in (None, ""):
            if 6 <= (t - date.fromisoformat(r["date"])).days <= 9 and best is None:
                best = float(r["external_share"])
    return round(cur - best, 3) if best is not None else None


def latest():
    if not os.path.exists(OUT):
        return {}
    rows = {}
    for r in csv.DictReader(open(OUT)):
        rows[r["token"]] = r
    return rows


if __name__ == "__main__":
    coins = dict(scan.WATCHLIST)
    for k, r in refresh(coins).items():
        print(k, r["coin_type"], r["taxonomy"], r["has_real_revenue"], r["klass"], r["score"], r["rev_30d"], r["rev_trend_7d"], r["rev_trend_30d"], r["tvl"])
