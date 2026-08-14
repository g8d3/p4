# Session Log — ag-04-monolith (Path B)

A/B test artifact. Recorded honestly.

## Run

- Start: 2026-08-13T16:31:24-05:00
- End: 2026-08-13T16:36:30-05:00
- Wall clock: ~5 min
- Shell commands run: 11
- Self-wakes / corrections: 0
  - The session was short enough to run synchronously in one window; the
    background + tmux self-wake pattern was not needed. No self-wake command
    fired.

## Environment

- System pandas 2.3.3, matplotlib 3.10.9, scipy 1.17.1 already installed — no
  venv needed. Input CSV (135,232 rows) fits easily in RAM.

## Problems encountered and how they were solved

1. **pandas 2.x removed `fisher` from `Series.kurt()`** → `TypeError:
   kurt() got an unexpected keyword argument 'fisher'`. Solved by computing
   skew/kurtosis with `scipy.stats.skew/kurtosis` (bias=False, fisher=False
   for classic kurtosis where normal = 3, matching the ag-02 spec's "> 3" rule).
2. **Boolean-mask reindex bug in the conditional section** — global signal
   masks (boolean Series indexed on the full DataFrame) were used to slice
   groupby subsets; pandas reindexed them and produced object-dtype masks,
   ending in a nonsensical `can only concatenate str` error inside a mean().
   Solved by computing the eight signal masks *inside each group* (per-group
   boolean columns), which are index-aligned by construction.
3. **Matplotlib Axes3D import warning** (harmless, multiple matplotlib installs
   on PATH) — ignored after confirming 2D plotting works.
4. **Model cannot view PNGs** (no image input in this session) — verified the
   5 charts via `file` (valid 990×550 PNGs) + non-empty byte sizes instead of
   visually.
5. **Synthetic v=0 backfill rows found** during data probing: ZEC 1d 999/1314
   rows, ZEC 1w 144/189, XMR 1d 999/1210 have v=0 pre-listing candles with
   synthetic prices. Kept per spec (Path A will see the same file), but ran a
   robustness pass excluding them: 1d kurtosis 12.8→10.7, p99.9 25.2→25.1 (no
   verdict change); and critically, the 1d vol_top10 "edge" collapses (MW p
   0.035 → 0.148) — downgraded to fragile/not tradeable in the report.
6. **Sample-size reality check** — most 1w (max n=190) and several 1d signals
   have n < 300, so p99 claims there are reported as "insufficient data", not
   results.

## Where context got heavy

- Not heavy. One analysis script (analyze.py) written once, two small bug
  fixes, two diagnostic passes. The conditional analysis produced 1,167 rows
  in cond_next.csv; interpreting the signal table needed one extra pass for
  downside-tail (p1/p0.1) directionality — that extra pass is what turned
  "edge" verdicts into the correct "volatility clustering, not direction"
  conclusion.
- What consumed context: the groupby/mask indexing subtlety (problem 2) and
  deciding how to handle the v=0 backfill honestly without breaking Path A
  output parity.

## Honest notes for comparison.md

- Command count is low (11) because the work was one self-contained script
  plus verification passes, no iterative debugging loop beyond two TypeErrors.
- No failed commands left running; no output was hand-patched — every number
  in report.md is from the script/JSON, not edited by hand.
- Deliverable parity caveat: `cond_next.csv` includes a pooled `coin=ALL`
  layer on top of the per-coin spec table (extra rows, same column schema) to
  power the significance check the spec asks for. If Path A emits only
  per-coin rows, the diff will show extra ALL rows on Path B's side.
