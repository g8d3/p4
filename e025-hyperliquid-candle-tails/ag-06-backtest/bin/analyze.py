#!/usr/bin/env python3
"""ag-06 — Weekday edge: permutation test + out-of-sample strategy backtest."""
import json
import os

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RNG_SEED = 42
N_PERM = 10_000

OUT = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(OUT, exist_ok=True)

CSV = os.path.join(os.path.dirname(__file__), "..", "..", "ag-01-data", "output", "candles_raw.csv")

WEEKDAY = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}

# Fees in % of notional, round trip (entry + exit)
FEE_TAKER_RT = 0.09    # 0.045% each side
FEE_MAKER_RT = 0.036   # 0.018% each side

rng = np.random.default_rng(RNG_SEED)


def load_1d():
    df = pd.read_csv(CSV)
    df = df[df["v"] != 0].copy()          # drop synthetic pre-listing candles
    d1 = df[df["tf"] == "1d"].copy()
    d1 = d1.sort_values(["coin", "t_ms"]).reset_index(drop=True)
    dt = pd.to_datetime(d1["t_ms"], unit="ms", utc=True)
    d1["weekday"] = dt.dt.weekday.astype(int)
    d1["date"] = dt.dt.strftime("%Y-%m-%d")
    g = d1.groupby("coin", sort=False)
    d1["ret"] = g["c"].pct_change() * 100.0
    d1["ret_next"] = g["ret"].shift(-1)
    d1["intraday"] = (d1["c"] - d1["o"]) / d1["o"] * 100.0
    return d1


def weekday_medians(vals, labels):
    return np.array([np.median(vals[labels == k]) for k in range(7)])


def tilt(meds):
    return (meds[3] + meds[6]) / 2 - (meds[0] + meds[2]) / 2


def spread(meds):
    return meds.max() - meds.min()


# ---------------------------------------------------------------------------
# Part 1 — Permutation test on the ag-05 finding (median ret_next by weekday)
# ---------------------------------------------------------------------------
def permutation_test(d1):
    d = d1[d1["ret_next"].notna()].copy()
    print("=== STEP 1/4: permutation test ===")

    per_coin = []
    V, W0, bounds = [], [], []
    for c, grp in d.groupby("coin", sort=True):
        v = grp["ret_next"].to_numpy(float)
        w = grp["weekday"].to_numpy(int)
        V.append(v)
        W0.append(w)
        bounds.append(len(v))
        per_coin.append(c)
    V = np.concatenate(V)
    W0 = np.concatenate(W0)
    bounds = np.cumsum(bounds)

    obs_meds = weekday_medians(V, W0)
    obs_tilt = tilt(obs_meds)
    obs_spread = spread(obs_meds)
    print(f"  observed weekday medians (ret_next): {obs_meds.round(4)}")
    print(f"  observed tilt (updays-down days): {obs_tilt:.4f}")
    print(f"  observed max-min spread: {obs_spread:.4f}")

    null_tilt = np.empty(N_PERM)
    null_spread = np.empty(N_PERM)
    start = 0
    for i in range(N_PERM):
        Wp = W0.copy()
        s = 0
        for b in bounds:
            Wp[s:b] = rng.permutation(W0[s:b])
            s = b
        m = weekday_medians(V, Wp)
        null_tilt[i] = tilt(m)
        null_spread[i] = spread(m)
    p_tilt = float((null_tilt >= obs_tilt).mean())
    p_spread = float((null_spread >= obs_spread).mean())
    print(f"  N_PERM={N_PERM}")
    print(f"  p(tilt)     = {p_tilt:.4f}")
    print(f"  p(spread)   = {p_spread:.4f}")

    # per-coin permutation
    coin_rows = []
    for c, grp in d.groupby("coin", sort=True):
        v = grp["ret_next"].to_numpy(float)
        w = grp["weekday"].to_numpy(int)
        m_obs = weekday_medians(v, w)
        t_obs = tilt(m_obs)
        n = 0
        for _ in range(N_PERM):
            wp = rng.permutation(w)
            t = tilt(weekday_medians(v, wp))
            if t >= t_obs:
                n += 1
        coin_rows.append({"coin": c, "n": len(v), "tilt_obs": t_obs, "p": n / N_PERM})

    coin_df = pd.DataFrame(coin_rows).sort_values("coin")
    n_pass_005 = int((coin_df["p"] < 0.05).sum())
    n_pass_001 = int((coin_df["p"] < 0.01).sum())
    print(coin_df.round(4).to_string(index=False))
    print(f"  coins passing p<0.05: {n_pass_005}/12, p<0.01: {n_pass_001}/12")

    # chart
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(null_tilt, bins=60, color="#7f7f7f", alpha=0.8,
            label=f"null (shuffled weekdays, N={N_PERM})")
    ax.axvline(obs_tilt, color="#d62728", lw=2.5,
               label=f"observed tilt = {obs_tilt:.3f}%")
    ax.set_xlabel("tilt = median ret_next on (Thu+Sun)/2 minus (Mon+Wed)/2 (%)")
    ax.set_ylabel("count of shuffles")
    ax.set_title("Permutation null vs observed weekday-direction pattern")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "permutation_null.png"), dpi=110)
    plt.close(fig)

    result = {
        "n_perm": N_PERM,
        "obs_meds": obs_meds.tolist(),
        "obs_tilt": obs_tilt,
        "obs_spread": obs_spread,
        "p_tilt": p_tilt,
        "p_spread": p_spread,
        "per_coin": coin_df.to_dict("records"),
        "n_pass_005": n_pass_005,
        "n_pass_001": n_pass_001,
    }
    return result


