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

All references below are for the **long** mirror; the short side is identical
with sell/buy swapped (mirror mode).

---

## 1. Parameter families

### Ladders (Tier 2 — swept a few at a time)

| Family | Meaning | Default (to tune, NOT validated) |
|---|---|---|
| `C = [c₁…cₙ]` | Buy depth ladder: each order fills when price drops cᵢ % below its reference | `[0.5, 1.0, 2.0, 3.0]` |
| `V = [v₁…vₙ]` | Take-profit ladder: each lot exits at +vᵢ % above its own buy | `[1.0]` per lot (see pairing TODO) |
| `R = [r₁…rₘ]` | Rebuy ladder: after a sell, capital re-enters at −rᵢ % below the sell price | `[0.75]` |
| `SL = [s₁…sₖ]` | Stop-loss ladder: each lot has its own stop depth (`exit_model = lot-based`) | `[2.0, 4.0]` |
| `Q = [q₁…qₙ]` | Volume per level (fraction of budget or USD) | `equal` |

Every level is a **lot** = a triple `(q_i, s_i, v_i)` — its own volume, stop, and
target → its own reward:risk `R:R = v_i / s_i`. This is what lets one entry carry
several risk-reward profiles: it **already is** the "open several trades at the
same price with different stops and different volumes" the user described (see
§4 equivalence).

### Anchors & trailing (Tier 1 — structural)

| Param | Options | Decision |
|---|---|---|
| `anchor_mode` | `activation_price` \| `rolling_high` \| `last_fill` | **TODO-1** (default `rolling_high`) |
| `sl_anchor` | `fixed_from_buy` \| `trailing_from_peak` | **TODO-2** (default `trailing_from_peak`) |
| `trail_dist_mode` | `none` \| `pct` \| `atr_mult` | **TODO-3** (default `atr_mult`) |
| `trail_dist` | value (pct or ×ATR) | sweep later |
| `exit_model` | `lot-based` (recommended) \| `fractional` | **TODO-4** (recommend `lot-based`) |

### Sides & structure (Tier 1)

| Param | Options | Decision |
|---|---|---|
| `sides` | `long` \| `short` \| `both_mirror` | **chosen: `both_mirror`** |
| `anchor_mode` for short | mirror (same params, swapped) | as above |
| `max_buy_depth` / max lots | exposure cap | sweep later |
| ladder exhaustion (`price < last cₙ`, no sells) | `extend` \| `freeze` \| `stop_grid` | **TODO-5** (default `freeze` + allocation target reduces) |

### Allocation targets (Tier 1 — the "success" layer)

The strategy's objective: **track a state-dependent target allocation.** The
grid is the controller; the *drift* (actual − target) is the error it corrects.

| State (measured) | Signal | Target allocation (example, single-asset BTC) |
|---|---|---|
| `RANGE` | \|EMA slope\| small, ATR normal | 40% BTC / 60% USDT |
| `TREND_UP` | EMA slope strong | 0% BTC / 100% USDT (grid disarmed) — or buy-ahead shorts |
| `TREND_DOWN` | EMA slope strongly negative | 0% BTC / 100% USDT (flat, disarmed) |

- **State** = a function of past bars only (EMA slope, ATR percentile, spread).
  Causal; no lookahead.
- The target **binds inventory naturally**: if the drift pushes BTC allocation
  above the target band, the grid stops buying or sells the excess — this is the
  clean answer to "I bought and can't sell."
- Exact state definitions + target bands: **TODO-6**.

### Execution / risk (Tier 1)

| Param | Notes |
|---|---|
| `maker_fee`, `taker_fee` | e022 convention: 0.02% maker, 0.06% taker; verify maker ratio |
| `min_order_notional` | avoid micro-fills (e022 used 1000 USDT) |
| `max_exposure` | notional cap, enforced with reduce-only flatten |
| `liquidation_model` | force-flatten when unrealized loss > threshold (e022) |

---

## 2. The three-tier parameter discipline

- **Tier 1 — structural:** decided by design once (`sides`, `anchor_mode`,
  `exit_model`, `q_rule`, allocation targets). Not swept.
