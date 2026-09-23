#!/usr/bin/env python3
"""e071 fetch: keyless live quotes into data/. Never computes multiples (see comps.py).

Sources: DexScreener tokens/v1 (solana/base/robinhood mints) + CoinGecko /coins/markets
(majors) + tweet seed quotes (RH names without feed yet, flagged stale=1).
All HTTP cached; reruns offline from cache.
"""
import json, os, time, urllib.request, urllib.error
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)
UNI = json.load(open(os.path.join(ROOT, "universe.json")))["tokens"]
CG = "https://api.coingecko.com/api/v3"
DEX = "https://api.dexscreener.com/tokens/v1"
GT = "https://api.geckoterminal.com/api/v2"
SOL_RPC = "https://api.mainnet-beta.solana.com"
BASE_RPC = "https://mainnet.base.org"
CACHE_AGE = 3 * 3600
QUOTE_AGE = 15 * 60  # quotes refetch every 15min cron tick; heavy detail/history keep long TTL

def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "p4-e071-fetch"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429,) or e.code >= 500:
                time.sleep(20 * (i + 1)); continue
            if e.code == 404:
                return None
            raise
        except Exception as e:
            print(f"  retry {url[:80]} ({e})"); time.sleep(5)
    print(f"  FAIL {url[:100]}"); return None

def cached(name, fn, max_age=CACHE_AGE):
    p = os.path.join(DATA, name)
    if os.path.exists(p) and (time.time() - os.path.getmtime(p)) < max_age:
        return json.load(open(p))
    v = fn()
    if v is not None:
        json.dump(v, open(p, "w"), indent=1)
    elif os.path.exists(p):
        return json.load(open(p))
    time.sleep(1)
    return v

def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # 1) CoinGecko majors in one call
    cg_ids = [t["coingecko_id"] for t in UNI if t.get("coingecko_id")]
    mk = cached("cg_markets.json",
        lambda: get(f"{CG}/coins/markets?vs_currency=usd&ids={','.join(cg_ids)}&price_change_percentage=1h,24h,7d,30d"),
        max_age=QUOTE_AGE)
    # per-coin detail for ath/atl/supply (cheap, cached long)
    for t in UNI:
        cid = t.get("coingecko_id")
        if not cid: continue
        cached(f"cg_coin__{cid}.json", lambda cid=cid: get(f"{CG}/coins/{cid}?localization=false&tickers=false&community_data=false&developer_data=false"), max_age=24*3600)
        time.sleep(2)
    # SOL price for SQUIRE fee conversion (1100 SOL creator fees -> USD sales proxy)
    sol = cached("cg_sol.json", lambda: get(f"{CG}/simple/price?ids=solana&vs_currencies=usd"), max_age=QUOTE_AGE)
    # 2) DexScreener per mint (solana/base/robinhood)
    for t in UNI:
        if t.get("chain") in ("solana", "base", "robinhood") and t.get("mint"):
            ch, mint = t["chain"], t["mint"]
            safe = mint.replace("/", "_")
            cached(f"dex__{t['symbol']}__{safe}.json", lambda ch=ch, mint=mint: get(f"{DEX}/{ch}/{mint}"), max_age=QUOTE_AGE)
            time.sleep(1)
    mode = os.environ.get("E071_MODE", "fast")
    slow = (mode == "full")
    if not slow:
        print("  fast mode: GT history + RPC supply skipped (served from cache)")
    # 3) GeckoTerminal history per mint (ATH/ATL/dates/sig-low/spark source)
    for t in UNI if slow else []:
        if t.get("chain") in ("solana", "base", "robinhood") and t.get("mint"):
            ch, mint = t["chain"], t["mint"]
            tok = cached(f"gt_token__{t['symbol']}.json",
                lambda ch=ch, mint=mint: get(f"{GT}/networks/{ch}/tokens/{mint}"),
                max_age=12 * 3600)
            pools = ((((tok or {}).get("data") or {}).get("relationships") or {}).get("top_pools") or {}).get("data") or []
            pid = (pools[0].get("id") or "").split("_", 1)[-1] if pools else None
            if pid:
                cached(f"gt_ohlcv__{t['symbol']}.json",
                    lambda ch=ch, pid=pid: get(f"{GT}/networks/{ch}/pools/{pid}/ohlcv/day?aggregate=1&limit=1000"),
                    max_age=12 * 3600)
            time.sleep(3)
    # 4) token supply via public RPCs (fills supply_total for chain mints)
    for t in UNI if slow else []:
        if t.get("chain") == "solana" and t.get("mint"):
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getTokenSupply",
                               "params": [t["mint"]]}).encode()
            def _sol(body=body):
                try:
                    req = urllib.request.Request(SOL_RPC, data=body,
                        headers={"Content-Type": "application/json", "User-Agent": "p4-e071-fetch"})
                    with urllib.request.urlopen(req, timeout=30) as r:
                        return json.load(r)
                except Exception as e:
                    print(f"  sol rpc fail ({e})"); return None
            cached(f"rpc_supply__{t['symbol']}.json", _sol, max_age=24 * 3600)
            time.sleep(2)
        if t.get("chain") == "base" and t.get("mint"):
            mint = t["mint"]
            def _base(mint=mint):
                try:
                    out = {}
                    for data, key in (("0x18160ddd", "totalSupply"), ("0x313ce567", "decimals")):
                        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                            "params": [{"to": mint, "data": data}, "latest"]}).encode()
                        req = urllib.request.Request(BASE_RPC, data=body,
                            headers={"Content-Type": "application/json", "User-Agent": "p4-e071-fetch"})
                        with urllib.request.urlopen(req, timeout=30) as r:
                            out[key] = json.load(r).get("result")
                    return out
                except Exception as e:
                    print(f"  base rpc fail ({e})"); return None
            cached(f"rpc_supply__{t['symbol']}.json", _base, max_age=24 * 3600)
            time.sleep(2)
    # 5) manifest
    man = {"fetched_at": now, "tokens": len(UNI), "cg_ids": cg_ids,
           "note": "Robinhood-chain names trade on DexScreener chainId robinhood (Uniswap v4).\nGeckoTerminal day-OHLCV fills ATH/ATL/sig-low/spark for DEX mints; public RPCs fill supply_total."}
    json.dump(man, open(os.path.join(DATA, "manifest.json"), "w"), indent=1)
    print(f"fetch ok → data/ ({len(UNI)} tokens, {len(cg_ids)} cg) at {now} sol={sol}")

if __name__ == "__main__":
    main()
