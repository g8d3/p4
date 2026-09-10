#!/usr/bin/env python3
"""Fetch launchpad-token stats: CoinGecko mcap history + DefiLlama fees → data/.

CoinGecko public tier: ~1 call / 20 s, backoff on 429. Everything cached in data/.
"""
import json, os, time, urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
# works both as e057/bin/fetch.py (config one level up) and as repo-root fetch.py (config next to it)
ROOT = HERE if os.path.exists(os.path.join(HERE, "config.json")) else os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

CG = "https://api.coingecko.com/api/v3"
LLAMA_OVERVIEW = "https://api.llama.fi/overview/fees?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"
LLAMA_SUMMARY = "https://api.llama.fi/summary/fees/{slug}?dataType={dtype}"
LLAMA_PROTOS = "https://api.llama.fi/protocols"
LLAMA_DEXS = "https://api.llama.fi/overview/dexs?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"
LLAMA_AGGS = "https://api.llama.fi/overview/aggregators?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"
PUMPFUN_NEWEST = "https://frontend-api-v3.pump.fun/coins?limit=1&sort=created_timestamp"
CG_SLEEP = 20          # seconds between CoinGecko calls (public tier)
BACKOFF = 65           # seconds on 429


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "p4-e057-research"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                wait = BACKOFF * (i + 1)
                print(f"  HTTP {e.code} on {url.split('?')[0]} → sleep {wait}s")
                time.sleep(wait)
                continue
            if e.code == 404:
                return None
            raise
        except Exception as e:
            print(f"  retry ({e})")
            time.sleep(10)
    raise RuntimeError(f"failed: {url}")


def cached(name, fetch_fn, force=False, max_age=None):
    path = os.path.join(DATA, name)
    if not force and os.path.exists(path):
        fresh = max_age is None or (time.time() - os.path.getmtime(path)) < max_age
        if fresh:
            with open(path) as f:
                return json.load(f)
    val = fetch_fn()
    if val is not None:
        with open(path, "w") as f:
            json.dump(val, f)
    time.sleep(1)
    return val