# ---------------------------------------------------------------------------
# Part 2/3 — Strategy backtest, out-of-sample (second half per coin)
# ---------------------------------------------------------------------------
def build_trades(d1):
    """OOS = t_ms strictly after the coin's median t_ms. Rule rows."""
    print("=== STEP 2/4: build trades (OOS) ===")
    oos_rows = []
    for c, grp in d1.groupby("coin", sort=True):
        med = grp["t_ms"].median()
        oos = grp[grp["t_ms"] > med]
        oos_rows.append(oos)
    oos = pd.concat(oos_rows).sort_values(["coin", "t_ms"]).reset_index(drop=True)
    print(f"  OOS candles per coin:")
    print(oos.groupby("coin").agg(first_date=("date", "min"), last_date=("date", "max"),
                                  n=("t_ms", "count")).to_string())

    RULES = {
        # weekday: +1 = long, -1 = short, 0 = no trade
        "A": {0: -1, 2: -1, 3: +1, 6: +1},
        "B": {1: +1, 4: +1, 5: +1, 0: -1, 2: -1, 3: -1, 6: -1},
        "C": {k: +1 for k in range(7)},
    }

    trades = []
    for coin, grp in oos.groupby("coin", sort=True):
        for _, r in grp.iterrows():
            wd = int(r["weekday"])
            intr = float(r["intraday"])
            for rule, m in RULES.items():
                side = m.get(wd, 0)
                if side == 0:
                    continue
                gross = intr * side
                net_t = gross - FEE_TAKER_RT
                net_m = gross - FEE_MAKER_RT
                trades.append({
                    "coin": coin, "t_ms": int(r["t_ms"]), "date": r["date"],
                    "weekday": wd, "weekday_name": WEEKDAY[wd], "rule": rule,
                    "side": "long" if side > 0 else "short",
                    "entry": float(r["o"]), "exit": float(r["c"]),
                    "gross_pct": round(gross, 6),
                    "fee_taker_pct": FEE_TAKER_RT,
                    "fee_maker_pct": FEE_MAKER_RT,
                    "net_taker_pct": round(net_t, 6),
                    "net_maker_pct": round(net_m, 6),
                })
    return pd.DataFrame(trades), oos


