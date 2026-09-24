#!/usr/bin/env python3
"""Render LEADERBOARD.md from history.jsonl: latest epoch table + champion streaks."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
rows = [json.loads(l) for l in (HERE / "history.jsonl").read_text().splitlines() if l.strip()]
epoch = max(r["epoch"] for r in rows)
cur = sorted([r for r in rows if r["epoch"] == epoch], key=lambda r: -r["fitness"])

wins: dict[str, int] = {}
for r in rows:
    e = r["epoch"]
    best = max((x for x in rows if x["epoch"] == e), key=lambda x: x["fitness"])
    if r is best:
        wins[r["name"]] = wins.get(r["name"], 0) + 1

print(f"# e073 leaderboard — epoch {epoch} (paper, model v0)")
print()
print("| genome | eff | rebate | net | retain | wash | share | fitness | epoch-wins |")
print("|---|---|---|---|---|---|---|---|---|")
for r in cur:
    print(f"| {r['name']} | {r['eff_bps']/100:.2f}% | {r['rebate_bps']/100:.2f}% "
          f"| {r['net_bps']/100:.2f}% | {r['retention']:.2f} | {r['wash']:.2f} "
          f"| {r['share']:.2f} | {r['fitness']:.1f} | {wins.get(r['name'], 0)} |")
print()
print(f"epochs so far: {epoch}. fitness = retainedVol x (1-wash) x retention.")
