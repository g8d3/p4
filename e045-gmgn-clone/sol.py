"""
sol.py — Solana memecoin client for the GMGN-style clone (e045).

Data sources (all free, no API key, public):
  * GeckoTerminal  geckoterminal.com/api/v2/networks/solana/...  -> pools, trending, token detail, OHLCV, txns
  * DexScreener    api.dexscreener.com/...                       -> token metadata/socials, boosts, new tokens
  * Solana RPC     getTokenLargestAccounts                        -> top holders (best-effort, cached)

This is the REAL GMGN surface: on-chain Solana memecoins with discovery, buy/sell
flow, stats and holders/whale data.
"""

from __future__ import annotations

import time
import json
import urllib.request

GT = "https://api.geckoterminal.com/api/v2/networks/solana"
DS = "https://api.dexscreener.com"
NETWORK = "solana"

# Solana public RPC endpoints (best-effort; often rate-limited/blocked).
RPC_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com",
    "https://mainnet.rpcpool.com",
]


class SOLError(Exception):
    pass


def _get(url: str, timeout: float = 15) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "e045-gmgn/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8")
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise SOLError(f"bad JSON from {url}: {body[:120]}") from exc


def _get_retry(url: str, tries: int = 3, timeout: float = 15) -> dict:
    """GET with retry/backoff — free APIs rate-limit intermittently."""
    import urllib.error
    for i in range(tries):
        try:
            return _get(url, timeout=timeout)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(0.4 * (i + 1))


def _cache_ttl(key: str, fn, ttl: float):
    now = time.time()
    box = getattr(_cache_ttl, "store", None)
    if box is None:
        box = {}
        setattr(_cache_ttl, "store", box)
    hit = box.get(key)
    if hit and hit[0] > now:
        return hit[1]
    try:
        val = fn()
    except Exception:
        val = hit[1] if hit else None
    if val is not None:
        box[key] = (now + ttl, val)
    return val


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _base_mint(pool: dict) -> str:
    rel = pool.get("relationships", {}).get("base_token", {})
    bid = rel.get("data", {}).get("id", "")
    return bid.split(":")[-1].split("_")[-1]


def _base_name(pool: dict) -> str:
    rel = pool.get("relationships", {}).get("base_token", {})
    bid = rel.get("data", {}).get("id", "")
    return bid.split(":")[-1].split("_")[-1]


def _pool_row(pool: dict) -> dict:
    a = pool.get("attributes", {})
    name = a.get("name", "")
    base = _base_name(pool)
    sym = name.split("/")[0] if "/" in name else base
    chg = a.get("price_change_percentage", {}) or {}
    tx = a.get("transactions", {}) or {}
    vol = a.get("volume_usd", {}) or {}
    t24 = tx.get("h24", {}) or {}
    # per-timeframe buy/sell breakdown (GMGN-style flow)
    _tf = ["m5", "m15", "m30", "h1", "h6", "h24"]
    periods = {}
    for tf in _tf:
        t = tx.get(tf) or {}
        if t:
            periods[tf] = {"buys": t.get("buys", 0), "sells": t.get("sells", 0),
                           "buyers": t.get("buyers", 0), "sellers": t.get("sellers", 0)}
    price_chg = {tf: _f(chg.get(tf)) for tf in _tf}
    return {
        "name": name.split("/")[0] if "/" in name else name,
        "symbol": sym,
        "mint": _base_mint(pool),
        "pool": a.get("address"),
        "pool_created_at": a.get("pool_created_at"),
        "price": _f(a.get("base_token_price_usd")),
        "quote_price": _f(a.get("quote_token_price_usd")),
        "market_cap": _f(a.get("market_cap_usd")) or None,
        "fdv": _f(a.get("fdv_usd")),
        "liquidity": _f(a.get("reserve_in_usd")),
        "volume_24h": _f(vol.get("h24")),
        "change_24h": price_chg.get("h24", 0),
        "change_1h": price_chg.get("h1", 0),
        "buys_24h": t24.get("buys", 0),
        "sells_24h": t24.get("sells", 0),
        "buyers_24h": t24.get("buyers", 0),
        "sellers_24h": t24.get("sellers", 0),
        "txns": periods,
        "price_change": price_chg,
        "dex": (pool.get("relationships", {}).get("dex", {}).get("data", {}).get("id") or "").split("-")[-1],
    }


