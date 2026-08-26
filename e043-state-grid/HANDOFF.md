# e043 — HANDOFF (session handoff for a FRESH agent)

Read this file instead of the chat history. It contains everything a new
agent needs to continue autonomously. If the user just says "continue", after
AGENTS.md read THIS FILE next. Follow AGENTS.md + e000-fundamentals
(timeouts, quiet machine, kill by PID, notify on completion, commit every
meaningful step).

## MISSION

Find a fee-aware, out-of-sample-validated edge in the grid/ladder family
(course material in parallel). Two non-negotiable rules from our own history:
(1) every claim gets an OOS check (60/40); (2) fees charged in every test.
The user's stated deeper goal: an AUTONOMOUS system that keeps screening and
testing candidate strategies (intuition engine = screen.py + BASE_RATES).

## WHERE WE ARE (2026-08-26) — current truth

We are inside NAUTILUS_A_PLAN.md (A/B protocol on e022's real Nautilus
harness, copy-then-improve, one change at a time). Progress:

- **Test 0 baseline parity: DONE, exact.** e022 v2: 5m +3.6449% / DD −7.1628 /
  PF 1.1386 (2,158 fills, fees 2,392.78); 1h +1.7133% / −7.5511 / 1.0418
  (1,103 fills, 1,974.96). Doc: output/nautilus_a/baseline_parity.md.
  **Correction captured**: e022 baselines actually use trend EMA 50/100,
  enter 1.0 / exit 0.5 (not 20/100/0.5/0.2 as the old plan table said) and
  1h uses --max-exposure-mult 4.0 ("cap 4x").
- **Test 1 (flatten maker vs taker): KEPT.** Config `flatten_mode=limit_first`,
  `--flatten-limit-offset-pct 0.05 --flatten-fallback-bars 3`. 5m +4.18%
  (fees −10%), 1h +3.29% (fees −38.6%); OOS better in 4/4 splits. Variant
  "far-grid limit" rejected (1h −13.8%). Doc: test1_flatten_maker.md.
  KEY LESSON: Nautilus executes marketable-side limits as TAKER (my first
  sign was wrong); maker limits must sit on the NON-marketable side.
- **Test 2 (regime enter threshold): KEPT per dataset.** 5m enter **0.8**
  (full +5.53%, OOS better both splits), 1h enter **1.5** (full +7.23%,
  OOS better return, DD deeper ~1.1pp = KEEP-CONDITIONAL flagged). Screen C
  predicted 1.5; engine chose 0.8 on 5m → rule 5: screens filter, engines
  decide, OOS certifies. Doc: test2_regime_stricter.md.
- **Stack T1+T2 (the current base for everything forward)**: 5m **+7.0705%** /
  DD −5.5684 / PF 1.2526 / fees 2,315.48; 1h **+8.4057%** / DD −7.7290 /
  PF 1.2013 / fees 1,191.11. Exact commands at bottom.
- **Test 3 (user features): Feature 1 (R-recycle) IN PROGRESS, PAUSED.**
  - Code: sr_grid_strategy_user.py has `recycle_enabled`/`recycle_pct` flags.
  - Interpretation 1 (re-arm SAME side after R% retrace): REJECTED —
    starves the sell side, grid breaks (5m −2.37%, 77 fills vs 2,315).
  - Interpretation 2 (freed capital feeds OPPOSITE side only after price
    moves R% in its favor): VERDICT BLOCKED — bookkeeping leak.
  - THE BLOCKER (fix before any rerun): `_rebalance_grid` computes
    total_budget from grid_budget + _unallocated + _pending_redistribute but
    is BLIND to `_recycle_queue` (the freed capital in the queue is
    invisible) → each rebalance re-arms a smaller grid; v2's
    `on_order_rejected` also never refunds `reserved` into `_unallocated`
    (pre-existing, never fired before because freed capital always flowed
    through `pending`). Symptom: fills collapse 2,315 → 78-110 in ALL
    recycle runs; 1h R=1.5% +9.46%/DD −4.95 is NOT evidence (lottery
    artifact, PF-rule 5b). Full doc:
    output/nautilus_a/test3_r_recycle_paused.md.
- **Intuition engine (from the "no intuition" conversation)**: 
  - `ag-01/bin/screen.py` — 3 cheap causal screens: A entry win rate
    (e.g. none of the simple (C,V,SL) bands clears fees on BTC), B fee
    breakeven, C regime churn (recursive EMA; regime is STICKY: 76-103 bars,
    P(flip ≤5 bars) ≈ 0 — the Fase-2 "flapping leak" was engine-EMA noise).
  - `BASE_RATES.md` — prior table + rules 1-6 + "WHO PAYS?" per idea.
    Rule 6: regime thresholds are dataset-specific (0.8 5m / 1.5 1h).
  - `SOLO_PROTOCOL.md` — candidate card + data-source card (data choice also
    needs a falsifier → breaks the "choosing data needs intuition" loop);
    rule 5b: verdicts on %-based metrics (return %, max DD, return/MaxDD),
    PF is informational only.
  - `output/nautilus_a/GLOSARIO.md` — one-page plain-language glossary
    (SPANISH, user-facing), plus benchmarks.md (B&H 5m −44% / 1h +181%,
    DCA, T-bills) — the honest context for all returns.

## NEXT STEP — ordered, when the user says "continue"

