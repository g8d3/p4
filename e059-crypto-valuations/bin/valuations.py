#!/usr/bin/env python3
"""e059 v1: P/Fees + P/Revenue multiples for ~20 major protocols.

Engine: DefiLlama free fees API (dailyFees/dailyRevenue, 30d annualized) +
CoinGecko market caps. Keyless, cached. Reuses e057 data/ files when present.
CoinGecko public tier: ~1 call / 20 s. No secrets, no funds, no trading.

Formulas (per banked spike):
  P/Fees    = market_cap / (sum(last 30d dailyFees) * 365/30)
  P/Revenue = market_cap / (sum(last 30d dailyRevenue) * 365/30)
  dailyRevenue = protocol revenue (holders revenue excluded; see caveats).
Every row carries freshness timestamps.
"""
import csv, json, os, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
os.makedirs(DATA, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
# reuse e057 cached fetches instead of refetching
E057 = "/home/vuos/code/p4/e057-launchpad-tokens/data"

CG = "https://api.coingecko.com/api/v3"
LLAMA_OVERVIEW = "https://api.llama.fi/overview/fees?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"
LLAMA_SUMMARY = "https://api.llama.fi/summary/fees/{slug}?dataType={dtype}"
CG_SLEEP = 20
BACKOFF = 65
CACHE_AGE = 20 * 3600  # refetch daily-ish
WINDOW = 30            # annualize trailing 30d


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "p4-e059-valuations"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429,) or e.code >= 500:
                wait = BACKOFF * (i + 1)
                print(f"  HTTP {e.code} → sleep {wait}s")
                time.sleep(wait)
                continue
            if e.code == 404:
                return None
            raise
        except Exception as e:
            print(f"  retry ({e})")
            time.sleep(10)
    raise RuntimeError(f"failed: {url}")


def e057_reuse(name):
    """Return e057's cached file if present, else None."""
    p = os.path.join(E057, name)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def cached(name, fetch_fn, max_age=CACHE_AGE, reuse_ok=True):
    path = os.path.join(DATA, name)
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < max_age:
        with open(path) as f:
            return json.load(f), False
    # reuse e057 copy (also refresh our own cache file with it)
    if reuse_ok:
        old = e057_reuse(name)
        if old is not None:
            with open(path, "w") as f:
                json.dump(old, f)
            return old, False
    val = fetch_fn()
    if val is not None:
        with open(path, "w") as f:
            json.dump(val, f)
    time.sleep(1)
    return val, True


def series_30d(chart):
    """totalDataChart entries are [unix_ts, value]; take trailing 30 daily points."""
    pts = [(int(ts), float(v or 0)) for ts, v in (chart or []) if v is not None]
    pts.sort()
    return pts[-WINDOW:]