def top_pools(n: int = 60) -> list[dict]:
    def f():
        d = _get(f"{GT}/pools?page=1&sort=h24_volume_usd_desc&include=base_token")
        return [_pool_row(p) for p in d.get("data", [])]

    return _cache_ttl("toppools", f, ttl=30) or []


def trending(n: int = 30) -> list[dict]:
    def f():
        d = _get(f"{GT}/trending_pools")
        return [_pool_row(p) for p in d.get("data", [])]

    return _cache_ttl("trending", f, ttl=30) or []


def boosts(n: int = 20) -> list[dict]:
    def f():
        d = _get(f"{DS}/token-boosts/top/v1?chainId={NETWORK}&limit=50")
        out = []
        for b in d:
            # no market data in this endpoint — never invent a ticker or prices
            desc = (b.get("description") or "")[:40]
            out.append({
                "name": desc or (b.get("tokenAddress") or ""),
                "symbol": (b.get("tokenAddress") or "")[:8],
                "mint": b.get("tokenAddress"),
                "pool": None, "price": None, "market_cap": None, "fdv": None,
                "liquidity": None, "volume_24h": None, "change_24h": None, "change_1h": None,
                "buys_24h": None, "sells_24h": None, "buyers_24h": None, "sellers_24h": None,
                "img": b.get("icon"),
                "flag": "boost",
                "boost": b.get("boosts", {}).get("active", 0) if isinstance(b.get("boosts"), dict) else 0,
            })
        return out

    return _cache_ttl("boosts", f, ttl=30) or []


def new_tokens(n: int = 30) -> list[dict]:
    def f():
        d = _get(f"{DS}/token-profiles/latest/v1?limit=50")
        out = []
        for b in d:
            if b.get("chainId") != NETWORK:
                continue
            out.append({
                "name": (b.get("tokenAddress") or "")[:8],
                "symbol": (b.get("tokenAddress") or "")[:8],
                "mint": b.get("tokenAddress"),
                "pool": None, "price": None, "market_cap": None, "fdv": None,
                "liquidity": None, "volume_24h": None, "change_24h": None, "change_1h": None,
                "buys_24h": None, "sells_24h": None, "buyers_24h": None, "sellers_24h": None,
                "img": b.get("icon"),
                "flag": "new",
            })
        return out

    return _cache_ttl("newtokens", f, ttl=30) or []


_MINT_INFO = {}  # mint -> (expiry, info)  — cached on-chain enrichment for listings


def _mint_info(mint: str, budget: dict):
    """Resolve a token mint to a real pool + market data (best pool by liquidity).
    Cached 180s; negative-cache 60s on failure. Bounded by `budget` per call so we
    do not hammer the free GeckoTerminal API. Never fabricates data."""
    now = time.time()
    hit = _MINT_INFO.get(mint)
    if hit and hit[0] > now:
        return hit[1]
    if budget["n"] <= 0:
        return None
    budget["n"] -= 1
    try:
        # DexScreener token endpoint: gives real market data (price, volume, liquidity,
        # mcap, fdv, txns) and is more lenient than GeckoTerminal's per-pool endpoint.
        dd = _get(f"{DS}/latest/dex/tokens/{mint}")
        pairs = dd.get("pairs", []) or []
        if not pairs:
            _MINT_INFO[mint] = (now + 60, None)
            return None
        p = max(pairs, key=lambda x: (x.get("liquidity") or {}).get("usd") or 0)
        bt = p.get("baseToken", {}) or {}
        txh = (p.get("txns", {}) or {})
        vol = (p.get("volume", {}) or {})
        prch = (p.get("priceChange", {}) or {})
        liq = (p.get("liquidity", {}) or {}).get("usd")
        periods = {}
        for tf in ("m5", "m1h", "m6h", "h24"):
            t = txh.get(tf)
            if t:
                periods[tf] = {"buys": t.get("buys", 0), "sells": t.get("sells", 0),
                               "buyers": t.get("buyers", 0), "sellers": t.get("sellers", 0)}
        h24 = txh.get("h24") or {}
        info = {
            "name": bt.get("name"),
            "symbol": bt.get("symbol"),
            "price": _f(p.get("priceUsd")),
            "volume_24h": _f(vol.get("h24")),
            "liquidity": _f(liq),
            "market_cap": _f(p.get("marketCap")) or None,
            "fdv": _f(p.get("fdv")),
            "change_24h": _f(prch.get("h24")),
            "change_1h": _f(prch.get("h1")),
            "buys_24h": h24.get("buys", 0), "sells_24h": h24.get("sells", 0),
            "buyers_24h": h24.get("buyers", 0), "sellers_24h": h24.get("sellers", 0),
            "pool": p.get("pairAddress"),
            "dex": p.get("dexId"),
            "txns": periods,
            "price_change": {t: _f(prch.get(t)) for t in ("m5", "m15", "m30", "h1", "h6", "h24")},
        }
        _MINT_INFO[mint] = (now + 180, info)
        return info
    except Exception:
        _MINT_INFO[mint] = (now + 60, None)
        return None


