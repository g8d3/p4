# e043 — State Grid: Design Spec (Fase 0)

A **percentage-ladder grid** where buy, take-profit, rebuy, stop-loss depths are
each a *distribution* (ladder) of percentages, governed by a **portfolio
allocation target layer** whose setpoints change with **state** (measured market
variables, never the calendar).

The cleanest mental model is **not "a grid of prices" — it is a state machine
over lots of capital.** Each lot runs a cycle:

```
ARMED  ──(price ≤ ref×(1−c_i))──────────────▶ BOUGHT
BOUGHT ──(price ≥ buy×(1+v_j))──────────────▶ SOLD ──(price ≤ sell×(1−r_k))──▶ RE-ARMED
BOUGHT ──(price ≤ buy×(1−s_l) or trail hit)──▶ STOPPED ──▶ ARMED
BOUGHT ──(new peak)─────────────────────────▶ peak update → trailing SL moves
```

All references below are for the **long** mirror; the short side is mirrored.

**Every value is a runtime parameter with a default.** Nothing is hardcoded and
nothing is "a design decision to lock in" — calibration is a separate concern
(§3). Defaults below are reasonable starting points, not validated results.

---

## 1. Complete parameter model

### 1.1 Tier 1 — structural parameters (defaults; rarely changed; NEVER swept together)

| Parameter | Type / options | Default | Meaning |
|---|---|---|---|
| `sides` | `long` \| `short` \| `both_mirror` | `both_mirror` | Which side(s) to trade; short mirrors long |
| `anchor_mode` | `activation_price` \| `rolling_high` \| `last_fill` | `rolling_high` | Reference the C ladder is measured from |
| `sl_anchor` | `fixed_from_buy` \| `trailing_from_peak` | `trailing_from_peak` | How the stop is anchored |
| `trail_dist_mode` | `none` \| `pct` \| `atr_mult` | `atr_mult` | Trailing distance mode (dynamic = `atr_mult`) |
| `trail_dist` | number | `2.5` | Distance; pct (%) or ×ATR per mode |
| `exit_model` | `lot-based` \| `fractional` | `lot-based` | How several stops/targets exit a level |
| `ladder_exhaustion` | `extend` \| `freeze` \| `stop_grid` | `freeze` | What happens when price passes the last C level with no sells |
| `pairing` | `per_level` \| `shared` | `per_level` | Does lot i use only vᵢ, or one shared V for all lots |
| `q_rule` | `equal` \| `depth_scaled` \| `volume_profile` | `equal` | Capital distribution curve across levels |
| `q_depth_direction` | `increasing` \| `decreasing` | `increasing` | Direction of `depth_scaled` (averaging-down vs shallow-heavy) |
| `allocation_map` | object (state→target table, §1.4) | see §1.4 | The "success" setpoints per state |
| `maker_fee`, `taker_fee` | number | `0.0002`, `0.0006` | Fees (0.02% / 0.06%) |
| `min_order_notional` | USD | `1000` | Skip micro-orders |
| `max_exposure` | USD notional | `400000` | Exposure cap; enforce with reduce-only flatten |
| `liquidation_margin_budget_mult` | number | `4` | Force-flatten threshold for unrealized loss |

### 1.2 Tier 2 — ladder shapes (swept 2-3 at a time)

| Parameter | Type | Default (to tune) | Meaning |
|---|---|---|---|
| `C` | vector `[c₁…cₙ]` | `[0.5, 1.0, 2.0, 3.0]` | Buy depth ladder (% below anchor) |
| `V` | vector `[v₁…vₙ]` | `[1.0, 1.5, 2.0, 2.5]` | Take-profit ladder (% above each buy) |
| `R` | vector `[r₁…rₘ]` | `[0.75]` | Rebuy ladder (% below each sell) |
| `SL` | vector `[s₁…sₖ]` | `[2.0, 4.0]` | Stop-loss ladder (% below buy) |
| `Q` | vector `[q₁…qₙ]` | `equal` | Volume per level (fraction of budget or USD) |

Every level is a **lot** = a triple `(q_i, s_i, v_i)` — its own volume, stop, and
target → its own `R:R = v_i / s_i`. This is what lets one entry carry several
risk-reward profiles at once (see §5 equivalence).

### 1.3 Tier 3 — adaptive mappings (each toggled by a parameter; ONE at a time)

Each mapping is a **parameter in itself**: enabled/disabled + its coefficients.
Added/validated one at a time; kept only if it survives out-of-sample.

| Mapping parameter | Driven variable → parameter | Example |
|---|---|---|
| `adaptive.spacing_vol` | ATR → C spacing | widen spacing when σ rises |
| `adaptive.targets_vol` | ATR → V | wider take-profits in high vol |
| `adaptive.sl_trend` | trend strength → SL | tighter stops in trends (or disarm) |
| `adaptive.q_drawdown` | drawdown → Q | reduce size after losses (risk-on/off) |
| `adaptive.q_liquidity` | book/volume profile → Q | more capital where volume/liquidity lives |
| `adaptive.onoff_regime` | range/trend classifier → grid on/off | grid only in range |
| `adaptive.r_fillrate` | R fill rate → R | widen R if it almost never triggers |

### 1.4 `allocation_map` — state→target table (a parameter object, with defaults)

The strategy's objective: **track a state-dependent target allocation.** The grid
is the controller; the *drift* (actual − target) is the error it corrects. State
signals are computed from past bars only (causal, no lookahead).

