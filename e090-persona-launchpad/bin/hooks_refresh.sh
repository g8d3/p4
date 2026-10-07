#!/bin/bash
# Refresh hook TVL from DefiLlama (keyless). Usage: bin/hooks_refresh.sh
cd "$(dirname "$0")/.."
python3 - <<'PY'
import json, urllib.request
SLUGS = {"Bunni v2 hook": "bunni", "EulerSwap hook": "euler", "Arrakis Pro Hook": "arrakis-finance",
         "Gamma Limit-Order Hook": "gamma", "Flaunch hook": "flaunch", "Angstrom hook": "angstrom",
         "Fables hook (ve(3,3))": "fables", "Meteora DLMM / DAMM v2": "meteora"}
def tvl(slug):
    try:
        d = json.load(urllib.request.urlopen(f"https://api.llama.fi/protocol/{slug}", timeout=15))
        t = d.get("tvl", [])
        return round(t[-1]["totalLiquidityUSD"]) if t else None
    except Exception: return None
p = "data/hooks.json"
db = json.load(open(p))
n = 0
for h in db["hooks"]:
    s = SLUGS.get(h["name"])
    if not s: continue
    v = tvl(s)
    if v is not None:
        h["tvl_usd"] = v
        h["tvl_source"] = f"DefiLlama protocol/{s}, 2026-10-07"
        n += 1
import datetime
db["updated"] = datetime.date.today().isoformat()
json.dump(db, open(p, "w"), indent=1, ensure_ascii=False)
print(f"refreshed {n} hook TVLs")
PY