def oos_weekday_diagnostics(d1):
    """Show where the pattern actually lives in the OOS window.

    The ag-05 finding was measured on ret_next (return of the NEXT candle).
    The strategy trades the SAME day's intraday (c-o)/o. For contiguous 1d
    candles ret_next[t] ~ intraday[t+1], so the finding's weekday and the
    strategy's weekday are shifted by one day. This table makes that visible.
    """
    print("=== STEP 3d: OOS weekday diagnostics ===")
    rows = []
    for c, grp in d1.groupby("coin", sort=True):
        med = grp["t_ms"].median()
        oos = grp[grp["t_ms"] > med]
        for _, r in oos.iterrows():
            rows.append({"weekday": int(r["weekday"]), "intraday": float(r["intraday"]),
                         "ret_next": float(r["ret_next"]) if pd.notna(r["ret_next"]) else np.nan})
    df = pd.DataFrame(rows)
    tab = df.groupby("weekday").agg(
        intraday_med=("intraday", "median"),
        ret_next_med=("ret_next", "median"),
        n=("intraday", "size"),
    ).reindex(range(7))
    tab["weekday"] = tab.index.map(WEEKDAY)
    print(tab.round(4).to_string())
    return tab


def equity_and_metrics(trades, oos_dates):
    """Pooled daily series (equal weight per coin per day) + metrics."""
    print("=== STEP 3/4: pooled metrics ===")
    all_dates = pd.Series(sorted(pd.unique(oos_dates)))
    metrics = {}
    curves = {}
    for rule in ["A", "B", "C"]:
        tr = trades[trades["rule"] == rule]
        daily = tr.groupby("date")["net_taker_pct"].mean()  # equal weight across coins
        # align to full OOS calendar; no-trade days = 0
        ser = daily.reindex(all_dates, fill_value=0.0).to_numpy()
        equity = np.cumprod(1 + ser / 100.0)
        peak = np.maximum.accumulate(equity)
        dd = (equity / peak - 1) * 100
        total = (equity[-1] - 1) * 100
        mdd = dd.min()
        sharpe = float(np.mean(ser) / np.std(ser) * np.sqrt(365.0)) if np.std(ser) > 0 else float("nan")

        # trade-level stats (gross + both fee nets)
        g = tr["gross_pct"]
        nt = tr["net_taker_pct"]
        nm = tr["net_maker_pct"]
        m = {
            "rule": rule,
            "n_trades": len(tr),
            "total_net_taker_pct": total,
            "expectancy_gross_pct": float(g.mean()),
            "expectancy_net_taker_pct": float(nt.mean()),
            "expectancy_net_maker_pct": float(nm.mean()),
            "winrate_gross": float((g > 0).mean()),
            "winrate_net_taker": float((nt > 0).mean()),
            "winrate_net_maker": float((nm > 0).mean()),
            "max_dd_net_taker_pct": mdd,
            "sharpe_daily": sharpe,
        }
        metrics[rule] = m
        curves[rule] = equity
        print(f"  {rule}: n={len(tr):5d} total={total:7.2f}% exp_t={nt.mean():+.4f}% "
              f"win_t={(nt>0).mean():.3f} mdd={mdd:6.2f}% sharpe={sharpe:.2f}")
    return metrics, curves


def per_coin_metrics(trades):
    print("=== STEP 3b: per-coin metrics ===")
    rows = []
    for (coin, rule), tr in trades.groupby(["coin", "rule"]):
        daily = tr.groupby("date")["net_taker_pct"].mean()
        equity = np.cumprod(1 + daily.to_numpy() / 100.0)
        peak = np.maximum.accumulate(equity)
        mdd = (equity / peak - 1).min() * 100
        g, nt = tr["gross_pct"], tr["net_taker_pct"]
        rows.append({
            "coin": coin, "rule": rule, "n_trades": len(tr),
            "total_net_taker_pct": (equity[-1] - 1) * 100,
            "expectancy_gross_pct": float(g.mean()),
            "expectancy_net_taker_pct": float(nt.mean()),
            "winrate_gross": float((g > 0).mean()),
            "winrate_net_taker": float((nt > 0).mean()),
            "max_dd_net_taker_pct": float(mdd),
        })
    df = pd.DataFrame(rows).pivot(index="coin", columns="rule",
                                  values=["total_net_taker_pct", "expectancy_net_taker_pct",
                                          "winrate_net_taker", "max_dd_net_taker_pct"])
    df.columns = ["_".join(map(str, c)).replace("total_net_taker_pct_", "total_")
                  for c in df.columns]
    df = df.sort_index()
    print(df.round(2).to_string())
    return df


