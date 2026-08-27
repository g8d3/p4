# e045 — GMGN Clone (Pulse, Hyperliquid terminal)

A functional GMGN-style trading/exploration terminal for **Hyperliquid**, built to
be "fully functional" with real data (no mock). It reuses the p4 stack and the
API knowledge from e021/e025/e036/e040.

## Inherits / references
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — conventions
- API patterns from e021-hyperliquid-playground, e036-trading-desk, e040-traderdev-local-replica

## What it is

A single-page, mobile-first, dark terminal that clones **gmgn.ai** on **two surfaces**
(venue toggle in the header):

- **Memecoins (Solana)** — the REAL GMGN clone: on-chain discovery (trending,
  new, boosts), token detail with price chart, market stats (mcap/FDV/volume/liquidity),
  buy/sell flow, top holders (best-effort on-chain) and socials. Data from
  **GeckoTerminal** (free public API) + **DexScreener** + **Solana RPC**.
- **Hyperliquid** — perps + spot terminal (see below).

Original GMGN-style features on the Hyperliquid surface:

- **Screener / Discovery** — tabs: Trending, Gainers, Losers, Volume, New; sortable
  columns; live search; Perps/Spot toggle.
- **Token detail** — price header, stat grid (Volume, OI, Funding, Oracle, Leverage
  / Market Cap, FDV, Supply), a candlestick chart with timeframe selector,
  buy/sell flow bars, recent-trades feed, and "whale moves" (largest notional trades).
- **Live-ish** — auto-refresh every 45s, `Cache-Control: no-store` so data is never stale.

## Verified facts about the Hyperliquid REST API

All calls are `POST https://api.hyperliquid.xyz/info`:

| payload type | returns | notes |
|---|---|---|
| `metaAndAssetCtxs` | `[meta, assetCtxs]` | perps; `assetCtxs` aligns 1:1 with `universe` |
| `spotMetaAndAssetCtxs` | `[meta, ctxs]` | `ctxs` has **more** entries than `universe` (718 vs 326) → must match by `ctx.coin`, not by index |
| `candleSnapshot` `{req:{coin,interval,startTime,endTime}}` | `[{t,T,s,i,o,c,h,l,v,n}]` | **no `limit`**; works for perp AND spot (`coin` = name or pair). `spotCandleSnapshot`/`spotRecentTrades` do NOT exist (422). |
| `recentTrades` `{coin}` | `[{coin,side,px,sz,time,hash,tid,users:[taker,maker]}]` | side `B`=buy, `A`=sell; works for perp AND spot |
| `l2Book` `{coin}` | `{coin,time,levels:[bids,asks]}` | works for both |
| `allMids` | `{coin: price}` | |

Spot caveats:
- Spot `universe` names are often placeholders like `@1`, `@2`; the *real* token
  symbol lives in `meta.tokens[i].name`. Map `pair.tokens[0] -> token.name` to get
  the display symbol, and keep `pair.name` as the API `coin` for candles/trades.
- Spot `ctxs` is NOT index-aligned with `universe`; build `{ctx.coin: ctx}`.

## Files
- `hl.py` — Hyperliquid client (TTL cache) + derived screener/token logic.
- `sol.py` — Solana memecoin client (GeckoTerminal + DexScreener + Solana RPC), cached.
- `app.py` — Flask backend (JSON API + read-only SQL snapshot cache).
- `templates/index.html`, `static/app.js`, `static/style.css` — SPA, no framework.

## Memecoin API (on-chain, free public APIs)
- `GET /api/memecoins/screener?sort=&order=&q=` — merged/de-duped feed (top pools + trending + boosts + new).
- `GET /api/memecoins/trending`
- `GET /api/memecoins/token?addr=<mint>` — detail seeded from the cached screener row (reliable), then enriched.
- `GET /api/memecoins/candles?pool=&interval=`
- `GET /api/memecoins/holders?addr=` — top holders, best-effort (Solana RPC; often rate-limited → empty).

## Data-source caveats (free APIs)
- **GeckoTerminal / DexScreener** are public + free but **rate-limit hard**; use TTL caching,
  `_get_retry`, and seed token detail from the cached screener to stay robust.
- **Top holders** needs Solana RPC `getTokenLargestAccounts`; public endpoints are
  429/403-blocked, so holders is best-effort — it shows a clear "unavailable" note when empty.
- GeckoTerminal `top_holders` requires an API key (401), so holders come from RPC instead.
- `bin/run.sh` — start server on `0.0.0.0:8338` (LAN/mobile accessible).
- `data/` — SQLite snapshot cache (`gmgn.sqlite3`), server log, saved screenshots.

## Run
```bash
./bin/run.sh      # or: python3 app.py
# phone/LAN: http://<machine-ip>:8338
```

## API endpoints
- `GET /api/health`
- `GET /api/meta?market=perp|spot`
- `GET /api/screener?market=&sort=&order=&q=&limit=` — sort keys: `price change volume mc fdv oi funding volume_base name`
- `GET /api/trending?market=&limit=`
- `GET /api/token?name=&market=`
- `GET /api/candles?name=&interval=&limit=` — intervals: 1m 3m 5m 15m 30m 1h 2h 4h 8h 12h 1d 3d 1w
- `GET /api/trades?name=&limit=` (returns trades + buy/sell `flow`)
- `GET /api/flow?name=` (flow + top `whales`)
- `GET /api/orderbook?name=`
- `GET /api/search?q=`
- `GET /api/db?sql=SELECT…` — read-only SQL over the snapshot cache (must start with SELECT)

## Frontend routing
- `#/` → screener, `#/token/<market>/<name>` → token detail (market is required so
  a token URL is self-contained; spot names resolve to their pair `coin` internally).

## Lessons learned (for future work)
- The browser tooling in this env: use `agent-browser` (drives Chrome via CDP) rather
  than raw `google-chrome --headless --screenshot`/`--dump-dom`, which hangs on GPU-less
  boxes. Launch Chrome yourself with `--remote-debugging-port` then `agent-browser connect <port>`.
- **Never** `pkill -f "app.py"` (or any `-f` pattern that appears in your own command
  line): it kills the invoking shell. Free the port with `fuser -k 8338/tcp` instead.
- Always bound long-running commands with `timeout`.
- The spot `metaAndAssetCtxs`-style response shape changed between p4 sessions; always
  re-validate field names before building against it.