1. **Fix the R-recycle bookkeeping** (sr_grid_strategy_user.py or a new
   patched path — never touch v2):
   a. `_flush_recycle` or `_rebalance_grid`: count sum(_recycle_queue)
      amounts as part of the rebalance budget so the free cash math stays
      consistent (deposit released items into `_unallocated` or
      `_pending_redistribute` only once; do not double count).
   b. `on_order_rejected`: refund `lv.reserved` into `_unallocated`.
   c. Add `n_rejections` counter to metrics.
2. **Diagnostic + rerun A/B interpretation 2** with R ∈ {0.5, 1.5} × {5m, 1h}
   (4 runs, ~1 min each; reuse the stack commands + `--recycle-enabled`).
   Verdict rules: return % + DD not worse than stack (5m +7.07/−5.57,
   1h +8.41/−7.73) AND fills NOT collapsed (<500 is suspicious again) AND
   OOS 60/40 if it looks good. Then update BASE_RATES + one course lesson.
3. **Test 3 remaining features** (one at a time, candidate card + screen
   before engine):
   - **Q multi-volume** (depth_scaled Q): screen prior LOW (sizing-only);
     one A/B then likely reject-documented.
   - **SL/V per-lot ladders** (each level own target/stop): screen prior LOW
     (no flat band clears fees), but ladder-over-grid is different geometry —
     one A/B to confirm/disprove.
   - **State allocation targets** (side multipliers per regime): HIGHEST
     prior of the four (regime disarming already helped in Test 2) — do this
     one if time only allows one.
4. After Test 3: reopen the idea of the slow state layer (funding rate from
   Hyperliquid is free NOW; falsifier card first), since valuation-style /
   opinion data (user's ask: P/E P/S PEG comps → mapped: fee revenue, miner
   revenue, MVRV) belongs to the SLOW regime/allocation layer, not entries.

## Exact stack commands (the base to beat / to build on)

```bash
# 5m stack (T1+T2):
python3 e043-state-grid/ag-01/bin/run_backtest_user.py --strategy user \
  --data ../e022-nautilus-sr-grid/ag-01/data/real_btc_5m.csv \
  --out-dir output/nautilus_a/t12_5m \
  --atr-mult 2.5 --max-levels 2 --min-order 1000 --trend-fast 50 --trend-slow 100 \
  --trend-enter 0.8 --trend-exit 0.5 --rebalance 192 \
  --flatten-mode limit_first --flatten-limit-offset-pct 0.05 --flatten-fallback-bars 3
# 1h stack: --data real_btc_1h.csv --trend-enter 1.5 --max-exposure-mult 4.0
# parity/screens quick check:
python3 e043-state-grid/ag-01/bin/screen.py --data <csv> --n-bars-per-year <105120|8760>
```

## Core numbers you must compare against

- Benchmarks: B&H 5m-yr **−44.0%** (grid +7.07 after stack), B&H 4y **+181%**,
  DCA30 4y +47.5%, T-bills ≈4-5%/yr. The 1h stack (+8.41%) is near T-bills(4y
  ≈+17-20%) but NOT above buy-hold — still a thin validated edge, no
  money-printer (Level 2 in SOLO_PROTOCOL, not Level 3).
- Never trust: PF alone (rule 5b), low-fill results (<500 fills year-should
  flag; <200 impossible to judge), same-idea reruns until verdict.

## DO NOT REDO (reject log, append even during pauses)

- same-side-only R-recycle (starves one side) — interpretation 1 data above.
- "marketable-side limits are maker" — they are TAKER in Nautilus matcher.
- Blaming harness for thin-family results — we reproduced e022 exactly
  (Test 0) and our stack is +7.1/+8.4 on the same engine.
- Unbounded sweeps; anchor_mode=activation_price without re-anchoring;
  cold-start causal EMA (use recursive ewm); PF as decisive metric.

## FILES MAP (updated)

| File | What it is |
|---|---|
| `NAUTILUS_A_PLAN.md` | Protocol + tests 1-3 definitions (baseline table needs the Test-0 corrections) |
| `SOLO_PROTOCOL.md` | Method: candidate card, data-source card, 7 rules + 5b |
| `COURSE_NOTES.md`, `SPEC.md` | Course + full parameterized design |
| `ag-01/bin/screen.py` | The 3 cheap causal screens (A/B/C) — run before any new idea |
| `ag-01/bin/run_backtest_user.py` | e022 runner copy + user strategy flags |
| `../e022-nautilus-sr-grid/ag-01/bin/sr_grid_strategy_user.py` | v2 subclass: flatten limit_first + recycle flag (v2 untouched) |
| `ag-01/output/nautilus_a/` | baseline_parity, benchmarks, test1/2 docs, test3_r_recycle_paused, BASE_RATES.md, GLOSARIO.md, all runs |
| `../e022-nautilus-sr-grid/ag-01/bin/run_backtest.py` (v2 harness) | untouched engine; only the user subclass was added next to it |

## GUARDRAILS

- Quiet machine for big runs; runs are ~10 s each — never parallelize more
  than 1-2 jobs; timeout-wrap everything; kill by PID.
- Commit after every meaningful step (`e043: ...`); notify done/error with
  `../e000-fundamentals/bin/notify.sh <done|error|info> "message"` (takes TWO
  args: level first).
- Night quiet: 21:00-10:00 — no heavy jobs, commit + notify + stop.
