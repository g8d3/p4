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
from nautilus_trader.model.events import OrderFilled, OrderRejected
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.orders import LimitOrder, MarketOrder

from sr_grid_strategy_v2 import SRGridConfigV2, SRGridStrategyV2


class SRGridConfigUser(SRGridConfigV2, frozen=True):
    """v2 config + Test 1 flatten knobs."""

    flatten_mode: str = "market"  # "market" (v2 exact) | "limit_first"
    flatten_limit_offset_pct: PositiveFloat = 0.05
    flatten_fallback_bars: PositiveInt = 3
    recycle_enabled: bool = False  # Test 3 feature 1
    recycle_pct: PositiveFloat = 0.5  # retracement R% before re-arming


class SRGridStrategyUser(SRGridStrategyV2):
    def __init__(self, config: SRGridConfigUser) -> None:
        super().__init__(config)
        self._flatten_limit_cid: str | None = None
        self._flatten_limit_bar = 0
        self._recycle_queue: list[dict[str, float | str]] = []
        self.n_rejections = 0

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
            pass
        elif self._bar_count - self._flatten_limit_bar >= self.config.flatten_fallback_bars:
            self._fallback_flatten_market()
        self._flush_recycle()

    def _fallback_flatten_market(self) -> None:
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

    def _flush_recycle(self) -> None:
        """Recycle queue (interpretation 2): the capital freed by a grid fill
        feeds the OPPOSITE side (as v2 does) but only after price moves R% in
        that side's favour (a sell after a buy fill waits for a +R% bounce).

        The queue is parked capital: it is intentionally NOT part of the
        rebalance budget (that would re-arm it immediately and cancel the
        retrace wait). When the retrace hits, the amount moves into
        ``_pending_redistribute`` and becomes visible to the normal
        redistribution machinery."""
        if not self.config.recycle_enabled or not self._recycle_queue:
            return
        price = self._closes[-1]
        pct = self.config.recycle_pct / 100.0
        still: list[dict[str, float | str]] = []
        for item in self._recycle_queue:
            fp = float(item["fill_price"])
            hit = (
                price <= fp * (1.0 - pct)
                if item["side"] == "BUY"
                else price >= fp * (1.0 + pct)
            )
            if hit:
                side = str(item["side"])
                self._pending_redistribute[side] = (
                    self._pending_redistribute.get(side, 0.0) + float(item["amount"])
                )
                self.log.info(
                    f"RECYCLE filled release: {side} freed={float(item['amount']):.2f} "
                    f"@ fill {fp:.2f} price now {price:.2f}"
                )
            else:
                still.append(item)
        self._recycle_queue = still

    def on_order_filled(self, event: OrderFilled) -> None:
        cid = event.client_order_id.value
        if cid == self._flatten_limit_cid:
            self._flatten_limit_cid = None
        if self.config.recycle_enabled and cid in self._level_by_order:
            # Count fill stats here: the recycle path returns early and must
            # not rely on super() (whose early-return used to drop them,
            # falsifying n_fills / total_commissions).
            self.n_fills += 1
            self.total_commissions += float(event.commission.as_double())
            level = self._level_by_order.pop(cid)
            self._levels.pop((level.side, level.price), None)
            freed = level.reserved
            if freed > 0:
                other = "SELL" if level.side == "BUY" else "BUY"
                self._recycle_queue.append(
                    {"side": other, "fill_price": level.price, "amount": freed}
                )
                self.log.info(
                    f"FILL {level.side}@{level.price:.2f} freed={freed:.2f} -> recycle {other} "
                    f"(R={self.config.recycle_pct}%)"
                )
            return
        super().on_order_filled(event)

    def on_order_rejected(self, event: OrderRejected) -> None:
        """v2 drops the rejected level but never refunds its ``reserved``
        notional, silently leaking capital from the pool. Never fired in the
        baseline (SIM engine accepts everything) but must be correct: refund
        and count."""
        cid = event.client_order_id.value
        lv = self._level_by_order.get(cid)
        super().on_order_rejected(event)
        self.n_rejections += 1
        if lv is not None:
            self._unallocated += float(lv.reserved)
            self.log.warning(
                f"ORDER REJECTED {lv.side}@{lv.price:.2f}: refunded reserved="
                f"{float(lv.reserved):.2f} into unallocated (reason={event.reason})"
            )
