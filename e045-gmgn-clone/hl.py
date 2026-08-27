"""
hl.py — Hyperliquid client for the GMGN-style clone (e045).

Unified client for perp + spot markets. Every REST endpoint is POST to
https://api.hyperliquid.xyz/info. Results are cached in-memory with a TTL so the
UI can auto-refresh without hammering the API.

Key facts (verified against the live API):
  * metaAndAssetCtxs        -> [meta, assetCtxs]  (perps)
  * spotMetaAndAssetCtxs    -> [meta, ctxs]       (spot pairs)
  * candleSnapshot          -> [ {t,T,s,i,o,c,h,l,v,n}, ... ]  (BOTH markets)
  * recentTrades            -> [ {coin,side,px,sz,time,hash,tid,users:[taker,maker]}, ... ] (BOTH)
  * l2Book                  -> {coin, time, levels:[bids[], asks[]] }  (BOTH)
  * allMids                 -> {coin: price}
"""

from __future__ import annotations

import time
import json
import urllib.request
import urllib.error
from typing import Any

BASE_URL = "https://api.hyperliquid.xyz/info"

# Perp/spot nudge: both candleSnapshot and recentTrades take a plain `coin`
# ("BTC" for perps, "PURR/USDC" for spot pairs). No spot-specific type names.


class HLError(Exception):
    """Raised when the Hyperliquid API returns an error."""


