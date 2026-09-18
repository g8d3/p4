# Ledger schema — `data/ledger.jsonl` (append-only, one JSON object per line)

- The folder is the source of truth. Sessions are ephemeral; this file is not.
- Never rewrite history. Corrections are new lines with `{"corrects": "<id>"}`.

```json
{"id":"evt-0001","ts":"2026-09-18T00:00:00Z","who":"scout|builder|watchdog|human","kind":"PAPER|CONFIRMED|COST|STOP","track":"A|B","task":"short id or url","jev":{"scam":0.0,"ev":0.0,"conf":0.0},"cost_usd":0.00002,"note":"one line"}
```

Rules:

- `PAPER` = simulated/prospective value. Never counted as profit.
- `CONFIRMED` = cash receipt with `receipt` field (tx id, payout id). Only these count.
- `COST` = inference spend per action (from API `usage.cost`). Builder LLM calls are logged as `{"kind":"COST","who":"builder","model":"...","cost_usd":...}` — these rows are the LLM side of the Jev-utilization metric on the desk.
- `STOP` = which stop rule fired (reserve|target|decay|pilot_cap|timebox).
- Running totals are computed from the file, never stored as editable state.
