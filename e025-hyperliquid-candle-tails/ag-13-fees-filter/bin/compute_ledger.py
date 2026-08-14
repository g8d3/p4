import pandas as pd
import numpy as np

CANDLES = "/home/vuos/code/p4/e025-hyperliquid-candle-tails/ag-01-data/output/candles_raw.csv"
df = pd.read_csv(CANDLES)
df = df[df.v > 0]
df = df.sort_values(["coin", "tf", "t_ms"]).reset_index(drop=True)

df["ret"] = df.groupby(["coin", "tf"])["c"].pct_change()
df["ret_next"] = df.groupby(["coin", "tf"])["ret"].shift(-1)
df["ret_pct"] = df["ret"] * 100.0

TAKER_RT = 0.09
MAKER_RT = 0.036
SLIP_TOP = 0.02
SLIP_SMALL = 0.10

def net(edge, rt_cost):
    return edge - rt_cost

print("=" * 70)
print("1) DAILY CRASH REVERSION (ag-07 verification, full sample)")
print("=" * 70)
res = []
for coin, g in df[df.tf == "1d"].groupby("coin"):
    g = g.dropna(subset=["ret"]).reset_index(drop=True)
    sigma = g["ret"].std()
    crash = g["ret"] < -3 * sigma
    idx = np.where(crash.values)[0]
    for i in idx:
        if i + 5 < len(g):
            pnl = (g["c"].iloc[i + 5] / g["c"].iloc[i] - 1) * 100.0
            res.append({"coin": coin, "pnl": pnl})
r = pd.DataFrame(res)
print(f"events(n>=5 candles ahead): {len(r)}")
print(f"mean: {r.pnl.mean():.3f}%  median: {r.pnl.median():.3f}%  win%: {(r.pnl>0).mean()*100:.1f}%")
signs = r.groupby("coin")["pnl"].mean() > 0
print(f"coins with positive mean: {signs.sum()}/{signs.shape[0]}")
base_mean = r.pnl.mean()
for label, rt in [("taker 0.09%", TAKER_RT), ("maker 0.036%", MAKER_RT),
                  ("taker+slip top 0.11%", TAKER_RT+SLIP_TOP),
                  ("taker+slip small 0.19%", TAKER_RT+SLIP_SMALL)]:
    print(f"  net @ {label}: mean {net(base_mean, rt):.3f}%  median {net(r.pnl.median(), rt):.3f}%")

print()
print("=" * 70)
print("2) POST-CRASH NEXT-CANDLE BOUNCE in % (ag-03, pooled)")
print("=" * 70)
for tf in ["5m", "1h"]:
    grp = df[df.tf == tf].dropna(subset=["ret", "ret_next"]).copy()
    gmean = grp.groupby("coin")["ret"].transform("mean")
    gstd = grp.groupby("coin")["ret"].transform("std")
    grp["z"] = (grp["ret"] - gmean) / gstd
    grp["rn"] = grp["ret_next"] * 100.0
    ev = grp[grp["z"] < -3]
    print(f"{tf}: n={len(ev)}  p50_next={ev.rn.median():.4f}%  mean_next={ev.rn.mean():.4f}%  "
          f"net(taker) p50={ev.rn.median()-TAKER_RT:.4f}%")

print()
print("=" * 70)
print("3) BREAKEVEN edge sizes")
print("=" * 70)
for label, rt in [("taker RT 0.09%", TAKER_RT), ("maker RT 0.036%", MAKER_RT),
                  ("taker+slip(top) 0.11%", TAKER_RT+SLIP_TOP),
                  ("taker+slip(small) 0.19%", TAKER_RT+SLIP_SMALL)]:
    print(f"  {label}: breakeven gross edge = {rt:.4f}% per trade")

print()
print("=" * 70)
print("4) 1H BODY-POSITION REVERSION edge in % (ag-05 patterns.csv)")
print("=" * 70)
pat = pd.read_csv("/home/vuos/code/p4/e025-hyperliquid-candle-tails/ag-05-seasonality/output/patterns.csv")
bh = pat[(pat.feature=="body_pos")&(pat.tf=="1h")]
for _, row in bh.iterrows():
    print(f"  {row.bucket}: median_next={row.median_next:.4f}%  n={row.n}")