class Hyperliquid:
    def __init__(self, base_url: str = BASE_URL, ttl: float = 5.0):
        self.base_url = base_url
        self.ttl = ttl
        self._cache: dict[str, tuple[float, Any]] = {}

    # ---- transport -------------------------------------------------------
    def _post(self, payload: dict) -> Any:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise HLError(f"bad JSON from {self.base_url}: {body[:200]}") from exc

    def _cached(self, key: str, fn) -> Any:
        now = time.time()
        hit = self._cache.get(key)
        if hit and hit[0] > now:
            return hit[1]
        val = fn()
        self._cache[key] = (now + self.ttl, val)
        return val

    # ---- market data -----------------------------------------------------
    def meta_and_asset_ctxs(self, market: str = "perp") -> tuple[dict, list]:
        """Return (meta, asset_ctxs) for the given market ('perp'|'spot')."""
        typ = "spotMetaAndAssetCtxs" if market == "spot" else "metaAndAssetCtxs"
        key = f"metaandctx::{market}"

        def fetch():
            raw = self._post({"type": typ})
            if not isinstance(raw, list) or len(raw) < 2:
                raise HLError(f"unexpected {typ} response: {str(raw)[:200]}")
            return raw[0], raw[1]

        return self._cached(key, fetch)

    def all_mids(self) -> dict[str, str]:
        return self._cached("allmids", lambda: self._post({"type": "allMids"}))

    def candles(
        self,
        coin: str,
        interval: str = "1m",
        limit: int = 200,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict]:
        """Return OHLCV candles for a coin (works for perp + spot names)."""
        ms = INTERVAL_MS.get(interval)
        if ms is None:
            ms = 60_000
        now = int(time.time() * 1000)
        if end_time is None:
            end_time = now
        if start_time is None:
            start_time = end_time - ms * limit

        req = {
            "coin": coin,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
        }
        key = f"candles::{coin}::{interval}::{start_time}::{end_time}"

        def fetch():
            raw = self._post({"type": "candleSnapshot", "req": req})
            return raw if isinstance(raw, list) else []

        return self._cached(key, fetch)

    def trades(self, coin: str, limit: int = 100) -> list[dict]:
        """Return recent trades for a coin (perp or spot). REST caps ~ per call."""
        key = f"trades::{coin}::{limit}"
        return self._cached(key, lambda: self._post({"type": "recentTrades", "coin": coin}))

    def l2_book(self, coin: str) -> dict:
        key = f"l2::{coin}"
        return self._cached(key, lambda: self._post({"type": "l2Book", "coin": coin}))

    # ---- derived helpers -------------------------------------------------
    def markets(self, market: str = "perp") -> list[dict]:
        """Enriched screener rows for the given market."""
        meta, ctxs = self.meta_and_asset_ctxs(market)
        rows = []
        if market == "spot":
            tokens = meta.get("tokens", [])
            uni = meta.get("universe", [])
            ctx_by_coin = {c.get("coin"): c for c in ctxs if c.get("coin")}
            idx_to_name = {t["index"]: t["name"] for t in tokens}
            for pair in uni:
                ctx = ctx_by_coin.get(pair["name"])
                if ctx is None:
                    continue
                base_idx = pair["tokens"][0]
                base = idx_to_name.get(base_idx, str(base_idx))
                rows.append(self._row(base, ctx, market, coin=pair["name"], meta=meta))
        else:
            uni = meta.get("universe", [])
            for u, ctx in zip(uni, ctxs):
                rows.append(self._row(u["name"], ctx, market, coin=u["name"], u=u))
        return rows

    def _row(self, name: str, ctx: dict, market: str, meta=None, u=None, pair=None, coin=None) -> dict:
        def f(x):
            try:
                return float(x)
            except (TypeError, ValueError):
                return 0.0

        mid = f(ctx.get("midPx") or ctx.get("markPx") or ctx.get("oraclePx") or 0)
        prev = f(ctx.get("prevDayPx"))
        change = ((mid - prev) / prev * 100.0) if prev else 0.0

        row = {
            "name": name,
            "coin": coin or name,
            "market": market,
            "price": mid,
            "change_24h": round(change, 3),
            "volume_24h": f(ctx.get("dayNtlVlm")),
            "volume_base": f(ctx.get("dayBaseVlm")),
            "mark_px": f(ctx.get("markPx")),
            "oracle_px": f(ctx.get("oraclePx")),
            "ts": time.time(),
        }
        if market == "perp":
            row["open_interest"] = f(ctx.get("openInterest"))
            row["funding"] = f(ctx.get("funding"))
            row["premium"] = f(ctx.get("premium"))
            row["max_leverage"] = (u or {}).get("maxLeverage")
            row["sz_decimals"] = (u or {}).get("szDecimals")
            row["genesis"] = (u or {}).get("name")  # latest available
        else:
            row["total_supply"] = f(ctx.get("totalSupply"))
            row["circulating_supply"] = f(ctx.get("circulatingSupply"))
            row["market_cap"] = f(ctx.get("circulatingSupply")) * mid
            row["fully_diluted_cap"] = f(ctx.get("totalSupply")) * mid
            row["liquidity"] = f(ctx.get("midPx")) * 0  # placeholder, refined below
            row["base_symbol"] = name.split("/")[0] if "/" in name else name
        return row

    def token_detail(self, name: str, market: str = "perp") -> dict:
        meta, ctxs = self.meta_and_asset_ctxs(market)
        want = {}
        if market == "spot":
            tokens = meta.get("tokens", [])
            uni = meta.get("universe", [])
            ctx_by_coin = {c.get("coin"): c for c in ctxs if c.get("coin")}
            idx_to_name = {t["index"]: t["name"] for t in tokens}
            idx_to_meta = {t["index"]: t for t in tokens}
            # resolve by real token symbol first, then by pair name
            target = None
            for pair in uni:
                base_idx = pair["tokens"][0]
                sym = idx_to_name.get(base_idx, str(base_idx))
                if sym == name or pair["name"] == name:
                    target = (pair, base_idx, sym)
                    break
            if target:
                pair, base_idx, sym = target
                ctx = ctx_by_coin.get(pair["name"])
                if ctx:
                    want = self._row(sym, ctx, market, coin=pair["name"], meta=meta)
                    want["pair"] = pair["name"]
                    want["token_meta"] = idx_to_meta.get(base_idx)
        else:
            uni = meta.get("universe", [])
            for u, ctx in zip(uni, ctxs):
                if u["name"] == name:
                    want = self._row(name, ctx, market, coin=u["name"], u=u)
                    break
        if not want:
            raise HLError(f"unknown token: {name}")
        want["name"] = name
        want["market"] = market
        return want


INTERVAL_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "8h": 28_800_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
    "3d": 259_200_000,
    "1w": 604_800_000,
}
