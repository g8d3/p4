# ag-01 — Data: download Hyperliquid candles (SHARED, run once)

Download candles for the top-10 perps (by volume AND open interest) across four
timeframes, maximum available history, into one clean long-format CSV.

**This download is consumed by BOTH paths of the A/B test (Path A = ag-02 +
ag-03, Path B = ag-04-monolith). Run it exactly once.** Never re-run or expand
it for one path — a second download would corrupt the test.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope
- [../../e021-hyperliquid-playground/AGENTS.md](../../e021-hyperliquid-playground/AGENTS.md) — API details, ranking, candle conventions

## Inputs

1. **Coin selection** — the top-10 union of volume/OI leaders. Read the e021
   ranking (e.g. `sqlite3 ../../e021-hyperliquid-playground/data/playground.db
   "SELECT name, dayNtlVlm, openInterest FROM r_2 ORDER BY dayNtlVlm DESC LIMIT 20"`),
   or re-fetch `metaAndAssetCtxs` from the API. Pick the union of top-10 by
   notional volume and top-10 by open interest notional (OI × markPx — the raw
   `openInterest` field is in coin units). ~12 coins expected.
2. **Timeframes** — `5m`, `1h`, `1d`, `1w` (interval strings exactly as the
   API expects).
3. **History** — full available history per coin, bounded by the exchange
   launch (late 2023) or `2023-01-01`, whichever is later.

## API

```
POST https://api.hyperliquid.xyz/info
{"type":"candleSnapshot","req":{"coin":"BTC","interval":"5m","startTime":MS,"endTime":MS}}
```

Response: array of `{t, T, s, i, o, c, h, l, v, n}` where `t` = open time (epoch
ms). **Max 5000 candles per request** — paginate:
`startTime = last_t + interval_ms`. All endpoints are public, no API key.

## Deliverables

| File | Contents |
|---|---|
| `output/candles_raw.csv` | One row per candle: `coin,tf,t_ms,o,h,l,c,v` |
| `output/manifest.json` | Fetch start/end, per-`(coin,tf)` row count + expected count, gaps, API errors (0 errors expected — record any). Include fetch start/end wall-clock timestamps — the A/B comparison uses them |

## Success criteria

- Rows ≥ 90% of expected per `(coin, tf)` (expected = history span ÷ interval).
- No duplicate `(coin, tf, t_ms)` — dedupe defensively.
- CSV is well-formed; 5m dominates row count (~250k+ per coin). Total ~3M rows.
- Every `(coin, tf)` combination present. If one coin is missing from the
  ranking or a timeframe fails, document it in the manifest and continue — do
  not silently drop it.

## Pitfalls

- `candleSnapshot` errors (422) on malformed requests; a failed page is logged
  and retried, not fatal.
- Some coins delisted/added over time — their earlier windows return empty
  arrays. That's a gap, not a crash.
- Keep the CSV in long format (stacked by coin/tf), NOT one file per coin.
- Writing ~3M CSV rows is fast; don't parallelize so hard you get rate-limited.
- Verify the output: `wc -l`, `awk -F, '{print $1","$2}' | sort | uniq -c` to
  confirm every (coin,tf) has rows and no garbage.

## Command execution

- Every API call: `timeout 30 curl -s ...` in a loop; page the fetch (batches
  of ~5000 candles). A single 5m history is ~65 requests.
- The full download is minutes — run it in background with progress markers
  (echo `=== coin/tf page N ===`), then self-wake to check.

## Self-command

Every background command MUST be followed by a self-wake so this agent never
blocks or sleeps:

```bash
( sleep 60; tmux send-keys -t 25-1 "Self-wake: check fetch progress. Log tail? file growing? errors? next batch or done?" Enter ) &
```

Check on each wake: the CSV is growing, `manifest.json` exists, no API errors
piling up. When the fetch completes, validate the CSV (row count, no dups) and
write `done.txt` with the row counts.

## Notify (mandatory)
In addition to writing `done.txt`, agents MUST notify on completion:
`notify.sh done "<agent> finished: <headline>"` (from `../../e000-fundamentals/bin/notify.sh`)
On an unrecoverable failure, before giving up: `notify.sh error "<agent> failed: <cause>"`

