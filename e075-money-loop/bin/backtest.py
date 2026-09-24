#!/usr/bin/env python3
"""Historical paper trading on e025 Hyperliquid data. Stdlib only.

Reads (never copies the 13MB files):
  ../e025-hyperliquid-candle-tails/ag-01-data/output/candles_raw.csv
  ../e025-hyperliquid-candle-tails/ag-01-data/output/funding_raw.csv

Strategies (causal, net of taker fees):
  S_FUND: daily mean funding z (trailing 90d) > +1.5 -> SHORT 1d,
          < -1.5 -> LONG 1d. Tests the funding-fade hypothesis.
  S_REV:  e025 daily decline reversion. T1 crash (ret < -3*sigma_365)
          OR T2 low-volume down (ret<0, vol_ratio < q20 trailing 101).
          LONG 5d, one position per coin.

Walk-forward: metrics reported on FULL sample + OOS second half by time.
GO rule (on OOS): expectancy > 2*round_trip_fees AND sharpe > 0.3 AND n >= 30.

Writes log/backtest.json + prints one-line summary. Exit 0 always (NOGO is
a result, not a failure). Never touches wallets, keys, or network.
"""
import csv
import json
import math
import pathlib
import statistics
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
CANDLES = ROOT.parent / "e025-hyperliquid-candle-tails" / "ag-01-data" / "output" / "candles_raw.csv"
FUNDING = ROOT.parent / "e025-hyperliquid-candle-tails" / "ag-01-data" / "output" / "funding_raw.csv"
OUT = ROOT / "log" / "backtest.json"
CONFIG = ROOT / "data" / "config.json"

DAY = 86400000
FEE_RT = 0.0009  # default, overridden by config


def load_config():
    try:
        return json.loads(CONFIG.read_text())
    except Exception:
        return {}


