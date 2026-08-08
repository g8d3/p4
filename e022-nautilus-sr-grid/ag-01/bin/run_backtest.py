"""Run a Nautilus Trader backtest of the S/R grid strategy.

Pipeline:
1. Load OHLCV bars (synthetic 5m by default, or real BTC via --data).
2. Build a synthetic BTC/USDT perpetual futures instrument + margin venue.
3. Run SRGridStrategy (v1) or SRGridStrategyV2 (--strategy v2) through
   BacktestEngine.
4. Write reports + metrics + equity curve to ag-01/output/.

Usage:
    python3 run_backtest.py [--data PATH] [--budget 30000] [--span 1.5]
    python3 run_backtest.py --strategy v2 --data data/real_btc_5m.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig, RiskEngineConfig
from nautilus_trader.model import (
    Bar,
    BarSpecification,
    BarType,
    Currency,
    InstrumentId,
    Money,
    Price,
    Quantity,
    Symbol,
    Venue,
)
from nautilus_trader.model.enums import BarAggregation, CurrencyType, OmsType, AccountType, PriceType
from nautilus_trader.model.instruments import CryptoFuture

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sr_grid_strategy import SRGridConfig, SRGridStrategy  # noqa: E402
from sr_grid_strategy_v2 import SRGridConfigV2, SRGridStrategyV2  # noqa: E402

AG_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = AG_DIR / "output"
DATA_FILE = AG_DIR / "data" / "synthetic_5m.csv"

USD = Currency("USDT", precision=2, iso4217=0, name="Tether", currency_type=CurrencyType.CRYPTO)
BTC = Currency("BTC", precision=8, iso4217=0, name="Bitcoin", currency_type=CurrencyType.CRYPTO)


def build_instrument(ts_event_ns: int, maker_fee: Decimal = Decimal("0.0002"), taker_fee: Decimal = Decimal("0.0006")) -> CryptoFuture:
    return CryptoFuture(
        instrument_id=InstrumentId(Symbol("BTC/USDT"), Venue("SIM")),
        raw_symbol=Symbol("BTC"),
        underlying=BTC,
        quote_currency=USD,
        settlement_currency=USD,
        is_inverse=False,
        activation_ns=ts_event_ns,
        expiration_ns=ts_event_ns + 10 * 365 * 24 * 3_600_000_000_000,
        price_precision=2,
        size_precision=6,
        price_increment=Price.from_str("0.01"),
        size_increment=Quantity.from_str("0.000001"),
        ts_event=ts_event_ns,
        ts_init=ts_event_ns,
        multiplier=Quantity.from_int(1),
        lot_size=Quantity.from_int(1),
        margin_init=Decimal("0.0"),
        margin_maint=Decimal("0.0"),
        maker_fee=maker_fee,
        taker_fee=taker_fee,
    )


def infer_bar_spec(df: pd.DataFrame) -> BarSpecification:
    """Infer the bar interval from the median timestamp delta."""
    ts = pd.to_datetime(df["timestamp"], utc=True)
    deltas = ts.diff().dropna().dt.total_seconds().astype(int)
    median = int(deltas.median()) if len(deltas) else 300
    if median % 3600 == 0:
        return BarSpecification(median // 3600, BarAggregation.HOUR, PriceType.LAST)
    if median % 60 == 0:
        return BarSpecification(median // 60, BarAggregation.MINUTE, PriceType.LAST)
    raise ValueError(f"cannot infer bar aggregation from median delta {median}s")


def load_bars(path: Path) -> tuple[list[Bar], BarType]:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    ts_ns = (df["timestamp"].astype("int64")).tolist()

    bar_spec = infer_bar_spec(df)
    bar_type = BarType(
        InstrumentId(Symbol("BTC/USDT"), Venue("SIM")),
        bar_spec,
    )

    bars = []
    for i in range(len(df)):
        bars.append(
            Bar.from_dict(
                {
                    "bar_type": str(bar_type),
                    "open": f"{df['open'].iloc[i]:.2f}",
                    "high": f"{df['high'].iloc[i]:.2f}",
                    "low": f"{df['low'].iloc[i]:.2f}",
                    "close": f"{df['close'].iloc[i]:.2f}",
                    "volume": f"{df['volume'].iloc[i]:.6f}",
                    "ts_event": ts_ns[i],
                    "ts_init": ts_ns[i],
                }
            )
        )
    return bars, bar_type


def compute_metrics(
    equity_curve: list[tuple[int, float]],
    fills_df: pd.DataFrame,
    positions_df: pd.DataFrame,
) -> dict:
    eq = pd.DataFrame(equity_curve, columns=["ts", "equity"])
    eq["ret"] = eq["equity"].pct_change()
    eq = eq.dropna()

    total_return = eq["equity"].iloc[-1] / eq["equity"].iloc[0] - 1.0
    pnl = eq["equity"].iloc[-1] - eq["equity"].iloc[0]

    # Annualized Sharpe (5-min samples -> 288 samples/day, 365 days).
    std = eq["ret"].std()
    sharpe = float("nan") if std == 0 or np.isnan(std) else (eq["ret"].mean() / std) * np.sqrt(288 * 365)

    # Max drawdown on equity.
    peak = eq["equity"].cummax()
    drawdown = eq["equity"] / peak - 1.0
    max_dd = float(drawdown.min())

    n_fills = len(fills_df) if not fills_df.empty else 0
    total_commissions = 0.0
    if not fills_df.empty:
        for c in fills_df["commissions"]:
            if isinstance(c, list):
                for item in c:
                    total_commissions += float(str(item).split()[0])
            elif isinstance(c, str) and c.strip():
                total_commissions += float(c.strip("[]' ").split()[0])

    pos = positions_df.copy()
    n_positions = len(pos) if not pos.empty else 0
    if not pos.empty and "realized_pnl" in pos.columns:
        rp = pos["realized_pnl"].map(lambda v: float(str(v).split()[0]))
        wins = pos[rp > 0]
        losses = pos[rp < 0]
        gross_win = float(wins["realized_pnl"].map(lambda v: float(str(v).split()[0])).sum()) if not wins.empty else 0.0
        gross_loss = abs(float(losses["realized_pnl"].map(lambda v: float(str(v).split()[0])).sum())) if not losses.empty else 0.0
        profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")
        win_rate = len(wins) / n_positions if n_positions else 0.0
    else:
        gross_win = gross_loss = profit_factor = win_rate = 0.0

    return {
        "total_return_pct": round(total_return * 100, 4),
        "total_pnl_usdt": round(pnl, 2),
        "sharpe": round(sharpe, 4),
        "max_drawdown_pct": round(max_dd * 100, 4),
        "n_fills": n_fills,
        "n_positions": n_positions,
        "total_commissions_usdt": round(total_commissions, 2),
        "gross_win_usdt": round(gross_win, 2),
        "gross_loss_usdt": round(gross_loss, 2),
    "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else None,
        "win_rate_pct": round(win_rate * 100, 4),
        "final_equity_usdt": round(float(eq["equity"].iloc[-1]), 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA_FILE)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--strategy", choices=["v1", "v2", "v3"], default="v1")
    parser.add_argument("--budget", type=float, default=30_000.0, help="grid budget (USDT)")
    parser.add_argument("--start-balance", type=float, default=100_000.0)
    parser.add_argument("--span", type=float, default=1.5, help="grid span % (v1 only)")
    parser.add_argument("--rebalance", type=int, default=96, help="rebalance interval in bars")
    parser.add_argument("--max-levels", type=int, default=8)
    parser.add_argument("--min-levels", type=int, default=3)
    parser.add_argument("--max-order-notional", type=float, default=5_000.0)
    parser.add_argument("--max-exposure-mult", type=float, default=1.5)
    parser.add_argument("--maker-fee", type=float, default=0.0002, help="maker fee rate")
    parser.add_argument("--taker-fee", type=float, default=0.0006, help="taker fee rate")
    parser.add_argument("--atr-mult", type=float, default=1.5, help="grid level spacing in ATR (v2)")
    parser.add_argument("--min-order", type=float, default=500.0, help="min order notional (v2)")
    parser.add_argument("--trend-fast", type=int, default=20, help="trend fast EMA (v2)")
    parser.add_argument("--trend-slow", type=int, default=100, help="trend slow EMA (v2)")
    parser.add_argument("--trend-enter", type=float, default=0.5, help="trend enter % (v2)")
    parser.add_argument("--trend-exit", type=float, default=0.2, help="trend exit % (v2)")
    parser.add_argument("--trend-off", action="store_true", help="disable trend filter (v2)")
    parser.add_argument("--trend-budget-mult", type=float, default=2.0, help="trend notional as mult of grid budget (v3)")
    parser.add_argument("--log-level", default="ERROR")
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    bars, bar_type = load_bars(args.data)
    first_ts = bars[0].ts_event
    instrument = build_instrument(first_ts, Decimal(str(args.maker_fee)), Decimal(str(args.taker_fee)))

    if args.strategy in ("v2", "v3"):
        if args.strategy == "v3":
            from sr_grid_strategy_v3 import SRGridConfigV3, SRGridStrategyV3
        else:
            from sr_grid_strategy_v2 import SRGridConfigV2, SRGridStrategyV2
        config_cls = SRGridConfigV3 if args.strategy == "v3" else SRGridConfigV2
        strategy_cls = SRGridStrategyV3 if args.strategy == "v3" else SRGridStrategyV2
        kwargs = dict(
            instrument_id=instrument.id,
            bar_type=bar_type,
            grid_budget=Decimal(str(args.budget)),
            rebalance_interval_bars=args.rebalance,
            max_levels_per_side=args.max_levels,
            grid_atr_mult=args.atr_mult,
            min_order_notional=Decimal(str(args.min_order)),
            max_order_notional=Decimal(str(args.max_order_notional)),
            max_exposure_budget_mult=args.max_exposure_mult,
            trend_filter_enabled=not args.trend_off,
            trend_ema_fast=args.trend_fast,
            trend_ema_slow=args.trend_slow,
            trend_enter_pct=args.trend_enter,
            trend_exit_pct=args.trend_exit,
        )
        if args.strategy == "v3":
            kwargs["trend_budget_mult"] = args.trend_budget_mult
        config = config_cls(**kwargs)
        strategy = strategy_cls(config=config)
    else:
        config = SRGridConfig(
            instrument_id=instrument.id,
            bar_type=bar_type,
            grid_budget=Decimal(str(args.budget)),
            grid_span_pct=args.span,
            rebalance_interval_bars=args.rebalance,
            max_levels_per_side=args.max_levels,
            min_levels_per_side=args.min_levels,
            max_order_notional=Decimal(str(args.max_order_notional)),
            max_exposure_budget_mult=args.max_exposure_mult,
        )
        strategy = SRGridStrategy(config=config)

    engine = BacktestEngine(
        config=BacktestEngineConfig(
            trader_id="TESTER-001",
            risk_engine=RiskEngineConfig(bypass=True),
            logging=LoggingConfig(log_level=args.log_level),
        )
    )
    engine.add_venue(
        venue=Venue("SIM"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USD,
        starting_balances=[Money(args.start_balance, USD)],
    )
    engine.add_instrument(instrument)
    engine.add_strategy(strategy)
    engine.add_data(bars)
    engine.run()

    account_df = engine.trader.generate_account_report(venue=Venue("SIM"))
    fills_df = engine.trader.generate_order_fills_report()
    positions_df = engine.trader.generate_positions_report()

    def save_report(name: str, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        df.to_csv(out_dir / name, index=False)
        return df

    account_df = save_report("account_report.csv", account_df)
    fills_df = save_report("fills_report.csv", fills_df)
    positions_df = save_report("positions_report.csv", positions_df)

    metrics = compute_metrics(strategy._equity_curve, fills_df, positions_df)
    metrics["n_rebalances"] = strategy.n_rebalances
    metrics["n_resyncs"] = strategy.n_resyncs
    metrics["n_fills"] = strategy.n_fills
    metrics["total_commissions_usdt"] = round(strategy.total_commissions, 2)
    for attr in ("n_regime_flips", "n_liquidations", "n_cap_enforcements"):
        if hasattr(strategy, attr):
            metrics[attr] = getattr(strategy, attr)

    # Equity curve.
    eq = pd.DataFrame(strategy._equity_curve, columns=["ts_ns", "equity"])
    eq.to_csv(out_dir / "equity_curve.csv", index=False)

    # Inventory clarity: BTC qty + USDT free over time.
    pos = pd.DataFrame(strategy._position_curve, columns=["ts_ns", "btc_qty", "usdt_free", "equity", "price"])
    pos.to_csv(out_dir / "position_curve.csv", index=False)

    # Charts.
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
        ts = pd.to_datetime(eq["ts_ns"])
        axes[0].plot(ts, eq["equity"], color="#1f77b4")
        axes[0].set_title(f"Equity curve  (total return {metrics['total_return_pct']:+.2f}%)")
        axes[0].set_ylabel("USDT")
        axes[0].grid(alpha=0.3)

        axes[1].plot(ts, pos["btc_qty"], color="#e57373", drawstyle="steps-post")
        axes[1].axhline(0, color="#888", lw=0.8)
        axes[1].set_title("BTC inventory (net position)")
        axes[1].set_ylabel("BTC")
        axes[1].grid(alpha=0.3)

        closes = [float(b.close.as_double()) for b in bars]
        axes[2].plot(ts, closes[: len(ts)], color="#888", lw=0.6)
        axes[2].set_title("Price")
        axes[2].set_ylabel("BTC/USDT")
        axes[2].grid(alpha=0.3)

        fig.tight_layout()
        fig.savefig(out_dir / "equity_curve.png", dpi=110)
        plt.close(fig)
    except Exception as exc:  # pragma: no cover
        print(f"chart generation skipped: {exc}")

    metrics_path = out_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))

    print("=== BACKTEST COMPLETE ===")
    for k, v in metrics.items():
        print(f"{k}: {v}")
    print(f"outputs written to {out_dir}")


if __name__ == "__main__":
    main()
