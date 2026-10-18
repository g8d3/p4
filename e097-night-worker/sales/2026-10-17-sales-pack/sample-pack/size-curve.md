# Size curve — overhead against carried context

From 373 ratable message samples, bucketed to the nearest 8 KB.
**Ranges, not a slope.** We tried to fit a size coefficient of our own and it did not
reproduce (paper §8), so this page reports what your sizes do and stops there.

| context size | rows | wall p50 | wall p90 |
|---|---|---|---|
| ~8 KB | 1 | 0.77 s | 0.77 s |
| ~24 KB | 1 | 1.05 s | 1.05 s |
| ~32 KB | 1 | 0.63 s | 0.63 s |
| ~48 KB | 1 | 0.48 s | 0.48 s |
| ~64 KB | 1 | 0.35 s | 0.35 s |
| ~72 KB | 4 | 2.41 s | 5.67 s |
| ~80 KB | 6 | 3.86 s | 7.24 s |
| ~88 KB | 8 | 3.80 s | 9.10 s |
| ~96 KB | 5 | 4.86 s | 22.59 s |
| ~104 KB | 17 | 2.26 s | 3.48 s |
| ~112 KB | 10 | 4.30 s | 11.02 s |
| ~120 KB | 13 | 5.54 s | 18.56 s |
| ~128 KB | 15 | 1.99 s | 20.48 s |
| ~136 KB | 13 | 3.02 s | 21.78 s |
| ~144 KB | 9 | 5.59 s | 11.78 s |
| ~152 KB | 10 | 5.39 s | 31.52 s |
| ~160 KB | 12 | 2.66 s | 14.56 s |
| ~168 KB | 7 | 5.23 s | 13.62 s |
| ~176 KB | 15 | 2.65 s | 8.02 s |
| ~184 KB | 13 | 4.14 s | 10.50 s |
| ~192 KB | 11 | 3.33 s | 7.81 s |
| ~200 KB | 7 | 3.26 s | 3.46 s |
| ~208 KB | 11 | 1.31 s | 2.74 s |
| ~216 KB | 7 | 2.45 s | 3.02 s |
| ~224 KB | 8 | 1.82 s | 2.45 s |
| ~232 KB | 8 | 1.88 s | 7.57 s |
| ~240 KB | 8 | 1.44 s | 2.42 s |
| ~248 KB | 11 | 1.46 s | 2.85 s |
| ~256 KB | 5 | 2.48 s | 8.57 s |
| ~264 KB | 8 | 1.69 s | 3.23 s |
| ~272 KB | 4 | 6.08 s | 19.00 s |
| ~280 KB | 9 | 2.01 s | 4.05 s |
| ~288 KB | 7 | 3.62 s | 7.33 s |
| ~296 KB | 5 | 3.80 s | 9.84 s |
| ~304 KB | 6 | 4.47 s | 7.96 s |
| ~312 KB | 8 | 2.75 s | 7.31 s |
| ~320 KB | 11 | 1.61 s | 5.21 s |
| ~328 KB | 11 | 1.97 s | 4.39 s |
| ~336 KB | 9 | 1.86 s | 3.59 s |
| ~344 KB | 7 | 2.47 s | 8.31 s |
| ~352 KB | 10 | 2.22 s | 4.96 s |
| ~360 KB | 9 | 2.18 s | 2.90 s |
| ~368 KB | 7 | 2.94 s | 5.38 s |
| ~376 KB | 6 | 2.85 s | 4.35 s |
| ~384 KB | 7 | 1.16 s | 1.38 s |
| ~392 KB | 10 | 2.64 s | 3.43 s |
| ~400 KB | 1 | 7.79 s | 7.79 s |

Caveats that apply to every row above: context size is confounded with cache state,
model and task type; a bucket with a handful of rows is an anecdote, not a rate; and
your own before/after series is the only honest way to price a compaction change.
