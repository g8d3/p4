#!/usr/bin/env python3
"""e060 paper-resolve: grade worthy calls 24h later, write paper/score.json.

Reads paper/calls.jsonl (worthy entries need token + priceUsd, logged by
bin/paper_snapshot.py). For each worthy call older than 24h with no outcome
in paper/outcomes.jsonl, re-fetch current price via the FREE Dexscreener
tokens API and append an outcome: hit = price up vs entry (1/0) + pct move.
Recomputes paper/score.json {resolved, hits, hit_rate_pct, pending}.

T0 free: Dexscreener public API only, ~1 req/call, timeout-guarded.
Run: cron 2x/day + after each paper_snapshot. Safe to re-run (idempotent).
"""
import json, os, time, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALLS = os.path.join(HERE, "paper", "calls.jsonl")
OUTCOMES = os.path.join(HERE, "paper", "outcomes.jsonl")
SCORE = os.path.join(HERE, "paper", "score.json")
UA = {"User-Agent": "e060-radar-resolve/1.0 (+local)"}
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
            try:
                px = fetch_price(chain, token)
            except Exception as ex:
                print(f"resolve skip {e.get('symbol')}/{chain}: {str(ex)[:80]}")
                pending += 1
                continue
            if px is None:
                pending += 1
                continue
            pct = round(100.0 * (px - entry) / entry, 2) if entry else 0.0
            rec = {"date": snap.get("date"), "symbol": e.get("symbol"),
                   "chain": chain, "token": token, "entry_ts": snap.get("ts"),
                   "entry_price": entry, "resolve_ts": now, "exit_price": px,
                   "pct_24h": pct, "hit": 1 if px > entry else 0}
            os.makedirs(os.path.dirname(OUTCOMES), exist_ok=True)
            with open(OUTCOMES, "a") as f:
                f.write(json.dumps(rec) + "\n")
            done_keys.add(key)
            new += 1
            print(f"resolved {rec['symbol']}/{chain}: {'HIT' if rec['hit'] else 'miss'} {pct:+.1f}%")
            time.sleep(1)  # be nice to the free tier
    outcomes = load_jsonl(OUTCOMES)
    resolved = len(outcomes)
    hits = sum(1 for o in outcomes if o.get("hit"))
    score = {"ok": True, "track": "e060", "updated_ts": now,
             "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
             "resolved": resolved, "hits": hits,
             "hit_rate_pct": round(100.0 * hits / resolved, 1) if resolved else None,
             "pending": pending, "new_this_run": new}
    os.makedirs(os.path.dirname(SCORE), exist_ok=True)
    with open(SCORE, "w") as f:
        json.dump(score, f)
    print(f"score: resolved={resolved} hits={hits} "
          f"hit_rate={score['hit_rate_pct']} pending={pending} new={new} -> {SCORE}")


if __name__ == "__main__":
    main()
