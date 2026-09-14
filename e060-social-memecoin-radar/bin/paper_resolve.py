#!/usr/bin/env python3
"""e060 paper-resolve: grade worthy calls 24h later, write paper/score.json.

Reads paper/calls.jsonl (worthy entries need token + priceUsd, logged by
bin/paper_snapshot.py). For each worthy call older than 24h with no outcome
in paper/outcomes.jsonl, re-fetch current price via the FREE Dexscreener
tokens API and append an outcome: hit = price up vs entry (1/0) + pct move.
Recomputes paper/score.json {resolved, hits, hit_rate_pct, pending}.

Fallback (run #70): when the Dexscreener tokens API returns nothing (token
left the boost universe or died), grade via the cached GeckoTerminal pool
(paper/pools.json, free, no key): first the hourly OHLCV candle covering
entry+24h, else the pool's current spot price. Outcome records carry
"src": dexscreener | gecko-ohlcv | gecko-spot so the card can say how
it graded. Fewer dropped outcomes -> N>=20 resolves faster.

T0 free: Dexscreener public API only, ~1 req/call, timeout-guarded.
Run: cron 2x/day + after each paper_snapshot. Safe to re-run (idempotent).
"""
import json, os, time, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALLS = os.path.join(HERE, "paper", "calls.jsonl")
OUTCOMES = os.path.join(HERE, "paper", "outcomes.jsonl")
SCORE = os.path.join(HERE, "paper", "score.json")
POOLS = os.path.join(HERE, "paper", "pools.json")
UA = {"User-Agent": "e060-radar-resolve/1.0 (+local)"}
UA_GECKO = {"User-Agent": "e060-radar-resolve/1.0 (+local)"}
GECKO_SLEEP_S = 3.0  # free tier is burst-limited; stay polite
DAY = 24 * 3600


def fetch_price(chain, addr):
    url = f"https://api.dexscreener.com/tokens/v1/{chain}/{addr}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=10) as r:
        pairs = json.load(r)
    if not pairs:
        return None
    best = max(pairs, key=lambda p: (p.get("volume") or {}).get("h24", 0))
    try:
        return float(best.get("priceUsd"))
    except (TypeError, ValueError):
        return None


def load_pools():
    try:
        with open(POOLS) as f:
            d = json.load(f)
        return {k: v for k, v in d.items() if not k.startswith("_") and v.get("pool_addr")}
    except Exception:
        return {}


