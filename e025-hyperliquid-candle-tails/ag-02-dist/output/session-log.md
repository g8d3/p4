# ag-02 session log — distribution analysis

## Timeline

| Event | Timestamp (UTC) |
|---|---|
| Session start | 2026-08-13T21:31:00Z |
| Input verified (candles_raw.csv, 135,232 rows, 12 coins × 4 tf) | 2026-08-13T21:32:00Z |
| Data-quality probe (v=0 synthetic backfill) | 2026-08-13T21:32:30Z |
| Analysis script written (`bin/analysis.py`) | 2026-08-13T21:33:00Z |
| Analysis run (background, PID=146337) | 2026-08-13T21:33:10Z |
| Outputs verified (stats.csv, 4× hist_*.csv, 5× charts, report.md) | 2026-08-13T21:34:00Z |
| Session end | 2026-08-13T21:35:00Z |

## Command count

- Foreground reads/probes: 4
- Background analysis run: 1
- Verification commands: 4

Total shell commands: ~9 (all short, none blocked; the analysis itself ran
backgrounded with `timeout 600` + self-wake per fundamentals).

## Problems hit + how solved

1. **Synthetic pre-listing candles (v=0).** Manifest flagged `v0_count` for
   1d/1w series — e.g. ZEC 1d is 999/1315 synthetic, XMR 1d 999/1210, ZEC 1w
   144/190. These rows have plausible-looking but zero-volume prices (synthetic
   backfill before listing). Computing returns on them would inject fake moves
   into the tail analysis — the exact thing ag-02 measures.
   **Solved**: dropped all `v==0` rows (3,175) before computing `ret`; returns
   computed on 132,009 rows. Documented the drop in report.md. Alternative
   considered: keeping them and annotating — rejected, since "don't silently
   treat a missing candle as a zero-move candle" and these are non-traded
   prices.
   **Context consumed**: one extra probe (ZEC 1d head/tail + uniqueness check)
   to confirm v=0 rows were synthetic rather than genuine flat candles.

2. **Histogram bin width vs outlier range.** Naive equal-width bins over
   `[min,max]` for 1w (max=+115%, min=-47%) would center far from 0 and
   squander bins on one tail.
   **Solved**: symmetric bins `[-max|min|max|, +max|min|max|]` (60 bins,
   0-centered) — verified each `hist_<tf>.csv` is symmetric around 0 and bin
   counts sum to the per-tf n.

3. **Cross-tf comparison scale.** 5m returns (σ≈0.2%) and 1w returns
   (σ≈12.7%) are incomparable on one axis.
   **Solved**: per analysis rules, normalized to z-scores per `(coin,tf)`
   before pooling for the overlay chart (`overlay_tails.png`); per-tf
   histograms stay raw. No timeframes pooled in any histogram.

4. **Kurtosis convention ambiguity.** Report says "kurtosis > 3" (Pearson
   raw); pandas `.kurt()` returns Fisher excess (normal = 0).
   **Solved**: added 3.0 to convert to raw kurtosis; report states the
   convention explicitly (normal = 3).

5. **Minor**: matplotlib printed an `Axes3D` import warning (unused); verified
   all PNGs are valid 1400×700 RGBA with PIL. This model cannot read images,
   so chart verification used PIL size/mode + non-trivial byte counts instead
   of visual inspection.

## Context consumed

- Full read of e000-fundamentals AGENTS.md (long, ~880 lines) — needed for
  command rules.
- e025 + ag-02 AGENTS.md (in system prompt).
- ag-01 manifest.json (517 lines) — needed to interpret v=0 flags and gaps.
- No web/API calls. No retries needed.

## Headline stats (for done.txt)

- n per tf (returns): 5m=60,277, 1h=60,014, 1d=10,250, 1w=1,468
- Raw kurtosis (pooled): 5m=9.27, 1h=10.11, 1d=13.79, 1w=10.59 (all >> 3 → fat-tailed everywhere)
- p99.9 in σ units: 5m=4.95, 1h=5.49, 1d=4.96, 1w=6.71 (all > 4σ → beyond normal ~3.09σ)
- Per-coin extremes: XRP 1d kurtosis=72.5 (max=+74.6%), ZEC 1h p99.9=8.76%, CRV 1w p99.9=106.9%
