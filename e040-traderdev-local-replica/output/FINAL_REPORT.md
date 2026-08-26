# e040 — Final cumulative report (2026-08-22)

The whole investigation in one chain: leaderboard → engine forensics →
local replica → falsification battery → filters → family screening →
realistic fills. The bottom line changed from "looks great" to
"mostly a backtest illusion".

## 1. The chain of evidence

| Stage | PF | %/day | Honest? |
|---|---|---|---|
| Their engine, published (EMA5/ATR0.02, BTC 2h) | 14.2 | 0.80 | contains engine quirks (double-exit loss cap, optimal same-bar fills, smaller effective trail) |
| Local replica, bar-level fills (same window) | 6.5–11.2 | 0.56 | assumes favorable-extreme-first within each 2h bar — optimistic |
| **Local replica, 5m intrabar fills (real sequence)** | **1.36–1.58** | **0.11–0.20** | **the true edge before slippage** |
| ZScore variant, bar-level / intrabar | 12.7 / 0.53 | 0.87 / −0.17 | zsignal fails under realistic fills too |
| Random-timing null (same exits) | 9.9 | 0.65 | ~80% of the bar-level profit is exit+machine, not signal |

## 2. Falsification battery results (output/falsification.json)

- **Permutation**: real timing beats all 120 random trials (p = 0.0) but
  random timing still nets 0.65%/day with the same exit structure. The
  signal is worth ~+22%/day uplift; the micro-trail exit structure is the
  engine of the returns.
- **Time-shift**: shifting entries +1/+2/+3 bars changes almost nothing
  (0.73–0.82%/day) — the edge is not about precise entry timing.
- **Direction**: long 0.26 vs short 0.35%/day (Bybit full) — no persistent
  asymmetry; legs rotate by window (SOL OOS was short-heavy, ETH balanced).
  The "shorts are weak" observation from their engine fixture did NOT
  generalize.
- **Fee stress (long-only Bybit)**: 0.05% comm + 0 slip: 0.26%/day (PF 5.8);
  +0.1% slip: 0.12%/day (PF 2.2); +0.3% slip: **−0.17%/day**. At 0.1%
  commission + 0.1% slip (realistic taker): 0.04%/day ≈ nothing.
- **Walk-forward**: every single 90-day window positive (Bybit BTC 2h:
  0.46–1.09%/day, PF 4.7–30; HL BTC 4h: 0.55–1.48%/day). Stability is
  excellent — the edge is steady, just tiny once fills are real.

## 3. Filters & regime (output/phase2_filters.json)

- `both + vol090` (skip entries when ATR% below 0.9 × its rolling median)
  is the best compromise: OOS BTC 0.49%/day DD −2.2% (vs raw −7.5%);
  in-sample BTC DD −3.0% (vs −6.4%); ETH ~unchanged DD −3.1%/−6.3%.
  SOL keeps a −14.8% tail regardless → the tail is coin-specific, and it
  persists even with filters.
- Trend filter (EMA100/200) alone over-filters: cuts %/day harder than DD.
- **The vol filter only matters if the strategy is tradeable at all** —
  currently it is not, under realistic costs.

## 4. Family screening (screener, reads only — 0 credits)

- The public leaderboard is ~90% the same EMA-VWAP idea (multiple "audit"
  clones of the same strategies) + tiny-sample 100%-WR flukes at the top of
  winrate sort. Kontrolle B ("trail_points=1") is the extreme of the same
  family (PF 12.7 at bar-level).
- Only genuinely different family found: **ZScore-Momentum** (z>2, SL/TP
  ATR-based). Locally at bar-level it BEAT the cross signal (0.87%/day,
  PF 12.7) — but under intrabar fills it is negative (PF 0.53). Another
  case of bar-fill optimism.
- Conclusion: no second family on the platform survives realistic fills;
  the platform's browse is a bar-optimism zoo.

## 5. Realistic-fill test (Phase 4; why not Nautilus)

We answered the fill question directly with a **5m intrabar path test**
(225k Bybit 5m candles; signals/ATR on 2h, trail arming & fills on 5m
extremes inside each 2h bar — no optimistic-sequence assumption):

- Cross intrabar: PF 1.36 (OOS) / 1.58 (in-sample), 0.11–0.20%/day.
- Zscore intrabar: PF 0.53/0.56, negative.

