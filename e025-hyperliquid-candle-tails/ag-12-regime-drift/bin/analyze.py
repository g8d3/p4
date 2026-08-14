#!/usr/bin/env python3
"""ag-12 regime drift: per-quarter volatility, tail shape, event frequency,
weekday effect, crash-reversion, and trend tests.

Input: ../ag-01-data/output/candles_raw.csv
Outputs: output/quarters.csv, output/pattern_stability.csv, output/charts/*.png
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDLES = os.path.join(ROOT, "..", "ag-01-data", "output", "candles_raw.csv")
OUT = os.path.join(ROOT, "output")
CH = os.path.join(OUT, "charts")
os.makedirs(CH, exist_ok=True)

COINS = ["BTC", "ETH", "SOL", "AAVE", "CRV", "DOGE", "XRP"]  # >= ~3y 1d history
TFS = ["5m", "1h", "1d", "1w"]
TF_MS = {"5m": 300000, "1h": 3600000, "1d": 86400000, "1w": 604800000}


def quarter_label(ts):
    dt = pd.to_datetime(ts, unit="ms", utc=True)
    return (dt.dt.year.astype(str) + "Q" + dt.dt.quarter.astype(str)).tolist()


def quarter_idx(ts):
    dt = pd.to_datetime(ts, unit="ms", utc=True)
    return (dt.dt.year - 2023) * 4 + dt.dt.quarter


def load():
    df = pd.read_csv(CANDLES)
    df = df[df["v"] > 0].copy()
    df = df.sort_values(["coin", "tf", "t_ms"]).reset_index(drop=True)
    df["quarter"] = quarter_label(df["t_ms"])
    df["qidx"] = quarter_idx(df["t_ms"])
    for tf in TFS:
        g = df[df["tf"] == tf].groupby("coin", sort=False)
        df.loc[df["tf"] == tf, "ret"] = g["c"].pct_change() * 100.0
    df.loc[df["tf"] == "1w", "ret"] = (
        df[df["tf"] == "1w"].groupby("coin", sort=False)["c"].pct_change() * 100.0
    )
    df["range"] = (df["h"] - df["l"]) / df["l"] * 100.0
    return df


def global_sigmas(df):
    return df[df["ret"].notna()].groupby(["coin", "tf"])["ret"].std()


def main():
    df = load()
    sig = global_sigmas(df)
    df["gsig"] = df.set_index(["coin", "tf"]).index.map(
        lambda k: sig.get(k, np.nan)
    )

    # ---------------- quarters.csv ----------------
    rows = []
    for (coin, tf), sub in df.groupby(["coin", "tf"]):
        sub = sub.dropna(subset=["ret"])
        if sub.empty:
            continue
        gs = sig[(coin, tf)]
        for q, qsub in sub.groupby("quarter"):
            rets = qsub["ret"]
            n = len(rets)
            ev = int((qsub["ret"].abs() > 3 * gs).sum())
            qint = (int(q[:4]) - 2023) * 4 + int(q[5:])
            rows.append(
                {
                    "coin": coin,
                    "tf": tf,
                    "quarter": q,
                    "qidx": qint,
                    "n": n,
                    "sigma_ret": round(rets.std(), 4),
                    "median_range": round(qsub["range"].median(), 4),
                    "kurtosis": round(float(rets.kurt()) + 3.0, 3),
                    "p99": round(rets.quantile(0.99), 3),
                    "p99_9": round(rets.quantile(0.999), 3),
                    "min": round(rets.min(), 3),
                    "max": round(rets.max(), 3),
                    "ev3_count": ev,
                    "ev3_rate": round(ev / n * 1000, 2),
                }
            )
    qdf = pd.DataFrame(rows)
    qdf = qdf.sort_values(["tf", "coin", "quarter"])
    qdf.to_csv(os.path.join(OUT, "quarters.csv"), index=False)
    print("quarters.csv rows:", len(qdf))

    # ---------------- pattern_stability.csv ----------------
    pdf_rows = []
    for tf in ["1d", "1h"]:
        sub = df[df["tf"] == tf].copy()
        sub = sub.dropna(subset=["ret"]).copy()
        sub["intraday"] = (sub["c"] - sub["o"]) / sub["o"] * 100.0
        sub["dt"] = pd.to_datetime(sub["t_ms"], unit="ms", utc=True)
        sub["weekday"] = sub["dt"].dt.weekday  # 0=Mon .. 6=Sun
        # next-5 cumulative return per candle (daily only)
        if tf == "1d":
            grp = sub.groupby("coin", sort=False)["c"]
            # ret_5 = cumulative close-to-close return over the next 5 days
            sub["ret_5"] = (grp.shift(-5) / sub["c"] - 1).mul(100.0)
            sub["ret_1"] = (grp.shift(-1) / sub["c"] - 1).mul(100.0)
        # weekday effect per quarter (ag-06 def: same-day intraday return)
        for (q, qidx), qsub in sub.groupby(["quarter", "qidx"]):
            wd = qsub.groupby("weekday")["intraday"].median()
            down = [wd.get(w, np.nan) for w in [0, 2]]
            up = [wd.get(w, np.nan) for w in [3, 6]]
            down_pool = qsub[qsub["weekday"].isin([0, 2])]["intraday"].median()
            up_pool = qsub[qsub["weekday"].isin([3, 6])]["intraday"].median()
            n_down = int(qsub["weekday"].isin([0, 2]).sum())
            n_up = int(qsub["weekday"].isin([3, 6]).sum())
            # per-coin sign of (Thu+Sun median) - (Mon+Wed median)
            coin_signs = []
            for coin, csub in qsub.groupby("coin"):
                cwd = csub.groupby("weekday")["intraday"].median()
                cup = np.nanmean([cwd.get(3, np.nan), cwd.get(6, np.nan)])
                cdn = np.nanmean([cwd.get(0, np.nan), cwd.get(2, np.nan)])
                if np.isfinite(cup) and np.isfinite(cdn):
                    coin_signs.append(1 if cup > cdn else -1)
            eff = up_pool - down_pool
            pdf_rows.append(
                {
                    "tf": tf,
                    "quarter": q,
                    "qidx": qidx,
                    "weekday_mon_med": wd.get(0, np.nan),
                    "weekday_wed_med": wd.get(2, np.nan),
                    "weekday_thu_med": wd.get(3, np.nan),
                    "weekday_sun_med": wd.get(6, np.nan),
                    "weekday_effect_med": round(float(eff), 4),
                    "weekday_n_down": n_down,
                    "weekday_n_up": n_up,
                    "weekday_coins_same_sign": int(sum(1 for s in coin_signs if s > 0)),
                    "weekday_coins_total": len(coin_signs),
                }
            )
        # crash-reversion per quarter (ag-07 def: 1d down 3-sigma events,
        # next-5 close-to-close return; 1h down events next-5 as well)
        if tf == "1d":
            ev = sub[sub["ret"] < -3 * sub["gsig"]].copy()
            base_5 = sub.groupby(["quarter", "qidx"])["ret_5"].mean()
            base_5m = sub.groupby(["quarter", "qidx"])["ret_5"].median()
            for (q, qidx), qsub in ev.groupby(["quarter", "qidx"]):
                n5 = qsub["ret_5"].notna().sum()
                row = {
                    "tf": tf,
                    "quarter": q,
                    "qidx": qidx,
                    "crash_ev_n": int(len(qsub)),
                    "crash_ev_n5": int(n5),
                    "crash_next5_mean": round(float(qsub["ret_5"].mean()), 3) if n5 else np.nan,
                    "crash_next5_median": round(float(qsub["ret_5"].median()), 3) if n5 else np.nan,
                    "base_next5_mean": round(float(base_5.get((q, qidx), np.nan)), 3),
                    "base_next5_median": round(float(base_5m.get((q, qidx), np.nan)), 3),
                    "crash_ev_mean_mag": round(float(qsub["ret"].mean()), 3),
                }
                pdf_rows.append(row)
    pdf = pd.DataFrame(pdf_rows)
    pdf = pdf.sort_values(["tf", "qidx"])
    pdf.to_csv(os.path.join(OUT, "pattern_stability.csv"), index=False)
    print("pattern_stability.csv rows:", len(pdf))

    # ---------------- pooled quarterly stats for trend/charts ----------------
    pooled = (
        qdf.groupby(["tf", "quarter"])
        .agg(
            sigma_med=("sigma_ret", "median"),
            sigma_iqr=("sigma_ret", lambda s: np.percentile(s, 75) - np.percentile(s, 25)),
            kurt_med=("kurtosis", "median"),
            p999_med=("p99_9", "median"),
            ev3_sum=("ev3_count", "sum"),
            n_sum=("n", "sum"),
        )
        .reset_index()
    )
    pooled["qidx"] = pooled["quarter"].map(
        lambda q: (int(q[:4]) - 2023) * 4 + int(q[5:])
    )
    pooled = pooled.sort_values(["tf", "qidx"])
    pooled.to_csv(os.path.join(OUT, "pooled_quarters.csv"), index=False)

    # ---------------- trend tests ----------------
    trend = []
    for tf in TFS:
        p = pooled[pooled["tf"] == tf]
        if len(p) < 4:
            trend.append(
                {
                    "tf": tf,
                    "metric": "sigma",
                    "n_quarters": int(len(p)),
                    "kendall_tau": np.nan,
                    "kendall_p": np.nan,
                    "slope_log_per_q": np.nan,
                    "note": "too few quarters",
                }
            )
            continue
        x = p["qidx"].values
        y = p["sigma_med"].values
        tau, pv = stats.kendalltau(x, y)
        lr = stats.linregress(x, np.log(y))
        trend.append(
            {
                "tf": tf,
                "metric": "sigma",
                "n_quarters": int(len(p)),
                "kendall_tau": round(float(tau), 3),
                "kendall_p": round(float(pv), 4),
                "slope_log_per_q": round(float(lr.slope), 4),
                "note": "",
            }
        )
        yk = p["kurt_med"].values
        tau, pv = stats.kendalltau(x, yk)
        trend.append(
            {
                "tf": tf,
                "metric": "kurtosis",
                "n_quarters": int(len(p)),
                "kendall_tau": round(float(tau), 3),
                "kendall_p": round(float(pv), 4),
                "slope_log_per_q": np.nan,
                "note": "",
            }
        )
    trenddf = pd.DataFrame(trend)
    trenddf.to_csv(os.path.join(OUT, "trend_test.csv"), index=False)
    print("trend_test.csv rows:", len(trenddf))

    # ---------------- charts ----------------
    plt.rcParams["figure.figsize"] = (9, 4.5)
    plt.rcParams["font.size"] = 8
    PAL = plt.get_cmap("tab10")

    # 1. vol over time per tf
    for tf in ["1d", "1h"]:
        fig, ax = plt.subplots()
        sub = qdf[qdf["tf"] == tf]
        coins = sorted(sub["coin"].unique())
        for i, c in enumerate(coins):
            cs = sub[sub["coin"] == c].sort_values("qidx")
            ax.plot(cs["quarter"], cs["sigma_ret"], "-o", ms=3, lw=1,
                    color=PAL(i % 10), label=c)
        mp = pooled[pooled["tf"] == tf].sort_values("qidx")
        ax.plot(mp["quarter"], mp["sigma_med"], "-D", ms=5, color="k",
                lw=2, label="pooled median")
        ax.set_title(f"{tf}: daily-return sigma per quarter")
        ax.set_ylabel("sigma of ret (%)")
        ax.legend(fontsize=6, ncol=3)
        ax.grid(alpha=0.3)
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()
        fig.savefig(os.path.join(CH, f"vol_over_time_{tf}.png"), dpi=120)
        plt.close(fig)

    # 2. kurtosis over time
    fig, ax = plt.subplots()
    for i, tf in enumerate(["1d", "1h", "5m"]):
        p = pooled[pooled["tf"] == tf].sort_values("qidx")
        if p.empty:
            continue
        ax.plot(p["quarter"], p["kurt_med"], "-o", ms=4, lw=1.5,
                color=PAL(i), label=f"{tf} (pooled median)")
    ax.axhline(3, color="k", ls="--", lw=1, label="normal (kurtosis=3)")
    ax.set_title("Tail shape: pooled median kurtosis per quarter")
    ax.set_ylabel("kurtosis (excess + 3)")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "kurtosis_over_time.png"), dpi=120)
    plt.close(fig)

    # 3. event frequency over time (1d)
    fig, ax = plt.subplots()
    for i, tf in enumerate(["1d", "1h"]):
        p = pooled[pooled["tf"] == tf].sort_values("qidx")
        rate = p["ev3_sum"] / p["n_sum"] * 1000
        ax.plot(p["quarter"], rate, "-o", ms=4, lw=1.5, color=PAL(i),
                label=f"{tf} (events per 1000 candles)")
    ax.set_title("3-sigma event frequency per quarter")
    ax.set_ylabel("events per 1000 candles")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "event_frequency_over_time.png"), dpi=120)
    plt.close(fig)

    # 4. weekday effect over time (1d)
    fig, ax = plt.subplots()
    wd = pdf[(pdf["tf"] == "1d") & (pdf["weekday_effect_med"].notna())].sort_values("qidx")
    if not wd.empty:
        ax.plot(wd["quarter"], wd["weekday_effect_med"], "-o", ms=4, lw=1.5,
                color=PAL(0), label="Thu+Sun vs Mon+Wed (pooled median, %)")
        ax.axhline(0, color="k", ls="--", lw=1)
        ax.set_title("Weekday effect per quarter (1d, ag-06 definition)")
        ax.set_ylabel("effect size (% intraday)")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
        ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "weekday_effect_over_time.png"), dpi=120)
    plt.close(fig)

    # 5. crash reversion over time (1d)
    fig, ax = plt.subplots()
    cr = pdf[(pdf["tf"] == "1d") & (pdf["crash_next5_median"].notna())].sort_values("qidx")
    if not cr.empty:
        ax.plot(cr["quarter"], cr["crash_next5_median"], "-o", ms=4, lw=1.5,
                color=PAL(1), label="crash events, median next-5 (%)")
        ax.plot(cr["quarter"], cr["base_next5_median"], "-s", ms=3, lw=1.2,
                color=PAL(3), alpha=0.7, label="all candles, median next-5 (%)")
        ax.set_title("Daily-crash reversion per quarter (1d)")
        ax.set_ylabel("next-5 return (%)")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
        ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "crash_reversion_over_time.png"), dpi=120)
    plt.close(fig)

    # 6. 1w vol over time (bonus)
    fig, ax = plt.subplots()
    sub = qdf[qdf["tf"] == "1w"]
    mp = pooled[pooled["tf"] == "1w"].sort_values("qidx")
    if not mp.empty:
        ax.plot(mp["quarter"], mp["sigma_med"], "-D", ms=4, color="k", lw=2,
                label="pooled median")
    for c in sorted(sub["coin"].unique()):
        cs = sub[sub["coin"] == c].sort_values("qidx")
        ax.plot(cs["quarter"], cs["sigma_ret"], "-o", ms=3, lw=1,
                color=PAL(COINS.index(c) % 10) if c in COINS else PAL(8),
                label=c, alpha=0.7)
    ax.set_title("1w: weekly-return sigma per quarter (thin: ~13 candles/quarter)")
    ax.set_ylabel("sigma of ret (%)")
    ax.legend(fontsize=6, ncol=3)
    ax.grid(alpha=0.3)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "vol_over_time_1w.png"), dpi=120)
    plt.close(fig)

    print("charts written:", sorted(os.listdir(CH)))
    print("DONE")


if __name__ == "__main__":
    main()
