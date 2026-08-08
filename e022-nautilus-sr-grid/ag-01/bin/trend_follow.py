"""Trend-following overlay prototype — the "other half" of the dual-regime idea.

v2's flat regime switch avoids losing in trends by going flat. The natural
upgrade (assumption #1 redesign) is to CAPTURE trends instead: when the EMA
fast/slow cross says trend, hold a directional position (long in uptrends,
short in downtrends) sized to a notional budget, with realistic taker fees,
an exposure cap, and a liquidation model. This script tests that overlay
standalone on real BTC.

Usage:
    python3 bin/trend_follow.py --data data/real_btc_1h.csv [--fast 50 --slow 200]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_backtest import compute_metrics, load_bars, build_instrument, USD  # noqa: E402

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig  # noqa: E402
from nautilus_trader.config import LoggingConfig, RiskEngineConfig, StrategyConfig  # noqa: E402
from nautilus_trader.model import Money, Venue  # noqa: E402
from nautilus_trader.model.data import Bar, BarType  # noqa: E402
from nautilus_trader.model.enums import OmsType, AccountType, OrderSide, PositionSide, TimeInForce  # noqa: E402
from nautilus_trader.model.events import OrderFilled  # noqa: E402
from nautilus_trader.model.instruments import Instrument  # noqa: E402
from nautilus_trader.model.orders import MarketOrder  # noqa: E402
from nautilus_trader.trading.strategy import Strategy  # noqa: E402

MAX_WINDOW = 500


class TrendFollowConfig(StrategyConfig, frozen=True):
    instrument_id: object
    bar_type: BarType
    budget: Decimal
    fast: int = 50
    slow: int = 200
    enter_pct: float = 1.0
    exit_pct: float = 0.5
    max_exposure_mult: float = 4.0
    liq_margin_budget_mult: float = 1.0
    equity_sample_interval_bars: int = 6


class TrendFollowStrategy(Strategy):
    def __init__(self, config: TrendFollowConfig) -> None:
        super().__init__(config)
        self.instrument: Instrument = None
        self._closes: deque[float] = deque(maxlen=MAX_WINDOW)
        self._bar_count = 0
        self._regime = "RANGE"
        self._flatten_pending = False
        self.n_fills = 0
        self.total_commissions = 0.0
        self.n_flips = 0
        self._equity_curve: list[tuple[int, float]] = []

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error("no instrument")
            self.stop()
            return
        self.subscribe_bars(self.config.bar_type)

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)

    def on_bar(self, bar: Bar) -> None:
        if bar.bar_type != self.config.bar_type:
            return
        self._bar_count += 1
        self._closes.append(float(bar.close.as_double()))
        if self._bar_count < self.config.slow + 2:
            return

        fast = self._ema(self.config.fast)
        slow = self._ema(self.config.slow)
        if slow <= 0:
            return
        ratio = fast / slow - 1.0
        enter = self.config.enter_pct / 100.0
        exit_ = self.config.exit_pct / 100.0

        new_regime = self._regime
        if self._regime == "RANGE":
            if ratio > enter:
                new_regime = "LONG"
            elif ratio < -enter:
                new_regime = "SHORT"
        elif self._regime == "LONG":
            if ratio < -enter:
                new_regime = "SHORT"
            elif ratio < exit_:
                new_regime = "RANGE"
        elif self._regime == "SHORT":
            if ratio > enter:
                new_regime = "LONG"
            elif ratio > -exit_:
                new_regime = "RANGE"

        if new_regime != self._regime:
            self._regime = new_regime
            self.n_flips += 1
            self._set_target(bar.close.as_double())

        # Enforce liquidation simple.
        pos = self._net_position()
        if pos is not None:
            price = float(bar.close.as_double())
            upnl = float(pos.unrealized_pnl(self.instrument.make_price(price)).as_double())
            margin = float(self.config.budget) * self.config.liq_margin_budget_mult
            if upnl < -margin:
                self.log.warning("LIQUIDATED")
                self._flatten(price)
                self._regime = "RANGE"

        if self._bar_count % self.config.equity_sample_interval_bars == 0:
            account = self.portfolio.account(venue=self.config.instrument_id.venue)
            if account is not None:
                bal = account.balance_total(None)
                self._equity_curve.append((self._clock.timestamp_ns(), float(bal.as_double())))

    def _set_target(self, price: float) -> None:
        if self._regime == "RANGE":
            self._flatten(price)
            return
        side = PositionSide.LONG if self._regime == "LONG" else PositionSide.SHORT
        pos = self._net_position()
        if pos is not None and pos.side == side and pos.quantity.as_double() != 0:
            return  # ya estamos en la dirección correcta
        if pos is not None:
            self._flatten(price)
        # Abrir en la dirección del régimen. Usamos order de mercado simple;
        # el coste es el taker fee (realista para trend-following).
        budget = float(self.config.budget) * self.config.max_exposure_mult
        qty = budget / price
        order_side = OrderSide.BUY if side == PositionSide.LONG else OrderSide.SELL
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=order_side,
            quantity=self.instrument.make_qty(qty),
        )
        self.submit_order(order)
        self.log.info(f"OPEN {side} qty={qty:.6f} @ {price:.2f}")

    def _flatten(self, price: float) -> None:
        pos = self._net_position()
        if pos is None:
            return
        qty = abs(float(pos.quantity.as_double()))
        if qty <= 0:
            return
        order_side = OrderSide.SELL if pos.side == PositionSide.LONG else OrderSide.BUY
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=order_side,
            quantity=self.instrument.make_qty(qty),
            reduce_only=True,
        )
        self.submit_order(order)
        self.log.info(f"FLAT {pos.side} qty={qty:.6f} @ {price:.2f}")

    def on_order_filled(self, event: OrderFilled) -> None:
        self.n_fills += 1
        self.total_commissions += float(event.commission.as_double())

    def _ema(self, period: int) -> float:
        closes = list(self._closes)[-period:]
        alpha = 2.0 / (period + 1)
        ema = closes[0]
        for c in closes[1:]:
            ema = alpha * c + (1 - alpha) * ema
        return ema

    def _net_position(self):
        for candidate in self.cache.positions(instrument_id=self.config.instrument_id):
            if candidate.quantity.as_double() != 0:
                return candidate
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "real_btc_1h.csv")
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parents[1] / "output" / "trend_follow")
    parser.add_argument("--budget", type=float, default=30_000.0)
    parser.add_argument("--start-balance", type=float, default=100_000.0)
    parser.add_argument("--fast", type=int, default=50)
    parser.add_argument("--slow", type=int, default=200)
    parser.add_argument("--enter", type=float, default=1.0)
    parser.add_argument("--exit", type=float, default=0.5)
    parser.add_argument("--max-exposure-mult", type=float, default=4.0)
    parser.add_argument("--maker-fee", type=float, default=0.0002)
    parser.add_argument("--taker-fee", type=float, default=0.0006)
    parser.add_argument("--log-level", default="ERROR")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    bars, bar_type = load_bars(args.data)
    instrument = build_instrument(bars[0].ts_event, Decimal(str(args.maker_fee)), Decimal(str(args.taker_fee)))

    config = TrendFollowConfig(
        instrument_id=instrument.id,
        bar_type=bar_type,
        budget=Decimal(str(args.budget)),
        fast=args.fast,
        slow=args.slow,
        enter_pct=args.enter,
        exit_pct=args.exit,
        max_exposure_mult=args.max_exposure_mult,
    )
    strategy = TrendFollowStrategy(config=config)

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

    fills_df = engine.trader.generate_order_fills_report()
    positions_df = engine.trader.generate_positions_report()
    metrics = compute_metrics(strategy._equity_curve, fills_df, positions_df)
    metrics["n_fills"] = strategy.n_fills
    metrics["n_flips"] = strategy.n_flips
    metrics["total_commissions_usdt"] = round(strategy.total_commissions, 2)

    (args.out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    eq = pd.DataFrame(strategy._equity_curve, columns=["ts_ns", "equity"])
    eq.to_csv(args.out_dir / "equity_curve.csv", index=False)
    fills_df.to_csv(args.out_dir / "fills_report.csv", index=False)
    positions_df.to_csv(args.out_dir / "positions_report.csv", index=False)

    print("=== TREND-FOLLOW COMPLETE ===")
    for k, v in metrics.items():
        print(f"{k}: {v}")
    print(f"outputs written to {args.out_dir}")


if __name__ == "__main__":
    main()