- **Tier 2 — ladder shapes:** swept 2-3 at a time (C, V, R, SL, Q shapes).
- **Tier 3 — adaptive mappings:** added ONE at a time, A/B against the static
  version, kept only if it survives out-of-sample.

Why: e022's best training config (+54.8%) failed OOS (−1.9%). More degrees of
freedom = more ability to fit noise. The tiers are the defense.

---

## 3. State vs time (guideline)

An adaptable parameter is a **function of measured state**, never of the
calendar:

- **Dependent on time (reject):** `spacing = f(date)`. Two identical days give
  different values only because they're different days. No predictive content,
  100% overfittable.
- **Dependent on state (accept):** `spacing = f(ATR(14))`. The 14-bar window is
  the *measurement instrument*; the driver is the *measured value*. Two equal
  ATRs give equal spacing regardless of when. Volatility clusters
  (well-documented), so ATR predicts future ATR — that's why state generalizes.

A state is always computed from one or more past time windows (ATR(14), EMA 50,
24h realized vol) — the window is just the ruler, not the cause.

---

## 4. Equivalence: "multiple trades at one price with different stops/volumes"

Opening N trades at price P — A: vol q_a, SL −50%; B: vol q_b, SL −30%; C: vol
q_c, SL −15% — is **mathematically identical** to splitting capital at P into N
lots with `SL = [50,30,15]` and `Q = [q_a,q_b,q_c]`. So:

- `SL` gives the **risk** (per-lot stop)
- `V` gives the **reward** (per-lot target)
- `Q` gives the **volume**
- all at the same entry price.

No fractional-exit machinery needed. `q_rule` defines the **capital allocation
curve** (how money sits across price levels); the market-liquidity-weighted
variant (volume profile, book walls from e021) is the most advanced form.

---

## 5. Success metrics

| Metric | What it measures | Role |
|---|---|---|
| Net PnL after fees | final result | ultimate criterion |
| Profit factor | gross win/loss | health |
| Max drawdown | risk | pain ceiling |
| **Rebalancing error** | distance to target allocation | north star (fidelity to setpoint) |
| **Time-in-inventory** | how long capital is stuck | grid death detector |

---

## 6. Open decisions (TODOs — user to resolve)

- **TODO-1** `anchor_mode`: `activation_price` / `rolling_high` / `last_fill`
  (default `rolling_high`)
- **TODO-2** `sl_anchor`: `fixed_from_buy` / `trailing_from_peak`
  (default `trailing_from_peak`)
- **TODO-3** `trail_dist_mode`: `none` / `pct` / `atr_mult` (default `atr_mult`)
- **TODO-4** `exit_model`: `lot-based` (recommended) / `fractional`
- **TODO-5** ladder exhaustion policy: `extend` / `freeze` / `stop_grid`
  (default `freeze` + allocation target reduces)
- **TODO-6** exact state definitions + target allocation bands (the state→target
  table above is an example, not final)
- **TODO-7** `pairing`: does lot i use only vᵢ (per-level V), or one shared V?
- **TODO-8** `q_rule` concrete: `equal` / `depth_scaled` (and which direction) /
  `volume_profile`

---

## 7. Phase plan

| Phase | Scope | Gate |
|---|---|---|
| **Fase 0** | This SPEC + resolved TODOs | user review |
| **Fase 1** | Bar-by-bar sim on real BTC (5m 1y + 1h 4y), static config, fixed fees | beat e022 v2: +3.6% (5m) / +1.7% (1h), DD < ~8% |
| **Fase 1b** | Tier-2 sweep, out-of-sample validation | robust, not just best-train |
| **Fase 2** | One adaptive mapping at a time, A/B | each survives OOS |
| **Fase 3** | Combine surviving mappings | net PnL + bounded rebalancing error |

Data: `../e022-nautilus-sr-grid/ag-01/data/real_btc_5m.csv` (1y) and
`real_btc_1h.csv` (4y). Live feeds later via `../e021-hyperliquid-playground/`.