def main():
    cfg = json.load(open(os.path.join(ROOT, "config.json")))
    coins = cfg["coins"]

    # 0) resolve missing cg_ids via /search (rare, spaced)
    for c in coins:
        if not c["cg_id"] and c.get("resolve"):
            res = cached(f"search__{c['resolve'].replace('.', '_').replace(' ', '_')}.json",
                         lambda: get(f"{CG}/search?query={urllib.parse.quote(c['resolve'])}"), force=True)
            hits = res.get("coins", [])[:5]
            print(f"resolve {c['symbol']}: " + ", ".join(f"{h['id']}({h['symbol']})" for h in hits))
            if hits:
                c["cg_id"] = hits[0]["id"]
            time.sleep(CG_SLEEP)

    ids = [c["cg_id"] for c in coins if c["cg_id"]]
    if len(ids) < len(coins):
        missing = [c["symbol"] for c in coins if not c["cg_id"]]
        print(f"WARNING: unresolved, skipped from CoinGecko: {missing}")

    # 1) current snapshot (1 call)
    print("markets...")
    markets = cached("markets.json",
                     lambda: get(f"{CG}/coins/markets?vs_currency=usd&ids={','.join(ids)}"
                                 f"&price_change_percentage=24h,7d,30d,1y"), force=True)
    print(f"  got {len(markets)} coins")

    # 2) mcap history per coin
    for c in coins:
        if not c["cg_id"]:
            continue
        print(f"history {c['symbol']} ({c['cg_id']})...")
        h = cached(f"mcap__{c['cg_id']}.json",
                   # NOTE: public tier caps history at 365 days (days=max → HTTP 401, error 10012)
                   lambda: get(f"{CG}/coins/{c['cg_id']}/market_chart?vs_currency=usd&days=365"),
                   max_age=20 * 3600)  # refetch daily-ish
        if h is None:
            print(f"  WARNING: no market_chart for {c['cg_id']} (bad id or delisted) → skipping")
            c["cg_id"] = None
            continue
        pts = len(h.get("market_caps", []))
        print(f"  {pts} points (365d)")
        time.sleep(CG_SLEEP)

        # coin data → all-time ATH / ATH date + social (twitter/reddit proxies)
        cached(f"coin__{c['cg_id']}.json",
               lambda: get(f"{CG}/coins/{c['cg_id']}?localization=false&tickers=false"
                           f"&market_data=true&community_data=true&developer_data=false"),
               max_age=20 * 3600)
        time.sleep(CG_SLEEP)

    # 3) DefiLlama: validate explicit slugs, fetch fees/revenue/holders-revenue per slug
    print("llama overview (validation)...")
    ov = cached("llama_overview.json", lambda: get(LLAMA_OVERVIEW), force=True)
    by_slug = {p["slug"]: p for p in ov.get("protocols", [])}

    all_slugs = sorted({s for c in coins for s in c["llama"]})
    for slug in all_slugs:
        if slug not in by_slug:
            print(f"  WARNING: slug '{slug}' not in DefiLlama fees overview")
            continue
        print(f"  '{slug}' ({by_slug[slug]['name']}): 24h fees ${by_slug[slug].get('total24h') or 0:,.0f}")
        out = {}
        for dtype in ("dailyFees", "dailyRevenue", "dailyHoldersRevenue"):
            try:
                s = cached(f"fees__{slug}__{dtype}.json", lambda: get(LLAMA_SUMMARY.format(slug=slug, dtype=dtype)), force=True)
                out[dtype] = (s or {}).get("totalDataChart", [])
            except Exception as e:
                print(f"  WARNING: {slug} {dtype} failed ({e}); continuing with empty")
                out[dtype] = []
            time.sleep(2)
        json.dump(out, open(os.path.join(DATA, f"llama__{slug}.json"), "w"))

    # 4) platform volume (DEX + aggregators) and liquidity (TVL)
    print("llama tvl + volumes...")
    protos = cached("llama_protocols.json", lambda: get(LLAMA_PROTOS), force=True) or []
    tvl = {p["slug"]: p.get("tvl") for p in protos if p.get("slug")}
    dexs = cached("llama_dexs.json", lambda: get(LLAMA_DEXS), force=True) or {"protocols": []}
    aggs = cached("llama_aggs.json", lambda: get(LLAMA_AGGS), force=True) or {"protocols": []}
    vol24 = {p["slug"]: p.get("total24h") for p in dexs.get("protocols", [])}
    vol30 = {p["slug"]: p.get("total30d") for p in dexs.get("protocols", [])}
    for p in aggs.get("protocols", []):
        vol24[p["slug"]] = p.get("total24h")
        vol30[p["slug"]] = p.get("total30d")
    json.dump({s: {"tvl": tvl.get(s), "vol24h": vol24.get(s), "vol30d": vol30.get(s)}
               for s in sorted(set(list(tvl) + list(vol24))) if s in
               {x for c in coins for x in c["llama"]}},
              open(os.path.join(DATA, "platform.json"), "w"), indent=1)

    # 5) pump.fun creation frontier (newest token mint time; rate signal accumulates over refreshes)
    try:
        front = get(PUMPFUN_NEWEST)
        newest = (front or [{}])[0].get("created_timestamp")
        if newest:
            newest = newest / 1000 if newest > 1e12 else newest  # pump.fun sends ms
            json.dump({"newest_created": int(newest), "recorded_at": int(time.time())},
                      open(os.path.join(DATA, "pumpfun_frontier.json"), "w"))
            print(f"  pump.fun newest coin: {time.strftime('%Y-%m-%d %H:%M', time.gmtime(newest))} UTC")
    except Exception as e:
        print(f"  pump.fun frontier skipped ({e})")

    print("done → data/")


if __name__ == "__main__":
    main()
