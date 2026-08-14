# ag-02 distribution report

Input: `../ag-01-data/output/candles_raw.csv` (135,232 raw rows).
Rows dropped: 3,175 synthetic pre-listing candles (v=0). Returns computed on 132,009 rows.

## Findings

- **Are returns fat-tailed? Yes, on every timeframe.** Pooled raw kurtosis:
  5m=9.27, 1h=10.11, 1d=13.79, 1w=10.59 — all far above the normal baseline of
  3. p99.9 sits at 4.95σ (5m), 5.49σ (1h), 4.96σ (1d), 6.71σ (1w), beyond the
  ±4σ criterion and well past the normal ~3.09σ. Every one of the 48 (coin,tf)
  cells in `stats.csv` has kurtosis > 3.
- **Which tf is most extreme?** On z-scored pooled returns, **1d has the
  heaviest center/tail mix** (kurtosis 13.79, p99.9=4.96σ) and **1w the most
  distant extreme quantile** (p99.9=6.71σ, i.e. the worst 0.1% of weekly moves
  are ~6.7 stdevs). The most extreme single event is CRV 1w: max=+115.16% in
  one week. Caveat: 1w/1d have far fewer samples (1,468 / 10,250 vs ~60,000)
  so their quantiles are noisier.
- **Coin outliers.**
  - XRP 1d kurtosis = **72.5** (skew 4.7), driven by a single +74.59% daily
    candle; exclude it and XRP 1d drops toward typical values. Check for a data
    artifact (listing/relisting) in ag-03.
  - ZEC 1h is the most extreme 1h (kurtosis 16.24, p99.9=8.76%, max=+11.59%,
    min=-14.86%).
  - CRV 1w kurtosis=22.60 and DOGE 1w kurtosis=26.13 with p99.9 ≈ +107% and
    +92% respectively — the 1w right tail is dominated by a handful of
    multi-hundred-percent weeks.
  - PUMP is the most extreme 5m coin (p99.9=1.83%, max=+2.56%) but its kurtosis
    (5.88) is mild — it has wide but not extreme-tail moves.
- **Symmetric or skewed?** Mean ~ 0 everywhere. Skews are small per coin
  (mostly |skew| < 1) except XRP 1d (+4.73), DOGE 1w (+3.23), CRV 1w (+3.04).
  Long-run mean drift is negligible (max |mean| = 4.30% for ZEC 1w, but only
  n=45).
- **Implication for ag-03**: tails are real and heavy at every tf; the extreme
  events to predict are 4.5-7σ moves. Use 1d/1w for "is a regime shift
  imminent" (fat, skewed, sparse), 5m/1h for high-frequency tail events (wide,
  numerous). Watch XRP 1d and ZEC 1h as probable anomaly/artifact cases.

## Unconditional (pooled across coins, per tf)

| tf   |     n |   kurtosis_unconditional |   p99_9_in_sigma |   p99_9_in_pct |
|:-----|------:|-------------------------:|-----------------:|---------------:|
| 5m   | 60277 |                  9.27115 |          4.95454 |        1.21743 |
| 1h   | 60014 |                 10.1148  |          5.49461 |        5.3397  |
| 1d   | 10250 |                 13.7934  |          4.96319 |       25.0974  |
| 1w   |  1468 |                 10.5851  |          6.71308 |       89.629   |

Kurtosis is raw (Pearson) kurtosis — normal = 3. p99.9 in σ units: for a normal distribution this is ~3.09σ.

## Per coin, per tf (from stats.csv)

Fat-tail criterion: kurtosis > 3 and p99.9 beyond ±4σ.

### 5m

Top 3 kurtosis: ETH=17.79, CRV=11.67, DOGE=11.52
Most extreme p99.9: PUMP p99.9=1.83%, min=-2.25%, max=2.56%

### 1h

Top 3 kurtosis: ZEC=16.24, XRP=12.43, ETH=12.08
Most extreme p99.9: ZEC p99.9=8.76%, min=-14.86%, max=11.59%

### 1d

Top 3 kurtosis: XRP=72.51, XMR=9.36, ETH=7.69
Most extreme p99.9: ZEC p99.9=36.23%, min=-26.01%, max=39.30%

### 1w

Top 3 kurtosis: DOGE=26.13, CRV=22.60, XRP=15.51
Most extreme p99.9: CRV p99.9=106.90%, min=-31.25%, max=115.16%