def buy_and_hold(d1):
    print("=== STEP 3c: buy-and-hold benchmark (OOS) ===")
    rows = []
    for c, grp in d1.groupby("coin", sort=True):
        med = grp["t_ms"].median()
        oos = grp[grp["t_ms"] > med]
        first, last = oos.iloc[0], oos.iloc[-1]
        gross = (last["c"] - first["c"]) / first["c"] * 100.0
        rows.append({"coin": c, "gross_pct": gross,
                     "net_taker_pct": gross - FEE_TAKER_RT,
                     "net_maker_pct": gross - FEE_MAKER_RT,
                     "first_date": first["date"], "last_date": last["date"]})
    bh = pd.DataFrame(rows)
    print(f"  pooled BH gross: {bh['gross_pct'].mean():.2f}%  "
          f"net taker: {bh['net_taker_pct'].mean():.2f}%")
    return bh


def equity_chart(trades, oos_dates, curves):
    print("=== STEP 4/4: charts ===")
    all_dates = pd.to_datetime(oos_dates, utc=True).unique()
    all_dates = pd.Series(sorted(all_dates))
    dd = {}
    for rule, eq in curves.items():
        peak = np.maximum.accumulate(eq)
        dd[rule] = (eq / peak - 1) * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    colors = {"A": "#1f77b4", "B": "#d62728", "C": "#2ca02c"}
    x = all_dates
    for rule, eq in curves.items():
        ax1.plot(x, (eq - 1) * 100, lw=1.6, color=colors[rule],
                 label=f"Rule {rule} (net taker)")
        ax2.plot(x, dd[rule], lw=1.2, color=colors[rule], label=f"Rule {rule}")
    ax1.set_ylabel("cumulative return (%)")
    ax1.set_title("Out-of-sample pooled equity — Rule A (weekday tilt) vs B (control) vs C (baseline long-every-day), net of taker fees")
    ax1.legend()
    ax1.grid(alpha=0.3)
    ax2.set_ylabel("drawdown (%)")
    ax2.set_xlabel("date (UTC)")
    ax2.legend(loc="lower left")
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "backtest_equity.png"), dpi=110)
    plt.close(fig)


def main():
    print("Loading 1d candles from", CSV)
    d1 = load_1d()
    print(f"  1d rows (v>0): {len(d1)}, coins: {d1['coin'].nunique()}")

    perm = permutation_test(d1)
    with open(os.path.join(OUT, "results.json"), "w") as f:
        json.dump(perm, f, indent=2)

    trades, oos = build_trades(d1)
    trades.to_csv(os.path.join(OUT, "backtest.csv"), index=False)
    print(f"  wrote backtest.csv: {len(trades)} rows, {trades['rule'].value_counts().to_dict()}")

    metrics, curves = equity_and_metrics(trades, oos["date"])
    pcoin = per_coin_metrics(trades)
    bh = buy_and_hold(d1)
    diag = oos_weekday_diagnostics(d1)
    equity_chart(trades, oos["date"], curves)

    summary = {
        "perm": perm,
        "metrics": metrics,
        "buy_and_hold": bh.to_dict("records"),
        "oos_weekday_diag": diag.round(4).to_dict("index"),
    }
    with open(os.path.join(OUT, "results.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("=== ALL DONE ===")


if __name__ == "__main__":
    main()
