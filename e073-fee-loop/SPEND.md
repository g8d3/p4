# SPEND — owner authorization (2026-09-24, standing order)

Owner: **use all credits.** No cap. Background intelligence stays on.

## Priority order (spend flows down, never up)

1. Stranger-facing proof: M1 referral page, paid actions, town participation.
2. Tables that earn: row-adders, scouts, freshness legs with filled columns.
3. Debates: positions argued with other agents, recorded.
4. Toy sims and polish: last, killed first if movement stalls.

## Movement rule (spending without movement = stop and report)

Spend is authorized; waste is not. If two consecutive reviews show no movement
in the three numbers (town status, table rows/columns, stranger count),
legs halt and the session reports instead of burning. Flat curves confess.

## Metering

Every LLM leg appends one row to `ledger/credits.jsonl` (kind=llm, model,
task, cost or unmetered-note). `bin/verify.sh` prints the running total.
Reconcile against the OpenCode dashboard; the photo is the cross-check.

## Safety rails (unchanged)

- No keys/tokens/passwords in town or logs. `.token` chmod 600, never committed.
- No mainnet money moves. Testnet/paper only until timelocked proposal + owner veto window.
- Rate limits: backoff, never hammer (the town already throttles us).
