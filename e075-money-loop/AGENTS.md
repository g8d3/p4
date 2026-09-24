# e075 — Money Loop (autonomous, observable, paper-first)

Goal: one agent cycle that can make money with zero human intervention,
on rails where autonomy is actually possible (on-chain / Hyperliquid API),
with every decision visible on one page.

## Decisions (user-approved 2026-09-24)

- Venue: `hl_spot_funding` — Hyperliquid spot + funding only. No memecoins,
  no illiquid DEX lottery, no perps speculation to start.
- Mode: historical backtest first. Paper-trade history, then decide to
  deploy first funds. No live trades until backtest says GO + user says GO.
- Caps (conservative): ≤$5 per action, ≤$25 total exposure,
  full stop at -$10 realized or -20% on deployed pilot, whichever first.
- Scaffold now, trade later: this loop is PAPER-ONLY until two gates pass.

## Two gates to live (both required, in order)

1. `BACKTEST_GO`: `bin/backtest.py` on e025 history reports GO
   (expectancy > 2× round-trip fees, Sharpe > 0.3, ≥30 OOS trades).
2. `HUMAN_GO`: user writes `GO` into `data/human_go.txt`.
   Without both, `bin/loop.sh` refuses any live order path
   (which does not exist yet — live executor is OUT OF SCOPE for v0).

v0 ships: historical backtest + daily paper monitor + desk.
v1 (separate approval): tiny live executor with the same caps.

## Cycle (one iteration = one check + one ledger row + one desk render)

```
bin/loop.sh -> backtest.py + balance.py -> data/ledger.jsonl -> render_desk.py -> desk.html
```

- Idempotent. Safe to re-run. Never spends money in v0 ($0 loop).
- Live data used: Hyperliquid public `POST /info` only (no keys).
  Secrets (`WALLET_PRIVATE_KEY`, `HL_API_KEY`) are never read by v0 scripts.
- Kill switch: `touch STOP` halts the loop immediately. `rm STOP` resumes.
- Cron: NOT enabled in v0. Human runs `bash bin/loop.sh`. Cron only after
  backtest GO + explicit resume approval (repo-wide cron is PAUSED anyway).

## Strategies backtested (causal only, net of taker fees 0.045%/side)

- `S_FUND` (funding fade): daily mean funding z-score vs trailing 90d.
  z > +1.5 → SHORT 1 day (crowded longs fade). z < -1.5 → LONG 1 day.
  Prior e025/ag-09 evidence: NO reliable edge — this backtest re-proves it
  on the same data instead of trusting memory.
- `S_REV` (e025 daily decline reversion): T1 crash (ret < -3σ trailing 365d)
  OR T2 low-volume down (ret<0 and vol ratio < q20 trailing 101d).
  LONG 5 days, one position per coin, equal notional. e025 OOS expectancy
  +0.55%/trade, Sharpe 0.44, maxDD -32% — re-validated here, not assumed.

Recommendation logic (in `backtest.py`): GO only on OOS second-half numbers.

## Files

| File | Purpose |
|---|---|
| `bin/backtest.py` | Historical paper trading on e025 candles+funding. Stdlib only. |
| `bin/balance.py` | Read-only wallet snapshot (HL public API + public EVM RPCs). Never uses private keys. |
| `bin/loop.sh` | One iteration driver (STOP guard → backtest → balance → ledger → desk). |
| `bin/render_desk.py` | Rebuilds `desk.html` from ledger + backtest + balance. |
| `bin/serve.sh` | Local desk server (python http.server, no deps). |
| `data/config.json` | Venue, caps, fees, gates. The loop reads this, not prose. |
| `data/ledger.jsonl` | Append-only truth, one row per iteration. |
| `data/human_go.txt` | Empty = no human approval. Must contain `GO` for any future live step. |
| `desk.html` | Observer desk — watch this, never the chat log. |
| `log/` | `backtest.json`, `balance.json`, `loop.log`. |

## Observer contract

Everything reviewable lives on `desk.html`: pulse, wallet snapshot,
backtest verdict (GO/NOGO with numbers), strategy table, ledger history,
caps, gates, kill-switch state. If it is not on the desk, it did not happen.

## Hard rules

- PAPER rows never count as profit. Only on-chain receipts count (v1+).
- No private keys, seeds, or API secrets in repo, logs, or desk output.
- Fees always applied in backtest. No lookahead (trailing windows only).
- One fact per column on the desk; stale data gets a STALE badge, never deleted.
