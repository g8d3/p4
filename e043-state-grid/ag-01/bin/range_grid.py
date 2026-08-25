#!/usr/bin/env python3
"""e043 — standalone port of e022's v2 two-sided ATR-spaced range grid.

Faithful, Nautilus-free re-implementation of SRGridStrategyV2 so we can (A1)
validate that the known-good base edge reproduces in our harness, then (A2)
layer the user's features (R-recycle, multi-volume Q, multi-stop SL/V) on top
and A/B them.

Core mechanics (matching e022 v2):
- EMA fast/slow regime filter with hysteresis; RANGE only → grid armed.
- Grid re-balanced every `rebalance_interval` bars.
- Price-space levels at whole multiples of `step = max(atr*atr_mult, min)`.
- Capital allocated per level via volume-profile KDE, clamped to [min,max].
- Fill → freed capital pooled to the OPPOSITE side, applied once per bar.
- Exposure cap: cancel inventory side + flatten excess, reduce-only.
- Liquidation: force-flatten when unrealized loss < margin.
- Maker fee on limit fills, taker fee on flatten markets.

Accounting: signed net inventory + running average entry price; realized PnL on
reductions, unrealized on mark. Equity = start + realized + unrealized.

Run with run_grid.py (reads OHLCV, walks bars causally).
"""

from dataclasses import dataclass, field
from typing import Dict, List
import numpy as np
import pandas as pd


@dataclass
class Config:
    budget: float = 30_000
    atr_period: int = 14
    atr_mult: float = 1.5
    max_levels: int = 3
    min_start: float = 200
    rebalance: int = 96
    trend_fast: int = 20
    trend_slow: int = 100
    trend_enter: float = 0.005      # 0.5%
    trend_exit: float = 0.002       # 0.2%
    max_exposure_mult: float = 3.0
    liquidation_mult: float = 1.0
    cap_overshoot: float = 0.10
    min_order: float = 500
    max_order: float = 10_000
    maker_fee: float = 0.0002
    taker_fee: float = 0.0006
    start_cash: float = 100_000
    vp_window: int = 400
    flatten_min_notional: float = 0.0   # skip regime-flatten if inventory < this


@dataclass
class Level:
    side: str
    price: float
    reserved: float = 0.0
    active: bool = True


