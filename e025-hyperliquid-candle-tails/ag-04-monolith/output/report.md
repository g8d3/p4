# e025 Hyperliquid Candle Tails — Combined Report (Path B: ag-04-monolith)

Date: 2026-08-13. Data: `../ag-01-data/output/candles_raw.csv`, 135,232 rows,
12 coins × 4 timeframes (5m, 1h, 1d, 1w). Returns `ret = (c[t]−c[t−1])/c[t−1]×100`
per (coin, tf), first candle per group dropped → 135,184 returns.
Kurtosis is Pearson (excess + 3), so a normal distribution has kurtosis 3.

## Part 1 — Distribution: are returns fat-tailed?

Yes. Every one of the 48 (coin, tf) pairs has kurtosis > 3, and 40/48 have
p99.9 beyond ±4σ. No timeframe is Gaussian.

Pooled per timeframe (min–max across the 12 coins):

| tf | n | mean % | stdev % | kurtosis | p99 % | p99.9 % |
|---|---|---|---|---|---|---|
| 5m | 60,277 | +0.001 | 0.18 | 5.6 – 17.8 | 0.24 – 1.12 | 0.48 – 1.83 |
| 1h | 60,014 | −0.002 | 0.89 | 6.4 – 16.2 | 1.42 – 4.44 | 2.49 – 8.76 |
| 1d | 13,012 | +0.164 | 4.82 | 3.6 – 71.3 | 7.74 – 18.05 | 11.38 – 36.24 |
| 1w | 1,881 | +1.108 | 13.26 | 3.5 – 26.2 | 20.70 – 59.95 | 21.93 – 130.75 |

- The one-in-1000 (p99.9) move is 3–5× the one-in-100 (p99) move at every tf,
  and far beyond ±4σ for most pairs — heavy tails confirmed.
- Most extreme pairs (kurtosis): XRP 1d 71.3 (p99.9 31.4%), DOGE 1w 26.2
  (p99.9 90.8%), ZEC 1w 24.1 (p99.9 130.7%), ETH 5m 17.8.
- Charts: `charts/hist_<tf>.png` (log-y, 60 equal-width bins centered on 0) and
  `charts/tail_overlay.png` (pooled z-score distributions, log-y) show the
  tails clearly; z-scores confirm the 1w distribution is the most extreme,
  5m the most "tame" relative to its own σ.

Data-quality caveat: ag-01 backfilled pre-listing candles with v=0 for several
coins (e.g. ZEC 1d 999/1314 rows, ZEC 1w 144/189 rows, XMR 1d 999/1210). Those
are synthetic price rows, not Hyperliquid trades. Their effect on the pooled
1d numbers is small (kurtosis 12.8 → 10.7, p99.9 25.2 → 25.1 excluding v=0)
but they *are* the source of the extreme ZEC 1d/1w tail stats. Excluding v=0
rows does not change any fat-tail verdict.

## Part 2 — Conditional tails: is the extreme predictable?

Method: per signal, split next-candle returns (`ret[t+1]`) into signal-present
vs absent and compare the tail. Table below is pooled across coins per tf
(`coin=ALL` in `cond_next.csv`; per-coin rows are in the same file). Verdict
rule: edge requires n ≥ 300, a bootstrap 95% CI on the group's p99 that
excludes the unconditional p99, and a significant Mann-Whitney U.

