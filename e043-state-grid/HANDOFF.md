# e043 — HANDOFF (session handoff for a FRESH agent)

Read this file instead of the chat history. It contains everything a new agent
needs to continue autonomously without talking to the user. Follow Conventional
**AGENTS.md** + **e000-fundamentals** (timeouts, quiet machine, kill by PID,
notify on completion).

## MISSION

Find a **statistically validated edge** in crypto (fee-aware, maker/taker
charged, out-of-sample checked) for a grid/ladder strategy family — and in
parallel, build the **trading course content** explaining everything in plain
language for a beginner. The course is as valuable as the edge.

Two rules that are NOT negotiable (proven by our own history):
1. Every claim needs an **out-of-sample check** (60/40 split). We caught our
   own fake +0.93% edge that was a cold-EMA bug.
2. **Fees are charged in every test** (maker 0.02%, taker 0.06%). A strategy
   that wins before fees and loses after is not a strategy.

## WHERE WE ARE (date 2026-08) — one paragraph each

- **SPEC (done)**: `SPEC.md` — full parameterized design of the user's ladder
  grid: four ladders C (buy depth) / V (take-profit) / R (rebuy) / SL (stop),
  per-level volume Q, long+short mirror, state allocation targets
  (allocation_map), dynamic trailing stop, three-tier parameter discipline.
  Everything is a runtime parameter with a default. NOTHING is hardcoded.
- **Fase 1 (done, honest NEGATIVE)**: `ag-01/bin/sim.py` + `sweep.py` — the
  one-sided %-ladder "buy C% dip below rolling high, exit +V%, stop −SL%,
  rebuy on −R% after win" is **structurally negative** on real BTC (1h 4y and
  5m 1y). Best ≈ breakeven while doing almost nothing. Bottleneck: entry win
  rate ~20–42% (needed ~50–67%). Not a tuning problem → see FASE1_FINDINGS.md.
- **Fase 2 (done, honest NEGATIVE)**: `ag-01/bin/range_grid.py` (standalone
  port of e022 v2 two-sided ATR grid) + sweeps. Makes money on synthetic
  range (gross), loses on real BTC. The e022-published edge (+3.6% 5m / +1.7%
  1h) does NOT reproduce in a simplified harness — it only lives in e022's
  exact Nautilus engine, and is thin even there (PF 1.04–1.14). Quantified
  leak found: taker-flatten churn from regime flapping (FLAT fees ~2× GRID
  fees). See FASE2_FINDINGS.md.
- **Levers tested (mixed)**: flatten threshold 1h −4.9→−2.2% (helps, not
  enough); entry confirmation "buy only above fast EMA" FAILED (win rate
  39→17%); stricter regime filter = dominant control.
- **Visualizer (done, course artifact)**: `ag-01/bin/backtest_viz.py` →
  `output/viz_*.html` — 4 self-contained mobile-first pages, each explaining
  in plain language: what the plan does (plan.json card: one-liner, "how it
  works" analogy, 3-column params table Setting→Plain words→Why), verdict,
  equity, price+fills, trades with fee-inclusive PnL $/%/log%, running PF,
  demoted-PF explainer with expectancy & log returns, glossary.
- **Decision taken (NEXT STEP, committed)**: `NAUTILUS_A_PLAN.md` —
  layer the user's features on e022's REAL Nautilus harness
  (`../e022-nautilus-sr-grid/ag-01/bin/run_backtest.py --strategy v2`).
  Protocol: copy-then-improve, ONE change at a time, OOS per change.
  3 tests: (1) flatten-maker vs taker, (2) stricter weather check,
  (3) user features (R-recycle depth, Q multi-volume, SL/V per-lot ladders,
  state allocation targets). Deliverables in output/nautilus_a/ + one course
  lesson each.

## DO NOT REDO (reject log — proven failures)

- ❌ More parameter sweeping on the one-sided ladder — the family is
  structurally negative; the entry (win rate) is the bottleneck.
- ❌ Blaming standard-ish backtest harnesses for thin-family results — verify
  against e022's Nautilus harness before claiming parity.
- ❌ `anchor_mode = activation_price` without re-anchoring — unusable on long
  multi-x datasets (−17,000%, infinite re-churn).
- ❌ Cold-start-EMA bugs: regime EMA must be computed causally (raw windowed
  cold-start EMA mislabeled early bars as RANGE and faked +0.93%). Use
  precomputed causal arrays (see run_grid.py: ema_window_series).
- ❌ Unbounded searches: every campaign declares a config budget + stopping
  rule BEFORE running.

## Key numbers to re-verify before trusting anything

- e022 v2 baseline: 5m +3.65% / DD −7.16% / PF 1.14; 1h +1.71% / DD −7.55% /
  PF 1.04. Configs: 5m atr 2.5 lv 2 reb 192 trend 50/100; 1h reb 96 cap 4×
  trend 20/100.
- Our best honest results: ladder ≈ breakeven-without-trading; two-sided grid
  best 1h −0.01% (PF 1.00), 5m −3.1%..−4.4%. All after fees, real BTC.
- Fees example: 5m ladder default = 18–20k fills → $15k+ fees on $100k.

## COURSE NOTES (already committed — keep extending)

`COURSE_NOTES.md` (plain glossary + 4 lessons), `SOLO_PROTOCOL.md` (method:
hypothesis card, 7 rules, reject log, falsifier habit), `SPEC.md`, the 4 viz
pages. NEW findings must be added in the same plain-language style.

## FILES MAP

| File | What it is |
|---|---|
| `SPEC.md` | The parameterized design (all params + defaults + config JSON shape) |
| `NAUTILUS_A_PLAN.md` | The committed next step (3 A/B tests, protocol) |
| `SOLO_PROTOCOL.md` | Method for solo strategy work (course + governance) |
| `COURSE_NOTES.md` | Plain-language course content |
| `ag-01/bin/sim.py` | One-sided %-ladder simulator (working, verified) |
| `ag-01/bin/sweep.py` | Ladder Tier-2 sweeper |
| `ag-01/bin/range_grid.py` | Two-sided ATR grid port (working, verified) |
| `ag-01/bin/run_grid.py`, `sweep_grid.py` | Grid driver + sweeper (causal precomputed EMA/ATR) |
| `ag-01/bin/backtest_viz.py` | Educational HTML generator (plan.json aware) |
| `ag-01/output/` | metrics.json / fills / equity / viz html / FASE1+2 findings |
| `data/` inputs | `../e022-nautilus-sr-grid/ag-01/data/real_btc_5m.csv`, `real_btc_1h.csv`, `synthetic_5m_range.csv` |

## GUARDRAILS (re-read e000-fundamentals)

- Quiet machine: check `uptime`/`free -h` before heavy work; batch, don't
  parallelize; Nautilus runs are ~4s each — run them one at a time.
- Every command: timeout wrapped. Kill by PID, never pkill.
- Commit after each meaningful step (`e043: ...`). Notify on completion
  (`e000-fundamentals/bin/notify.sh`).
- If a decision is needed that you cannot make: `notify.sh ... --ask` with
  evidence, then stop and wait.