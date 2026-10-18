# Cache report — our own fleet (500 message samples, 2026-10-18)

Measured from the monitor's message samples (373 OK rows, 127 excluded as failed/replayed), window 2026-10-18 → 2026-10-18.

- **Cache-hit rate**: 99% [measured] over the 373 rows we can rate (99% over every row in the file, including the excluded ones)
- **Cached tokens per turn**: p50 212,608, mean 226,045 [measured]
- **Verdict**: not enough rows at the same context size to compare cache states; the overall figures below mix sizes and are not a separation test

## Method and limits

- Rows with `status: failed` or `streamed: false` are excluded: their durations are not
  generation time, and including them is how a cache table turns into a fake finding.
- Context size is bucketed to the nearest 8 KB and cache state is >50% of the context
  cached; both thresholds are stated parameters, not measurements, so you can re-run them
  differently. Every figure above comes from the sample file.
- We do **not** sell cache discipline. This page reports your rows; where they show no
  separating effect it says so, exactly as our own 500-turn sample did (paper §6).
