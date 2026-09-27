# e078 — Edge Terminal (crypto decision terminal, paper-first)

Goal: one screen that tells a user whether to trade or provide liquidity at their
risk tier — with the receipts to justify it — and that can grow into a money-maker
behind gates (paper first, real money only after proof + human GO).

## Inherits
- [../AGENTS.md](../AGENTS.md) — standing rules (server status, user-seat review, config-over-hardcode)
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles, command rules, GPU rules

## Product

**Edge Terminal** — decide, don't dabble.

| Surface | What the user does |
|---|---|
| Markets | Sortable board (price, 24h, funding APR, OI, RSI, 7d, signal, conviction) + **track-record header**: 180d backtest win rate/avg R/maxDD and live calls resolving at a fixed horizon |
| Trade | WebGL candle chart (GPU), risk tier selector, decision card (entry/stop/target/size/lev/R:R/fee-vs-risk + per-coin receipt + invalidation rule), confirm dialog, **share card** PNG export |
| LP | DefiLlama pools vs the trade alternative on the same weekly scale, model vs live data labelled |
| Portfolio | Paper positions, live PnL, stop/target/liquidation, LP accrual, history, portfolio risk rails |
| `/admin.html` | Ops: cache, upstream errors, ledger, needs.json, config reload, kill switch |
| `/desk.html` | Observer desk — one row per agent cycle (bin/loop.sh) |

Risk tiers live in `server/config.json → tiers` (conservative / balanced / degen).

## Architecture

```
public/engine.js   SHARED MATH — required by server, loaded by browser, asserted by tests
server/server.js   zero-dependency Node server: static + /api/* with TTL cache
server/config.json ALL machine values: port, upstreams, universe, tiers, risk rails, TTLs
bin/serve.sh       start/stop/restart + URL report (LAN/tailnet resolved live)
bin/gpu-browser.sh Chrome on the real AMD GPU (--use-angle=vulkan) + agent-browser attach
bin/loop.sh|py     one agent cycle: probe /api/* -> data/loop_log.jsonl -> public/desk.html
test/              node:test over indicators, scoring, sizing, fee math
```

Upstreams (keyless, list in config): Hyperliquid `POST /info`, DefiLlama yields,
alternative.me Fear&Greed. Keyful sources go through `needs.json` first.

## Gates (paper first)

v0 is PAPER ONLY. Positions live in `localStorage`, every fill also posts to the
server ledger (`/api/ledger` → `data/ledger.jsonl`) so the gate is auditable.
Live executor is out of scope until the paper ledger shows positive expectancy over
≥50 closed trades AND the human writes `GO` in `data/human_go.txt`.
Kill switch: `data/STOP` (or the Admin button) → `/api/board` returns 503, the app
shows a kill banner.

## GPU rule (this experiment)

The browser MUST run on the AMD GPU (ANGLE over RADV Vulkan), not SwiftShader —
agent-browser's own launcher hardcodes `--use-gl=swiftshader`, so we launch Chrome
ourselves and `agent-browser connect <port>`. Proof: `bin/gpu-browser.sh verify`
prints the WebGL renderer (must say RADV). The chart is real WebGL work every frame.
The GPU badge in the UI is hidden unless `?debug=1` — it is an internal artifact,
except when the renderer is software, where it always shows.

## Learnings (pitfalls for the next agent)

- **HL funding lies**: `assetCtxs[].funding` sits at the 1.25e-5/hour floor for most
  coins — identical values across the universe. Use `fundingHistory` (hourly; APR =
  rate×24×365) and its 7d z-score instead.
- **HL candles come as strings** — arithmetic on them concatenates (`"1.69"+"0.36"`),
  which silently poisons a backtest with NaN. Normalize at the boundary.
- **Never `pkill -f <pattern>`** when your own shell command line contains that
  pattern — it kills the tool session (happened here). Kill by PID or use
  `bin/serve.sh stop`.
- **Screenshots lag one capture**: the file on disk is current, the preview you read
  right after may show the previous frame. Re-read before judging a visual change.
- **Empty candle responses are not errors** — a coin with no candles would otherwise
  publish a hollow row (null indicators → bogus NEUTRAL score). Keep the last good
  row (`lastGood`), mark it `stale`, and drop coins that never had data.
- **Config is hot-reloaded** via `POST /api/admin/reload`; restart only after
  changing `server/server.js`.

## Run

```bash
bash bin/serve.sh              # start + URL report
bash bin/gpu-browser.sh open   # GPU browser on the app
npm test && npm run check      # 19 assertions + syntax
bash bin/loop.sh one           # one agent cycle -> public/desk.html
```

## Backlog (v3 candidates, from the v2 critique)

Alerts (webhook/ntfy on score crossings) · watchlist + sparklines + column memory ·
equity curve / export CSV · token fee-router builder (configurable fee splits to
LP / burn / stake / vault / perps) · external trader leaderboard · PWA install ·
light theme · per-coin funding OI sparklines · state sync beyond localStorage.
