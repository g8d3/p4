# session-log — ag-07 event study

## Start

2026-08-14 ~06:43 UTC (opencode, opencode-go/deepseek-v4-flash, window 25-7)

## Pre-declared test grid (declared before computing, per e025 rules)

- Feature build: `ret`, `range`, `body`, `sigma` (global stdev), `rolsig`
  (rolling-20 stdev, valid ≥50 obs), `vol_pct`, `hour`.
- Events: `|ret| > 3 × sigma`, side = sign. Pivot window N=5, confirmed at +5.
  `dist_high/dist_low` = (close − last confirmed pivot) / rolsig.
- Outcomes: cumulative return +1/+3/+5/+10, full +1..+10 path, MAE/MFE over
  next 10 candles.
- Splits for Q4: extension (ext/mid/con), volume (p90+ vs <p90), regime
  (rolsig ≥ median vs <), hour (4 blocks of 6h UTC). n≥50 per subgroup.
- Q3 clustering: inter-event intervals vs geometric(p) null, per (coin,tf).
- Q6: per-coin sign replication + first/second-half replication, per (side,tf).

## Commands run

1. `ls` / `wc -l` on `../ag-01-data/output/candles_raw.csv` (135,232 lines incl. header).
2. Python inline: inspected manifest.json (12 coins, 4 tfs, retention windows).
3. Python inline: row counts per (coin,tf), dupe check (0 dupes), v=0 count (3,175).
4. `python3 bin/analyze.py` (write script) — first run FAILED:
   `ValueError: min_periods 50 must be <= window 20` on `rolling(20, min_periods=50)`.
   Fixed by `rolling(20, min_periods=20)` + masking the first 50 observations of
   each series (keeps the AGENTS.md intent: 20-period stdev, usable only after
   50 obs).
5. Second run FAILED later: `KeyError: 't'` — the events table didn't carry the
   global index column used for interval computation. Added `t` to the events
   output columns.
6. Third run — SUCCESS. 2,139 events detected; all CSVs written.
7. Inspection run (inline): event-vs-unconditional baselines (up/down/all
   candles mean cum5 per tf, event magnitude per side).
8. Re-run `analyze.py` after clipping `dist_high/dist_low` to ±20σ and adding
   `context.csv`. SUCCESS.
9. `python3 bin/charts.py` — SUCCESS, 8 PNGs. Only warning: unrelated
   matplotlib Axes3D import warning (system has duplicate matplotlib).
10. `file` on the 8 PNGs to confirm they are valid images.

Command count: ~10 bash invocations (several of them one-shot inline python).

## Problems hit and solutions

- **`min_periods > window` (pandas)**: pandas forbids `min_periods` greater
  than the rolling window. AGENTS.md wanted a 20-period stdev "min 50 obs".
  Solved with `rolling(20).std()` and masking `cumcount < 50` → exactly the
  documented semantics.
- **Missing `t` for clustering**: the inter-event interval needs the position
  of each event within its (coin,tf) series; the events CSV initially lacked
  it. Added a global per-series index column to the events output.
- **`dist` unbounded**: `dist_high/dist_low` divide by `rolsig`, which can
  approach 0 in dead-quiet markets → values of 5,000+σ (nonsense). Because the
  ext/mid/con buckets depend only on the ±1 boundary, clipped the values to
  ±20σ for reporting. Bucket labels provably unchanged. Documented in report.
  (First version of the distribution table had p99 = 2004–7181σ — the fix made
  it 20σ and the medians sane.)
- **Stray output file**: accidentally wrote `extension.csv.tmp.csv` (dead
  variable in an early draft); removed it and pointed the final write at the
  right path.
- Charts: attempted to visualize-verify PNGs, but this model has no image input
  support — verified instead via `file` (valid PNG, correct dimensions) and by
  reviewing the plotting logic against the CSVs. Noted as a limitation.

## Anything that consumed context

- The inherited AGENTS.md stack (fundamentals + e025 + ag-02/ag-03/ag-05) is
  large; the ag-05 analyze.py was read to match code conventions.
- Re-reading and re-printing split/clustering tables to phrase the report with
  exact numbers (several inline python calls).

## Notes on data

- 5m/1h are API-retention snapshots (~17 days / ~7 months). All 5m/1h claims
  apply to that single recent window, not multi-year history.
- 1w (22 events) and 1d down/low-volume cells (n<50) excluded from claims per
  the n≥50 rule; called out in the report.
- Coins are correlated — pooled events are not 12× independent; per-coin
  replication rates reported instead.

## End

2026-08-14 ~06:55 UTC. All deliverables present: events.csv, event_paths.csv,
extension.csv, clustering.csv, splits.csv, mae_mfe.csv, replication.csv,
context.csv, 8 charts, report.md, beginners_guide.md, session-log.md.
