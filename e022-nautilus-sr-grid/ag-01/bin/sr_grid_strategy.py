"""S/R grid strategy for Nautilus Trader.

Concept
-------
A mean-reversion grid whose levels are placed automatically on detected
support/resistance levels (fractal pivots, clustered, gap-filled at ATR
spacing) instead of fixed spacing.

Two mechanisms drive the grid:

1. **Rebalance** (every `rebalance_interval_bars` bars): re-detect S/R around
   the current price, rebuild the grid, and re-split the total grid budget
   across the two sides proportionally to the number of levels on each side.
   Within a side, the budget is allocated across levels proportional to a
   *volume profile* distribution (a kernel density estimate of traded volume
   over a rolling window).

2. **Fill redistribution** (on every grid fill): the capital reserved for the
   filled order is *freed* and moved to the OPPOSITE side, where it is
   distributed across that side's active levels according to the current
   volume-profile probability distribution. A filled cell is consumed until
   the next rebalance, so repeated fills on one side walk the grid budget
   toward the opposite side (buy fills push capital into sells and vice
   versa).

Trading model
-------------
- Margin account (1:1, zero margin requirement), OMS netting on a synthetic
  BTC/USDT perpetual futures instrument. Both sides quote simultaneously with
  resting limit orders; this is the standard setup for grid bots.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

import numpy as np

from nautilus_trader.config import PositiveFloat, PositiveInt, StrategyConfig
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, PositionSide, TimeInForce
from nautilus_trader.model.events import OrderFilled, OrderRejected, OrderCanceled
from nautilus_trader.model.identifiers import ClientOrderId, InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.orders import LimitOrder
from nautilus_trader.trading.strategy import Strategy

# Rolling window large enough to cover every rolling computation.
MAX_WINDOW = 600


class SRGridConfig(StrategyConfig, frozen=True):
    """
    Configuration for ``SRGridStrategy``.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument to trade.
    bar_type : BarType
        The bar type to subscribe to.
    grid_budget : Decimal
        Total notional reserved for the grid (quote currency).
    rebalance_interval_bars : int, default 96
        Rebuild the grid every N bars (96 x 5min = 8h).
    pivot_window : int, default 3
        Fractal half-width: a pivot needs to be the max/min of the surrounding
        2*window+1 bars.
    pivot_lookback_bars : int, default 240
        Only consider pivots from the last N bars.
    cluster_tol_pct : float, default 0.10
        Pivots within this % of price are clustered into a single level.
    grid_span_pct : float, default 1.5
        Levels must lie within this % of the current price.
    min_levels_per_side : int, default 3
        Minimum number of levels per side (gap-filled if needed).
    max_levels_per_side : int, default 8
        Maximum number of levels per side.
    fill_gaps : bool, default True
        Insert intermediate levels at ATR spacing when S/R levels are sparse.
    fill_gap_atr_mult : float, default 1.0
        Insert filler levels when the gap between consecutive levels exceeds
        this multiple of ATR.
    atr_period : int, default 30
        Period for the ATR used by gap filling.
    vol_window_bars : int, default 400
        Rolling window for the volume profile distribution.
    vol_kde_bandwidth_pct : float, default 0.25
        KDE bandwidth as a % of the current price.
    min_order_notional : Decimal, default 100
        Minimum notional for a single grid order.
    max_order_notional : Decimal, default 5000
        Maximum notional for a single grid order.
    max_exposure_budget_mult : float, default 1.5
        Maximum net position notional as a multiple of the grid budget. When a
        rebalance would push exposure past this cap, the side that adds
        inventory in the capped direction is not quoted.
    enforce_cap_on_fills : bool, default True
        If True, the exposure cap is also enforced between rebalances: as soon
        as fills push net exposure past the cap, the inventory-side grid levels
        are cancelled and their capital moved to the unallocated pool. This
        stops the grid from accumulating an unbounded position in a trend.
    trend_filter_enabled : bool, default False
        If True, only quote the side that fades the trend (buys in uptrends,
        sells in downtrends), based on the close vs its EMA. In a trend, the
        grid stops adding inventory in the trend direction.
    trend_ema_period : int, default 100
        EMA period for the trend filter.
    trend_min_dist_pct : float, default 0.3
        Minimum |close/EMA - 1| (in %) before the market counts as trending.
    equity_sample_interval_bars : int, default 6
        Sample account equity every N bars for the equity curve.

    """

    instrument_id: InstrumentId
    bar_type: BarType
    grid_budget: Decimal
    rebalance_interval_bars: PositiveInt = 96
    pivot_window: PositiveInt = 3
    pivot_lookback_bars: PositiveInt = 240
    cluster_tol_pct: PositiveFloat = 0.10
    grid_span_pct: PositiveFloat = 1.5
    min_levels_per_side: PositiveInt = 3
    max_levels_per_side: PositiveInt = 8
    fill_gaps: bool = True
    fill_gap_atr_mult: PositiveFloat = 1.0
    atr_period: PositiveInt = 30
    vol_window_bars: PositiveInt = 400
    vol_kde_bandwidth_pct: PositiveFloat = 0.25
    min_order_notional: Decimal = 100
    max_order_notional: Decimal = 5_000
    max_exposure_budget_mult: PositiveFloat = 1.5
    enforce_cap_on_fills: bool = True
    trend_filter_enabled: bool = False
    trend_ema_period: PositiveInt = 100
    trend_min_dist_pct: PositiveFloat = 0.3
    equity_sample_interval_bars: PositiveInt = 6


@dataclass
class GridLevel:
    """One grid level: a resting limit order with a reserved notional."""

    price: float
    side: str  # "BUY" or "SELL"
    reserved: float = 0.0
    order_id: Optional[str] = None


class SRGridStrategy(Strategy):
    def __init__(self, config: SRGridConfig) -> None:
        super().__init__(config)

        self.instrument: Instrument = None

        self._closes: deque[float] = deque(maxlen=MAX_WINDOW)
        self._highs: deque[float] = deque(maxlen=MAX_WINDOW)
        self._lows: deque[float] = deque(maxlen=MAX_WINDOW)
        self._volumes: deque[float] = deque(maxlen=MAX_WINDOW)

        self._bar_count = 0
        self._last_rebalance = 0
        self._last_rebalance_attempt = 0

        self._levels: dict[tuple[str, float], GridLevel] = {}
        self._level_by_order: dict[str, GridLevel] = {}
        self._unallocated = 0.0
        self._pending_redistribute: dict[str, float] = {"BUY": 0.0, "SELL": 0.0}

        self.n_rebalances = 0
        self.n_resyncs = 0
        self.n_fills = 0
        self.n_cap_enforcements = 0
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

        self._flush_redistribution()

        if self._last_rebalance == 0 or self._bar_count - self._last_rebalance >= self.config.rebalance_interval_bars:
            if self._bar_count - self._last_rebalance_attempt >= self.config.rebalance_interval_bars:
                self._last_rebalance_attempt = self._bar_count
                self._rebalance_grid()

        self._enforce_cap_on_fills()

        if self._bar_count % self.config.equity_sample_interval_bars == 0:
            self._sample_equity()

    def _min_warmup(self) -> int:
        cfg = self.config
        return (
            max(cfg.pivot_lookback_bars, cfg.vol_window_bars, cfg.atr_period)
            + 2 * cfg.pivot_window
            + 1
        )

    # -- grid management ----------------------------------------------------

    def _rebalance_grid(self) -> None:
        price = self._closes[-1]
        atr = self._atr()
        levels = self._detect_sr_levels()

        buy_levels = self._select_levels(levels, price, direction=-1, atr=atr)
        sell_levels = self._select_levels(levels, price, direction=+1, atr=atr)

        nb, ns = len(buy_levels), len(sell_levels)
        if nb + ns == 0:
            self.log.warning("Rebalance found no grid levels")
            return

        # Check the caps BEFORE cancelling anything: if both sides get removed,
        # the rebalance is a no-op and the current grid stays untouched. (The
        # pool is estimated from the base budget + freed capital.)
        cap_total = float(self.config.grid_budget) * self.config.max_exposure_budget_mult
        pool_est = min(float(self.config.grid_budget) + self._unallocated, cap_total)
        buy_budget = pool_est * nb / (nb + ns)
        sell_budget = pool_est * ns / (nb + ns)
        buy_levels, sell_levels = self._apply_exposure_caps(
            buy_levels, sell_levels, buy_budget, sell_budget, price
        )
        buy_levels, sell_levels = self._apply_trend_filter(buy_levels, sell_levels, price)
        nb, ns = len(buy_levels), len(sell_levels)
        if nb + ns == 0:
            self.log.info("Rebalance skipped: exposure cap or trend filter removed both sides")
            return

        # Fold freed capital into the pool, then rebuild the grid. The pool is
        # CLAMPED to the risk cap: freed capital that could not be reabsorbed
        # by the opposite side (e.g. a trend where one side never fills) must
        # NOT re-inflate the grid deployment.
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
            f"REBALANCE price={price:.2f} atr={atr:.2f} "
            f"buy={nb} sell={ns} levels total={len(self._levels)}"
        )

    def _apply_exposure_caps(
        self,
        buy_levels: list[float],
        sell_levels: list[float],
        buy_budget: float,
        sell_budget: float,
        price: float,
    ) -> tuple[list[float], list[float]]:
        pos = None
        for candidate in self.cache.positions(instrument_id=self.config.instrument_id):
            if candidate.quantity.as_double() != 0:
                pos = candidate
                break
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

    def _apply_trend_filter(
        self, buy_levels: list[float], sell_levels: list[float], price: float
    ) -> tuple[list[float], list[float]]:
        """Only quote the side that fades the trend (buys up, sells down)."""
        if not self.config.trend_filter_enabled:
            return buy_levels, sell_levels
        ema = self._ema()
        min_dist = self.config.trend_min_dist_pct / 100.0
        if price > ema * (1 + min_dist):
            # Uptrend → don't accumulate shorts, only buy dips.
            sell_levels = []
        elif price < ema * (1 - min_dist):
            # Downtrend → don't accumulate longs, only sell rallies.
            buy_levels = []
        return buy_levels, sell_levels

    def _ema(self) -> float:
        period = self.config.trend_ema_period
        closes = list(self._closes)[-period:]
        if len(closes) < period:
            return self._closes[-1]
        alpha = 2.0 / (period + 1)
        ema = closes[0]
        for c in closes[1:]:
            ema = alpha * c + (1 - alpha) * ema
        return ema

    def _enforce_cap_on_fills(self) -> None:
        """Cancel the inventory side as soon as fills push past the cap.

        The exposure cap is otherwise only checked at rebalance, so a sustained
        trend can grow the position unboundedly between rebalances. This runs
        after every bar to stop that accumulation.
        """
        if not self.config.enforce_cap_on_fills:
            return
        pos = None
        for candidate in self.cache.positions(instrument_id=self.config.instrument_id):
            if candidate.quantity.as_double() != 0:
                pos = candidate
                break
        if pos is None:
            return
        notional = abs(float(pos.quantity.as_double())) * self._closes[-1]
        cap = float(self.config.grid_budget) * self.config.max_exposure_budget_mult
        side_to_cancel = None
        if pos.side == PositionSide.LONG and notional > cap:
            side_to_cancel = "BUY"
        elif pos.side == PositionSide.SHORT and notional > cap:
            side_to_cancel = "SELL"
        if side_to_cancel is None:
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
        self.log.info(f"Exposure cap enforced on fills: cancelled {side_to_cancel} levels")

    def _allocate_and_place(self, prices: list[float], side: str, budget: float) -> None:
        if not prices:
            return
        probs = self._vp_probabilities(prices)
        for price, prob in zip(prices, probs):
            notional = float(budget) * float(prob)
            notional = self._clamp_notional(notional)
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
        if cid not in self._level_by_order:
            return

        self.n_fills += 1
        self.total_commissions += float(event.commission.as_double())

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

    def _detect_sr_levels(self) -> list[float]:
        """Fractal pivots, clustered into S/R level prices."""
        cfg = self.config
        w = cfg.pivot_window
        n = len(self._closes)
        if n < 2 * w + 2:
            return []

        highs = np.array(self._highs)
        lows = np.array(self._lows)

        pivot_prices = []
        start = max(w, n - cfg.pivot_lookback_bars)
        for i in range(start, n - w):
            # A pivot must be strictly higher/lower than ALL its 2*w neighbours
            # (the window must NOT include the bar itself).
            if highs[i] > np.max(highs[i - w : i]) and highs[i] > np.max(highs[i + 1 : i + w + 1]):
                pivot_prices.append(float(highs[i]))
            if lows[i] < np.min(lows[i - w : i]) and lows[i] < np.min(lows[i + 1 : i + w + 1]):
                pivot_prices.append(float(lows[i]))

        if not pivot_prices:
            return []

        return self._cluster(pivot_prices)

    def _cluster(self, prices: list[float]) -> list[float]:
        """Greedily merge nearby prices (within cluster_tol_pct) into levels."""
        tol = self.config.cluster_tol_pct / 100.0
        sorted_prices = sorted(prices)
        levels: list[float] = []
        current = sorted_prices[0]
        group = [current]
        for p in sorted_prices[1:]:
            if p - current <= tol * current:
                group.append(p)
                current = p
            else:
                levels.append(float(np.mean(group)))
                group = [p]
                current = p
        levels.append(float(np.mean(group)))
        return levels

    def _select_levels(
        self, levels: list[float], price: float, direction: int, atr: float
    ) -> list[float]:
        """Select grid levels on one side, gap-filling sparse S/R with ATR."""
        cfg = self.config
        span = cfg.grid_span_pct / 100.0
        lo, hi = price * (1 - span), price * (1 + span)

        if direction == -1:
            cand = sorted([p for p in levels if lo <= p < price], reverse=True)
        else:
            cand = sorted([p for p in levels if price < p <= hi])

        step = max(atr * cfg.fill_gap_atr_mult, self._min_step())
        out: list[float] = []

        if not cand:
            # Pure grid fallback: fill the span at ATR spacing.
            cur = price
            while len(out) < cfg.max_levels_per_side:
                cur = cur - step * direction
                if not (lo <= cur <= hi):
                    break
                out.append(round(cur, self.instrument.price_precision))
            return out[: cfg.max_levels_per_side]

        prev = price
        for p in cand:
            gap = abs(prev - p)
            if cfg.fill_gaps and len(out) + 1 < cfg.max_levels_per_side and gap > step:
                # Insert intermediate levels between prev and this S/R level.
                cur = prev - step * direction
                while abs(cur - p) > step * 0.5 and len(out) < cfg.max_levels_per_side:
                    if not (lo <= cur <= hi):
                        break
                    out.append(round(cur, self.instrument.price_precision))
                    cur = cur - step * direction
            out.append(round(p, self.instrument.price_precision))
            prev = p
            if len(out) >= cfg.max_levels_per_side:
                break

        return out[: cfg.max_levels_per_side]

    def _min_step(self) -> float:
        return float(self.instrument.price_increment.as_double())

    def _vp_probabilities(self, prices: list[float]) -> np.ndarray:
        """Volume-profile distribution: KDE of traded volume at each price."""
        n = min(self.config.vol_window_bars, len(self._closes))
        closes = np.array(self._closes)[-n:]
        volumes = np.array(self._volumes)[-n:]
        prices = np.asarray(prices, dtype=float)

        if len(closes) == 0 or prices.size == 0:
            return np.full(len(prices), 1.0 / max(len(prices), 1))

        total_vol = volumes.sum()
        if total_vol <= 0:
            return np.full(len(prices), 1.0 / max(len(prices), 1))

        bandwidth = self.config.vol_kde_bandwidth_pct / 100.0 * self._closes[-1]
        if bandwidth <= 0:
            return np.full(len(prices), 1.0 / max(len(prices), 1))

        # KDE: density(p) = sum_i v_i * K((p - close_i) / h)
        diff = (prices[:, None] - closes[None, :]) / bandwidth
        kernel = np.exp(-0.5 * diff**2)
        density = kernel @ volumes
        denom = density.sum()
        if denom <= 0:
            return np.full(len(prices), 1.0 / max(len(prices), 1))
        return density / denom

    # -- accounting ----------------------------------------------------------

    def _sample_equity(self) -> None:
        account = self.portfolio.account(venue=self.config.instrument_id.venue)
        if account is None:
            return
        balance = account.balance_total(None)
        ts = self._clock.timestamp_ns()
        self._equity_curve.append((ts, float(balance.as_double())))

        # Inventory clarity: how much of each asset is held, at all times.
        btc_qty = 0.0
        free_money = account.balance_free(None)
        usdt_free = float(free_money.as_double()) if free_money is not None else 0.0
        for candidate in self.cache.positions(instrument_id=self.config.instrument_id):
            if candidate.quantity.as_double() != 0:
                btc_qty = float(candidate.quantity.as_double())
                break
        self._position_curve.append(
            (ts, btc_qty, usdt_free, float(balance.as_double()), self._closes[-1])
        )

    # -- state ---------------------------------------------------------------

    def on_save(self) -> dict[str, bytes]:
        return {}

    def on_load(self, state: dict[str, bytes]) -> None:
        pass