Nautilus was skipped deliberately: with the same 2h bars its engine makes
the same bar-close assumptions; the intrabar test is strictly more
informative for this question (a tick-level Nautilus catalog is not
available on this box).

## VERDICT

**The leaderboard's +16,000% is a backtest illusion chain.** Each honest
step down (engine quirks → bar fills → intrabar fills → real costs)
destroys an order of magnitude of edge:

- True gross edge with realistic sequence: ~0.1–0.2%/day (PF 1.4-1.6).
- Minus realistic taker round-trips (~0.1–0.15%/trade × ~2.3 trades/day):
  **≈ zero to slightly negative**.
- It becomes interesting only as a *maker* strategy (limit fills, rebate)
  — and maker fills are exactly what this entry style cannot guarantee.

What the investigation DID prove:
1. The trader.dev leaderboard numbers are engine-specific artifacts
   (documented quirks), not tradable edges.
2. Our local replicator is (now) honest — it quantifies the optimism gap.
3. The per-day stability is genuinely high (all walk-forward windows
   positive) — but the level is too low under real costs.

## Next options (honest list)

1. **Maker-infra experiment**: re-simulate with limit entries (cross at
   2h close but fill only when a 5m bar trades back through the level)
   and maker fees — the only variant with a theoretical margin.
2. **Different regime**: the exit-style "micro-trail" harvests bar-drift;
   it's a bet ON 2h-bar autocorrelation. A direct autocorrelation study
   (e025 style) tells us if the drift is even stationary across regimes.
3. **Longer-horizon version**: same idea at 1d/1w (fewer trades, PT
   costs negligible, fills matter less) — the one configuration where bar
   optimism fades and costs don't eat it.
4. Paper-trade the intrabar-realism numbers (0.1-0.2%/day gross) to
   benchmark future claims — never again trust a bar-level backtest on
   this pattern.

## Files

- `output/falsification.json` / `falsification.log` — battery
- `output/phase2_filters.json` — filter matrix
- `output/intrabar.json` + `intrabar_zscore.json` — realistic fills
- `output/report.md` + `hyperliquid_port.md` — earlier stages
- `bin/backtest.py` (honest engine), `bin/falsification.py`,
  `bin/phase2_filters.py`, `bin/intrabar.py`, `bin/fetch_bybit.py`,
  `bin/fetch_hyperliquid.py`


## 6. Phase 5 — Bigger timeframes (1d / 1w): the one survivor

Motivated by the cost finding: at 1d the captured % move per trade is
larger, so fixed costs bite less. Tested with the same honesty chain
(warning: daily-anchored VWAP is degenerate on daily bars, so weekly
anchor was used; 1w has only 31 trades -> report only).

### 1-day results

| Config | PF | %/day (after 0.05% fees) | DD |
|---|---|---|---|
| Bar-level BTC (optimistic) | 5.0 | 0.30 | -14.9% |
| Bar-level ETH | 5.2 | 0.50 | -21.9% |
| Bar-level SOL | 3.1 | 0.59 | -25.3% |
| **Intrabar-5m BTC (realistic)** | **6.4** | **0.149** | **-2.0%** |
| **Intrabar-5m ETH (realistic)** | **7.4-9.6** | **0.28-0.29** | **-4.7/-5.6%** |

Surprise: on 1d the REALISTIC version has HIGHER PF and LOWER DD than the
bar-level one — the daily micro-trail is so small relative to the daily
range that the intrabar path barely harms it; bar-level optimism even
LOWERED PF (it counted pumped-and-dumped days as wins, and those bars'
trails get clipped realistically losing less).

Cost check for 1d: ~0.13-0.20 trades/day; fees per day ≈ 0.01-0.02%
(sum of 0.1% per round-trip) vs 0.15-0.29%/day wins → fees are a single
digit % of the edge. A further +0.1%/side slippage costs ≈ 0.03%/day —
the edge survives with margin (unlike 2h where costs killed it).

### 1w

31 trades total — statistical noise, no conclusion. (Report only.)

### VERDICT UPDATE

**The 1-day version is the only configuration that survives the entire
honesty chain: real intrabar fills + real fees + margin for slippage.
0.15-0.29%/day, PF 6.4-9.6, DD -2 to -6%.** Not a fortune (and still
small-sample: 149-157 trades), but it is the correct candidate for a
paper-trade — 2h and all the leaderboard's "profitable" variants are not.


