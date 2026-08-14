# ag-06 — Part 1: Permutation test (is the weekday pattern real?)

Date: 2026-08-13
Input: `../ag-01-data/output/candles_raw.csv` → 1d candles, v>0, 12 coins,
10,262 rows. Reproduces the ag-05 weekday finding (`median ret_next` by open
day, UTC).

## Plain English

Imagine you found a coin that lands "heads" 9 times out of 10. Before you
bet money on it, you should check: is this coin actually weighted, or did I
just get lucky? A **permutation test** answers that question by **scrambling
the labels**.

Here our "labels" are the weekday of each candle (Monday, Tuesday, ...).
We scramble which day each candle belongs to — each candle keeps its own
return, we just randomly reassign which weekday it "happened on". If the
weekday pattern still shows up after scrambling, it was never real; it was
just luck. We scramble 10,000 times and count how often luck produces a
pattern as strong as the one we actually saw.

The **p-value** is that count divided by 10,000. A p-value of 0.01 means:
luck would produce a pattern this strong only 1 time in 100. In this test
luck never did — the p-value came out below 1 in 10,000.

## The metric we measure

The ag-05 finding says: Mon/Wed tend down, Thu/Sun tend up (as measured on
`ret_next`, the return of the **following** candle). We need one number that
captures "how strong is the pattern". We use the **tilt**:

```
tilt = median ret_next on (Thu + Sun) / 2   minus   median ret_next on (Mon + Wed) / 2
```

The "up" days minus the "down" days. If the pattern is real, tilt should be
well above 0. We also compute the **max-minus-min spread** (the biggest
weekday median minus the smallest) as a second, direction-agnostic check.

Observed weekday medians of `ret_next` (12 coins pooled):

| Day | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| median ret_next | −0.42% | −0.09% | −0.60% | +0.20% | +0.07% | −0.21% | +0.28% |

Observed tilt = **+0.749%**. Observed max−min spread = **+0.873%**.

## How the test works

1. Per coin, keep its candles and their `ret_next` values in time order.
2. Shuffle the weekday labels **within each coin** (per-coin keeps the series
   structure — we never mix one coin's returns into another coin's labels).
3. Recompute the pooled median per weekday, then the tilt and the spread.
4. Repeat 10,000 times with a fresh shuffle each time.
5. p-value = fraction of shuffles whose metric is **≥** the observed one.

## Result — pooled (all 12 coins)

| Metric | Observed | Null mean | Null p99.9 | p-value |
|---|---|---|---|---|
| tilt (up days − down days) | +0.749% | ≈ 0.00% | ≈ +0.10% | **< 0.0001** |
| max−min spread | +0.873% | ≈ +0.28% | ≈ +0.34% | **< 0.0001** |

**p < 0.0001**: not one of the 10,000 shuffles produced a pattern as strong
as what we actually observe. The observed tilt (+0.749%) is ~7× larger than
the 99.9th percentile of the null distribution. The weekday pattern would
appear by chance less than 1 time in 10,000.

Chart: `permutation_null.png` — histogram of the 10,000 shuffled tilts with
the observed value marked (red line, far in the right tail).

## Result — per coin

| Coin | n (1d) | tilt observed | p-value | passes p<0.05 |
|---|---|---|---|---|
| AAVE | 1123 | +0.823% | 0.009 | ✅ |
| BTC | 1264 | +0.407% | 0.001 | ✅ |
| CRV | 1186 | +1.135% | 0.001 | ✅ |
| DOGE | 1228 | +0.930% | <0.0001 | ✅ |
| ETH | 1264 | +0.526% | 0.001 | ✅ |
| HYPE | 616 | +1.564% | 0.013 | ✅ |
| LIT | 234 | −1.210% | 0.834 | ❌ |
| PUMP | 399 | +1.934% | 0.025 | ✅ |
| SOL | 1258 | +0.596% | 0.023 | ✅ |
| XMR | 210 | +0.112% | 0.443 | ❌ |
| XRP | 1153 | +0.928% | <0.0001 | ✅ |
| ZEC | 315 | +1.598% | 0.065 | ❌ |

**9 of 12 coins pass individually (p<0.05); 6 of 12 pass at p<0.01.**

The three coins that fail (LIT, XMR, ZEC) are exactly the ones with the
shortest histories — 234, 210 and 315 1d candles vs 1,100–1,260 for the
established coins. With that little data, a single coin's weekday medians are
too noisy to reach significance on their own. LIT is the only coin whose
tilt points the **wrong** way (−1.21%), and it has just 234 candles. The
pooled result — where the data from all coins is combined — is unambiguous.

## Verdict

**The weekday pattern is real, not chance.** The pooled p-value is below
1-in-10,000, and the pattern survives a per-coin test in the large majority
of coins. Part 2 turns this into a tradeable rule, and Part 3 checks whether
the pattern is big enough to survive fees on data the pattern never saw.

### Caveats

- p < 0.0001 is "real" in the statistical sense, but statistical reality is
  not the same as profitability. The next two parts measure the *money*.
- The 12 coins are correlated (they move together), so the effective number
  of independent experiments is much smaller than 12. The per-coin p-values
  should not be read as 12 fully independent tests.
