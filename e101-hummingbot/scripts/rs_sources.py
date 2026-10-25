#!/usr/bin/env python3
"""Cached source adapters (free APIs). Cache: data/cache/*.json with TTL.

CoinGecko /coins/{id}: categories (taxonomy group), market cap, volume, links,
  developer + community data. TTL 24h, 1 call every 6.5s (free tier ~10/min).
CoinMarketCap Basic: enabled only if CMC_API_KEY exists in .secrets/cmc.env
  (or env). Without a key it returns {} and logs once. Never invents values.
"""
import json, os, time
import rstrength_scan as scan

CACHE = os.path.join(scan.BASE, "data", "cache")
SECRETS = [os.path.join(scan.BASE, ".secrets", "cmc.env"),
           os.path.expanduser("~/code/p4/e100-openbot/.secrets/cmc.env")]
_last = [0.0]


def cached(name, ttl, fn):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, name + ".json")
    if os.path.exists(p) and time.time() - os.path.getmtime(p) < ttl:
        return json.load(open(p))
    v = fn()
    json.dump(v, open(p, "w"))
    return v


def _cg_coin(cid):
    wait = 6.5 - (time.time() - _last[0])
    if wait > 0: time.sleep(wait)
    _last[0] = time.time()
    d = scan.get_json(f"https://api.coingecko.com/api/v3/coins/{cid}?localization=false"
                      "&tickers=false&market_data=true&community_data=true&developer_data=true&sparkline=false")
    md, l = d.get("market_data") or {}, d.get("links") or {}
    return {"id": cid, "categories": d.get("categories") or [],
            "market_cap": (md.get("market_cap") or {}).get("usd"),
            "volume_24h": (md.get("total_volume") or {}).get("usd"),
            "homepage": [u for u in l.get("homepage") or [] if u],
            "github": [u for u in (l.get("repos_url") or {}).get("github") or [] if u],
            "twitter": l.get("twitter_screen_name") or None,
            "developer": {k: (d.get("developer_data") or {}).get(k) for k in
                          ("commit_count_4_weeks", "stars", "pull_request_contributors")},
            "community": {k: (d.get("community_data") or {}).get(k) for k in
                          ("twitter_followers", "telegram_channel_user_count")}}


def cg_meta(cid):
    try:
        return cached("cg_" + cid, 86400, lambda: _cg_coin(cid))
    except Exception as e:
        scan.log(f"cg meta {cid} unavailable: {e.__class__.__name__}")
        return {}


def taxonomy(meta):
    c = [x.lower() for x in meta.get("categories") or []]
    if any("meme" in x for x in c): return "meme"
    if any(x in ("layer 1 (l1)", "smart contract platform") for x in c): return "l1"
    if any("decentralized exchange" in x or "dex" in x for x in c): return "dex"
    if any("perpetual" in x or "derivatives" in x for x in c): return "perps"
    if any("launchpad" in x for x in c): return "launchpad"
    if any("ai" == x or "artificial intelligence" in x for x in c): return "ai"
    if any("oracle" in x for x in c): return "oracle"
    return "other" if c else None


# business-class judgment from CoinGecko categories + a DefiLlama revenue fact.
# Config, not data: these category lists decide the label; unknown -> None (n/a).
INFRA_CATS = {"infrastructure", "oracle", "bridge", "bridges", "wallets", "wallet",
              "interoperability", "privacy", "node infrastructure", "restaking",
              "staking", "staking pool", "data availability", "dev tools",
              "developer platform", "developer tools", "computational infrastructure"}
STABLE_CATS = {"stablecoin", "stablecoins", "algorithmic stablecoin", "wrapped-staked-only"}


def business_class(meta, is_meme=False, has_product_rev=False, launchpad_platform=False):
    """'stable' | 'real_business' | 'casino' | 'infra' | None (never guessed).
    A product-revenue fact (or launchpad-platform status) outranks a meme tag:
    platform tokens earn fees on OTHER coins, so "meme" alone is not casino."""
    c = {x.lower() for x in meta.get("categories") or []}
    if any(any(s in x for s in STABLE_CATS) for x in c): return "stable"
    if has_product_rev or launchpad_platform: return "real_business"
    if is_meme: return "casino"
    if c & INFRA_CATS: return "infra"
    return None


def cmc_key():
    if os.environ.get("CMC_API_KEY"): return os.environ["CMC_API_KEY"]
    for p in SECRETS:
        if os.path.exists(p):
            for line in open(p):
                if line.startswith("CMC_API_KEY="):
                    return line.split("=", 1)[1].strip() or None
    return None


def cmc_quotes(symbols):
    """CMC Basic /v2/cryptocurrency/quotes/latest. Disabled (returns {}) without a key."""
    k = cmc_key()
    if not k:
        return {}
    import urllib.request
    def f():
        req = urllib.request.Request(
            "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?symbol=" + ",".join(symbols),
            headers={"X-CMC_PRO_API_KEY": k, "Accept": "application/json"})
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        out = {}
        for s, arr in (d.get("data") or {}).items():
            if arr:
                q = arr[0]["quote"]["USD"]
                out[s] = {"market_cap": q.get("market_cap"), "volume_24h": q.get("volume_24h"),
                          "volume_change_24h": q.get("volume_change_24h")}
        return out
    return cached("cmc_quotes", 3600, f)  # Basic: 10k credits/month -> hourly cache max


if __name__ == "__main__":
    print("CMC enabled:", bool(cmc_key()))
    m = cg_meta("ore"); print(taxonomy(m), {k: m.get(k) for k in ("categories", "market_cap", "github", "developer")})