def gecko_ohlcv_close(network, pool_addr, target_ts):
    """Hourly-candle close nearest entry+24h (free, no key). Returns
    (price, candle_ts) or (None, None). Picks the newest candle at or
    before target; if all are newer, takes the earliest available."""
    url = (f"https://api.geckoterminal.com/api/v2/networks/{network}"
           f"/pools/{pool_addr}/ohlcv/hour?aggregate=1"
           f"&before_timestamp={int(target_ts) + 7200}&limit=24")
    req = urllib.request.Request(url, headers=UA_GECKO)
    with urllib.request.urlopen(req, timeout=12) as r:
        d = json.load(r)
    candles = ((d.get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
    if not candles:
        return None, None
    at_or_before = [c for c in candles if c and c[0] <= target_ts]
    pick = max(at_or_before, key=lambda c: c[0]) if at_or_before else min(candles, key=lambda c: c[0])
    try:
        return float(pick[4]), int(pick[0])
    except (TypeError, ValueError, IndexError):
        return None, None


def gecko_spot(network, pool_addr):
    """Current base-token price for a pool (free, no key). Last resort."""
    url = (f"https://api.geckoterminal.com/api/v2/networks/{network}"
           f"/pools/{pool_addr}")
    req = urllib.request.Request(url, headers=UA_GECKO)
    with urllib.request.urlopen(req, timeout=12) as r:
        d = json.load(r)
    try:
        return float(((d.get("data") or {}).get("attributes") or {}).get("base_token_price_usd"))
    except (TypeError, ValueError):
        return None


def resolve_with_fallback(chain, token, entry_ts, pools):
    """(price, src, resolve_ts). Dexscreener first; vanished tokens fall
    back to cached GeckoTerminal pool OHLCV at entry+24h, then spot."""
    target = int(entry_ts) + DAY
    try:
        px = fetch_price(chain, token)
    except Exception:
        px = None
    if px is not None:
        return px, "dexscreener", int(time.time())
    rec = pools.get(token) or {}
    network, pool_addr = rec.get("network"), rec.get("pool_addr")
    if not network or not pool_addr:
        return None, "none", int(time.time())
    try:
        px, candle_ts = gecko_ohlcv_close(network, pool_addr, target)
    except Exception:
        px, candle_ts = None, None
    time.sleep(GECKO_SLEEP_S)
    if px is not None:
        return px, "gecko-ohlcv", int(candle_ts) + 3600 if candle_ts else int(time.time())
    try:
        px = gecko_spot(network, pool_addr)
    except Exception:
        px = None
    time.sleep(GECKO_SLEEP_S)
    if px is not None:
        return px, "gecko-spot", int(time.time())
    return None, "none", int(time.time())


def load_jsonl(path):
    recs = []
    try:
        with open(path) as f:
            for line in f:
                try:
                    recs.append(json.loads(line))
                except Exception:
                    pass
    except FileNotFoundError:
        pass
    return recs


def main():
    now = int(time.time())
    done_keys = set()
    outcomes = load_jsonl(OUTCOMES)
    for o in outcomes:
        done_keys.add((o.get("date"), o.get("symbol"), o.get("chain")))
    new, pending = 0, 0
    pools = load_pools()
    n_gecko = 0
    for snap in load_jsonl(CALLS):
        for e in snap.get("top", []) or []:
            if not e.get("worthy"):
                continue
            try:
                entry = float(e.get("priceUsd"))
            except (TypeError, ValueError):
                continue  # pre-priceUsd snapshot: unresolvable, skip
            token, chain = e.get("token"), e.get("chain")
            if not token or not chain:
                continue
            key = (snap.get("date"), e.get("symbol"), chain)
            if key in done_keys:
                continue
            age = now - int(snap.get("ts", now))
            if age < DAY:
                pending += 1
                continue
            px, src, rts = resolve_with_fallback(chain, token, int(snap.get("ts", now)), pools)
            if px is None:
                print(f"resolve skip {e.get('symbol')}/{chain}: no price (dex+gecko)")
                pending += 1
                continue
            if src != "dexscreener":
                n_gecko += 1
            pct = round(100.0 * (px - entry) / entry, 2) if entry else 0.0
            rec = {"date": snap.get("date"), "symbol": e.get("symbol"),
                   "chain": chain, "token": token, "entry_ts": snap.get("ts"),
                   "entry_price": entry, "resolve_ts": rts, "exit_price": px,
                   "pct_24h": pct, "hit": 1 if px > entry else 0, "src": src}
            os.makedirs(os.path.dirname(OUTCOMES), exist_ok=True)
            with open(OUTCOMES, "a") as f:
                f.write(json.dumps(rec) + "\n")
            done_keys.add(key)
            new += 1
            print(f"resolved {rec['symbol']}/{chain}: {'HIT' if rec['hit'] else 'miss'} {pct:+.1f}% via {src}")
            time.sleep(1)  # be nice to the free tier
    outcomes = load_jsonl(OUTCOMES)
    resolved = len(outcomes)
    hits = sum(1 for o in outcomes if o.get("hit"))
    # shadow bar (PAPER-tracked candidate, N<20 = THIN, never live on THIN):
    # txns>=30k & vol>=1M would have kept CATFLIGHT(+2.6%) + Stunk only.
    feats = {}
    for line in load_jsonl(CALLS):
        for e in (line.get("top") or []):
            feats[(line.get("date"), e.get("symbol"), e.get("chain"))] = e
    sh = [o for o in outcomes
          if (lambda e: (float(e.get("txns_h24") or 0) >= 3e4 and
                          float(e.get("vol_h24") or 0) >= 1e6))
          (feats.get((o.get("date"), o.get("symbol"), o.get("chain")), {}))]
    sh_hits = sum(1 for o in sh if o.get("hit"))
    shadow = {"rule": "txns>=30k & vol>=1M", "n": len(sh), "hits": sh_hits,
              "hit_rate_pct": round(100.0 * sh_hits / len(sh), 1) if sh else None,
              "thin": len(sh) < 20}
    score = {"ok": True, "track": "e060", "updated_ts": now,
             "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
             "resolved": resolved, "hits": hits,
             "hit_rate_pct": round(100.0 * hits / resolved, 1) if resolved else None,
             "shadow": shadow,
             "pending": pending, "new_this_run": new}
    os.makedirs(os.path.dirname(SCORE), exist_ok=True)
    with open(SCORE, "w") as f:
        json.dump(score, f)
    print(f"score: resolved={resolved} hits={hits} "
          f"hit_rate={score['hit_rate_pct']} pending={pending} new={new} gecko_fb={n_gecko} -> {SCORE}")


if __name__ == "__main__":
    main()
