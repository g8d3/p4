"""Generate synthetic 5-minute OHLCV bars for backtesting.

Produces a regime-switching series (range / trend up / trend down) driven by
Gaussian noise. The range regime mean-reverts to a slow anchor, which creates
repeated swing highs/lows that a pivot-based S/R detector can find, and higher
volume near the anchor so the volume-profile distribution is meaningful.

Output: ag-01/data/synthetic_5m.csv
Columns: timestamp (ISO UTC), open, high, low, close, volume
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _regime_sequence(n: int, rng: np.random.Generator, mode: str) -> np.ndarray:
    """Markov chain over regimes {0: RANGE, 1: TREND_UP, 2: TREND_DOWN}."""
    if mode == "range":
        return np.zeros(n, dtype=np.int8)
    if mode == "trend":
        return np.full(n, 1, dtype=np.int8)
    if mode == "downtrend":
        return np.full(n, 2, dtype=np.int8)

    stay = {0: 0.985, 1: 0.985, 2: 0.985}
    regimes = np.empty(n, dtype=np.int8)
    regimes[0] = 0
    for i in range(1, n):
        if rng.random() < stay[regimes[i - 1]]:
            regimes[i] = regimes[i - 1]
        else:
            regimes[i] = rng.choice([0, 1, 2], p=[0.5, 0.25, 0.25])
    return regimes


def generate(n_bars: int, seed: int = 42, start_price: float = 30_000.0, mode: str = "mixed") -> pd.DataFrame:
    rng = np.random.Generator(np.random.PCG64(seed))

    regimes = _regime_sequence(n_bars, rng, mode)

    drift = {0: 0.0, 1: 0.00045, 2: -0.00045}  # per bar
    vol = {0: 0.0022, 1: 0.0035, 2: 0.0035}  # per-bar std of log-return
    base_vol_mult = {0: 1.0, 1: 0.6, 2: 0.6}

    closes = np.empty(n_bars)
    opens = np.empty(n_bars)
    highs = np.empty(n_bars)
    lows = np.empty(n_bars)
    volumes = np.empty(n_bars)

    # Slow anchor the range regime mean-reverts to.
    anchor = start_price
    price = start_price

    for i in range(n_bars):
        regime = regimes[i]

        if regime == 0:
            # Mean reversion toward the anchor: fraction of the log distance.
            mr = 0.012 * np.log(anchor / price)
        else:
            mr = 0.0

        ret = drift[regime] + mr + rng.normal(0.0, vol[regime])
        close = price * np.exp(ret)

        # Update the anchor slowly; occasional anchor jumps in range mode.
        anchor *= np.exp(rng.normal(0.0, 0.00008))
        if regime == 0 and rng.random() < 0.002:
            anchor *= np.exp(rng.normal(0.0, 0.004))

        opens[i] = price
        highs[i] = max(price, close) * np.exp(abs(rng.normal(0.0, vol[regime]) * 0.45))
        lows[i] = min(price, close) * np.exp(-abs(rng.normal(0.0, vol[regime]) * 0.45))
        closes[i] = close
        volumes[i] = rng.lognormal(mean=4.6, sigma=0.55) * base_vol_mult[regime] * (
            1.0 + 25.0 * abs(ret) / vol[regime]
        )
        price = close

    index = pd.date_range("2025-01-01 00:00", periods=n_bars, freq="5min", tz="UTC")

    df = pd.DataFrame(
        {
            "timestamp": index,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S+00:00")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-bars", type=int, default=34_560, help="number of 5-min bars (default 34560 = 120 days)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start-price", type=float, default=30_000.0)
    parser.add_argument("--mode", choices=["mixed", "range", "trend", "downtrend"], default="mixed",
                        help="market regime: mixed (default), range only, trend up only, or trend down only")
    parser.add_argument("--out", type=Path, default=DATA_DIR / "synthetic_5m.csv")
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df = generate(args.n_bars, seed=args.seed, start_price=args.start_price, mode=args.mode)
    df.to_csv(args.out, index=False)

    stats = {
        "mode": args.mode,
        "bars": len(df),
        "start": df["timestamp"].iloc[0],
        "end": df["timestamp"].iloc[-1],
        "min_close": round(float(df["close"].min()), 2),
        "max_close": round(float(df["close"].max()), 2),
        "last_close": round(float(df["close"].iloc[-1]), 2),
    }
    print("=== synthetic data ===")
    for k, v in stats.items():
        print(f"{k}: {v}")
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
