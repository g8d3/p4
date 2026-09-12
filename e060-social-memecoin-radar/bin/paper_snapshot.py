#!/usr/bin/env python3
"""e060 paper-track: snapshot today's top rotation calls to paper/calls.jsonl.

Kill rule (owner-blessed): no signal in 2 weeks of paper-tracking -> kill.
Each line: {date, ts, stale, top:[{symbol, chain, score, boost_usd, vol_h24, priceChange_h24}], n}.
Evaluated by comparing snapshot prices vs later prices (manual review weekly).
T0 free: reads local /api/rotation only, no paid APIs.
"""
import json, os, time, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "paper", "calls.jsonl")
BASE = os.environ.get("E060_BASE", "http://127.0.0.1:8323")

def main():
    with urllib.request.urlopen(BASE + "/api/rotation", timeout=20) as r:
        d = json.load(r)
    top = [{"symbol": x.get("symbol"), "chain": x.get("chain"),
            "score": x.get("rotation_score"), "boost_usd": x.get("boost_usd"),
            "vol_h24": x.get("vol_h24"), "chg24": x.get("priceChange_h24")}
           for x in d.get("rows", [])[:10]]
    rec = {"date": time.strftime("%Y-%m-%d"), "ts": int(time.time()),
           "stale": d.get("stale"), "n": len(d.get("rows", [])), "top": top}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"paper snapshot {rec['date']}: {len(top)} calls, stale={rec['stale']} -> {OUT}")

if __name__ == "__main__":
    main()
