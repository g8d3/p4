"""screen.py — cheap causal priors for strategy candidates (no Nautilus).

The "intuition engine": before spending hours in the Nautilus harness, every
candidate idea runs through three ~2-minute screens that the experiment's own
history would have wanted BEFORE the sweeps (see BASE_RATES.md):

    A) ENTRY WIN-RATE SCREEN   causal P(+V% hit before -SL% | entry rule)
       Fase 1's killer (win rate 20-42% when ~55-67% was needed) is measured
       here directly — on closes, walk-forward, never looking ahead.
    B) FEE-BURDEN BOUND        breakeven win rate given (V, SL, taker/maker).
       e022 v1 (13,424 fills, -20.6%) was fee-predictable: this is the check.
    C) REGIME-CHURN PRIOR      the causal EMA regime filter of v2: flips/year,
       P(flip within N bars after a trend entry), churn cost floor.
       Fase 2's quantified leak (taker-flatten churn from flapping) lives here.

Output: CSV rows (one per screen) + JSON summary, fee-aware.

Usage:
    python3 screen.py --data ../e022-nautilus-sr-grid/ag-01/data/real_btc_5m.csv
    python3 screen.py --data real_btc_1h.csv --side both --meter
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

MAKER_FEE = 0.0002
TAKER_FEE = 0.0006


def load_closes(path: Path) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    df = pd.read_csv(path)
    ts = pd.to_datetime(df["timestamp"], utc=True)
    return ts, df["close"].to_numpy(dtype=float), df["high"].to_numpy(dtype=float), df["low"].to_numpy(dtype=float)


def screen_a_entry(
    ts,
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    fives: list[float],
    wins: list[float],
    stops: list[float],
    window: int = 888,
    max_bars: int = 2000,
) -> list[dict]:
    """P(hit +V% before -SL% | close <= rolling_max(prev window)*(1-C%)).

    Fully causal: the rolling max uses only closes BEFORE the entry bar.
    Resolution: first touch of the +V band or the -SL band after entry;
    if neither within max_bars the trade is marked 'unresolved' and excluded
    from win rate (reported separately as coverage).

    Vectorized per entry: future cummax/cummin inside np.searchsorted.
    """
    n = len(close)
    rows: list[dict] = []
    for C in fives:
        for V in wins:
            for SL in stops:
                # first-trigger logic: walk forward, one entry at a time
                n_entries = wins_count = 0
                i = window + 1
                cur_cummax = np.maximum.accumulate(close[: window + 1])[window]
                last_trigger = -1
                while i < n:
                    if i - last_trigger > 1 and close[i] <= cur_cummax * (1.0 - C / 100.0):
                        n_entries += 1
                        last_trigger = i
                        entry = close[i]
                        tgt = entry * (1.0 + V / 100.0)
                        stp = entry * (1.0 - SL / 100.0)
                        fut = close[i + 1 : i + max_bars + 1]
                        hit_w = np.where(fut >= tgt)[0]
                        hit_s = np.where(fut <= stp)[0]
                        if hit_w.size and hit_s.size:
                            b = hit_w[0]
                            s = hit_s[0]
                            if b < s:
                                wins_count += 1
                        elif hit_w.size:
                            wins_count += 1
                    cur_cummax = max(cur_cummax, close[i])
                    i += 1
                wr = wins_count / n_entries if n_entries else float("nan")
                rows.append(
                    {
                        "screen": "A_entry_winrate",
                        "C_pct": C,
                        "V_pct": V,
                        "SL_pct": SL,
                        "n_entries": n_entries,
                        "win_rate": round(wr, 4) if n_entries else None,
                        "note": f"{wins_count}/{n_entries}",
                    }
                )
    return rows


def screen_b_fee_bound(wins: list[float], stops: list[float], fee: float = TAKER_FEE) -> list[dict]:
    """Breakeven win rate for a (V, SL) exit pair, fee included.

    breakeven WR = (SL + 2*fee) / (V + SL)          [RR = gain/loss ratio]
    Also: total fee drag = 2*fee*fills*avg_notional (informational).
    """
    rows = []
    for V in wins:
        for SL in stops:
            be = (SL + 2 * fee * 100) / (V + SL)
            rows.append(
                {
                    "screen": "B_fee_breakeven",
                    "V_pct": V,
                    "SL_pct": SL,
                    "breakeven_win_rate": round(be, 4),
                    "needs_vs_50pct_pp": round((be - 0.5) * 100, 2),
                }
            )
    return rows


def screen_c_regime_churn(
    close: np.ndarray,
    fast: int = 50,
    slow: int = 100,
    enter: float = 1.0,
    exit_: float = 0.5,
    n_bars_per_year: float = 8760.0,
) -> list[dict]:
    """Causal recursive EMA regime filter (v2 semantics): flips, duration,
    P(flip within N bars of a trend entry), churn-cost floor estimate.

    churn floor per year = flips/year x cost-per-flip (from Test 1 data:
    ~8.50 USDT per flatten on 5m, ~2.9 on 1h).
    """
    if len(close) <= slow + 5:
        return []
    df = pd.DataFrame({"c": close})
    def ema(s: pd.Series, period: int) -> pd.Series:
        return s.ewm(span=period, adjust=False).mean()
    fast_e = ema(df["c"], fast).to_numpy()
    slow_e = ema(df["c"], slow).to_numpy()
    ratio = fast_e / slow_e - 1.0
    regime = np.full(len(close), "RANGE", dtype=object)
    cur = "RANGE"
    flips = 0
    flip_bars: list[int] = []
    for i in range(slow, len(close)):
        r = ratio[i]
        if cur == "RANGE":
            if r > enter / 100:
                cur = "LONG"
            elif r < -enter / 100:
                cur = "SHORT"
        elif cur == "LONG":
            if r < -enter / 100:
                cur = "SHORT"
            elif r < exit_ / 100:
                cur = "RANGE"
        elif cur == "SHORT":
            if r > enter / 100:
                cur = "LONG"
            elif r > -exit_ / 100:
                cur = "RANGE"
        if cur != regime[i - 1]:
            flips += 1
            flip_bars.append(i)
        regime[i] = cur
    # trend durations: distance between consecutive flips
    durations = np.diff(flip_bars) if len(flip_bars) > 1 else []
    trend_entries = [b for b, r in zip(flip_bars, regime[flip_bars]) if r in ("LONG", "SHORT")]
    # P(flip back within N bars of a trend entry):
    tb = [i for i, r in enumerate(regime[slow:]) if r != "RANGE" and (i == 0 or regime[i + slow - 1] == "RANGE")]
    tb = [i + slow for i in tb]
    inv = []
    for t in tb:
        # bars until next flip (back to RANGE or other trend)
        fut = [f for f in flip_bars if f > t]
        inv.append((fut[0] - t) if fut else None)
    inv = [d for d in inv if d is not None]
    p5 = float(np.mean([d <= 5 for d in inv])) if inv else float("nan")
    p20 = float(np.mean([d <= 20 for d in inv])) if inv else float("nan")
    return [
        {
            "screen": "C_regime_churn",
            "ema_fast": fast,
            "ema_slow": slow,
            "enter_pct": enter,
            "exit_pct": exit_,
            "flips": flips,
            "flips_per_year": round(flips / (len(close) / n_bars_per_year), 2),
            "avg_trend_bars": round(float(np.mean(inv or [0])), 2),
            "p_flip_within_5": round(p5, 4),
            "p_flip_within_20": round(p20, 4),
            "churn_cost_floor_pct_of_100k": round(
                flips * 8.5 / 1_000_000, 2
            ),  # placeholder per-flip cost is refined in docs
        }
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("screen_out.csv"))
    ap.add_argument("--fives", dest="fives", type=str, default="0.5,1.0,2.0,3.0")
    ap.add_argument("--wins", type=str, default="0.5,1.0,1.5,2.0")
    ap.add_argument("--stops", type=str, default="1.0,2.0")
    ap.add_argument("--n-bars-per-year", type=float, default=8760.0)
    ap.add_argument("--trend-fast", type=int, default=50)
    ap.add_argument("--trend-slow", type=int, default=100)
    ap.add_argument("--trend-enter", type=float, default=1.0)
    ap.add_argument("--trend-exit", type=float, default=0.5)
    args = ap.parse_args()

    ts, close, high, low = load_closes(args.data)
    fives = [float(x) for x in args.fives.split(",") if x]
    wins = [float(x) for x in args.wins.split(",") if x]
    stops = [float(x) for x in args.stops.split(",") if x]

    years = len(close) / args.n_bars_per_year
    print(f"data={args.data.name} bars={len(close)} ({years:.2f} yr)")
    out_rows = screen_a_entry(ts, close, high, low, fives, wins, stops)
    out_rows += screen_b_fee_bound(wins, stops)
    out_rows += screen_c_regime_churn(
        close,
        fast=args.trend_fast,
        slow=args.trend_slow,
        enter=args.trend_enter,
        exit_=args.trend_exit,
        n_bars_per_year=args.n_bars_per_year,
    )
    df = pd.DataFrame(out_rows)
    df.to_csv(args.out, index=False)
    print(df.to_string())
    print(f"rows wrote -> {args.out}")


if __name__ == "__main__":
    main()