## 7. Phase 6 — Monte Carlo of the 1-day version + stop-loss question

**Backtest is one path; MC asks: how stable is it?** 10,000 reshuffles of
the realized per-trade return series (iid + blocks-of-3), 1x compounding:

| | BTC 1d | ETH 1d |
|---|---|---|
| p(ending negative) | 0.0 | 0.0 |
| median equity (10k start) | 31.8k (3.2x) | 90.0k (9.0x) |
| 5th pct equity | 23.2k (2.3x) | 49.1k (4.9x) |
| median max DD | -2.2% | -3.6% |
| 5th pct max DD | -3.8% | -5.9% |

iid vs blocks-of-3: identical -> no path-dependence in the risk.

**Stop loss (the user's question): the strategy HAS NO stop loss.** Only
the trailing order (after it arms) and reversal exits at bar close. So we
tested: same realized series with per-trade loss clipped at 2/5/10%:
**nothing changes (BTC identical, ETH < 0.1% difference)** — the worst
realized trade is already better than -2% of equity. On 1d the risk tail
is small by construction (losses exit at next day close, ~0.5-1.5%).
A hard SL is therefore optional insurance, not a fix.

Caveat (honest): MC reshuffles the SAME historical window — it tests
sequencing luck, not regime change. Regime risk is the remaining unknown.


## 8. Phase 7 — Full history (2023-2026), parameter sweep, maker, EMA7 winner

**Full history (bar-level, Bybit 1d, weekly VWAP):** 2023-2024 and 2024-2026
windows were strong on all 3 coins (PF 14-1367 bar-level, clearly optimistic),
but the FRESH May-Aug 2026 slice is flat/negative per coin (BTC PF 1.04,
ETH 1.36, SOL 0.84; 19-25 trades each). First evidence that the 1d edge may
be regime-cooling — the live paper monitor's job is to confirm or refute.

**Sweep:** EMA7 is the sweet spot (bar-level PF 14.3-14.6 stable across
mult 0.01-0.05, DD -7.25%). EMA9's bar PF 2466 / DD -0.04% is a red flag
(too-good -> validate with fills before trusting).

**Honest-fill validation (5m intrabar, 2024-08 -> 2026-08, mult 0.02):**

| Coin | EMA5 PF / %day / DD | EMA7 PF / %day / DD | EMA9 PF / %day / DD |
|---|---|---|---|
| BTC | 6.43 / 0.156 / -2.0 | **8.91 / 0.173 / -2.3** | 15.05 / 0.167 / -1.7 (88 tr) |
| ETH | 7.38 / 0.296 / -5.6 | **12.39 / 0.298 / -6.3** | 23.5 / 0.287 / -2.0 (78 tr) |
| SOL | 7.20 / 0.300 / -3.3 | **14.08 / 0.364 / -2.6** | - |

**Winner: EMA7/0.02, 1d, realistic fills: PF 8.9-14.1, 0.17-0.36%/day net,
DD -2.3/-6.3/-2.6%** on BTC/ETH/SOL (112-132 trades each; MC p(neg)=0.0
for all three, median equity 3.6x/9.3x/15.1x, DD p05 -3.4/-6.3/-4.4%).

**Maker scenario:** fee0 adds only ~0.02%/day (0.32 vs 0.30) — nice, not
decisive. On 1d costs are a single-digit % of the edge. (The
fee-of-0.05%+3bps-slip case: 0.31%/day still profitable.)

Monitor switched to EMA7. Interactive viewer: REPORT.html.


## 9. Phase 8 — Synthetic-data negative control (the missing null)

60 pure-noise price series mimicking BTC daily vol (sigma 2.47%/day), run
through the same EMA7/0.02 daily machinery:

| Series | median PF | PF p05-p95 | positive % | med %/day |
|---|---|---|---|---|
| Zero-drift random walk | 1.42 | 0.88-2.19 | 90% | 0.071 |
| Real-drift random walk | 1.36 | 0.91-1.93 | 85% | 0.059 |
| **REAL BTC** | **14.4** | — | — | **0.302** |

Interpretation (definitive): the trailing machine is a drift-HARVESTER —
it prints a small positive expectancy (PF ~1.4) even on pure noise
(90% of noise series are profitable!). The real value (PF 14x) comes from
real market structure responding to the signal. So the chain is:
noise-machinery (PF 1.4) << real-machine-with-random-entries (PF 9.9,
permutation) << real-machine-with-real-signal (PF 14.4). The signal's
job is to concentrate the machine on the ~2x of days with real drift.


## 10. Phase 9 — The look-ahead correction (the honest-fill test's own bug)

Triggered while building the strategy example chart: the demo exit showed
entry and exit on the SAME day, which is impossible when entry fills at the
day's close. Root cause: in the intraday (5m) walkers (intrabar.py for 2h,
phase5 intrabar_daily for 1d), after entering "at the close" the simulator
kept walking that SAME bucket's 5m bars — i.e. bars that happened BEFORE
entry (look-ahead), and it also filled same-bar stop hits at the bar OPEN
instead of the stop. Both bugs fixed (entry bucket's walk skipped; fill at
stop unless gap). EVERY intrabar number above them is corrected.