def screener() -> list[dict]:
    """Merged, deduped screener feed (top pools + trending + boosts + new)."""
    seen = {}
    for src in (top_pools(), trending(), boosts(), new_tokens()):
        for r in src:
            key = r.get("mint") or r.get("pool") or r.get("name")
            if not key:
                continue
            if key not in seen or (r.get("volume_24h") or 0) > (seen[key].get("volume_24h") or 0):
                seen[key] = r
    rows = [seen[k] for k in seen]
    # Enrich flagged (boost/new) listings with real on-chain pool data, batch-limited.
    budget = {"n": 8}
    for r in rows:
        if r.get("flag") and r.get("mint") and not r.get("pool"):
            info = _mint_info(r["mint"], budget)
            if info:
                for k in ("name", "symbol", "price", "volume_24h", "liquidity", "change_24h",
                          "buys_24h", "sells_24h", "buyers_24h", "sellers_24h", "fdv",
                          "market_cap", "pool", "dex", "txns", "price_change"):
                    v = info.get(k)
                    if v not in (None, 0, "", [], {}):
                        r[k] = v
                r["data"] = True  # now has real data (origin/flag kept for the New tab)
    return rows


def _screener_row_for_mint(mint: str):
    for r in screener():
        if r.get("mint") == mint or r.get("pool") == mint:
            return r
    return None