| State | Signal (default) | Target allocation (default, single-asset BTC) |
|---|---|---|
| `RANGE` | \|EMA slope\| small, ATR normal | `{BTC: 0.40, USDT: 0.60}` |
| `TREND_UP` | EMA slope strong positive | `{BTC: 0.00, USDT: 1.00}` (grid disarmed) |
| `TREND_DOWN` | EMA slope strongly negative | `{BTC: 0.00, USDT: 1.00}` (flat, disarmed) |

The target **binds inventory naturally**: if the drift pushes BTC allocation
above the target band, the grid stops buying or sells the excess — the clean
answer to "I bought and can't sell."

---

## 2. The three-tier discipline (about TUNING, not about parameterization)

Everything is a parameter. The tiers govern **how many you sweep at once**, not
whether they exist:

- **Tier 1 — structural:** defaults, rarely changed; never swept together
  (correlated effects, can't attribute).
- **Tier 2 — ladder shapes:** swept 2-3 at a time (C, V, R, SL, Q shapes).
- **Tier 3 — adaptive mappings:** ONE at a time, A/B against the static config.

Why: e022's best training config (+54.8%) failed OOS (−1.9%). More degrees of
freedom = more ability to fit noise. The tiers are the defense.

---

## 3. State vs time (guideline)

An adaptable parameter is a **function of measured state**, never of the
calendar:

- **Dependent on time (reject):** `spacing = f(date)`. No predictive content,
  100% overfittable.
- **Dependent on state (accept):** `spacing = f(ATR(14))`. The 14-bar window is
  the *measurement instrument*; the driver is the *measured value*. Volatility
  clusters (well-documented), so ATR predicts future ATR — that's why state
  generalizes.

A state is always computed from one or more past time windows (ATR(14), EMA 50,
24h realized vol) — the window is just the ruler, not the cause.

---

## 4. `q_rule` = the capital allocation curve

`q_rule` defines the **capital allocation curve**: the function mapping level
depth → capital of that level (how your money sits across the price axis).

- `equal`: flat curve
- `depth_scaled`: monotonic in depth (direction set by `q_depth_direction`)
- `volume_profile`: q ∝ where volume/liquidity actually trades → more capital
  where price spends time. Most advanced; can be weighted by market liquidity
  (book walls / imbalance from e021) via `adaptive.q_liquidity`.

---

## 5. Equivalence: "multiple trades at one price with different stops/volumes"

Opening N trades at price P — A: vol q_a, SL −50%; B: vol q_b, SL −30%; C: vol
q_c, SL −15% — is **mathematically identical** to splitting capital at P into N
lots with `SL = [50,30,15]` and `Q = [q_a,q_b,q_c]`. So:

- `SL` gives the **risk** (per-lot stop)
- `V` gives the **reward** (per-lot target)
- `Q` gives the **volume**
- all at the same entry price.

No fractional-exit machinery needed (`exit_model = lot-based`).

---

## 6. Success metrics

| Metric | What it measures | Role |
|---|---|---|
| Net PnL after fees | final result | ultimate criterion |
| Profit factor | gross win/loss | health |
| Max drawdown | risk | pain ceiling |
| **Rebalancing error** | distance to target allocation | north star (fidelity to setpoint) |
| **Time-in-inventory** | how long capital is stuck | grid death detector |

---

## 7. Phase plan

| Phase | Scope | Gate |
|---|---|---|
| **Fase 0** | This SPEC (all parameters + defaults) | user review |
| **Fase 1** | Bar-by-bar sim on real BTC (5m 1y + 1h 4y), static config, fixed fees | beat e022 v2: +3.6% (5m) / +1.7% (1h), DD < ~8% |
| **Fase 1b** | Tier-2 sweep, out-of-sample validation | robust, not just best-train |
| **Fase 2** | One adaptive mapping at a time, A/B | each survives OOS |
| **Fase 3** | Combine surviving mappings | net PnL + bounded rebalancing error |

Data: `../e022-nautilus-sr-grid/ag-01/data/real_btc_5m.csv` (1y) and
`real_btc_1h.csv` (4y). Live feeds later via `../e021-hyperliquid-playground/`.

---

## 8. Config shape (interface for the sim)

The sim takes a single JSON config; every value above maps to a key, e.g.:

```json
{
  "tier1": {
    "sides": "both_mirror",
    "anchor_mode": "rolling_high",
    "sl_anchor": "trailing_from_peak",
    "trail_dist_mode": "atr_mult", "trail_dist": 2.5,
    "exit_model": "lot-based",
    "ladder_exhaustion": "freeze",
    "pairing": "per_level",
    "q_rule": "equal", "q_depth_direction": "increasing",
    "maker_fee": 0.0002, "taker_fee": 0.0006,
    "min_order_notional": 1000, "max_exposure": 400000,
    "liquidation_margin_budget_mult": 4,
    "allocation_map": {
      "RANGE":       {"BTC": 0.40, "USDT": 0.60},
      "TREND_UP":    {"BTC": 0.00, "USDT": 1.00},
      "TREND_DOWN":  {"BTC": 0.00, "USDT": 1.00}
    }
  },
  "tier2": { "C": [0.5,1,2,3], "V": [1,1.5,2,2.5], "R": [0.75], "SL": [2,4], "Q": "equal" },
  "tier3": {
    "adaptive.spacing_vol": {"on": false, "atr_mult": 1.5},
    "adaptive.onoff_regime": {"on": false, "ema_fast": 50, "ema_slow": 100, "enter_pct": 1.0, "exit_pct": 0.5}
  }
}
```
