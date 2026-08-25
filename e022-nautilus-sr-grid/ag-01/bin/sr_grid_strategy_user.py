"""S/R grid strategy USER — e043 copy-then-improve layer on top of v2.

Implements NAUTILUS_A_PLAN Test 1 (and future tests 2-3) as a subclass of
``SRGridStrategyV2`` so the v2 baseline stays byte-for-byte untouched.

Test 1 — flatten with maker limit instead of taker market:

    v2 flattens to zero on trend entry with a reduce-only MARKET order
    (taker fee 0.06%). ``flatten_mode = "limit_first"`` instead submits a
    reduce-only LIMIT order at ``price +/- flatten_limit_buffer_pct`` (a
    maker order, fee 0.02%), and falls back to a market order if the limit
    did not fill after ``flatten_fallback_bars`` bars. ``flatten_mode =
    "market"`` is exactly v2 behavior (parity gate).

Acceptance (from NAUTILUS_A_PLAN.md Test 1): commissions down >10% and
return not worse.
"""

from __future__ import annotations

from nautilus_trader.config import PositiveFloat, PositiveInt
from nautilus_trader.model.enums import OrderSide, PositionSide, TimeInForce
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.orders import LimitOrder, MarketOrder

from sr_grid_strategy_v2 import SRGridConfigV2, SRGridStrategyV2


class SRGridConfigUser(SRGridConfigV2, frozen=True):
    """v2 config + Test 1 flatten knobs."""

    flatten_mode: str = "market"  # "market" (v2 exact) | "limit_first"
    flatten_limit_offset_pct: PositiveFloat = 0.05
    flatten_fallback_bars: PositiveInt = 3


class SRGridStrategyUser(SRGridStrategyV2):
    def __init__(self, config: SRGridConfigUser) -> None:
        super().__init__(config)
        self._flatten_limit_cid: str | None = None
        self._flatten_limit_bar = 0

    # -- Test 1: flatten limit-first -----------------------------------------

    def _flatten_position(self, price: float) -> None:
        if self.config.flatten_mode == "market":
            super()._flatten_position(price)
            return

        pos = self._net_position()
        if pos is None:
            return
        qty = abs(float(pos.quantity.as_double()))
        if qty <= 0:
            return

        # Maker-side limit: SELL waits ABOVE current price, BUY waits BELOW.
        # (A limit on the marketable side - SELL below / BUY above - is filled
        # immediately as TAKER by the SIM matching engine, i.e. same as market.)
        # offset 0.0 = "far grid level" (grid_atr_mult x ATR) as a % of price.
        offset = self.config.flatten_limit_offset_pct
        if offset <= 0:
            atr = self._atr() if self._atr() > 0 else (price * 0.002)
            offset = atr * self.config.grid_atr_mult / price * 100.0
        if pos.side == PositionSide.LONG:
            side = OrderSide.SELL
            limit_price = float(price) * (1.0 + offset / 100.0)
        else:
            side = OrderSide.BUY
            limit_price = float(price) * (1.0 - offset / 100.0)

        order: LimitOrder = self.order_factory.limit(
            instrument_id=self.config.instrument_id,
            order_side=side,
            quantity=self.instrument.make_qty(qty),
            price=self.instrument.make_price(limit_price),
            time_in_force=TimeInForce.GTC,
            reduce_only=True,
        )
        self.submit_order(order)
        self._flatten_order_id = order.client_order_id.value
        self._flatten_limit_cid = order.client_order_id.value
        self._flatten_limit_bar = self._bar_count
        self.log.info(
            f"FLATTEN {pos.side} qty={qty:.6f} @limit {limit_price:.2f} reduce_only "
            f"(fallback +{self.config.flatten_fallback_bars} bars)"
        )

    def on_bar(self, bar: object) -> None:
        super().on_bar(bar)
        if self._flatten_limit_cid is None:
            return
        if self._bar_count - self._flatten_limit_bar < self.config.flatten_fallback_bars:
            return
        order = self.cache.order(ClientOrderId(self._flatten_limit_cid))
        if order is None or not order.is_active_local:
            self._flatten_limit_cid = None
            return
        self.cancel_order(order)
        self._flatten_limit_cid = None

        price = self._closes[-1]
        pos = self._net_position()
        if pos is None or abs(float(pos.quantity.as_double())) <= 0:
            return
        side = OrderSide.SELL if pos.side == PositionSide.LONG else OrderSide.BUY
        mkt: MarketOrder = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=side,
            quantity=self.instrument.make_qty(abs(float(pos.quantity.as_double()))),
            reduce_only=True,
        )
        self.submit_order(mkt)
        self._flatten_order_id = mkt.client_order_id.value
        self.log.info(f"FLATTEN fallback to market reduce_only (limit unfilled)")

    def on_order_filled(self, event: OrderFilled) -> None:
        cid = event.client_order_id.value
        if cid == self._flatten_limit_cid:
            self._flatten_limit_cid = None
        super().on_order_filled(event)
