"""S/R grid strategy v2 — redesigned to survive real BTC.

This is the v2 redesign of ``sr_grid_strategy.py`` (v1 baseline). It attacks the
two killers identified in the real-data reality check:

1. **5m churn / fees** — v1 placed up to 8 levels per side, gap-filled at 1.0
   ATR, and filled 13-16k times per year (fee-dominated). v2 price-spaces the
   grid (levels at whole multiples of `grid_atr_mult` x ATR from the current
   price, default 1.5), caps levels at 3 per side, raises `min_order_notional`,
   and quotes maker-only (all grid orders are resting GTC limit orders).

2. **1h trend inventory** — v1 kept quoting the counter-trend side and
   accumulated inventory into 4-year trends. v2 replaces this with a **flat
   regime switch**: a hysteresis-filtered EMA fast/slow trend filter cancels
   the grid and flattens to zero when the market is trending; the grid is only
   armed in the range regime.

It also adds a simple **liquidation / leverage model**: exposure is capped at
`max_exposure_budget_mult` x budget, and a margin buffer
(`liquidation_margin_budget_mult` x budget) force-flattens the position when
unrealized loss exceeds it — so the sim can no longer ride a position into
negative equity for free.

Volume-profile redistribution is kept as the capital-allocation mechanism:
freed capital from a filled grid level is pooled and redistributed to the
opposite side proportional to a rolling KDE of traded volume, applied once per
bar (no per-fill churn).

Interface: ``SRGridStrategyV2(config)`` mirrors ``SRGridStrategy(config)`` so
``run_backtest.py`` can drive either via ``--strategy``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import numpy as np

from nautilus_trader.config import PositiveFloat, PositiveInt, StrategyConfig
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, PositionSide, TimeInForce
from nautilus_trader.model.events import OrderFilled, OrderRejected, OrderCanceled
from nautilus_trader.model.identifiers import ClientOrderId, InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.orders import LimitOrder, MarketOrder
from nautilus_trader.trading.strategy import Strategy

# Rolling window large enough to cover every rolling computation.
MAX_WINDOW = 600


class SRGridConfigV2(StrategyConfig, frozen=True):
    """
    Configuration for ``SRGridStrategyV2``.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument to trade.
    bar_type : BarType
        The bar type to subscribe to.
    grid_budget : Decimal
        Total notional reserved for the grid (quote currency).
    rebalance_interval_bars : int, default 96
        Rebuild the grid every N bars (96 x 5m = 8h; 96 x 1h = 4 days).
    atr_period : int, default 14
        Period for the ATR used by grid spacing.
    grid_atr_mult : float, default 1.5
        Grid levels are spaced `grid_atr_mult` x ATR apart (the "price-space"
        fix for 5m churn). Levels sit at whole multiples of this step from the
        current price, so they cannot crowd together like v1's clustered S/R.
    max_levels_per_side : int, default 3
        Far fewer levels than v1 (which used up to 8).
    min_order_notional : Decimal, default 500
        Minimum notional for a single grid order. Levels that would be too
        small are dropped (less churn).
    max_order_notional : Decimal, default 10_000
        Maximum notional for a single grid order.
    max_exposure_budget_mult : float, default 3.0
        Maximum net position notional as a multiple of the grid budget. The
        leverage model: with a 30k budget this caps notional at 90k USDT on a
        100k account (~0.9x), far below v1's effective ~3.1x.
    trend_filter_enabled : bool, default True
        Enable the flat regime switch. When a strong trend is detected the
        grid is cancelled and the position is flattened to zero.
    trend_ema_fast : int, default 20
        Fast EMA period for the regime filter.
    trend_ema_slow : int, default 100
        Slow EMA period for the regime filter.
    trend_enter_pct : float, default 0.5
        Enter a trend regime when |fast/slow - 1| exceeds this %.
    trend_exit_pct : float, default 0.2
        Return to the range regime when |fast/slow - 1| drops below this %
        (hysteresis prevents regime flapping and taker-fee churn).
    liquidation_margin_budget_mult : float, default 1.0
        Liquidation margin as a multiple of the grid budget. When unrealized
        loss exceeds this margin the position is force-flattened.
    cap_overshoot_pct : float, default 10.0
        The exposure cap is enforced with a small band: the inventory side is
        cancelled and the excess position flattened once notional exceeds
        `max_exposure_budget_mult` x budget x (1 + this %). Avoids churning
        the flatten on every bar the position ticks over the cap.
    equity_sample_interval_bars : int, default 6
        Sample account equity every N bars for the equity curve.
    """

    instrument_id: InstrumentId
    bar_type: BarType
    grid_budget: Decimal
    rebalance_interval_bars: PositiveInt = 96
    atr_period: PositiveInt = 14
    grid_atr_mult: PositiveFloat = 1.5
    max_levels_per_side: PositiveInt = 3
    min_order_notional: Decimal = 500
    max_order_notional: Decimal = 10_000
    max_exposure_budget_mult: PositiveFloat = 3.0
    trend_filter_enabled: bool = True
    trend_ema_fast: PositiveInt = 20
    trend_ema_slow: PositiveInt = 100
    trend_enter_pct: PositiveFloat = 0.5
    trend_exit_pct: PositiveFloat = 0.2
    liquidation_margin_budget_mult: PositiveFloat = 1.0
    cap_overshoot_pct: PositiveFloat = 10.0
    equity_sample_interval_bars: PositiveInt = 6


@dataclass
class GridLevel:
    """One grid level: a resting limit order with a reserved notional."""

    price: float
    side: str  # "BUY" or "SELL"
    reserved: float = 0.0
    order_id: Optional[str] = None


class SRGridStrategyV2(Strategy):
    def __init__(self, config: SRGridConfigV2) -> None:
        super().__init__(config)

        self.instrument: Instrument = None

        self._closes: deque[float] = deque(maxlen=MAX_WINDOW)
        self._highs: deque[float] = deque(maxlen=MAX_WINDOW)
        self._lows: deque[float] = deque(maxlen=MAX_WINDOW)
        self._volumes: deque[float] = deque(maxlen=MAX_WINDOW)

        self._bar_count = 0
        self._last_rebalance = 0
        self._last_rebalance_attempt = 0

        self._regime: str = "RANGE"  # "RANGE" | "LONG" | "SHORT"
        self._flatten_order_id: Optional[str] = None

        self._levels: dict[tuple[str, float], GridLevel] = {}
        self._level_by_order: dict[str, GridLevel] = {}
        self._unallocated = 0.0
        self._pending_redistribute: dict[str, float] = {"BUY": 0.0, "SELL": 0.0}

        self.n_rebalances = 0
        self.n_resyncs = 0
        self.n_fills = 0
        self.n_cap_enforcements = 0
        self.n_regime_flips = 0
        self.n_liquidations = 0
        self.total_commissions = 0.0

        self._equity_curve: list[tuple[int, float]] = []  # (ts_ns, equity)
        # (ts_ns, btc_qty, usdt_free, equity, price) — inventory at all times.
        self._position_curve: list[tuple[int, float, float, float, float]] = []

    # -- lifecycle ----------------------------------------------------------

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument for {self.config.instrument_id}")
            self.stop()
            return
        self.subscribe_bars(self.config.bar_type)

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)

    # -- data ---------------------------------------------------------------

    def on_bar(self, bar: Bar) -> None:
        if bar.bar_type != self.config.bar_type:
            return

        self._bar_count += 1
        self._closes.append(float(bar.close.as_double()))
        self._highs.append(float(bar.high.as_double()))
        self._lows.append(float(bar.low.as_double()))
        self._volumes.append(float(bar.volume.as_double()))

        if self._bar_count < self._min_warmup():
            return

        price = self._closes[-1]
        old_regime = self._regime
        self._update_regime()
        if self._regime != old_regime:
            self._on_regime_change(old_regime, self._regime, price)

        if self._regime != "RANGE":
            # Flat regime switch: no quoting, no inventory. The grid was
            # cancelled on regime entry; liquidation still applies in case a
            # flatten market order has not yet filled.
            self._check_liquidation(price)
            self._sample_equity()
            return

        self._flush_redistribution()

        if self._last_rebalance == 0 or self._bar_count - self._last_rebalance >= self.config.rebalance_interval_bars:
            if self._bar_count - self._last_rebalance_attempt >= self.config.rebalance_interval_bars:
                self._last_rebalance_attempt = self._bar_count
                self._rebalance_grid()

        self._enforce_cap_on_fills()
        self._check_liquidation(price)

        if self._bar_count % self.config.equity_sample_interval_bars == 0:
            self._sample_equity()

    def _min_warmup(self) -> int:
        cfg = self.config
        return max(cfg.atr_period, cfg.trend_ema_slow) + 5

    # -- regime switching ---------------------------------------------------

    def _update_regime(self) -> None:
        if not self.config.trend_filter_enabled:
            self._regime = "RANGE"
            return
        fast = self._ema(self.config.trend_ema_fast)
        slow = self._ema(self.config.trend_ema_slow)
        if slow <= 0:
            return
        ratio = fast / slow - 1.0
        enter = self.config.trend_enter_pct / 100.0
        exit_ = self.config.trend_exit_pct / 100.0

        if self._regime == "RANGE":
            if ratio > enter:
                self._regime = "LONG"
            elif ratio < -enter:
                self._regime = "SHORT"
        elif self._regime == "LONG":
            if ratio < -enter:
                self._regime = "SHORT"
            elif ratio < exit_:
                self._regime = "RANGE"
        elif self._regime == "SHORT":
            if ratio > enter:
                self._regime = "LONG"
            elif ratio > -exit_:
                self._regime = "RANGE"

    def _on_regime_change(self, old: str, new: str, price: float) -> None:
        self.n_regime_flips += 1
        self.log.info(f"REGIME {old} -> {new} price={price:.2f}")
        if new == "RANGE":
            # Re-arm the grid immediately on return to range.
            self._last_rebalance = 0
            self._last_rebalance_attempt = 0
            return
        # Entering a trend: cancel the grid and flatten to zero.
        self._cancel_all_orders()
        self._levels.clear()
        self._flatten_position(price)

    def _flatten_position(self, price: float) -> None:
        pos = self._net_position()
        if pos is None:
            return
        qty = abs(float(pos.quantity.as_double()))
        if qty <= 0:
            return
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=(
                OrderSide.SELL if pos.side == PositionSide.LONG else OrderSide.BUY
            ),
            quantity=self.instrument.make_qty(qty),
            reduce_only=True,
        )
        self.submit_order(order)
        self._flatten_order_id = order.client_order_id.value
        self.log.info(
            f"FLATTEN {pos.side} qty={qty:.6f} @market reduce_only"
        )

    def _ema(self, period: int) -> float:
        closes = list(self._closes)[-period:]
        if len(closes) < period:
            return self._closes[-1]
        alpha = 2.0 / (period + 1)
        ema = closes[0]
        for c in closes[1:]:
            ema = alpha * c + (1 - alpha) * ema
        return ema

    # -- grid management ----------------------------------------------------

    def _rebalance_grid(self) -> None:
        price = self._closes[-1]
        if self._regime != "RANGE":
            return

        buy_levels, sell_levels = self._build_price_grid(price)

        nb, ns = len(buy_levels), len(sell_levels)
        if nb + ns == 0:
            self.log.warning("Rebalance found no grid levels")
            return

        # Caps checked BEFORE cancelling: if both sides get removed the
        # current grid stays untouched.
        cap_total = float(self.config.grid_budget) * self.config.max_exposure_budget_mult
        pool_est = min(float(self.config.grid_budget) + self._unallocated, cap_total)
        buy_budget = pool_est * nb / (nb + ns)
        sell_budget = pool_est * ns / (nb + ns)
        buy_levels, sell_levels = self._apply_exposure_caps(
            buy_levels, sell_levels, buy_budget, sell_budget, price
        )
        nb, ns = len(buy_levels), len(sell_levels)
        if nb + ns == 0:
            self.log.info("Rebalance skipped: exposure cap removed both sides")
            return

        # Fold freed capital into the pool, then rebuild the grid, clamped to
        # the risk cap so freed capital never re-inflates deployment.
        self._cancel_all_orders()
        self._levels.clear()
        total_budget = float(self.config.grid_budget) + self._unallocated
        for side in ("BUY", "SELL"):
            total_budget += self._pending_redistribute.pop(side, 0.0)
        self._unallocated = max(0.0, total_budget - cap_total)
        total_budget = min(total_budget, cap_total)

        if nb != 0 and ns != 0:
            buy_budget = total_budget * nb / (nb + ns)
            sell_budget = total_budget * ns / (nb + ns)
        else:
            buy_budget = total_budget if nb else 0.0
            sell_budget = total_budget if ns else 0.0

        self._allocate_and_place(buy_levels, "BUY", buy_budget)
        self._allocate_and_place(sell_levels, "SELL", sell_budget)

        self._last_rebalance = self._bar_count
        self.n_rebalances += 1
        self.log.info(
            f"REBALANCE price={price:.2f} atr={self._atr():.2f} "
            f"buy={nb} sell={ns} levels total={len(self._levels)}"
        )

    def _build_price_grid(self, price: float) -> tuple[list[float], list[float]]:
        """Price-space the grid: levels at whole multiples of step from price.

        This is the core anti-churn change vs v1. The step is forced to at
        least `grid_atr_mult` x ATR (default 1.5), so adjacent levels can never
        crowd closer than ~1.5 ATR — the distance a 5-min BTC bar needs to
        actually cross before a fill.
        """
        step = max(self._atr() * self.config.grid_atr_mult, self._min_step())
        n = self.config.max_levels_per_side
        buy_levels = [round(price - step * k, self.instrument.price_precision) for k in range(1, n + 1)]
        sell_levels = [round(price + step * k, self.instrument.price_precision) for k in range(1, n + 1)]
        return (
            [p for p in buy_levels if p > 0],
            [p for p in sell_levels if p > 0],
        )

    def _apply_exposure_caps(
        self,
        buy_levels: list[float],
        sell_levels: list[float],
        buy_budget: float,
        sell_budget: float,
        price: float,
    ) -> tuple[list[float], list[float]]:
        pos = self._net_position()
        long_notional = short_notional = 0.0
        if pos is not None:
            notional = abs(float(pos.quantity.as_double())) * price
            if pos.side == PositionSide.LONG:
                long_notional = notional
            else:
                short_notional = notional

        cap = float(self.config.grid_budget) * self.config.max_exposure_budget_mult
        if long_notional + buy_budget > cap:
            buy_levels = []
        if short_notional + sell_budget > cap:
            sell_levels = []
        return buy_levels, sell_levels

    def _enforce_cap_on_fills(self) -> None:
        """Cancel the inventory side and flatten the excess when past the cap.

        v1's cap only cancelled orders, which left the position stuck at max
        long/short after the inventory side's levels had all filled (real 5m
        blowout to ~2.5x account notional). v2 also flattens the over-cap
        portion with a reduce-only market order so net exposure is genuinely
        bounded between rebalances.

        A small hysteresis band (`cap_overshoot_pct`) prevents the flatten
        order from being re-submitted every bar while notional sits just above
        the cap.
        """
        pos = self._net_position()
        if pos is None:
            return
        price = self._closes[-1]
        notional = abs(float(pos.quantity.as_double())) * price
        cap = float(self.config.grid_budget) * self.config.max_exposure_budget_mult
        band = cap * (1.0 + self.config.cap_overshoot_pct / 100.0)
        side_to_cancel = None
        if pos.side == PositionSide.LONG:
            if notional > band:
                side_to_cancel = "BUY"
                excess_qty = float(pos.quantity.as_double()) - cap / price
            else:
                return
        elif pos.side == PositionSide.SHORT:
            if notional > band:
                side_to_cancel = "SELL"
                excess_qty = abs(float(pos.quantity.as_double())) - cap / price
            else:
                return
        else:
            return

        if excess_qty <= 0:
            return

        self.n_cap_enforcements += 1
        for key in [k for k, lv in self._levels.items() if lv.side == side_to_cancel]:
            lv = self._levels[key]
            if lv.order_id is not None:
                self._cancel(lv.order_id)
                self._level_by_order.pop(lv.order_id, None)
                lv.order_id = None
            self._unallocated += lv.reserved
            self._levels.pop(key)

        # Flatten the over-cap excess (reduce-only market order).
        reduce_side = OrderSide.SELL if pos.side == PositionSide.LONG else OrderSide.BUY
        qty = self.instrument.make_qty(excess_qty)
        if qty.as_double() > 0:
            order = self.order_factory.market(
                instrument_id=self.config.instrument_id,
                order_side=reduce_side,
                quantity=qty,
                reduce_only=True,
            )
            self.submit_order(order)
        self.log.info(
            f"Exposure cap enforced on fills: cancelled {side_to_cancel} levels, "
            f"flattening {excess_qty:.6f} excess"
        )

    def _check_liquidation(self, price: float) -> None:
        """Simple liquidation model: force-flatten when unrealized loss
        exceeds the margin buffer. Keeps the leverage honest."""
        pos = self._net_position()
        if pos is None:
            return
        margin = (
            float(self.config.grid_budget) * self.config.liquidation_margin_budget_mult
        )
        upnl = float(pos.unrealized_pnl(self.instrument.make_price(price)).as_double())
        if upnl < -margin:
            self.n_liquidations += 1
            self.log.warning(
                f"LIQUIDATION upnl={upnl:.2f} < margin={-margin:.2f}: force-flattening"
            )
            self._cancel_all_orders()
            self._levels.clear()
            self._unallocated = 0.0
            self._flatten_position(price)

    def _allocate_and_place(self, prices: list[float], side: str, budget: float) -> None:
        if not prices:
            return
        probs = self._vp_probabilities(prices)
        for price, prob in zip(prices, probs):
            notional = float(budget) * float(prob)
            notional = self._clamp_notional(notional)
            if notional < float(self.config.min_order_notional):
                # Too small to be worth an order: park it for the next
                # rebalance instead of quoting churn.
                self._unallocated += notional
                continue
            level = GridLevel(price=price, side=side, reserved=notional)
            self._levels[(side, price)] = level
            self._submit_limit(level)

    def _submit_limit(self, level: GridLevel) -> None:
        if level.reserved <= 0:
            return
        qty = self.instrument.make_qty(level.reserved / level.price)
        if qty.as_double() <= 0:
            return
        order: LimitOrder = self.order_factory.limit(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY if level.side == "BUY" else OrderSide.SELL,
            quantity=qty,
            price=self.instrument.make_price(level.price),
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)
        level.order_id = order.client_order_id.value
        self._level_by_order[level.order_id] = level

    def _resync_levels(self, levels: list[GridLevel]) -> None:
        """Cancel and resubmit the given levels with their updated size."""
        for level in levels:
            if level.reserved <= 0:
                if level.order_id is not None:
                    self._cancel(level.order_id)
                    level.order_id = None
                continue
            if level.order_id is not None:
                self._cancel(level.order_id)
                level.order_id = None
            self._submit_limit(level)

    def _cancel(self, client_order_id: str) -> None:
        order = self.cache.order(ClientOrderId(client_order_id))
        if order is not None and order.is_active_local:  # noqa: SIM102
            self.cancel_order(order)

    def _cancel_all_orders(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        self._level_by_order.clear()
        for level in self._levels.values():
            level.order_id = None

    def _clamp_notional(self, notional: float) -> float:
        return float(
            np.clip(
                notional,
                float(self.config.min_order_notional),
                float(self.config.max_order_notional),
            )
        )

    # -- fills --------------------------------------------------------------

    def on_order_filled(self, event: OrderFilled) -> None:
        cid = event.client_order_id.value
        self.n_fills += 1
        self.total_commissions += float(event.commission.as_double())

        if cid == self._flatten_order_id:
            self._flatten_order_id = None
            return
        if cid not in self._level_by_order:
            return

        level = self._level_by_order.pop(cid)
        self._levels.pop((level.side, level.price), None)
        freed = level.reserved

        other_side = "SELL" if level.side == "BUY" else "BUY"
        self._pending_redistribute[other_side] = (
            self._pending_redistribute.get(other_side, 0.0) + freed
        )

        self.log.info(
            f"FILL {level.side}@{level.price:.2f} freed={freed:.2f} "
            f"pending->{other_side} total={self._pending_redistribute[other_side]:.2f}"
        )

    def _flush_redistribution(self) -> None:
        """Apply pooled freed capital to the target side, once per bar."""
        for side in ("BUY", "SELL"):
            freed = self._pending_redistribute.pop(side, 0.0)
            if freed <= 0:
                continue
            others = [lv for lv in self._levels.values() if lv.side == side]
            if not others:
                self._unallocated += freed
                continue
            probs = self._vp_probabilities([lv.price for lv in others])
            for lv, prob in zip(others, probs):
                lv.reserved = self._clamp_notional(lv.reserved + freed * float(prob))
            self._resync_levels(others)
            self.n_resyncs += 1

    def on_order_canceled(self, event: OrderCanceled) -> None:
        cid = event.client_order_id.value
        if cid in self._level_by_order:
            lv = self._level_by_order.pop(cid)
            if lv.order_id == cid:
                lv.order_id = None

    def on_order_rejected(self, event: OrderRejected) -> None:
        cid = event.client_order_id.value
        if cid in self._level_by_order:
            lv = self._level_by_order.pop(cid)
            lv.order_id = None
            self.log.warning(
                f"Order rejected {lv.side}@{lv.price:.2f}: {event.reason}"
            )

    # -- indicators / distributions -----------------------------------------

    def _atr(self) -> float:
        n = min(self.config.atr_period, len(self._closes))
        if n < 2:
            return 0.0
        highs = np.array(self._highs)[-n:]
        lows = np.array(self._lows)[-n:]
        closes = np.array(self._closes)[-n:]
        prev_close = np.roll(closes, 1)
        prev_close[0] = closes[0]
        tr = np.maximum.reduce([highs - lows, np.abs(highs - prev_close), np.abs(lows - prev_close)])
        return float(np.mean(tr))

    def _min_step(self) -> float:
        return float(self.instrument.price_increment.as_double())

    def _vp_probabilities(self, prices: list[float]) -> np.ndarray:
        """Volume-profile distribution: KDE of traded volume at each price."""
        n = min(400, len(self._closes))
        closes = np.array(self._closes)[-n:]
        volumes = np.array(self._volumes)[-n:]
        prices = np.asarray(prices, dtype=float)

        if len(closes) == 0 or prices.size == 0:
            return np.full(len(prices), 1.0 / max(len(prices), 1))

        total_vol = volumes.sum()
        if total_vol <= 0:
            return np.full(len(prices), 1.0 / max(len(prices), 1))

        bandwidth = 0.25 / 100.0 * self._closes[-1]
        if bandwidth <= 0:
            return np.full(len(prices), 1.0 / max(len(prices), 1))

        diff = (prices[:, None] - closes[None, :]) / bandwidth
        kernel = np.exp(-0.5 * diff**2)
        density = kernel @ volumes
        denom = density.sum()
        if denom <= 0:
            return np.full(len(prices), 1.0 / max(len(prices), 1))
        return density / denom

    # -- accounting ----------------------------------------------------------

    def _net_position(self):
        for candidate in self.cache.positions(instrument_id=self.config.instrument_id):
            if candidate.quantity.as_double() != 0:
                return candidate
        return None

    def _sample_equity(self) -> None:
        account = self.portfolio.account(venue=self.config.instrument_id.venue)
        if account is None:
            return
        balance = account.balance_total(None)
        ts = self._clock.timestamp_ns()
        self._equity_curve.append((ts, float(balance.as_double())))

        btc_qty = 0.0
        free_money = account.balance_free(None)
        usdt_free = float(free_money.as_double()) if free_money is not None else 0.0
        pos = self._net_position()
        if pos is not None:
            btc_qty = float(pos.quantity.as_double())
        self._position_curve.append(
            (ts, btc_qty, usdt_free, float(balance.as_double()), self._closes[-1])
        )

    # -- state ---------------------------------------------------------------

    def on_save(self) -> dict[str, bytes]:
        return {}

    def on_load(self, state: dict[str, bytes]) -> None:
        pass
