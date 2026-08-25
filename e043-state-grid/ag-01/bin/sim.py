#!/usr/bin/env python3
"""e043 State Grid — Fase 1 bar-by-bar event-driven backtest on real OHLCV.

A percentage-ladder grid with state (trend-regime) allocation control.

Reads e022-style OHLCV CSV, walks bars causally, computes a trend-regime state
from PAST bars only (EMA fast/slow + ATR, indicator values shifted by one bar),
disarms the grid outside RANGE (allocation target 0), and runs lot-based ladder
lots: buy depth C, take-profit V, rebuy R after a win, stop SL / trailing stop.
Fills: entries/crosses at the limit price (intrabar), exits at TP/SL on
intrabar high/low. Emits equity curve, fills report, and metric JSON.

Run:
    python3 ag-01/bin/sim.py --data <ohlcv.csv> [--config cfg.json] [--out-dir X]
"""

import argparse, json, math, os
import pandas as pd
import numpy as np

# --------------------------------------------------------------------------- #
# Defaults (SPEC §8); overridable via --config <file.json>
# --------------------------------------------------------------------------- #
DEFAULTS = {
    "tier1": {
        "sides": "both_mirror",
        "anchor_mode": "rolling_high",
        "anchor_lookback": 288,           # bars of rolling high for the anchor
        "sl_anchor": "trailing_from_peak",# fixed_from_buy | trailing_from_peak
        "trail_dist_mode": "atr_mult",    # none | pct | atr_mult
        "trail_dist": 2.5,                # ×ATR when atr_mult
        "trail_pct": 0.02,                # pct when pct
        "exit_model": "lot-based",
        "ladder_exhaustion": "freeze",    # extend | freeze | stop_grid
        "pairing": "per_level",           # per_level | shared
        "maker_fee": 0.0002,
        "taker_fee": 0.0006,
        "min_order_notional": 1000,
        "max_exposure": 400_000,
        "liquidation_margin_budget_mult": 4,
        "budget": 30_000,                 # capital deployed to the grid
        "start_cash": 100_000,
        "allocation_map": {               # side multiplier per regime
            "RANGE":      {"long": 1.0, "short": 1.0},
            "TREND_UP":   {"long": 0.0, "short": 0.0},
            "TREND_DOWN": {"long": 0.0, "short": 0.0},
        },
        "regime": {"ema_fast": 50, "ema_slow": 100,
                   "enter_pct": 0.010, "exit_pct": 0.005},
    },
    "tier2": {
        "C": [0.005, 0.010, 0.020, 0.030],
        "V": [0.010, 0.015, 0.020, 0.025],
        "R": [0.0075],
        "SL": [0.020, 0.040],
        "Q": "equal",
    },
    "tier3": {},
}


# --------------------------------------------------------------------------- #
# Indicators (causal; consumer shifts by one bar to avoid lookahead)
# --------------------------------------------------------------------------- #
def add_indicators(df, cfg):
    r = cfg["tier1"]["regime"]
    df = df.copy()
    df["ema_fast"] = df["close"].ewm(span=r["ema_fast"], adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=r["ema_slow"], adjust=False).mean()
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    return df


def trend_state(slope, prev_state, enter_pct, exit_pct):
    if prev_state == "RANGE":
        if slope > enter_pct: return "TREND_UP"
        if slope < -enter_pct: return "TREND_DOWN"
        return "RANGE"
    if abs(slope) < exit_pct:
        return "RANGE"
    return "TREND_UP" if slope > 0 else "TREND_DOWN"


# --------------------------------------------------------------------------- #
# Lot model
# --------------------------------------------------------------------------- #
class Lot:
    __slots__ = ("side", "q", "c", "v", "s", "r", "state",
                 "buy_px", "entry", "peak", "stop", "tp", "sell_px")
    def __init__(self, side, q, c, v, s, r):
        self.side = side            # +1 long, -1 short
        self.q = q                  # USD notional of this lot
        self.c, self.v, self.s, self.r = c, v, s, r
        self.state = "ARMED"        # ARMED | BOUGHT | REBUYING
        self.buy_px = None
        self.entry = None
        self.peak = None
        self.stop = None
        self.tp = None
        self.sell_px = None


