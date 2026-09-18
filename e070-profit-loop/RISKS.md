# e070 Risk Register — read before activating the loop

Status: SCAFFOLD ONLY. No continuous work runs. Cron repo-wide is PAUSED
since 2026-09-15. Activating anything needs explicit user approval.

| # | Risk | Likelihood / Impact | Mitigation | Tripwire |
|---|---|---|---|---|
| R1 | Loop silently stops (session death, reboot, API outage, 429, expired key, cron still paused) and nobody notices; "continuous" was an illusion | High / High | Heartbeat file + watchdog with staleness threshold; idempotent `loop.sh`; every iteration logs start/end; stale badge in any UI | `bin/watchdog.sh` nonzero, or no heartbeat in 2x period |
| R2 | No money-handling tools (no wallet, no exchange keys, no payout rails) → agents drift: fake "profit" (paper treated as real) or scammy monetization to show progress | High / High | PAPER vs CONFIRMED split in ledger (only receipts count); payout-rail checklist before any cash claim; blocklist: no private keys/seeds/orders in repo or logs | Any ledger row claiming profit without receipt id |
| R3 | Credit overspend: loop burns the full $9.81 on triage with zero return | Medium / High | `credits.py` floor gate ($0.80 reserve); $2.50 pilot cap; per-task cost logged; cheapest model first (Jev ~$0.015/1k) | Cost-per-iteration rising, or floor breach |
| R4 | Scope drift: agents chase memecoin lottery or paid X pipe (Jev: meme_profitable 0.09) to "go faster" | Medium / High | Pinned Jev verdict in AGENTS.md; Track A/B allowlist; any new track needs a Jev comparison + user nod | Non-allowlist model/venue/pipe appears in ledger |
| R5 | Bounty fraud: fake bounties, wallet-connect scams, "pay fee to unlock payout" | Medium / High | Jev scam screen on every task (tested 0.94–0.98 on scams); never connect wallets; never pay upfront fees; `needsCap` check | scam_score > 0.5 → auto-skip + log |
| R6 | Secret leakage into logs/repos (API keys, tokens) | Medium / High | Env-only keys; never print secrets; `data/` + `log/` ignored by git; pre-commit grep for `sk-` | Any secret-shaped string in tracked files |
| R7 | ToS violations (X scraping, spam outreach, unofficial APIs) | Medium / Medium | Free-official sources only (Dexscreener, venue-direct); no X scraping; no bulk outreach | New data source without ToS note |
| R8 | False profit claims (paper P&L screenshots sold as edge) | Medium / Medium | Ledger schema enforces `kind: PAPER\|CONFIRMED`; Track B channel labeled paper until receipts | PAPER row cited as profit |
| R9 | Two-agent write conflicts (scout + builder clobbering ledger/state) | Medium / Medium | Single-writer rule: append-only JSONL, one line per event, atomic appends; agents own separate scratch files | Interleaved/corrupt ledger line |
| R10 | Watchdog flapping: restarts loop constantly, burning credits while "helping" | Low / Medium | Backoff + max 6 restarts/day circuit breaker; watchdog never spends inference itself (no model calls) | >6 wakeups/day → page human, stop auto |

## Two-agent split (when activated)

- Scout (cheap, Jev-only): discovers tasks, triages, writes `data/candidates.jsonl`. No LLM calls.
- Builder (expensive): reads top candidate, attempts with coder LLM, verifies with tests, appends ledger.
- Each writes own heartbeat (`who=scout|builder|watchdog`). Watchdog spends $0.

## Activation checklist (all required)

1. User explicitly resumes cron or approves manual cadence.
2. Payout rails documented (where does cash land? who owns it?).
3. Pilot cap set ($2.50) and floor verified via `bin/credits.py`.
4. `bin/chaos.sh` passes 10/10 with live files intact (tripwires proven, $0 spent).