class RangeGrid:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.pos_qty = 0.0            # +long / -short (net, signed)
        self.avg_price = 0.0
        self.realized = 0.0
        self.regime = "RANGE"
        self.levels: Dict[str, Level] = {}
        self.unallocated = 0.0
        self.pending = {"BUY": 0.0, "SELL": 0.0}
        self.bar_count = 0
        self.last_rebalance = -10**9
        self.last_rebalance_attempt = -10**9
        self.fills = []               # (bar, side, px, notional, fee, kind)
        self.equity = []

        self.n_rebalances = 0
        self.n_fills = 0
        self.n_regime_flips = 0
        self.n_liquidations = 0
        self.n_cap_enforcements = 0
        self.commissions = 0.0

    # -- regime -------------------------------------------------------------
    def update_regime(self, ema_fast, ema_slow):
        ratio = ema_fast / ema_slow - 1.0
        ent, ext = self.cfg.trend_enter, self.cfg.trend_exit
        if self.regime == "RANGE":
            if ratio > ent: self.regime = "LONG"
            elif ratio < -ent: self.regime = "SHORT"
        elif self.regime == "LONG":
            if ratio < -ent: self.regime = "SHORT"
            elif ratio < ext: self.regime = "RANGE"
        elif self.regime == "SHORT":
            if ratio > ent: self.regime = "LONG"
            elif ratio > -ext: self.regime = "RANGE"

    # -- inventory / accounting --------------------------------------------
    def _trade(self, delta_signed, price, fee_notional, fee_rate, bar, kind):
        fee = fee_notional * fee_rate
        self.fills.append((bar, "BUY" if delta_signed > 0 else "SELL",
                           round(price, 2), round(fee_notional, 2),
                           round(fee, 4), kind))
        self.realized -= fee
        self.commissions += fee
        self.n_fills += 1
        if delta_signed == 0:
            return
        if self.pos_qty == 0:
            self.pos_qty = delta_signed
            self.avg_price = price
            return
        if self.pos_qty * delta_signed > 0:
            nq = self.pos_qty + delta_signed
            self.avg_price = (self.avg_price * self.pos_qty + price * delta_signed) / nq
            self.pos_qty = nq
        else:
            closed = min(abs(self.pos_qty), abs(delta_signed))
            if self.pos_qty > 0:
                self.realized += (price - self.avg_price) * closed
            else:
                self.realized += (self.avg_price - price) * closed
            self.pos_qty += delta_signed
            if self.pos_qty == 0:
                self.avg_price = 0.0
            elif abs(delta_signed) >= abs(self.pos_qty):
                self.avg_price = price

    def net_notional(self, price):
        return abs(self.pos_qty) * price

    def unrealized(self, price):
        if self.pos_qty > 0:
            return (price - self.avg_price) * self.pos_qty
        if self.pos_qty < 0:
            return (self.avg_price - price) * abs(self.pos_qty)
        return 0.0

    def equity_now(self, price):
        return self.cfg.start_cash + self.realized + self.unrealized(price)

    # -- grid --------------------------------------------------------------
    def rebalance(self, price, atr, closes, volumes):
        if self.regime != "RANGE":
            return
        step = max(atr * self.cfg.atr_mult, 1e-9)
        n = self.cfg.max_levels
        buy_levels = [round(price - step * k, 2) for k in range(1, n + 1) if price - step * k > 0]
        sell_levels = [round(price + step * k, 2) for k in range(1, n + 1)]

        cap_total = self.cfg.budget * self.cfg.max_exposure_mult
        # exposure caps on sides
        long_n, short_n = 0.0, 0.0
        if self.pos_qty > 0: long_n = self.pos_qty * price
        elif self.pos_qty < 0: short_n = -self.pos_qty * price
        buy_budget = self.pending_total() * len(buy_levels) / max(len(buy_levels) + len(sell_levels), 1)
        sell_budget = self.pending_total() * len(sell_levels) / max(len(buy_levels) + len(sell_levels), 1)
        if long_n + buy_budget > cap_total: buy_levels = []
        if short_n + sell_budget > cap_total: sell_levels = []
        if not buy_levels and not sell_levels:
            return

        total = self.cfg.budget + self.unallocated + self.pending["BUY"] + self.pending["SELL"]
        self.pending = {"BUY": 0.0, "SELL": 0.0}
        self.unallocated = max(0.0, total - cap_total)
        total = min(total, cap_total)

        nb, ns = len(buy_levels), len(sell_levels)
        if nb and ns:
            buy_budget = total * nb / (nb + ns)
            sell_budget = total * ns / (nb + ns)
        else:
            buy_budget = total if nb else 0.0
            sell_budget = total if ns else 0.0

        self.levels.clear()
        self._allocate(buy_levels, "BUY", buy_budget, closes, volumes, price)
        self._allocate(sell_levels, "SELL", sell_budget, closes, volumes, price)
        self.last_rebalance = self.bar_count
        self.n_rebalances += 1

    def pending_total(self):
        return self.unallocated + self.pending["BUY"] + self.pending["SELL"]

    def _allocate(self, prices, side, budget, closes, volumes, price):
        if not prices or budget <= 0:
            return
        probs = self._vp(prices, closes, volumes, price)
        for p, prob in zip(prices, probs):
            notional = float(np.clip(budget * prob, self.cfg.min_order, self.cfg.max_order))
            self.levels[(side, p)] = Level(side, p, notional)

    def _vp(self, prices, closes, volumes, price):
        prices = np.asarray(prices, float)
        n = min(self.cfg.vp_window, len(closes))
        closes = np.asarray(closes)[-n:]
        volumes = np.asarray(volumes)[-n:]
        if n == 0 or prices.size == 0 or volumes.sum() <= 0:
            return np.full(prices.size, 1.0 / max(prices.size, 1))
        bw = 0.25 / 100.0 * price
        if bw <= 0:
            return np.full(prices.size, 1.0 / max(prices.size, 1))
        diff = (prices[:, None] - closes[None, :]) / bw
        dens = np.exp(-0.5 * diff**2) @ volumes
        s = dens.sum()
        return dens / s if s > 0 else np.full(prices.size, 1.0 / max(prices.size, 1))

    # -- one bar -----------------------------------------------------------
    def step(self, bar, high, low, close, atr, ema_fast, ema_slow, closes, volumes, origin):
        old = self.regime
        self.update_regime(ema_fast, ema_slow)
        if self.regime != old:
            self.n_regime_flips += 1
            self.levels.clear()
            self.pending = {"BUY": 0.0, "SELL": 0.0}
            self.unallocated = 0.0
            self.last_rebalance = -10**9
            self.last_rebalance_attempt = -10**9
            if self.regime != "RANGE":
                if abs(self.pos_qty) * close >= self.cfg.flatten_min_notional:
                    self._flatten(bar, close, market=True)

        if self.regime == "RANGE":
            if self.bar_count - self.last_rebalance_attempt >= self.cfg.rebalance:
                self.last_rebalance_attempt = self.bar_count
                self.rebalance(close, atr, closes, volumes)
            self._process_fills(bar, high, low)
            self._flush_pending(closes, volumes, close)
            self._enforce_cap(bar, close)
            self._check_liquidation(bar, close)

        self.equity.append(self.equity_now(close))

    def _process_fills(self, bar, high, low):
        for key in list(self.levels):
            lv = self.levels[key]
            if not lv.active:
                continue
            if lv.side == "BUY" and low <= lv.price:
                self._trade(+lv.reserved / lv.price, lv.price, lv.reserved,
                            self.cfg.maker_fee, bar, "GRID")
                self.pending["SELL"] += lv.reserved
                del self.levels[key]
            elif lv.side == "SELL" and high >= lv.price:
                self._trade(-lv.reserved / lv.price, lv.price, lv.reserved,
                            self.cfg.maker_fee, bar, "GRID")
                self.pending["BUY"] += lv.reserved
                del self.levels[key]

    def _flush_pending(self, closes, volumes, price):
        for side in ("BUY", "SELL"):
            freed = self.pending.get(side, 0.0)
            self.pending[side] = 0.0
            if freed <= 0:
                continue
            others = [lv for lv in self.levels.values() if lv.side == side]
            if not others:
                self.unallocated += freed
                continue
            probs = self._vp([lv.price for lv in others], closes, volumes, price)
            for lv, prob in zip(others, probs):
                lv.reserved = float(np.clip(lv.reserved + freed * prob,
                                            self.cfg.min_order, self.cfg.max_order))

    def _enforce_cap(self, bar, price):
        cap = self.cfg.budget * self.cfg.max_exposure_mult
        band = cap * (1 + self.cfg.cap_overshoot)
        notional = self.net_notional(price)
        side = None
        if self.pos_qty > 0 and notional > band:
            side = "BUY"; target = cap / price
        elif self.pos_qty < 0 and notional > band:
            side = "SELL"; target = -cap / price
        else:
            return
        # cancel that side's remaining levels, park their capital
        for key in list(self.levels):
            if self.levels[key].side == side:
                self.unallocated += self.levels[key].reserved
                del self.levels[key]
        # flatten excess to the cap (reduce-only market)
        excess = self.pos_qty - target if self.pos_qty > 0 else self.pos_qty - target
        if abs(excess) > 1e-9:
            self._trade(-excess if self.pos_qty > 0 else -excess, price,
                        abs(excess) * price, self.cfg.taker_fee, bar, "CAP")
        self.n_cap_enforcements += 1

    def _check_liquidation(self, bar, price):
        margin = self.cfg.budget * self.cfg.liquidation_mult
        if self.unrealized(price) < -margin:
            self.n_liquidations += 1
            self._flatten(bar, price, market=True)
            self.levels.clear()
            self.unallocated = 0.0
            self.pending = {"BUY": 0.0, "SELL": 0.0}

    def _flatten(self, bar, price, market=False):
        qty = self.pos_qty
        if abs(qty) < 1e-9:
            return
        self._trade(-qty, price, abs(qty) * price,
                    self.cfg.taker_fee if market else self.cfg.maker_fee, bar,
                    "FLAT" if market else "GRID")


def add_indicators(df, cfg):
    df = df.copy()
    df["ema_fast"] = df["close"].ewm(span=cfg.trend_fast, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=cfg.trend_slow, adjust=False).mean()
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(cfg.atr_period).mean()
    return df
