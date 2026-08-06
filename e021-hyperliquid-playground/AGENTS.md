# e021 — Hyperliquid API Playground

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, SQLite/CSV conventions

An API playground for [Hyperliquid](https://hyperliquid.gitbook.io) (mainnet + testnet). Call **any** info endpoint (or any custom POST/GET JSON), store every response as rows in SQLite, and query everything with **full SQL** from a mobile-first web UI.

## Core idea

Everything the playground produces is a **SQLite table**, so one generic SQL engine and one generic table renderer serve all of them:

| Table | Contents |
|---|---|
| `calls` | **Flows** — the configured, repeatable definitions (the playground's admin table) |
| `logs` | **Runs** — one row per execution of a flow (status, latency, row count) |
| `r_<id>` | One table per flow holding flattened response rows |

The UI is a single page: pick a table (or type any SQL), run it, and the same generic component renders `calls`, `logs`, and every result table. `SELECT`, `WHERE`, `LIMIT/OFFSET`, `GROUP BY`, `JOIN`, `ORDER BY` all work; queries are read-only by design (writes happen only through the scheduler/CRUD API).

**Naming**: a *flow* is the definition you configure (runs on an interval); a *run* is one execution of it. Every flow stores its own **Read SQL** (how its results are viewed, `{{table}}` = its result table) and the exact resolved request it last sent (`last_request`).

## Run

```bash
./run.sh            # uvicorn on 0.0.0.0:8310, opens nothing
# from the phone / LAN: http://<host>:8310
# any dir override: HL_DATA_DIR=/path ./run.sh
```

## How a call is stored

A flow config = `{name, base_url, path, method, payload(JSON), interval_sec, enabled, result_shape, read_sql, keep_last, ...}`. The scheduler (and the "Run now" button) executes it and the response is flattened into rows:

- **`auto`** (default) — smart flattening:
  - arrays of objects → one row per object
  - `{coin: mid}` maps (allMids) → one row per key (`key`, `value`)
  - `metaAndAssetCtxs`-style `[{universe, …}, assetCtxs]` → merged index-wise into one row per coin (`name`, `markPx`, `midPx`, `funding`, `openInterest`, …)
  - `l2Book.levels` → one row per level with a `side` column
  - nested objects stay as JSON cells (nothing is lost)
- **`rows`** — top-level elements are flat rows, inner lists kept as JSON cells
- **`raw`** — single row with the whole response in `_raw`

Dynamic columns are created with NUMERIC affinity, so `ORDER BY markPx` sorts numerically while names/hashes stay text.

## Coin filter (ranking)

Step 1 of the guided flow: limit the market to the coins that matter before
pulling candles/books. `metaAndAssetCtxs` is fetched once (the "Fetch markets
ranking" button, or `/api/ranking/setup`) and every coin is ranked by 24h
notional volume (`dayNtlVlm`) and open interest. The UI exposes two sliders —
**coverage percentage** per metric — and computes the top-N automatically:

- `GET /api/ranking` — ranked list with `rank_vol`, `rank_oi`, `cum_vol`, `cum_oi`
- `PUT /api/watchlist` `{vol_pct, oi_pct}` — resolves top-N per metric, stores
  the union in `config` as JSON for later steps (fan-out) to consume
- `GET /api/watchlist` — the saved selection

Measured on real data (2026-08): top 10 coins = 95.3% of 24h volume, top 20 =
97.3%. Open interest is long-tailed — 95% OI needs ~28 coins. Defaults
(95% vol / 95% OI) resolve to ~29 coins; 90%/90% ≈ 15 coins.

**Units pitfall**: `openInterest` from `metaAndAssetCtxs` is in **coin units**
(BTC ≈ 35k BTC), NOT USD. The ranking converts it to notional with
`openinterest * markpx` before ranking/summing. `dayNtlVlm` is already USD.

## Candles: bounded + incremental

Candle calls (and any watchlist-backed call) use payload templates resolved
per request. Templates are **unquoted** in the JSON:

| Template | Resolves to |
|---|---|
| `{{coins}}` | The saved watchlist (or all coins in the latest markets snapshot). **Fan-out**: one request per coin, all stored in one table. |
| `{{last_t}}` | `max(last_t_col)` for that coin; if empty, `now − backfill_ms` (one-shot backfill). |
| `{{now_ms}}` | Current epoch ms (required for candle `endTime` — `endTime:0` returns HTTP 500). |

Per-flow config that makes storage bounded and duplicate-free:

| Config | Meaning |
|---|---|
| `keep_last` | Keep only the last N rows per group (0 = unlimited). |
| `keep_group_col` | Column to prune per coin (candles: `s`). |
| `dedup_cols` | Skip rows already present (candles: `s,t` avoids boundary re-fetch dups). |
| `last_t_col` | Column used by `{{last_t}}` (candles: `t`). |
| `backfill_ms` | First-run window (default 7 days). |

**Transparency**: every run stores the exact resolved request(s) that were sent
to the API as JSON in `calls.last_request` (and per-run in `logs.request`). The
query's **Edit form shows it read-only** ("Last request"), and the coin filter
card shows its own SQL inline ("View SQL") — nothing stays hidden in the
playground.

Verified on real data: 29-coin watchlist, 1h candles — backfill = 4901 rows
(~169 candles/coin, 14s), subsequent runs add 0 rows (all deduped), and
`keep_last=10` caps every coin at its 10 newest candles.

## API (REST)

| Method/Path | Purpose |
|---|---|
| `GET /` | The UI |
| `GET /api/status`, `/api/tables`, `/api/endpoints` | Discovery |
| `GET /api/stats` | DB file size, per-table rows/size/24h growth, flow cap utilization |
| `GET /api/ranking`, `POST /api/ranking/setup` | Coin filter: rank by volume/OI, fetch markets once |
| `GET/PUT /api/watchlist` | Persist the coverage-% watchlist selection |
| `POST /api/query` `{sql}` | Run read-only SQL → `{columns, rows, truncated, error}` |
| `POST /api/calls` / `PUT /api/calls/{id}` / `DELETE /api/calls/{id}` | CRUD |
| `POST /api/calls/{id}/run` / `/clear` | Run one flow now / clear its rows |
| `POST /api/calls/run_all` | Run every flow now |

## Structure

```
e021-hyperliquid-playground/
├── AGENTS.md
├── run.sh
├── data/playground.db          # runtime, gitignored
└── hl_playground/
    ├── __init__.py
    ├── app.py                  # FastAPI routes + static
    ├── db.py                   # SQLite schema, query guard, CRUD
    ├── extract.py              # JSON response → flat rows
    ├── scheduler.py            # interval thread + HTTP client
    └── static/index.html       # mobile-first single page
```

## Conventions

- Results are stored in SQLite (see fundamentals: tabular data prefers CSV, but a live-updating queryable store justifies SQLite here; the data is also queryable, not just diffable).
- No API keys needed — all endpoints used are public.
- Every command in this repo: timeout it, run blocking things in background.

## Pitfalls

- `metaAndAssetCtxs` / `spotMetaAndAssetCtxs` return a **mixed list** `[{universe, …}, assetCtxs]` — the extractor merges them; do not "fix" it to a flat array.
- Some endpoints (e.g. `recentFunding`, `perpVolume`) now reject their old payloads with 422 — a failed call is simply logged, not fatal.
- `candleSnapshot` with `startTime: 0` returns zero candles — use a real millisecond window.
- Result columns are dynamic; a column appearing in a later response is added via `ALTER TABLE` on the next run.
- Queries are read-only: multi-statement, DDL, and DML via `/api/query` are rejected. Deletes happen through the CRUD endpoints.