def main():
    cfg = json.load(open(os.path.join(ROOT, "config.json")))
    protos = cfg["protocols"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1) CoinGecko market caps: single /markets call for all ids, cached
    ids = [p["cg_id"] for p in protos]
    need = set(ids)
    have = {m.get("id") for m in (e057_reuse("markets.json") or [])}
    use_cache = need <= have  # e057 copy only covers its own coins; refetch if ours missing
    markets, fresh_mkt = cached(
        "markets.json",
        lambda: get(f"{CG}/coins/markets?vs_currency=usd&ids={','.join(ids)}"),
        max_age=(CACHE_AGE if use_cache else -1),
        reuse_ok=use_cache)
    if fresh_mkt:
        time.sleep(CG_SLEEP)
    mcap = {m["id"]: m.get("market_cap") for m in (markets or [])}
    mcap_at = (os.path.getmtime(os.path.join(DATA, "markets.json")))
    mcap_at = datetime.fromtimestamp(mcap_at, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    missing = [p["symbol"] for p in protos if not mcap.get(p["cg_id"])]
    if missing:
        print(f"WARNING: no CoinGecko mcap for {missing}")
    e057_hit = sum(1 for p in protos
                   if os.path.exists(os.path.join(E057, "markets.json")) and p["cg_id"]
                   in {m.get("id") for m in (e057_reuse("markets.json") or [])})
    print(f"markets: {len(mcap)} caps (mcap_at={mcap_at})")

    # 2) DefiLlama: validate slugs, fetch dailyFees + dailyRevenue per slug
    print("llama overview...")
    ov, _ = cached("llama_overview.json", lambda: get(LLAMA_OVERVIEW), max_age=CACHE_AGE)
    by_slug = {p["slug"]: p for p in (ov or {}).get("protocols", [])}

    rows = []
    for p in protos:
        slugs = [s for s in p["llama"] if s in by_slug]
        skipped = sorted(set(p["llama"]) - set(slugs))
        if skipped:
            print(f"  {p['symbol']}: slug not in fees overview, skipped: {skipped}")
        fees_pts, rev_pts = [], []
        for slug in slugs:
            for dtype, acc in (("dailyFees", fees_pts), ("dailyRevenue", rev_pts)):
                s, fresh = cached(f"fees__{slug}__{dtype}.json",
                                  lambda: get(LLAMA_SUMMARY.format(slug=slug, dtype=dtype)),
                                  max_age=CACHE_AGE)
                chart = (s or {}).get("totalDataChart", [])
                if fresh:
                    time.sleep(2)
                if not chart:  # fall back to e057's merged llama__ file / any stale copy
                    old = e057_reuse(f"llama__{slug}.json") or {}
                    chart = (old.get(dtype) or [])
                acc.append(chart)
        # merge multi-slug charts by date (sum same-day values)
        def merge(charts):
            by_day = {}
            for ch in charts:
                for ts, v in series_30d(ch):
                    day = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
                    by_day[day] = by_day.get(day, 0) + v
            return sorted(by_day.items())
        f30, r30 = merge(fees_pts), merge(rev_pts)
        fsum = sum(v for _, v in f30)
        rsum = sum(v for _, v in r30)
        # time dimension (owner 2026-09-12): trailing-7d vs trailing-30d fees
        # momentum >1 = fees accelerating, <1 = decelerating
        f7 = f30[-7:] if len(f30) >= 7 else f30
        f7sum = sum(v for _, v in f7)
        f7ann = f7sum * 365 / max(len(f7), 1) if f7 else 0
        r7 = r30[-7:] if len(r30) >= 7 else r30
        r7sum = sum(v for _, v in r7)
        # annualize over actual day counts (multi-slug unions can exceed 30d)
        fann = fsum * 365 / max(len(f30), 1) if f30 else 0
        rann = rsum * 365 / max(len(r30), 1) if r30 else 0
        mc = mcap.get(p["cg_id"])
        days = [d for d, _ in f30 + r30]
        through = max(days) if days else None
        rows.append({
            "symbol": p["symbol"], "name": p["name"], "cg_id": p["cg_id"],
            "category": p.get("category", "Other"),
            "slugs_used": slugs,
            "market_cap_usd": mc, "mcap_at": mcap_at,
            "fees_30d_usd": round(fsum, 2), "fees_ann_usd": round(fann, 2),
            "revenue_30d_usd": round(rsum, 2), "revenue_ann_usd": round(rann, 2),
            "p_fees": round(mc / fann, 2) if mc and fann else None,
            "p_revenue": round(mc / rann, 2) if mc and rann else None,
            "fees_7d_usd": round(f7sum, 2), "fees_7d_ann_usd": round(f7ann, 2),
            "p_fees_7d": round(mc / f7ann, 2) if mc and f7ann else None,
            "fees_momentum": round(f7ann / fann, 3) if fann else None,
            "revenue_7d_usd": round(r7sum, 2),
            "n_days": len(f30), "data_through": through, "fetched_at": now,
            "method": "P/Fees=mcap/(sum(dailyFees)*365/n_days); P/Revenue likewise on dailyRevenue (protocol revenue)",
        })
        print(f"  {p['symbol']}: mcap={mc} P/Fees={rows[-1]['p_fees']} "
              f"P/Rev={rows[-1]['p_revenue']} (n={len(f30)}, through={through})")

    def med(xs):
        xs = sorted(x for x in xs if x is not None)
        if not xs:
            return None
        m = len(xs) // 2
        return round((xs[m] + xs[~m]) / 2, 2)

    cats = {}
    for r in rows:
        cats.setdefault(r["category"], []).append(r)
    cat_med = {c: {"n": len(rs), "median_p_fees": med([x["p_fees"] for x in rs]),
                    "median_p_revenue": med([x["p_revenue"] for x in rs]),
                    "median_momentum": med([x["fees_momentum"] for x in rs])}
               for c, rs in cats.items()}

    out = {"as_of": now, "window_days": WINDOW, "annualization": "sum(trailing ~30d)*365/n_days",
           "categories": sorted(cats), "category_medians": cat_med,
           "sources": ["DefiLlama /summary/fees (free, keyless)", "CoinGecko /coins/markets (public)"],
           "caveats": [
               "dailyRevenue = protocol revenue only; holders-revenue (token-holder distributions) excluded — P/Revenue overstates cost vs total fees by design.",
               "L1 chain fees (ETH/SOL/...) accrue mostly to validators/stakers, not the token — P/Fees is a network-activity multiple, not equity P/E.",
               "Annualization extrapolates trailing 30d; crypto fees are spiky — compare across regimes, not as a point fair value.",
               "Mcap is fully-diluted-agnostic (circulating only); unlock schedules not reflected.",
           ],
           "protocols": rows}
    json.dump(out, open(os.path.join(OUT, "multiples.json"), "w"), indent=1)
    with open(os.path.join(OUT, "multiples.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "name", "category", "cg_id", "slugs_used", "market_cap_usd",
                                          "mcap_at", "fees_30d_usd", "fees_ann_usd", "revenue_30d_usd",
                                          "revenue_ann_usd", "p_fees", "p_revenue", "fees_7d_usd",
                                          "fees_7d_ann_usd", "p_fees_7d", "fees_momentum",
                                          "revenue_7d_usd", "n_days",
                                          "data_through", "fetched_at"])
        w.writeheader()
        for r in rows:
            r2 = dict(r)
            r2["slugs_used"] = "+".join(r2["slugs_used"])
            w.writerow({k: r2.get(k) for k in w.fieldnames})
    print(f"done → output/multiples.json + .csv ({len(rows)} protocols)")


if __name__ == "__main__":
    main()
