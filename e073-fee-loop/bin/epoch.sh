#!/usr/bin/env bash
# One paper epoch: simulate, then promote winner + 2 mutants into genomes.json.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 loop.py
python3 - <<'EOF'
import json
from pathlib import Path
import random
random.seed()
H = Path("history.jsonl")
G = Path("genomes.json")
rows = [json.loads(l) for l in H.read_text().splitlines() if l.strip()]
epoch = max(r["epoch"] for r in rows)
cur = [r for r in rows if r["epoch"] == epoch]
old = {g["name"]: g for g in json.loads(G.read_text())}
win = max(cur, key=lambda r: r["fitness"])
champ = dict(old[win["name"]]); champ["name"] = "champion"

def mutate(g, name):
    m = dict(g)
    m["name"] = name
    field = random.choice(["rebateDefaultPct", "baseBps", "sinkPOL", "sinkStake", "discGenPct"])
    if field == "baseBps":
        m[field] = max(50, min(150, g[field] + random.choice([-10, 10])))
    elif field in ("sinkPOL", "sinkStake"):
        d = random.choice([-10, 10])
        m["sinkPOL"] = max(10, min(80, g["sinkPOL"] + (d if field == "sinkPOL" else -d)))
        m["sinkStake"] = max(10, min(80, g["sinkStake"] + (d if field == "sinkStake" else -d)))
        m["sinkBurn"] = 100 - m["sinkPOL"] - m["sinkStake"]
    else:
        m[field] = max(0, min(100, g[field] + random.choice([-10, 10])))
    return m

# champion-streak tracking: needs 2 in a row to dethrone (kept in genomes.json wins)
prev_wins = old.get("champion", {}).get("wins", 0)
champ["wins"] = prev_wins + 1 if win["name"] == "champion" or old.get(win["name"], {}).get("wins", 0) >= 0 and win["name"] != "champion" else 1
G.write_text(json.dumps([champ, mutate(champ, "challenger-a"), mutate(champ, "challenger-b")], indent=2))
print(f"promoted for epoch {epoch + 1}: champion ex-{win['name']} + 2 mutants")
EOF