def load_daily_candles():
    """Per coin: sorted list of (t_day, close, volume) from 1d candles."""
    per = defaultdict(list)
    with open(CANDLES, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("tf") != "1d":
                continue
            try:
                per[row["coin"]].append((int(row["t_ms"]), float(row["c"]), float(row["v"])))
            except (ValueError, KeyError):
                continue
    for coin in per:
        per[coin].sort()
    return per


def load_daily_funding():
    """Per coin: sorted list of (t_day, mean_funding_that_day)."""
    buckets = defaultdict(lambda: defaultdict(list))
    with open(FUNDING, newline="") as f:
        for row in csv.DictReader(f):
            try:
                t = int(row["time_ms"])
                fr = float(row["fundingRate"])
            except (ValueError, KeyError):
                continue
            day = t - (t % DAY)
            buckets[row["coin"]][day].append(fr)
    out = {}
    for coin, days in buckets.items():
        out[coin] = sorted((d, sum(v) / len(v)) for d, v in days.items())
    return out


def pct(a, b):
    return (b - a) / a if a else 0.0


def quantile(xs, q):
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (k - lo)


def sharpe(daily_rets):
    if len(daily_rets) < 5:
        return 0.0
    mu = statistics.fmean(daily_rets)
    sd = statistics.pstdev(daily_rets)
    return (mu / sd * math.sqrt(365)) if sd > 0 else 0.0


def maxdd(equity):
    peak, dd = equity[0] if equity else 1.0, 0.0
    for e in equity:
        peak = max(peak, e)
        dd = min(dd, e / peak - 1 if peak else 0.0)
    return dd


def run_fund_strategy(daily, funding):
    """Returns list of trades: (coin, entry_i, exit_i, side, ret_gross)."""
    trades = []
    fund_by_day = {d: v for d, v in funding}
    fdays = sorted(fund_by_day)
    fvals = [fund_by_day[d] for d in fdays]
    closes = [c for _, c, _ in daily]
    days = [t for t, _, _ in daily]
    day_to_fund = {d: fund_by_day[d] for d in days if d in fund_by_day}
    # need index mapping day->position in daily array
    idx = {d: i for i, d in enumerate(days)}
    for j, d in enumerate(fdays):
        if d not in idx:
            continue
        i = idx[d]
        if i + 1 >= len(daily):
            continue
        hist = fvals[max(0, j - 90):j]
        if len(hist) < 30:
            continue
        mu = statistics.fmean(hist)
        sd = statistics.pstdev(hist)
        if sd == 0:
            continue
        z = (fund_by_day[d] - mu) / sd
        if z > 1.5:
            side = -1
        elif z < -1.5:
            side = +1
        else:
            continue
        gross = side * pct(closes[i], closes[i + 1])
        trades.append({"coin": None, "entry": i, "exit": i + 1, "side": side,
                       "day": d, "z": round(z, 2), "gross": gross})
    return trades


def run_rev_strategy(daily):
    """e025 S_REV: LONG 5d on crash or low-volume-down. One position per coin."""
    n = len(daily)
    closes = [c for _, c, _ in daily]
    vols = [v for _, _, v in daily]
    rets = [pct(closes[i - 1], closes[i]) if i > 0 else 0.0 for i in range(n)]
    trades = []
    busy_until = -1
    for i in range(1, n - 5):
        if i <= busy_until:
            continue
        hist_ret = rets[max(1, i - 365):i]
        if len(hist_ret) < 60:
            continue
        sigma = statistics.pstdev(hist_ret)
        t1 = rets[i] < -3 * sigma if sigma > 0 else False
        # T2: low-volume down
        w0 = max(1, i - 101)
        med_v = statistics.median(vols[w0:i]) if i - w0 >= 30 else None
        t2 = False
        if med_v and med_v > 0 and rets[i] < 0:
            ratios = [vols[k] / med_v for k in range(w0, i)]
            q20 = quantile(ratios, 0.20)
            t2 = (vols[i] / med_v) < q20
        if not (t1 or t2):
            continue
        gross = pct(closes[i], closes[i + 5])
        trades.append({"entry": i, "exit": i + 5, "side": +1,
                       "trigger": "T1" if t1 and not t2 else ("T2" if t2 and not t1 else "T1+T2"),
                       "gross": gross})
        busy_until = i + 5
    return trades


def score(trades, fee_rt):
    nets = [t["gross"] - fee_rt for t in trades]
    n = len(nets)
    if n == 0:
        return {"n": 0, "win_rate": 0.0, "expectancy": 0.0, "total": 0.0,
                "sharpe": 0.0, "maxdd": 0.0}
    wins = sum(1 for x in nets if x > 0)
    eq = 1.0
    curve = [1.0]
    for x in nets:
        eq *= (1 + x)
        curve.append(eq)
    return {"n": n, "win_rate": round(wins / n, 4),
            "expectancy": round(statistics.fmean(nets), 5),
            "total": round(eq - 1, 4), "sharpe": round(sharpe(nets), 3),
            "maxdd": round(maxdd(curve), 4)}


def main():
    cfg = load_config()
    fee_rt = cfg.get("fees", {}).get("round_trip", FEE_RT)
    universe = cfg.get("universe", [])
    if not CANDLES.exists() or not FUNDING.exists():
        err = {"ok": False, "error": "e025 data missing",
               "hint": str(CANDLES)}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(err, indent=2))
        print("BACKTEST ERROR: e025 data missing")
        return 0
    daily = load_daily_candles()
    funding = load_daily_funding()
    coins = [c for c in universe if c in daily] or sorted(daily)
    all_fund, all_rev = [], []
    per_coin = {}
    for coin in coins:
        d = daily[coin]
        mid = len(d) // 2
        f_trades = run_fund_strategy(d, funding.get(coin, []))
        r_trades = run_rev_strategy(d)
        for t in f_trades:
            t["coin"] = coin
        for t in r_trades:
            t["coin"] = coin
        # split OOS by time (second half of that coin's days)
        f_oos = [t for t in f_trades if t["entry"] >= mid]
        r_oos = [t for t in r_trades if t["entry"] >= mid]
        per_coin[coin] = {
            "days": len(d,
),
            "fund_full": score(f_trades, fee_rt),
            "fund_oos": score(f_oos, fee_rt),
            "rev_full": score(r_trades, fee_rt),
            "rev_oos": score(r_oos, fee_rt),
        }
        all_fund += f_trades
        all_rev += r_trades
    # pooled OOS: second-half trades by entry day per coin already filtered above;
    # approximate pooled OOS as sum of per-coin OOS trade lists rebuilt here:
    oos_fund = [t for coin in coins for t in
                [x for x in run_fund_strategy(daily[coin], funding.get(coin, []))]
                if t["entry"] >= len(daily[coin]) // 2]
    oos_rev = [t for coin in coins for t in
               [x for x in run_rev_strategy(daily[coin])]
               if t["entry"] >= len(daily[coin]) // 2]
    fund_full = score(all_fund, fee_rt)
    fund_oos = score(oos_fund, fee_rt)
    rev_full = score(all_rev, fee_rt)
    rev_oos = score(oos_rev, fee_rt)

    def go(m):
        return (m["expectancy"] > 2 * fee_rt and m["sharpe"] > 0.3 and m["n"] >= 30)

    rec_fund = "GO" if go(fund_oos) else "NOGO"
    rec_rev = "GO" if go(rev_oos) else "NOGO"
    overall = "GO" if (rec_fund == "GO" or rec_rev == "GO") else "NOGO"
    # deployable strategy = the better OOS expectancy among GO, else best NOGO for paper
    pick = "S_REV" if rev_oos["expectancy"] >= fund_oos["expectancy"] else "S_FUND"
    result = {
        "ok": True,
        "fee_round_trip": fee_rt,
        "coins": coins,
        "strategies": {
            "S_FUND": {"full": fund_full, "oos": fund_oos, "recommendation": rec_fund,
                       "note": "funding fade, 1d hold"},
            "S_REV": {"full": rev_full, "oos": rev_oos, "recommendation": rec_rev,
                      "note": "e025 decline reversion, LONG 5d"},
        },
        "overall": overall,
        "deploy_candidate": pick if overall == "GO" else None,
        "paper_default": pick,
        "per_coin": per_coin,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2))
    print(f"BACKTEST {overall} | S_FUND oos n={fund_oos['n']} exp={fund_oos['expectancy']} shr={fund_oos['sharpe']} | "
          f"S_REV oos n={rev_oos['n']} exp={rev_oos['expectancy']} shr={rev_oos['sharpe']} | fees={fee_rt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
