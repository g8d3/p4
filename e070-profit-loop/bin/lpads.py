#!/usr/bin/env python3
"""Launchpad directory by chain: numbers + functions. $0 inference, free APIs only.
Sources: DefiLlama protocols (tvl/mcap/chains) + per-protocol fees summary (fees/revenue).
Functions taxonomy is curated in SEEDS (validate/extend by hand or Jev later).
Output: data/lpads.json snapshot {ts, rows:[{launchpad,chain,functions,tvl_usd,mcap_usd,fees_24h,revenue_24h}]}.
Usage: python3 bin/lpads.py
"""
import datetime
import json
import urllib.request

DIR = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
OUT = DIR + "/data/lpads.json"

# functions taxonomy: bonding | amm-grad | perps | staking | referral | streaming-fees | multi-asset | rwa | graduating-supply
SEEDS = [
    {"slug": "pumpswap", "label": "pump.fun / PumpSwap", "chain": "Solana",
     "functions": ["bonding", "amm-grad", "streaming-fees"]},
    {"slug": "sunpump", "label": "SunPump", "chain": "Tron",
     "functions": ["bonding", "amm-grad"]},
    {"slug": "raydium", "label": "Raydium (graduation venue)", "chain": "Solana",
     "functions": ["amm-grad", "perps"]},
    {"slug": "arcus-perps", "label": "Arcus (Robinhood Chain)", "chain": "Robinhood Chain",
     "functions": ["perps", "amm-grad"]},
    {"slug": "four-meme", "label": "Four.meme", "chain": "BSC",
     "functions": ["bonding", "amm-grad"]},
    {"slug": "clanker", "label": "Clanker", "chain": "Base",
     "functions": ["bonding", "amm-grad", "streaming-fees"]},
    {"slug": "zora", "label": "Zora coins", "chain": "Base",
     "functions": ["graduating-supply", "streaming-fees"]},
    {"slug": "believe", "label": "Believe", "chain": "Solana",
     "functions": ["bonding", "amm-grad", "referral"]},
]


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())


def main():
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%FT%TZ")
    protos = {p.get("slug"): p for p in get("https://api.llama.fi/protocols")}
    rows = []
    for s in SEEDS:
        p = protos.get(s["slug"], {}) or {}
        fees, rev = None, None
        try:
            f = get("https://api.llama.fi/summary/fees/%s?dataType=dailyFees" % s["slug"])
            series = (f.get("totalDataChart") or [])
            if series:
                fees = series[-1][1]
        except Exception:  # noqa: BLE001 - venue absent from fees api
            pass
        try:
            f = get("https://api.llama.fi/summary/fees/%s?dataType=dailyRevenue" % s["slug"])
            series = (f.get("totalDataChart") or [])
            if series:
                rev = series[-1][1]
        except Exception:  # noqa: BLE001
            pass
        rows.append({"launchpad": s["label"], "chain": s.get("chain") or p.get("chain", "?"),
                     "functions": s["functions"], "tvl_usd": round(p.get("tvl") or 0),
                     "mcap_usd": round(p.get("mcap") or 0) or None,
                     "fees_24h_usd": round(fees or 0) or None,
                     "revenue_24h_usd": round(rev or 0) or None,
                     "llama_slug": s["slug"], "found": bool(p)})
    json.dump({"ts": ts, "rows": rows}, open(OUT, "w"), indent=1)
    found = sum(1 for r in rows if r["found"])
    print(json.dumps({"ts": ts, "rows": len(rows), "found_on_llama": found,
                      "missing": [r["llama_slug"] for r in rows if not r["found"]]}))


if __name__ == "__main__":
    main()