| tf | signal | n (yes) | p99 yes % | p99 base % | p99 CI | MW p | verdict |
|---|---|---|---|---|---|---|---|
| 5m | prev −2σ | 1,511 | 0.81 | 0.64 | 0.70–0.91 | 1e-5 | **edge** |
| 5m | prev −3σ | 424 | 0.91 | 0.64 | 0.71–0.95 | 4e-5 | **edge** |
| 5m | vol spike top1% | 612 | 1.03 | 0.64 | 0.84–1.29 | 0.044 | **edge** |
| 5m | prev +2σ | 1,668 | 0.88 | 0.64 | 0.84–1.02 | 0.147 | no edge |
| 5m | prev +3σ | 495 | 0.86 | 0.64 | 0.80–0.95 | 0.067 | no edge |
| 5m | vol top1% | 612 | 0.94 | 0.64 | 0.84–1.03 | 0.056 | no edge |
| 5m | vol top10% | 6,035 | 0.84 | 0.64 | 0.78–0.90 | 0.999 | no edge |
| 5m | up5 | 1,427 | 0.87 | 0.64 | 0.67–0.96 | 0.066 | no edge |
| 1h | prev +2σ | 1,659 | 5.05 | 2.88 | 4.10–5.70 | 2e-5 | **edge** |
| 1h | prev −2σ | 1,539 | 5.02 | 2.88 | 4.41–5.40 | 2e-7 | **edge** |
| 1h | prev −3σ | 490 | 6.40 | 2.88 | 5.37–7.75 | 1e-5 | **edge** |
| 1h | vol top1% | 611 | 8.76 | 2.88 | 6.35–9.98 | 2e-4 | **edge** |
| 1h | prev +3σ | 555 | 5.84 | 2.88 | 4.39–8.76 | 0.428 | no edge |
| 1h | vol top10% | 6,011 | 4.67 | 2.88 | 4.26–5.12 | 0.423 | no edge |
| 1h | vol spike top1% | 611 | 8.59 | 2.88 | 5.94–9.99 | 0.070 | no edge |
| 1h | up5 | 1,281 | 3.00 | 2.88 | 2.70–3.54 | 5e-5 | no edge |
| 1d | vol top10% | 1,310 | 20.98 | 14.27 | 18.74–24.23 | 0.035 | **edge** (fragile, see below) |
| 1d | prev +2σ | 388 | 23.72 | 14.27 | 18.65–26.47 | 0.793 | no edge |
| 1d | up5 | 344 | 18.56 | 14.27 | 11.46–21.22 | 0.634 | no edge |
| 1d | other | — | — | — | — | — | insufficient data (n < 300) |
| 1w | all signals | — | — | — | — | — | insufficient data (max n = 190) |

Reading the pattern — the "edges" are volatility clustering, not direction.
Wherever the p99 of the next candle shifts up, the p1 (downside tail) shifts
out by a comparable amount (e.g. 5m prev −3σ: p99 0.91 vs 0.64, p1 −0.76 vs
−0.59; 1h vol top1%: p99 8.76 vs 2.88, p1 −5.76 vs −2.61). The distribution
widens symmetrically. The only directional signal in the *mean* is a mild
bounce after large down moves (1h prev −3σ → next mean +0.30%, 5m +0.03%),
which is tiny next to the ±0.6–11% tail widths and is not statistically
actionable.

Multiple-testing note: 32 signal×tf tests; the coherent, cross-tf vol-
clustering results (every extreme-move and high-vol signal widens the next
tail) are the credible ones. Individual 5m flags (prev −2σ/−3σ) should be read
as part of that same clustering pattern, not as directional edges.

Fragile result: the 1d vol top10% flag disappears when synthetic v=0 backfill
rows are excluded (n=1,087, p99 20.95 vs 14.62, MW p=0.148). Do not trade it.

## Overall conclusion

- **Fat tails: confirmed at all timeframes.** Kurtosis 3.5–71, p99.9 beyond 4σ
  for 40/48 pairs. Expected for perp returns.
- **Predictable directional edge in next-candle returns: no.** After extreme
  moves, volume spikes, and high-volatility states, the *variance* of the next
  candle rises in both tails — the classic volatility-clustering effect — but
  the sign of the move is not predictable.
- **Where the edge actually is:** volatility/range conditioning, exactly what
  e022 (volume-profile S/R grid) exploits. Directional strategies on
  close-to-close returns would be fighting noise.
