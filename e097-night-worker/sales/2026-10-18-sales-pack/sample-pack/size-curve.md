# Size curve — overhead against carried context

From 362 ratable message samples, bucketed to the nearest 8 KB.
**Ranges, not a slope.** We tried to fit a size coefficient of our own and it did not
reproduce (paper §8), so this page reports what your sizes do and stops there.

| context size | rows | wall p50 | wall p90 |
|---|---|---|---|
| ~8 KB | 3 | 0.45 s | 0.77 s |
| ~16 KB | 1 | 4.62 s | 4.62 s |
| ~24 KB | 2 | 0.72 s | 1.05 s |
| ~32 KB | 2 | 0.47 s | 0.63 s |
| ~48 KB | 2 | 0.42 s | 0.48 s |
| ~64 KB | 1 | 0.35 s | 0.35 s |
| ~72 KB | 6 | 1.88 s | 2.80 s |
| ~80 KB | 6 | 3.86 s | 7.24 s |
| ~88 KB | 14 | 2.08 s | 9.10 s |
| ~96 KB | 11 | 1.88 s | 8.45 s |
| ~104 KB | 14 | 2.28 s | 3.44 s |
| ~112 KB | 12 | 2.09 s | 8.86 s |
| ~120 KB | 14 | 4.62 s | 18.56 s |
| ~128 KB | 12 | 4.38 s | 20.48 s |
| ~136 KB | 18 | 2.81 s | 10.86 s |
| ~144 KB | 13 | 2.67 s | 11.78 s |
| ~152 KB | 16 | 2.67 s | 31.52 s |
| ~160 KB | 12 | 3.78 s | 14.56 s |
| ~168 KB | 14 | 2.41 s | 13.62 s |
| ~176 KB | 15 | 3.44 s | 8.02 s |
| ~184 KB | 11 | 3.93 s | 6.49 s |
| ~192 KB | 15 | 2.76 s | 13.24 s |
| ~200 KB | 18 | 2.54 s | 6.92 s |
| ~208 KB | 9 | 2.56 s | 5.15 s |
| ~216 KB | 8 | 3.30 s | 6.86 s |
| ~224 KB | 14 | 3.43 s | 7.12 s |
| ~232 KB | 15 | 3.25 s | 13.71 s |
| ~240 KB | 15 | 3.86 s | 9.55 s |
| ~248 KB | 14 | 4.82 s | 10.38 s |
| ~256 KB | 10 | 4.96 s | 13.87 s |
| ~352 KB | 5 | 2.25 s | 4.53 s |
| ~360 KB | 9 | 2.18 s | 2.90 s |
| ~368 KB | 7 | 2.94 s | 5.38 s |
| ~376 KB | 6 | 2.85 s | 4.35 s |
| ~384 KB | 7 | 1.16 s | 1.38 s |
| ~392 KB | 10 | 2.64 s | 3.43 s |
| ~400 KB | 1 | 7.79 s | 7.79 s |

Caveats that apply to every row above: context size is confounded with cache state,
model and task type; a bucket with a handful of rows is an anecdote, not a rate; and
your own before/after series is the only honest way to price a compaction change.
