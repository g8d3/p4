#!/usr/bin/env python3
"""e073 paper epoch v0: simulate traders choosing fee universes, score fitness.

Model (toy, deterministic, documented limits):
- Representative user earns half the max discount (avg contributor).
- effectiveFee = base * (1 - discount_rep), capped.
- rebate = promoterPoolShare * rebateDefault (of effective fee).
- netFee = effectiveFee - rebate. Traders choose by logit on netFee.
- retention rises with rebate generosity + low net fee.
- wash rises with rebate, falls with stake weight (generosity/farmer tradeoff).

Fitness = retainedVolume * (1 - wash) * retention. No new code per genome:
genomes are config rows in genomes.json.
"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GENOMES = HERE / "genomes.json"
HISTORY = HERE / "history.jsonl"

N_TRADERS = 1000
AVG_VOL_ETH = 1.0
LOGIT_K = 8.0  # sensitivity to net-fee differences (bps units)


def simulate(g, epoch):
    disc_max = g["discVolPct"] + g["discGenPct"] + g["discBuildPct"] + g["discStakePct"]
    disc_rep = min(g["capPct"], disc_max * 0.5)  # avg user gets half the max
    eff_bps = g["baseBps"] * (1 - disc_rep / 100)
    promoter_pool_bps = eff_bps * (100 - g["platformSharePct"]) / 100
    rebate_bps = promoter_pool_bps * g["rebateDefaultPct"] / 100
    net_bps = eff_bps - rebate_bps
    retention = min(0.95, 0.35 + (g["rebateDefaultPct"] / 100) * 0.4
                    + max(0, (100 - eff_bps) / 100) * 0.3)
    wash = min(0.6, max(0.02, 0.05 + (g["rebateDefaultPct"] / 100) * 0.20
                        - (g["discStakePct"] / 10) * 0.015))
    return {"eff_bps": round(eff_bps, 2), "rebate_bps": round(rebate_bps, 2),
            "net_bps": round(net_bps, 2), "retention": round(retention, 4),
            "wash": round(wash, 4)}


def main():
    epoch = 1
    if HISTORY.exists():
        done = [json.loads(l) for l in HISTORY.read_text().splitlines() if l.strip()]
        if done:
            epoch = max(r["epoch"] for r in done) + 1
    genomes = json.loads(GENOMES.read_text())
    sims = [(g, simulate(g, epoch)) for g in genomes]

    # logit choice on net fee (lower net = more share)
    utils = [-s["net_bps"] * LOGIT_K / 100 for _, s in sims]
    m = max(utils)
    exps = [math.exp(u - m) for u in utils]
    tot = sum(exps)

    rows = []
    for (g, s), e in zip(sims, exps):
        share = e / tot
        volume = share * N_TRADERS * AVG_VOL_ETH
        retained = volume * s["retention"]
        fitness = retained * (1 - s["wash"]) * s["retention"]
        rows.append({"epoch": epoch, "name": g["name"], **s,
                     "share": round(share, 4), "volume": round(volume, 2),
                     "retained": round(retained, 2),
                     "fitness": round(fitness, 2)})

    rows.sort(key=lambda r: -r["fitness"])
    with HISTORY.open("a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    w = 12
    print(f"epoch {epoch}  (N={N_TRADERS} paper traders, model v0)")
    print(f"{'genome':<22}{'eff':>7}{'rebate':>8}{'net':>7}{'retain':>8}{'wash':>7}{'share':>7}{'fitness':>9}")
    for r in rows:
        print(f"{r['name']:<22}{r['eff_bps']:>7.1f}{r['rebate_bps']:>8.1f}"
              f"{r['net_bps']:>7.1f}{r['retention']:>8.2f}{r['wash']:>7.2f}"
              f"{r['share']:>7.2f}{r['fitness']:>9.1f}")
    print(f"winner: {rows[0]['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
