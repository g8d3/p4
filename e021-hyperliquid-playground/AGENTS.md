# e021 — Hyperliquid API Playground

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, SQLite/CSV conventions

An API playground for [Hyperliquid](https://hyperliquid.gitbook.io) (mainnet + testnet). Call **any** info endpoint (or any custom POST/GET JSON), store every response as rows in SQLite, and query everything with **full SQL** from a mobile-first web UI.

## Core idea

Everything the playground produces is a **SQLite table**, so one generic SQL engine and one generic table renderer serve all of them:

| Table | Contents |
|---|---|
| `calls` | Scheduled call configs — the playground's own admin table |
| `logs` | One row per execution (status, latency, row count) |
| `r_<id>` | One table per call holding flattened response rows |

The UI is a single page: pick a table (or type any SQL), run it, and the same generic component renders `calls`, `logs`, and every result table. `SELECT`, `WHERE`, `LIMIT/OFFSET`, `GROUP BY`, `JOIN`, `ORDER BY` all work; queries are read-only by design (writes happen only through the scheduler/CRUD API).

## Run

```bash
./run.sh            # uvicorn on 0.0.0.0:8310, opens nothing
# from the phone / LAN: http://<host>:8310
# any dir override: HL_DATA_DIR=/path ./run.sh
```

## How a call is stored

A call config = `{name, base_url, path, method, payload(JSON), interval_sec, enabled, result_shape}`. The scheduler (and the "Run now" button) executes it and the response is flattened into rows:

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

## API (REST)

| Method/Path | Purpose |
|---|---|
| `GET /` | The UI |
| `GET /api/status`, `/api/tables`, `/api/endpoints` | Discovery |
| `GET /api/ranking`, `POST /api/ranking/setup` | Coin filter: rank by volume/OI, fetch markets once |
| `GET/PUT /api/watchlist` | Persist the coverage-% watchlist selection |
| `POST /api/query` `{sql}` | Run read-only SQL → `{columns, rows, truncated, error}` |
| `POST /api/calls` / `PUT /api/calls/{id}` / `DELETE /api/calls/{id}` | CRUD |
| `POST /api/calls/{id}/run` / `/clear` | Run now / clear rows |
| `POST /api/calls/run_all` | Run every call now |

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
