# ag-14 — Volume × price interaction for direction

Phase 6 of e025. Does **volume confirm or contradict price moves**? Five
declared signals, all targeting DIRECTION (next-1 and next-5 period returns),
analyzed on **1d (primary)** with **1h** as secondary sensitivity. The fee
reality from ag-13 (0.09% taker round trip) is stated next to every effect.

Input: `../ag-01-data/output/candles_raw.csv` (12 coins × 4 tfs, 135,232
rows; 3,175 v=0 synthetic pre-listing candles dropped). Hyperliquid volume is
**total** per candle — there is no separate up/down volume, so all signals are
computed from OHLCV alone.

Limitation stated up front: on **1h every effect collapses to ±0.01pp** — these
are daily/positional effects, consistent with ag-13's finding that intraday
edges die at 0.09% round trip. 5m is not reported as tradeable evidence.

---

## Verdicts on the 5 signals (1d)

### 1. Move × volume interaction — NULL (insufficient per-coin data)

Bucket: sign(ret) × volume percentile within (coin, tf) series.

| bucket | n | mean next-1d | win | mean next-5d |
|---|---|---|---|---|
| up \| vol<50 | 2535 | +0.20% | 47.9% | +1.12% |
| up \| vol>99 | 290 | +0.09% | 46.2% | +0.91% |
| down \| vol<50 | 2550 | +0.22% | 51.8% | +0.78% |
| down \| vol>99 | 322 | +0.36% | 53.0% | +1.56% |

The classic hypothesis — *up moves on high volume continue* — is **not
confirmed**: `E[next1 | up, vol>99] − E[next1 | up, vol<50] = −0.11pp`
(slightly negative, the opposite of continuation). If anything, **down** moves
on extreme volume bounce harder (+0.36% next-1d vs +0.22% on low volume), a
panic-volume → reversion pattern. **But the vol>99 bucket has ~30 obs per coin
per year, so only 1–3 coins have n≥30 in both cells on 1d — per-coin
replication is untestable.** Honest verdict: no evidence of volume-confirmed
continuation on 1d; the data is too thin in the tail to say more. Net-of-fees:
even the largest delta (0.13pp) is ~1.4× the 0.09% fee.

### 2. OBV divergence — REAL but small; the strongest signal in this grid

OBV slope (10d) vs price slope (10d). OBV uses close-to-close sign of ret.

| bucket | n | mean next-1d | median next-1d | win | mean next-5d |
|---|---|---|---|---|---|
| price↑ OBV↑ (up-confirmation) | 3724 | +0.24% | −0.13% | 48.6% | +0.96% |
| price↑ OBV↓ (**bearish divergence**) | 1237 | **−0.10%** | −0.15% | 46.5% | **−0.15%** |
| price↓ OBV↑ (bullish divergence) | 932 | −0.03% | −0.14% | 46.5% | +0.45% |
| price↓ OBV↓ (down-confirmation) | 4261 | +0.15% | +0.07% | 50.9% | +0.70% |

