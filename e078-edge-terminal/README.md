# Edge Terminal

**Decide, don't dabble.** A crypto decision terminal: live perp board, a risk-tier
decision card (LONG / WAIT with entry, stop, target, size), a DefiLlama LP
comparison, a paper portfolio, and — the part that matters — a *receipt*: the
signal's own track record, backtested and logged live.

Paper first. No keys, no orders, no custody. Live execution is gated behind
`data/human_go.txt` + a positive paper ledger (≥50 closed trades).

## Run

```bash
bash bin/serve.sh          # start (prints LAN + tailnet URLs)
bash bin/gpu-browser.sh open   # Chrome on the real AMD GPU + agent-browser attached
npm test                   # 19 assertions over the math that gives trading advice
bash bin/loop.sh one       # one agent cycle -> data/loop_log.jsonl + public/desk.html
bash bin/loop.sh watch     # forever, until data/LOOP_STOP
```

Pages:

| URL | What |
|---|---|
| `/` | the terminal (Markets · Trade · LP · Portfolio) |
| `/admin.html` | ops: cache, upstream errors, ledger, needs.json, config reload, kill switch |
| `/desk.html` | observer desk — one row per agent cycle |

## Tabs

- **Markets** — sortable board (price, 24h, funding APR, OI, RSI, 7d, signal, conviction)
  plus the **track record header**: `180d backtest win rate / avg R / maxDD` and the
  count of live calls resolving at a fixed horizon. Per-coin breakdown on expand.
- **Trade** — GPU (WebGL) candle chart, risk tier selector, decision card with
  entry / stop / target / size / leverage / R:R / fee-vs-risk, a **receipt line**
  (how this coin's signals performed historically), invalidation rule, confirm
  dialog, and a **share card** that exports a 1200×630 PNG + copies the call text.
- **LP** — live DefiLlama pools vs the trade alternative on the same weekly scale,
  with the model assumption and the live data explicitly labelled as such.
- **Portfolio** — paper positions with live PnL, stops/targets enforced, liquidation
  cushion, LP accrual, history, and portfolio-level risk rails.

## Risk tiers (config, never hardcoded)

`server/config.json → tiers`: `conservative` (0.5% risk, 1×, wide stop, yield first),
`balanced` (1%, 2×), `degen` (3%, 5×, tight stop). They change risk per trade, max
leverage, ATR stop/target multiples and the minimum signal strength required to act.

## Signal

`public/engine.js` is the single source of truth — required by the Node server,
loaded by the browser, asserted by `test/engine.test.js`:

```
score = 0.40·trend + 0.20·rsi + 0.25·momentum + 0.15·funding(z)   in [-1, +1]
LONG if score ≥ +0.25, SHORT if ≤ −0.25, else NEUTRAL   (thresholds in config)
```

Funding uses the **7-day z-score of Hyperliquid's hourly funding history** — the live
`funding` field is pinned at HL's 1.25e-5/hour floor for most coins and is useless
for ranking.

## Receipts

- `/api/backtest` — 180d of daily candles per coin, the same `scoreOf()`, forward
  3-day horizon, stop/target checked bar by bar (stop wins ties), tier stops.
  Cached 15 min. Labelled in-sample in the UI.
- `/api/track` — every signal the board prints is appended to `data/signals.jsonl`
  (deduped per coin+side every 6h) and resolved at the 4h horizon.

## Admin

`/api/status` (stats, cache, gates, needs) · `POST /api/admin/reload` (re-read
`config.json`, no restart) · `POST /api/admin/kill|unkill` (`data/STOP` → `/api/board`
returns 503 and the app shows a kill banner) · `GET|POST /api/ledger` (server-side
paper ledger, so the live-money gate is auditable from any browser).

## DX

- `dev.liveReload` in config: the page polls `/api/version` and reloads itself when
  you save a file — edit `public/*`, watch the browser follow.
- Static assets are served `no-cache`; JSON >2KB gzipped; `/api/candles` validates
  coin + interval; test + `npm run check` cover the shared engine.

## Layout

```
public/     index.html app.js chart.js(WEBGL) engine.js(shared math) style.css admin.{html,js} desk.html
server/     server.js (zero deps)  config.json (every machine value)
bin/        serve.sh gpu-browser.sh loop.sh loop.py
test/       engine.test.js (node:test, 19 assertions)
data/       ledger.jsonl signals.jsonl loop_log.jsonl [STOP human_go.txt]
shots/      screenshots from the user-seat review
```
