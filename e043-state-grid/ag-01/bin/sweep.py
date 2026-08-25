#!/usr/bin/env python3
"""e043 State Grid — Fase 1b: Tier-2 parameter sweep.

Runs the bar-by-bar sim over a small grid of Tier-2 configs (C spacing, V
target, SL ratio, regime filter, trailing off/on) on a given OHLCV file and
writes a comparison CSV. Bounded on purpose (three-tier discipline): only a few
parameters swept at once, nothing structural.

Run:
    python3 ag-01/bin/sweep.py --data <ohlcv.csv> --out-prefix 1h  [--grid small]
"""

import argparse, json, os, sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim


# --------------------------------------------------------------------------- #
# Grids
# --------------------------------------------------------------------------- #
GRIDS = {
    "small": {   # the promising corner: strict regime + wide geometry
        "c_mult": [2, 4],
        "V": [0.03, 0.05, 0.08],
        "sl_ratio": [2.0],
        "enter": [0.002, 0.003],
        "trailing": [False, True],
    },
    "wide": {    # larger search for a later pass
        "c_mult": [2, 4, 6],
        "V": [0.03, 0.05, 0.08, 0.12],
        "sl_ratio": [1.5, 2.5],
        "enter": [0.002, 0.003, 0.005],
        "trailing": [False, True],
    },
}

C_BASE = [0.02, 0.04, 0.06]


def build_configs(grid):
    out = []
    for cm in grid["c_mult"]:
        C = [round(x * cm, 3) for x in C_BASE]
        for v in grid["V"]:
            V = [v] * len(C)
            for sr in grid["sl_ratio"]:
                SL = [round(v * sr, 4)] * len(C)
                for ent in grid["enter"]:
                    for tr in grid["trailing"]:
                        cfg = sim.load_config(None)
                        cfg["tier2"]["C"] = C
                        cfg["tier2"]["V"] = V
                        cfg["tier2"]["SL"] = SL
                        cfg["tier1"]["anchor_mode"] = "rolling_high"
                        cfg["tier1"]["regime"] = {
                            "ema_fast": 50, "ema_slow": 100,
                            "enter_pct": ent, "exit_pct": round(ent * 0.5, 4)}
                        if tr:
                            cfg["tier1"]["sl_anchor"] = "trailing_from_peak"
                            cfg["tier1"]["trail_dist_mode"] = "atr_mult"
                            cfg["tier1"]["trail_dist"] = 2.5
                        else:
                            cfg["tier1"]["sl_anchor"] = "fixed_from_buy"
                            cfg["tier1"]["trail_dist_mode"] = "none"
                        out.append({
                            "cfg": cfg,
                            "tag": f"c{cm}_v{v:.0{2}}_sl{sr:.1f}_e{ent*1000:.0f}_tr{int(tr)}",
                        })
    return out


def run_one(df, cfg, start, anchor_vals):
    d = sim.add_indicators(df, cfg)
    g = sim.Grid(cfg)
    for i in range(start, len(d)):
        row = d.iloc[i].copy()
        row["ema_fast"] = d["ema_fast"].iloc[i - 1]
        row["ema_slow"] = d["ema_slow"].iloc[i - 1]
        row["atr"] = d["atr"].iloc[i - 1]
        row["_rhigh"] = anchor_vals[i]
        g.step(i, row)
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--grid", default="small", choices=GRIDS)
    ap.add_argument("--start", type=int, default=300)
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    rb = sim.DEFAULTS["tier1"]["anchor_lookback"]
    highs = df["high"].values
    anchor_vals = np.array([highs[max(0, i - rb):i].max() if i > 0 else highs[0]
                            for i in range(len(df))], dtype=float)

    configs = build_configs(GRIDS[args.grid])
    rows = []
    for item in configs:
        g = run_one(df, item["cfg"], args.start, anchor_vals)
        m = sim.compute_metrics(item["cfg"], g)
        wr = (g.n_win / (g.n_win + g.n_loss) * 100 if g.n_win + g.n_loss else 0)
        rows.append({
            "tag": item["tag"],
            "return_pct": m["total_return_pct"],
            "max_dd_pct": m["max_drawdown_pct"],
            "n_fills": m["n_fills"],
            "commissions": m["total_commissions_usdt"],
            "realized_pnl": m["realized_pnl_usdt"],
            "sharpe": m["sharpe"],
            "win_rate_pct": round(wr, 2),
            "exposure_time_pct": m["exposure_time_pct"],
        })
        print(item["tag"], "->", m["total_return_pct"], "DD", m["max_drawdown_pct"],
              "fills", m["n_fills"], "wr", round(wr, 1), flush=True)

    out = pd.DataFrame(rows).sort_values("return_pct", ascending=False)
    outfile = f"output/{args.out_prefix}_sweep_{args.grid}.csv"
    os.makedirs("output", exist_ok=True)
    out.to_csv(outfile, index=False)
    print("\nWrote", outfile)
    print(out.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
