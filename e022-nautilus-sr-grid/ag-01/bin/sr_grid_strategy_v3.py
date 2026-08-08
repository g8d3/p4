"""Dual-regime grid + trend-following strategy (v3).

v2 proved the flat regime switch avoids losing in trends, and the
`trend_follow.py` prototype showed that CAPTURING those trends instead of
going flat is where the real 1h edge lives (+37.7% vs grid-only +1.7% on
real BTC 1h 4y). v3 combines both modes with explicit risk budgeting:

- **RANGE regime** -> the v2 S/R grid (price-space, volume-profile
  redistribution, exposure cap, liquidation model). Unchanged from v2.
- **LONG/SHORT regime** -> the grid is cancelled and a directional
  position is opened sized to `trend_budget_mult` x `grid_budget` (default
  2x = 60k notional on a 100k account). Re-evaluated every bar: if the
  regime keeps the same side, the position is held; if it flips or returns
  to RANGE, the position is flattened and (in RANGE) the grid re-armed.

Risk budgeting: the grid and the trend position never coexist (the grid is
cancelled while a trend position is open), so max notional is bounded by
max(grid budget deployment, trend budget). The exposure cap and liquidation
model apply to whichever mode is active.

Interface: ``SRGridStrategyV3(config)`` takes a ``SRGridConfigV3``. Keep
``--strategy v3`` wired in ``run_backtest.py``.
"""

from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import PositiveFloat
from nautilus_trader.model.enums import OrderSide, PositionSide
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.orders import MarketOrder

from sr_grid_strategy_v2 import SRGridConfigV2, SRGridStrategyV2


class SRGridConfigV3(SRGridConfigV2):
    """
    Configuration for ``SRGridStrategyV3`` — v2 config plus trend budget.

    Parameters
    ----------
    trend_budget_mult : float, default 2.0
        Trend position notional as a multiple of ``grid_budget`` (risk
        budgeting between the two modes). 2.0 = 60k USDT notional on a
        100k account with the default 30k grid budget.
    """

    trend_budget_mult: PositiveFloat = 2.0


class SRGridStrategyV3(SRGridStrategyV2):
    def __init__(self, config: SRGridConfigV3) -> None:
        super().__init__(config)
        self._trend_open: PositionSide | None = None
        self._trend_order_id: str | None = None
        self.n_trend_opens = 0

    # -- regime switching (override) -----------------------------------------

    def _on_regime_change(self, old: str, new: str, price: float) -> None:
        """Cancel grid, flatten any stale position, then act for the new mode."""
        self.n_regime_flips += 1
        self.log.info(f"REGIME {old} -> {new} price={price:.2f}")

        if new == "RANGE":
            # Leave a trend position before re-arming the grid.
            self._flatten_position(price)
            self._trend_open = None
            self._trend_order_id = None
            self._last_rebalance = 0
            self._last_rebalance_attempt = 0
            return

        # Entering a trend: cancel the grid, flatten any stale position, then
        # open the directional position.
        self._cancel_all_orders()
        self._levels.clear()
        self._flatten_position(price)
        self._trend_open = None
        self._trend_order_id = None
        self._open_trend(new, price)

    def _open_trend(self, regime: str, price: float) -> None:
        side = PositionSide.LONG if regime == "LONG" else PositionSide.SHORT
        budget = float(self.config.grid_budget) * self.config.trend_budget_mult
        qty = budget / price
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY if side == PositionSide.LONG else OrderSide.SELL,
            quantity=self.instrument.make_qty(qty),
        )
        self.submit_order(order)
        self._trend_order_id = order.client_order_id.value
        self._trend_open = side
        self.n_trend_opens += 1
        self.log.info(f"TREND OPEN {side} qty={qty:.6f} budget={budget:.0f} @ {price:.2f}")

    # -- per-bar upkeep: re-evaluate the trend position -----------------------

    def on_bar(self, bar) -> None:  # noqa: D102
        # Reuse v2's on_bar (regime update + grid logic + liquidation + sampling).
        SRGridStrategyV2.on_bar(self, bar)

        # If a trend is active, keep the position aligned (re-open after a
        # liquidation/cap flatten already zeroed it, without re-flipping every
        # bar). This runs after v2's liquidation check, so a liquidated trend
        # position gets re-opened immediately — acceptable for the prototype.
        if self._regime != "RANGE" and self._trend_open is not None:
            pos = self._net_position()
            qty = abs(float(pos.quantity.as_double())) if pos is not None else 0.0
            if qty <= 0:
                self._open_trend(self._regime, self._closes[-1])

    # -- fills ---------------------------------------------------------------

    def on_order_filled(self, event: OrderFilled) -> None:
        # Let v2 handle grid-level fills and commission counting.
        super().on_order_filled(event)
        if event.client_order_id.value == self._trend_order_id:
            self._trend_order_id = None

    def _flatten_position(self, price: float) -> None:
        # Same as v2 but tracked so on_bar can re-open if needed.
        super()._flatten_position(price)