def token_detail(mint: str) -> dict:
    """Resilient detail: seed from the cached screener row, then enrich (best-effort)."""

    def f():
        detail = {"mint": mint}
        # 0) seed from cached screener row (reliable; avoids re-hitting GeckoTerminal per token)
        srow = _screener_row_for_mint(mint)
        if srow:
            for k in ("name", "symbol", "price", "volume_24h", "liquidity", "change_24h",
                      "buys_24h", "sells_24h", "buyers_24h", "sellers_24h", "fdv",
                      "market_cap", "pool", "dex", "img", "mint", "txns", "price_change"):
                v = srow.get(k)
                if v not in (None, 0, "", [], {}):
                    detail.setdefault(k, v)
        # 1) pools (stable) — primary source for price/flow when not in the screener
        try:
            pd = _get(f"{GT}/tokens/{mint}/pools")
            pools = [_pool_row(p) for p in pd.get("data", [])]
            pools.sort(key=lambda x: (x.get("liquidity") or 0), reverse=True)
            detail["pools"] = pools[:5]
            if pools:
                p = pools[0]
                detail.setdefault("pool", p.get("pool"))
                if not detail.get("name"):
                    detail["name"] = p.get("name")
                if not detail.get("symbol"):
                    detail["symbol"] = p.get("symbol")
                if not detail.get("price"):
                    detail["price"] = p.get("price")
                detail.setdefault("liquidity", p.get("liquidity"))
                detail.setdefault("volume_24h", p.get("volume_24h"))
                detail.setdefault("change_24h", p.get("change_24h"))
                detail.setdefault("buys_24h", p.get("buys_24h"))
                detail.setdefault("sells_24h", p.get("sells_24h"))
                detail.setdefault("buyers_24h", p.get("buyers_24h"))
                detail.setdefault("sellers_24h", p.get("sellers_24h"))
                detail.setdefault("dex", p.get("dex"))
                detail.setdefault("img", p.get("img"))
                if not detail.get("txns"):
                    detail["txns"] = p.get("txns")
                if not detail.get("price_change"):
                    detail["price_change"] = p.get("price_change")
        except Exception:
            detail.setdefault("pools", [])
        # 2) metadata (image/supply/decimals/mcap) — best-effort, may be rate-limited
        try:
            d = _get(f"{GT}/tokens/{mint}")
            a = d["data"]["attributes"]
            detail.setdefault("img", a.get("image_url"))
            detail.setdefault("supply", a.get("total_supply"))
            detail.setdefault("decimals", a.get("decimals"))
            if not detail.get("name"):
                detail["name"] = a.get("name") or mint[:8]
            if not detail.get("symbol"):
                detail["symbol"] = a.get("symbol") or mint[:8]
            if not detail.get("fdv"):
                detail["fdv"] = _f(a.get("fdv_usd"))
            if detail.get("market_cap") is None:
                detail["market_cap"] = _f(a.get("market_cap_usd")) or None
        except Exception:
            pass
        # 3) DexScreener socials/description + market cap fallback
        try:
            dd = _get(f"{DS}/latest/dex/tokens/{mint}")
            pairs = dd.get("pairs", [])
            if pairs:
                p = pairs[0]
                info = p.get("info", {}) or {}
                detail.setdefault("description", info.get("description"))
                detail.setdefault("socials", info.get("socials") or [])
                detail.setdefault("websites", [w.get("url") for w in (info.get("websites") or [])])
                detail.setdefault("dex", p.get("dexId"))
                if detail.get("market_cap") is None:
                    detail["market_cap"] = _f(p.get("marketCap")) or None
                if not detail.get("fdv"):
                    detail["fdv"] = _f(p.get("fdv"))
        except Exception:
            detail.setdefault("socials", [])
        # NEVER invent a name/symbol/price — leave them null if the source doesn't have them
        # 4) top holders (best-effort)
        detail["holders"] = holders(mint)
        return detail

    return _cache_ttl(f"tokdetail::{mint}", f, ttl=25) or {"mint": mint}


def candles(pool: str, timeframe: str = "15m") -> list[dict]:
    # GeckoTerminal ohlcv: {minute|hour|day} + aggregate
    tmap = {"1m": ("minute", 1), "5m": ("minute", 5), "15m": ("minute", 15),
            "1h": ("hour", 1), "4h": ("hour", 4), "1d": ("day", 1)}
    unit, agg = tmap.get(timeframe, ("minute", 15))
    url = f"{GT}/pools/{pool}/ohlcv/{unit}?aggregate={agg}&limit=150&currency=usd"

    def f():
        d = _get_retry(url, tries=3)
        li = d.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
        out = []
        for row in li:
            if isinstance(row, list) and len(row) >= 6:
                out.append({"t": int(row[0]) * 1000, "o": row[1], "h": row[2], "l": row[3], "c": row[4], "v": row[5]})
        return out

    return _cache_ttl(f"candles::{pool}::{timeframe}", f, ttl=30) or []


def holders(mint: str) -> list[dict]:
    """Top holders via Solana RPC getTokenLargestAccounts (best-effort, cached 120s)."""

    def f():
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getTokenLargestAccounts",
                              "params": [mint]}).encode("utf-8")
        for rpc in RPC_ENDPOINTS:
            try:
                req = urllib.request.Request(rpc, data=payload,
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=12) as r:
                    d = json.loads(r.read().decode("utf-8"))
                val = d.get("result", {}).get("value", [])
                if val:
                    total = sum((x.get("uiAmount") or 0) for x in val)
                    rows = []
                    for x in val:
                        amt = x.get("uiAmount") or 0
                        rows.append({"owner": x.get("address"),
                                     "amount": round(amt, 2),
                                     "pct": round((amt / total * 100.0) if total else 0, 2)})
                    return rows
            except Exception:
                continue
        return []

    return _cache_ttl(f"holders::{mint}", f, ttl=120) or []
