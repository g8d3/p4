# ag-03 session log (Path A, window 25-3)

## A/B test data

- **Start**: 2026-08-13T16:29:00-05:00
- **End**: 2026-08-13T16:35:10-05:00
- **Duration**: ~6 min
- **Command count**: 16 bash commands
- **Output files**: `cond_next.csv` (988 rows), `report.md`, `abs_next.csv`
  (auxiliary, |ret_next| vol-clustering evidence used by report.md)

## Steps

1. Read AGENTS.md (ag-03 + inherited e025, ag-02-dist, e000). Confirmed scope,
   derived column definitions (ret, range), deliverable schema, decision rules.
2. Verified input CSV (135,232 rows, 12 coins × 4 tf, 48 pairs, 0 gaps per
   manifest).
3. Wrote `bin/analyze_cond.py`: computes ret/range/σ per (coin,tf), 9 signals
   (4 extreme-move, 2 range-state, 1 volume, 2 streak), and for each signal
   the yes/no/base stats of ret[t+1] per (coin,tf) PLUS a pooled z-scored
   analysis with coin=ALL (per-tf) — needed because single-coin tail samples
   are below n=300. Adds MW-U p-value (yes vs no) and bootstrap p99 CI.
4. Launched analysis in background with self-wake (fundamentals pattern);
   ran ~60s, exit=0.
5. Interpreted results, generated aggregate summaries, wrote report.md.

## Problems hit + how solved

1. **Per-coin tail samples are tiny (n<300 for nearly every tail signal)** —
   the deliverable schema is per (coin,tf), but +3σ events on one coin/tf are
   ~30–50 samples and 1w groups often n≈0–26. Solving: added `coin=ALL`
   pooled rows (z-normalized per coin/tf, pooled per tf) to `cond_next.csv`
   and built all verdicts on those, treating per-coin rows as the raw table +
   caveats. This is the main structural decision of the experiment.
2. **RuntimeWarnings from numpy std on n=1 groups** (1w `-3σ`, `dn5`) —
   harmless (NaN for empty groups), noted; not fixed in code to keep stats
   honest (NaN = no data).
3. **Inspection pivot KeyError: 'base'** — my ad-hoc query filtered
   `group='base' AND signal='range_top1'`, but base rows are stored ONCE per
   (coin,tf) with `signal='base'` (the unconditional distribution is shared
   across signals). Solved by joining yes-rows against the `signal='base'`
   row. Cost 3 redundant pivot attempts.
4. **Python attribute syntax** `m.p99.9_next` → SyntaxError; fixed with
   bracket access `m['p99.9_next']`.
5. **NaN medians** in per-coin aggregates because empty yes-groups produce
   NaN p99.9; fixed with `np.nanmedian`.

## Context consumed

- Reading 3 inherited AGENTS.md files (e000 is large — 1 read of ~880 lines).
- Two full inspection passes over `cond_next.csv` (pooled rows + per-coin
  24-row join) plus three aggregate summaries to build report numbers.
- The pivot debugging detour (#3) cost ~3 extra commands; everything else was
  on the critical path.

## Verdict summary (full detail in report.md)

- Extreme prev move (±2σ/±3σ): no directional edge; vol clusters (p99 1.5–2.2×).
- Volatility state (range top decile/pct): vol clustering is real and strong
  (stdev_next 1.5–2.5×, p99 1.9–2.7×).
- Volume spike: same effect, weaker proxy.
- 5-candle streaks: insufficient data / no robust edge.
- Overall: **no predictable directional edge, but vol clusters** — clean
  result pointing strategy toward range/vol work, not directional tails.
