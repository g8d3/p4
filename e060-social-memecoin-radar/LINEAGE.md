# e060 LINEAGE — where every number comes from (owner-ordered 2026-09-13)

## Pipeline (source → table → filter → table)

1. **Dexscreener `token-boosts/top`** (free, keyless) → universe: top-15
   paid boosts. This is bought attention (projects pay for visibility).
2. **Dexscreener `tokens/v1/{chain}/{addr}`** (free) → per token, the
   highest-volume pair: price, vol_h24, txns_h24, chg24h, dex, pair URL.
3. **rotation table** (`/api/rotation`, rebuilt every 5m, cached):
   - `score = 10·log10(boost$+1) + 5·log10(vol+1)` — paid attention + size.
   - `heat = score + 5·log10(txns+1) + min(|chg24h|,150)/10` — attention
     + trade-speed + move size (capped).
   - Sorted by score. 15 rows.
4. **worthy filter** → `heat ≥ 80 AND vol ≥ $500k AND txns ≥ 10k`.
5. **paper snapshot** (cron 07:17 UTC, `paper_snapshot.py`) → passing
   tokens + entry price banked in `paper/calls.jsonl` (one row/call).
6. **paper resolve** (`paper_resolve.py`, ≥24h later) → hit = price up;
   `paper/score.json` holds hit-rate → card shows it.
7. **backtest: NONE.** Dexscreener free tier is current-price only, so no
   history exists (cure queued: bank rotation snapshots as history).

## Honesty note (read before trusting the name)

**No social input exists anywhere in this pipeline.** No X pipe, no
Reddit counts, no sentiment score — the code itself says "social
velocity deferred". What the radar actually measures is *bought
attention + on-chain velocity*. The name overpromises; the social
pipe is queued work (free first: Alternative.me Fear&Greed; paid
quoted per clone-before-pay: LunarCrush, Santiment — see ISSUES).

## Link-forward (what happens after Dexscreener)

Today the `pair ↗` link lands on the pair page and stops. Next steps
queued: per-row sparkline from banked snapshots (own history, no key),
pair-age / liquidity columns from the same free payload, alert on
first worthy flag per token (not per snapshot).
