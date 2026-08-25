# BASE_RATES — the experiment's accumulated priors ("intuition table")

This file is the intuition engine of e043. Every candidate idea - and every
candidate DATA SOURCE - gets its prior from HERE, not from vibes. Every entry
has three mandatory answers: (1) what did we test, (2) what happened after
fees + OOS, (3) WHO PAYS (= where would the profit come from; empty answer =
fail flag, as in every losing idea so far).

Table = append-only. Prior screen IDs: A = entry win rate, B = fee breakeven,
C = regime churn (see `ag-01/bin/screen.py`).

## Base rates — strategies (all after fees, real BTC)

| # | Strategy family | Return (best) | Max DD | PF | Fee/OOS story | WHO PAYS? | Prior today |
|---|---|---|---|---|---|---|---|
| 1 | e022 v1 grid (13M fills/yr) | −20.6% (5m) | −48.5 | 0.53 | fees DOMINATED (−25k USDT) | none — bleeding to venue | ~0 |
| 2 | e022 v2 grid (range-only, trend-off switch) | +3.64% (5m) / +1.71% (1h) | −7.2/−7.6 | 1.14/1.04 | survives fees; thin; OOS-tested | opportunistic: calm-flow makers (not identified) | 0.2 |
| 3 | e043 Fase 1: one-sided %-ladder | ≈ breakeven doing nothing | — | ~1.0 | fees + low win rate | none — structural | 0 |
| 4 | e043 Fase 2: two-sided ATR grid port | −0.01% best (1h), −3..−4% 5m | — | 1.00 | taker-flatten churn | none | 0 |
| 5 | **Nautilus-A Test 1: maker-limit flatten** | **+4.18% (5m) / +3.29% (1h)** | −6.9/−7.3 | 1.16/1.08 | fees −10%/−38.6%, 4/4 OOS splits better | venue (fee-bleed only) — pure cost fix | **KEEP** |

## Base rates — data sources (each needs a falsifier card, see SOLO_PROTOCOL)

| Data source | Variable it measures | Scale | Available now? | Purity (opinion \$ paid) | Falsifier |
|---|---|---|---|---|---|
| Price/vol (already have) | opinion + disagreement | 5m-1h | yes | high | (baseline) |
| Funding rate (perp) | leverage demand of "opinion" | daily | **yes** — Hyperliquid public | high | does funding z-score win A/B? |
| MVRV / realized cap | price vs what holders PAID (P/B of opinion) | daily/weekly | glassnode (paid) or proxy: price vs 200d avg | high | MVRV-z predicts 30d? OOS |
| Network fees (P/S analog) | real usage = "sales" | monthly | glassnode / block explorers | medium | fee-growth vs price regression |
| Stablecoin supply ratio / exchange flows | dry powder / migration intent | daily | paid providers | medium | same protocol |
| Options IV / skew (if Hyperliquid) | expected move & tail demand | intraday | HL options or Deribit | high but new | IV premium vs realized? |
| Prediction markets / social | raw belief polls | hours-days | open APIs | LOW purity (talk ≠ \$) | sentiment predicts price? OOS |
| Fundamentals (P/E, P/S, PEG, comps) — equity-style | not applicable to BTC 1:1 (see mapped crypto analogs) | — | — | LOW | only via crypto analog (fee-revenue, MVRV) |

Valuations (user's ask) mapped honestly: P/S → network fee revenue; P/E →
miner revenue; P/B → MVRV (realized value); PEG → fee-revenue growth; comps →
BTC vs gold / ETH / NDX. These belong to the SLOW STATE layer (weekly regime /
allocation target), NOT 5m entry triggers.

## Screen results (measured priors, 2026-08)

Run: `python3 ag-01/bin/screen.py --data <csv> --n-bars-per-year <n>` (2 min).

**A — entry win rate** (buy dip C% below rolling-888-high; exit +V% / stop −SL%;
66k/51k entries on 5m/1h):

| V / SL | 1.0 / 1.0 | 1.5 / 1.0 | 2.0 / 1.0 | 0.5 / 1.0 |
|---|---|---|---|---|
| measured WR (5m / 1h) | 49.8% / 50.6% | 41.6% / 43.1% | 34.8% / 38.2% | 64.2% / 63.5% |
| **fee breakeven WR** | **56.0%** | **44.8%** | **37.3%** | **74.7%** |
| net edge | **NEGATIVE** | roughly −3pp | −2.5pp | NEGATIVE |

No (C,V,SL) combo on this entry rule clears fees. Fase 1's structural kill,
reproduced in 2 minutes of numpy instead of 2 weeks of sweeps.

**C — regime churn (recursive causal EMA 50/100, enter 1.0 / exit 0.5)**:

| | flips/yr | avg trend (bars) | P(flip ≤5 bars) | P(flip ≤20 bars) |
|---|---|---|---|---|
| 5m | 42 | 76.7 | 0.0% | 0.0% |
| 1h | 60.5 | 103.1 | 0.0% | 0.8% |

Regime sticks. In v2's engine (naive windowed EMA) flips are ~2x higher
(86/402) — that is ENGINE NOISE, not market behavior. Prior for any future
regime-switch churn estimate: use the recursive EMA, split the difference.

## Rules this table encodes

1. P(simple mean-reversion %-exit works net on BTC) ≈ **<10%** at realistic
   bands — entry first, always.
2. P(cost-fixes (maker/liquidity/flag hygiene) survive) ≈ **>70%** — they are
   engineering, not alpha. Always do them first.
3. P(unknown-manual-knobs alpha) ≈ **<15%** — knobs are for robustness, not for
   finding the edge.
4. P(new DATA layer (fundings/flow/MVRV) adds state) ≈ **medium-high** but only
   after a falsifier card passes — target: allocation target layer, not entry.
