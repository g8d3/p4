#!/usr/bin/env python3
"""e060 pools-backfill: second FREE price source for pending worthy calls.

For every worthy token in paper/calls.jsonl, resolve its top GeckoTerminal
pool (free API, no key) and cache paper/pools.json:
  {token: {network, pool, pool_addr, px_usd, ts}, ...}

Why: Dexscreener boost-universe churns (today 4/8 calls still tracked) and
dead tokens can vanish from the tokens API. A cached pool address lets the
resolver grade via pool OHLCV as fallback, so fewer outcomes drop and N>=20
resolves faster. Expected metric gain: pending->resolved coverage up, no
dropped grades. T1 free ($0). Safe to re-run (idempotent, keeps old on fail).
"""
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALLS = os.path.join(HERE, "paper", "calls.jsonl")
POOLS = os.path.join(HERE, "paper", "pools.json")
UA = {"User-Agent": "e060-radar-pools/1.0 (+local)"}
SLEEP_S = 3.0  # GeckoTerminal free tier is burst-limited; stay polite


def gecko_token(network, addr):
    url = f"https://api.geckoterminal.com/api/v2/networks/{network}/tokens/{addr}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.load(r)


def main():
    toks = {}  # token -> chain
    try:
        with open(CALLS) as f:
            for line in f:
                try:
                    snap = json.loads(line)
                except Exception:
                    continue
                for e in snap.get("top", []) or []:
                    if e.get("worthy") and e.get("token"):
                        toks[e["token"]] = (e.get("chain") or "").lower()
    except FileNotFoundError:
        pass
    prev = {}
    try:
        with open(POOLS) as f:
            prev = json.load(f)
    except Exception:
        pass
    out = dict(prev)
    n_new, n_fail, n_skip = 0, 0, 0
    now0 = int(time.time())
    for token, chain in sorted(toks.items()):
        prev_rec = out.get(token, {})
        if (prev_rec.get("pool") and isinstance(prev_rec.get("ts"), int)
                and now0 - prev_rec["ts"] < 86400):
            n_skip += 1
            continue
        net = {"solana": "solana", "robinhood": "robinhood"}.get(chain, chain)
        try:
            d = gecko_token(net, token)
            attrs = (d.get("data") or {}).get("attributes", {})
            rels = ((d.get("data") or {}).get("relationships") or {}).get(
                "top_pools", {}).get("data", [])
            pool_id = (rels[0].get("id") if rels else "") or ""
            pool_addr = pool_id.split("_", 1)[1] if "_" in pool_id else ""
            out[token] = {"network": net, "pool": pool_id,
                          "pool_addr": pool_addr,
                          "px_usd": attrs.get("price_usd"),
                          "ts": int(time.time())}
            n_new += 1
        except Exception as ex:
            n_fail += 1
            if token not in out:
                out[token] = {"network": net, "error": str(ex)[:120],
                              "ts": int(time.time())}
        time.sleep(SLEEP_S)
    out["_meta"] = {"ts": int(time.time()), "tokens": len(toks),
                    "resolved": sum(1 for k, v in out.items()
                                    if not k.startswith("_") and v.get("pool")),
                    "source": "geckoterminal-free"}
    with open(POOLS, "w") as f:
        json.dump(out, f, indent=1)
    print(f"pools ok: {out["_meta"]["resolved"]}/{len(toks)} pools, skipped={n_skip}, "
          f"failed={n_fail} -> {POOLS}")


if __name__ == "__main__":
    main()