def order_lots(cfg):
    t1, t2 = cfg["tier1"], cfg["tier2"]
    C, V, SL, R = t2["C"], t2["V"], t2["SL"], t2["R"]
    sides = (["long", "short"] if t1["sides"] == "both_mirror" else ["long"])
    n = len(C)
    per_lot = t1["budget"] / (len(sides) * n)
    lots = []
    for sn in sides:
        side = 1 if sn == "long" else -1
        for i in range(n):
            v = V[i] if (t1["pairing"] == "per_level" and i < len(V)) else V[0]
            s = SL[i % len(SL)]
            lots.append(Lot(side, per_lot, C[i], v, s, R[0]))
    return lots


class Grid:
    def __init__(self, cfg):
        self.cfg = cfg
        self.t1, self.t2 = cfg["tier1"], cfg["tier2"]
        self.lots = order_lots(cfg)
        self.cash = self.t1["start_cash"]
        self.start_cash = self.t1["start_cash"]
        self.realized = 0.0
        self.last_state = "RANGE"
        self.anchor = None
        self.atr_now = 0.0
        self.fills = []               # (bar, side, action, px, notional, fee)
        self.equity = []
        self.n_bars = 0
        self.exposure_ratio_sum = 0.0
        self.n_win = 0
        self.n_loss = 0
        self.wins_pnl = 0.0
        self.losses_pnl = 0.0

    # ---- helpers ----------------------------------------------------------
    def side_allowed(self, side):
        am = self.t1["allocation_map"].get(self.last_state, {})
        return am.get("long" if side == 1 else "short", 0.0) > 0

    def trail_dist(self, px):
        if self.t1["trail_dist_mode"] == "atr_mult":
            return self.t1["trail_dist"] * self.atr_now
        if self.t1["trail_dist_mode"] == "pct":
            return self.t1["trail_pct"] * px
        return 0.0

    def gross_exposure(self):
        return sum(l.q for l in self.lots if l.state == "BOUGHT")

    # ---- order / position lifecycle ---------------------------------------
    def set_buy_limits(self):
        for lot in self.lots:
            if lot.state not in ("ARMED", "REBUYING"):
                continue
            base = lot.sell_px if lot.state == "REBUYING" else self.anchor
            pct = lot.r if lot.state == "REBUYING" else lot.c
            lot.buy_px = base * (1 - pct) if lot.side == 1 else base * (1 + pct)

    def open_pos(self, i, lot, px):
        fee = lot.q * self.t1["maker_fee"]
        self.fills.append((i, lot.side, "OPEN", round(px, 2), lot.q, round(fee, 2)))
        self.realized -= fee
        lot.state = "BOUGHT"
        lot.entry = px
        lot.peak = px
        lot.tp = px * (1 + lot.v * lot.side)
        if self.t1["sl_anchor"] == "fixed_from_buy":
            lot.stop = px * (1 - lot.s * lot.side)
        else:  # trailing_from_peak
            lot.stop = px * (1 - lot.s * lot.side)   # initial = fixed stop
        lot.buy_px = None

    def close_pos(self, i, lot, px):
        side = lot.side
        pnl = lot.q * (px - lot.entry) / lot.entry * side
        fee = lot.q * self.t1["maker_fee"]
        self.fills.append((i, side, "CLOSE", round(px, 2), lot.q, round(fee, 2)))
        self.realized += pnl - fee
        if pnl > 0:
            self.n_win += 1; self.wins_pnl += pnl
        else:
            self.n_loss += 1; self.losses_pnl += pnl
        lot.sell_px = px
        if pnl > 0:
            lot.state = "REBUYING"       # win → wait for R drop to rebuy
        else:
            lot.state = "ARMED"          # stop → recycle to original C lot
        lot.buy_px = None

    def flatten(self, i, c):
        for lot in self.lots:
            if lot.state == "BOUGHT":
                self.close_pos(i, lot, c)

    def mark(self, px):
        total = self.cash + self.realized
        for lot in self.lots:
            if lot.state == "BOUGHT":
                total += lot.q * (px - lot.entry) * lot.side / lot.entry
        return total

    def record(self, c):
        self.equity.append(self.mark(c))
        self.exposure_ratio_sum += self.gross_exposure() / self.start_cash

    # ---- one bar ----------------------------------------------------------
    def step(self, i, row):
        self.n_bars += 1
        h, l, c = row["high"], row["low"], row["close"]
        self.atr_now = float(row["atr"]) if row["atr"] == row["atr"] else 0.0

        slope = (row["ema_fast"] - row["ema_slow"]) / row["ema_slow"]
        rg = self.t1["regime"]
        self.last_state = trend_state(slope, self.last_state, rg["enter_pct"], rg["exit_pct"])

        # rolling-high anchor (causal max computed in main loop)
        if self.t1["anchor_mode"] == "rolling_high":
            self.anchor = row["_rhigh"]

        # state disarmed (allocation target 0 both sides) → flatten, no grid
        if not self.side_allowed(1) and not self.side_allowed(-1):
            self.flatten(i, c)
            self.record(c)
            return

        self.set_buy_limits()
        exposure = self.gross_exposure()

        # exits (TP/SL) via intrabar high/low
        for lot in list(self.lots):
            if lot.state != "BOUGHT":
                continue
            if lot.side == 1:
                if h >= lot.tp:
                    self.close_pos(i, lot, lot.tp); continue
                if l <= lot.stop:
                    self.close_pos(i, lot, lot.stop); continue
                if h > lot.peak:
                    lot.peak = h
                    if self.t1["sl_anchor"] == "trailing_from_peak":
                        lot.stop = max(lot.stop, lot.peak - self.trail_dist(lot.peak))
            else:
                if l <= lot.tp:
                    self.close_pos(i, lot, lot.tp); continue
                if h >= lot.stop:
                    self.close_pos(i, lot, lot.stop); continue
                if l < lot.peak:
                    lot.peak = l
                    if self.t1["sl_anchor"] == "trailing_from_peak":
                        lot.stop = min(lot.stop, lot.peak + self.trail_dist(lot.peak))

        # entries (ladder sequence: ONE fill per side per bar; a real ladder
        # scales in as price crosses each level, not all at once on a gap)
        for side in (1, -1):
            if not self.side_allowed(side):
                continue
            armed = [lot for lot in self.lots
                     if lot.state == "ARMED" and lot.side == side
                     and lot.buy_px is not None
                     and ((side == 1 and l <= lot.buy_px)
                          or (side == -1 and h >= lot.buy_px))]
            if armed and exposure < self.t1["max_exposure"]:
                pick = min(armed, key=lambda x: x.c)   # shallowest level first
                self.open_pos(i, pick, pick.buy_px)
                exposure += pick.q
            rebuy = [lot for lot in self.lots
                     if lot.state == "REBUYING" and lot.side == side
                     and lot.buy_px is not None
                     and ((side == 1 and l <= lot.buy_px)
                          or (side == -1 and h >= lot.buy_px))]
            if rebuy and exposure < self.t1["max_exposure"]:
                self.open_pos(i, rebuy[0], rebuy[0].buy_px)
                exposure += rebuy[0].q

        self.record(c)


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def compute_metrics(cfg, grid):
    eq = np.array(grid.equity, dtype=float)
    rets = np.diff(eq) / eq[:-1] if len(eq) > 1 else np.array([])
    start = cfg["tier1"]["start_cash"]
    total_pnl = eq[-1] - start
    total_return = total_pnl / start * 100.0
    peak = np.maximum.accumulate(eq)
    max_dd = ((eq - peak) / peak).min() * 100.0
    sharpe = (rets.mean() / rets.std() * math.sqrt(252)
              if len(rets) > 2 and rets.std() > 0 else 0.0)

    # profit factor / win rate from recorded round-trip PnLs
    # (reconstruct via CLOSE fills: we logged notional and price; entry/px known
    #  only implicitly, so track through realized grouping is skipped here —
    #  we expose realized PnL and commissions directly.)
    total_fees = sum(f[5] for f in grid.fills)
    n_fills = len(grid.fills)
    return {
        "total_return_pct": round(total_return, 4),
        "total_pnl_usdt": round(total_pnl, 2),
        "sharpe": round(float(sharpe), 4),
        "max_drawdown_pct": round(float(max_dd), 4),
        "n_fills": n_fills,
        "n_lots": len(grid.lots),
        "total_commissions_usdt": round(total_fees, 2),
        "realized_pnl_usdt": round(grid.realized, 2),
        "final_equity_usdt": round(float(eq[-1]), 2),
        "exposure_time_pct": round(grid.exposure_ratio_sum / max(grid.n_bars, 1) * 100, 4),
        "n_bars": grid.n_bars,
        "final_state": grid.last_state,
        "n_win": grid.n_win, "n_loss": grid.n_loss,
        "wins_pnl_usdt": round(grid.wins_pnl, 2),
        "losses_pnl_usdt": round(grid.losses_pnl, 2),
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def load_config(path):
    cfg = json.loads(json.dumps(DEFAULTS))
    if path and os.path.exists(path):
        user = json.load(open(path))
        for tier, body in user.items():
            cfg[tier].update(body)
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--config", default=None)
    ap.add_argument("--out-dir", default="output/default")
    ap.add_argument("--start", type=int, default=2_000, help="skip warmup bars")
    args = ap.parse_args()

    cfg = load_config(args.config)
    df = pd.read_csv(args.data)
    df = add_indicators(df, cfg)

    rb = cfg["tier1"]["anchor_lookback"]
    highs = df["high"].values
    # causal rolling-high column: max high over [i-rb, i-1]
    df["_rhigh"] = np.array([highs[max(0, i - rb):i].max() if i > 0 else highs[0]
                             for i in range(len(df))], dtype=float)

    grid = Grid(cfg)
    start = max(200, args.start)
    for i in range(start, len(df)):
        row = df.iloc[i].copy()
        # shift indicators by one bar for causality
        row["ema_fast"] = df["ema_fast"].iloc[i - 1]
        row["ema_slow"] = df["ema_slow"].iloc[i - 1]
        row["atr"] = df["atr"].iloc[i - 1]
        row["_rhigh"] = df["_rhigh"].iloc[i]
        grid.step(i, row)

    os.makedirs(args.out_dir, exist_ok=True)
    m = compute_metrics(cfg, grid)
    json.dump(m, open(f"{args.out_dir}/metrics.json", "w"), indent=2)
    pd.DataFrame({"i": list(range(len(grid.equity))),
                  "equity": grid.equity}).to_csv(
        f"{args.out_dir}/equity_curve.csv", index=False)
    pd.DataFrame(grid.fills, columns=["bar", "side", "action", "price",
                                      "notional", "fee"]).to_csv(
        f"{args.out_dir}/fills_report.csv", index=False)

    name = os.path.basename(args.out_dir)
    summ_path = os.path.join(os.path.dirname(args.out_dir.rstrip("/")), "summary.csv")
    os.makedirs(os.path.dirname(summ_path), exist_ok=True)
    if not os.path.exists(summ_path):
        open(summ_path, "w").write("run,return_pct,max_dd_pct,n_fills,commissions,realized_pnl,sharpe\n")
    with open(summ_path, "a") as f:
        f.write(f"{name},{m['total_return_pct']},{m['max_drawdown_pct']},"
                f"{m['n_fills']},{m['total_commissions_usdt']},"
                f"{m['realized_pnl_usdt']},{m['sharpe']}\n")

    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()