- **Bearish divergence** (price makes a higher move but OBV doesn't confirm)
  predicts a *negative* next-1d mean (−0.10%) and next-5d (−0.15%), while
  up-confirmation is +0.24% / +0.96%. Spread = **0.34pp next-1d, 1.11pp
  next-5d**.
- **Replication**: 6/10 coins agree next-1d, **8/10 coins agree next-5d**,
  and the pooled effect is negative in **both split halves** (−0.55pp h1,
  −0.10pp h2). Median per-coin delta next-1d = −0.23pp, next-5d = −0.98pp.
- **Net of fees**: a short entered after bearish divergence earns +0.104%
  gross next-1d → **+0.01pp net** (fee 0.09%). Over 5 days: +0.146% gross →
  **+0.06pp net**. It survives fees but is a whisper, not an edge.

### 3. VWAP distance — NULL (no mean reversion)

`dist = (c − vwap20)/vwap20` in σ units.

| bucket | n | mean next-1d | win | mean next-5d |
|---|---|---|---|---|
| z < −1 (stretched below) | 2761 | +0.24% | 52.5% | +0.86% |
| −0.5..0.5 (at VWAP) | 2437 | −0.13% | 45.8% | −0.16% |
| z > 1 (stretched above) | 2329 | +0.37% | 49.2% | +1.87% |

Stretched **above** VWAP does NOT revert — if anything it continues (+0.13pp
next-1d vs stretched below), i.e. a momentum tilt, not the mean-reversion the
hypothesis predicted. **Split halves disagree** (+0.51 h1 vs −0.31 h2) and
per-coin replication is 7/12 — this is a null. Honest: VWAP distance carries
no tradeable directional information on 1d.

### 4. Up/down volume ratio — NULL

Trailing-10 candle `Σv[up]/Σv[down]`.

| bucket | n | mean next-1d | win | mean next-5d |
|---|---|---|---|---|
| ratio < 0.5 (down-volume dominant) | 2033 | +0.22% | 51.7% | +0.69% |
| ratio > 2 (up-volume dominant) | 1579 | +0.28% | 48.1% | +1.58% |

Delta +0.07pp next-1d pooled but **split halves disagree** (+0.32 h1 vs −0.30
h2) and next-5d replication drops to 5/10. Null. The 1.58% next-5d on high
up-ratio is carried by a few coins (CRV +7.7, DOGE +3.5) and does not
replicate.

### 5. Volume-adjusted return — REAL on the DOWN side, small

`vol_adj = ret / (v/median_v)`; buckets are quintiles of |vol_adj| per (coin,
tf) within each sign. q5 = the move happened on **unusually low volume for its
size**.

| bucket | n | mean next-1d | median next-1d | win | mean next-5d |
|---|---|---|---|---|---|
| down_q1 (down on high volume for size) | 1024 | −0.13% | −0.13% | 46.5% | −0.06% |
| down_q5 (down on low volume for size) | 994 | **+0.24%** | +0.20% | 53.4% | **+1.27%** |
| up_q1 (up on high volume for size) | 1010 | +0.03% | −0.13% | 48.0% | +0.36% |
| up_q5 (up on low volume for size) | 1062 | +0.17% | −0.28% | 45.2% | +1.07% |

- A **down move that happened on unusually low volume for its size** bounces:
  +0.24% next-1d vs −0.13% for a down move on high volume for size → delta
  **+0.38pp next-1d, +1.32pp next-5d**. Median per-coin delta +0.47pp next-1d
  (6/9 coins positive), split-half consistent (both halves positive).
- This is the same family as ag-07/ag-08's **daily-crash reversion**: a big
  move not backed by volume reverts. On the UP side the effect does not
  replicate (5/10 coins next-1d, halves disagree).
- **Net of fees**: long after a low-volume down move earns +0.24% gross
  next-1d → **+0.15pp net**; next-5d +1.27% gross → **+1.18pp net**. The only
  effect in the grid that clears fees with room on the 5-day horizon.

---

## Replication summary (per signal × tf)

From `output/replication.csv` (per-coin rows require n≥30 in both buckets of
the effect):

| Signal | tf | headline effect | pooled next-1d | next-5d | coins next-1d | coins next-5d | split-half consistent |
|---|---|---|---|---|---|---|---|
| move_vol up | 1d | up vol>99 − up vol<50 | −0.11pp | −0.21pp | 1 valid | 1 valid | no |
| move_vol down | 1d | down vol>99 − down vol<50 | +0.13pp | +0.78pp | 3 valid | 3 valid | no |
| **obv bearish div** | **1d** | bear_div − up_conf | **−0.34pp** | **−1.11pp** | **6/10** | **8/10** | **yes (both −)** |
| obv bullish div | 1d | bull_div − down_conf | −0.17pp | −0.25pp | 6/10 | 7/10 | yes (both −) |
| vwap_dist | 1d | z>1 − z<−1 | +0.13pp | +1.02pp | 7/12 | 7/12 | no |
| ud_vol_ratio | 1d | ratio>2 − ratio<0.5 | +0.07pp | +0.89pp | 7/10 | 5/10 | no |
| **vol_adj down** | **1d** | down_q5 − down_q1 | **+0.38pp** | **+1.32pp** | **6/9** | **6/9** | **yes (both +)** |
| vol_adj up | 1d | up_q5 − up_q1 | +0.14pp | +0.71pp | 5/10 | 8/10 | no |

All 1h sensitivity rows: pooled deltas between −0.05 and +0.05pp, replication
~50/50 → **every effect is a 1d-only effect**.

---

## The fee reality (ag-13 model: taker 0.045% per side, 0.09% round trip)

| Signal (1d) | Gross edge next-1d | Net next-1d | Gross edge next-5d | Net next-5d | Tradeable? |
|---|---|---|---|---|---|
| OBV bearish-div short | +0.104% | **+0.01pp** | +0.146% | **+0.06pp** | survives fees, too small to matter |
| vol-adj down-q5 long | +0.241% | **+0.15pp** | +1.267% | **+1.18pp** | marginal next-1d, real next-5d |

Breakeven rule: any edge must exceed 0.09% round trip. Two of five signals
clear it on the mean; only the vol-adjusted-down-move reversal clears it with
meaningful room, and only on the 5-day horizon.

## Honest nulls

- **Move × volume**: the classic "volume confirms the move" continuation does
  not appear on 1d. High-volume up moves do not continue more than low-volume
  ones. The vol>99 per-coin cell is too small to establish anything stronger.
- **VWAP distance**: no mean reversion; split halves disagree — null.
- **Up/down volume ratio**: no replicable directional effect — null.
- **Everything at 1h**: dead. These are daily/positional effects only.
- Expectation confirmed: the classic literature effects are real in sign
  (OBV divergence, low-volume-move reversal) but small; only the reversal
  survives costs, and only on the 5-day horizon.

## Bottom line

Volume does carry directional information on 1d, but only in two narrow
forms: **bearish OBV divergence** (price up, volume down → subsequent
weakness, −0.34pp vs up-confirmation) and **down-moves on abnormally low
volume for their size reverting** (+0.38pp next-1d, +1.32pp next-5d). The
second is the only signal that survives the 0.09% round-trip cost with room,
and it is the same phenomenon ag-07/ag-08 found for daily crashes. The classic
"volume confirms continuation" interaction — the headline hypothesis of this
phase — is not present in the data.