Results after correction (fills now honest, same-bucket path removed):

| Version | In-sample | OOS |
|---|---|---|
| 2h intrabar | PF 0.72, -0.036%/day, DD -25.9% | PF 0.28, -0.135%/day, DD -14.6% |
| 1d EMA5 | loses (PF 0.16-0.36) | — |
| 1d EMA7 | BTC 1.12 / ETH 1.13 / SOL 3.77 (0.001-0.011%/day) | — |
| 1d EMA9 | 1.13 / 3.5 / 2.98 (0.0005-0.006%/day, 62-80 trades) | — |

Monte Carlo on corrected 1d EMA7 BTC: p(negative) = 0.98 (median equity 7,770 from 10k;
DD p05 -45%). The earlier "p(neg)=0.0 / DD -2%" belonged to the contaminated list.

**FINAL VERDICT (definitive):** the entire leaderboard family nets ~0 or loses
under honest day-scale fills. The chain of corrections: engine quirks -> bar
fill-optimism -> same-bucket look-ahead -> wrong same-bar fill. Each peeled
layer removed an order of magnitude. The only marginal positive left is
SOL 1d EMA7 (+0.011%/day, PF 3.77) - small sample, likely noise, but the
paper monitor (running daily on BTC/ETH/SOL) is the live arbiter.


## 11. Phases 10-11 — The hunt: cross-sectional momentum REJECTED, TSMR SURVIVES

After the micro-trail family died honestly, the hunt moved to lower-frequency
families (weeks-scale holds = cost-insensitive, daily-close fills = honest).

### Candidate 1: cross-sectional weekly momentum (rejected by null)
Long top-3 / short bottom-3 of 12 HL perps by L-day momentum, weekly.
- Screen: 0.06-0.33%/day, PF 1.09-1.17 — thin.
- Walk-forward: 2023 +0.20, 2024 -0.06, 2025 +0.51, 2026 -0.07 — unstable.
- **Permutation null: p = 1.0** (random coin ranking >= real: 0.186 vs 0.168%/day)
- MC: p(neg)=13%, DD p05 -78%.
Verdict: the ranking has ZERO information; profit was directional beta.

### Candidate 2: time-series momentum + vol-targeting (SURVIVED the gauntlet)
Per coin, weekly: 30-day return > 0 -> long at weight = 20% target vol / 30d
realized vol (cap 1), equal allocation across 5 majors, else flat.
- Screen L=30: 0.164%/day, PF 2.01, DD -3.7% (BTC buy&hold: 0.27%/day, DD -53%)
- ALL L (30-180) positive; walk-forward: ALL 4 years positive (0.087-0.126%/day,
  PF 1.9-2.2, DD -2.4 to -3.7%)
- **Permutation null: p = 0.0** (real 0.164 vs random-sign median 0.0007)
- MC: p(neg)=0.0, p05 equity 2.4x, DD p05 -5.1%
- Robustness: majors-only BETTER (0.31%/day, PF 2.12); fees 0.035/0.07/0.10% barely
  change it (0.164 -> 0.149); works BTC-only too.
Why it survives: multi-week holds make costs negligible; vol-targeting keeps DD
single-digit; daily-close fills are the honest execution (no intrabar fantasy).
The null proves the trend SIGN is the edge (cross-sectional ranks carried none).

**Graduated**: weekly paper monitor live (bin/paper_tsmr.py, cron 00:30 UTC,
$30k paper, majors L30). Expected: ~0.16-0.31%/day, DD p05 -5%.
