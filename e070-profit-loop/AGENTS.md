# e070 — Profit Loop (Jev-gated bounty harvester)

Goal: convert ~$9.81 OpenRouter inference credits into real cash to buy
more credits. Jev triages cheap; expensive LLMs touch only high-EV tasks.

## Verdict that pins scope (2026-09-18, Jev via OpenRouter, ~$0.0002)

- 100-vertical choice: `bounty_coding` 0.49, `freelance_api_integration` 0.29.
- 22-option ladder: `sell_signals` 0.38 vs `sell_labor_direct` 0.34 (split).
- Absolute 14d scoring: `bounty_coding` EV 0.97 / feas 1.36 / speed 0.83 /
  buyer 0.57 wins on cash-now; `sell_signals` EV 0.06 — best destination,
  worst 14-day cash (no buyers yet).
- `meme_profitable` 0.09. Live meme trading is OUT for the cash track.
- `small_test $2-3 first` 0.99. `spend_to_zero` 0.12 — never run to zero.

## Two tracks, one loop

- Track A (cash now): `bounty_coding` + `sell_labor_direct`. Jev screens
  every task (scam, EV, fit, difficulty); escalate to coder LLM only if
  EV high AND confidence > 0.6.
- Track B (free, background): `ship_funding_alerts` on the e058 scanner —
  public proof-of-work channel that grows into `sell_signals` later.
  No paid X pipe. Dexscreener + venue-direct free APIs only.

## Payout rails (decided 2026-09-18, owner drives, asker only does human gates)

- Track B (sell alerts/API): **Polar MoR fits Colombia, no LLC.** Colombia is on
  Polar's Stripe-Connect-Express payout list; individuals can sell globally,
  no Stripe-in-country and no US LLC needed. No Polar keys in env yet — when the
  asker provides `POLAR_API_KEY`, verify with `GET /v1/products?limit=1` (200 =
  active) plus payout-account-connected check.
- Track A (bounty inbound): Polar is irrelevant — money flows platform→asker
  (Algora `/tip` → Stripe claim link → **human-only** claim with GitHub login,
  per e054 PLAYBOOK). e054's richest vein (Turso $1k/bug) is DEAD (program
  retired) — so scout runs **recon-first** (live-vein confirmation, paper-only)
  before any hunt spend. Candidates: Polar.sh bounties, new Algora challenges,
  per-org `/tip` history.
- Roles: the owner (this session) decides and executes everything; the asker only
  clears human-only gates (account registration, claim clicks, secrets via env,
  legal/tax). Watching is done by the PROGRAM (heartbeat + watchdog + desk),
  not by the owner personally — the owner reviews on wake and reports here.

## Recon leg 1 result (2026-09-18, scout, $0.00013) — DECISION: park Track A

- Live-verified: Turso retired; all 4 Algora challenges Completed; Polar has no
  bounty program (pure billing SaaS). Jev EV 0 on all five defined programs.
- Only non-zero vein: ad-hoc `/tip` on merged Turso PRs (rail proven, no live
  buyer) → WATCH, $0 spend, trigger-based re-check only (new `/tip` comment or
  new Algora challenge). Never re-scan the dead list on a schedule.
- Liveness test (codified): "latest merged PR carries a maintainer tip comment"
  is the cheap decisive live-buyer probe.
- Pivot: effort moves to Track B (alert shipper dry-run); Track A wakes only on
  trigger or a widened-map recon leg.

## Builder leg 1 result (2026-09-18, builder, $0.00002) — DECISION: B-paid KILL

- Dry-run works (exit 0, `bin/alert_dryrun.py`, e058 untouched): top persistent
  spreads found, decay trap correctly avoided (T 10392%→3975% rejected, LSK
  picked). Feed itself is STALE (sampler halted Sep 15, cron paused repo-wide).
- Jev: `buyer_exists` 0.08, `feasibility_14d` 0.24 → paid tier KILLED for 14d.
  Blocker is distribution (no audience), not data. Track B stays free
  proof-of-work only; needs live feed + first inbound interest to revisit.
- Next (decided): widen-map recon leg — freelance API/automation gigs, template
  packs, one-trader scoring pilot (Jev's untested runners-up). Both cash tracks
  resolved negative; the map, not the loop, was wrong.

## Multi-agent system (decided 2026-09-18, owner) — replaces single-loop legs

- Watcher (`bin/watch.py`, $0 inference): finds just-opened bounties/contests via
  time-boxed web search, diffs against `data/watch.jsonl`. Speed wins claims.
- Hunter (Jev triage + builder): scores watcher finds, keeps live ones, runs
  claim→fix→submit in one pass. Escalates to expensive LLM only on high EV.
- Trend-scout (`bin/trends.py`, $0 inference): permanent web radar on agent-earning
  trends → `data/trends.jsonl`. Demand-side only (who PAYS, never rails).
- x402 rule (2026-09-18, user): x402 is a rail aggregator over existing chain
  payments — never a task, vein, or radar query. Banned from scout/hunter/trend
  scope until a buyer asks to pay per call. Agents that mention it as an
  opportunity are drifting; the endpoint stays parked at $0.
- Keeper (`bin/metrics.py`, $0, read-only): KPIs in `data/metrics.jsonl` — finds_7d,
  cost_per_find_7d, confirmed_payouts, revenue, roi. Improvement rule: week-over-week
  finds up OR cost-per-find down; else the owner logs a pivot decision.
- Wallet: agent-controlled Arbitrum wallet (~$100 USDC verified 2026-09-18).
  On-chain pilot caps: ≤$5 per action, ≤$25 total; every spend logged with tx hash.
  Keys via env only (`WALLET_PRIVATE_KEY`), never in repo/logs. Human tops up on
  request, never per-cycle. First runs are supervised; autonomy grows with receipts.
- v0 honesty: watcher finds are noisy (generic articles mixed in) — the hunter's
  first job is the Jev filter layer before any claim spend.

## Hard rules

- PAPER-ONLY ledger until pilot proves EV. Paper rows are labeled PAPER;
  only confirmed receipts count as profit. No live trading keys in repo.
- Never print secrets. Keys via env only (`OPENROUTER_API_KEY`).
- Paper-track before live. $50 single-spend cap (inherited from e058).
- No wallet connects, no upfront fees, no wallet seeds in repo or logs.
- Jev-first: every task gets the cheap gate before any expensive call.
- Cron is PAUSED repo-wide since 2026-09-15 (user request). Nothing in
  this experiment runs on its own until the user explicitly resumes it.

## Smart stops (user-approved)

Halt whichever first: reserve floor ($0.80 left), +$50 confirmed payout,
10 consecutive fails (edge decay), $2.50 pilot spend, or 14-day time box.

## Runtime (where the cycle lives) — agreed 2026-09-18

- The cycle is a PROGRAM on this machine, not this chat: `loop.sh` on cron
  cadence + `watchdog.sh` + desk on :8327. This chat is supervision only.
- Phase 1 (now): supervised pilot — the owner runs bounded evidence legs and
  records every pivot in `data/decisions.jsonl`, which the desk renders.
  Subsessions are scaffolding for evidence-gathering, not the cycle itself.
- Phase 2 (autonomous): legs codified as `loop.sh` tasks, cron resumed
  (currently PAUSED repo-wide — needs the asker's explicit resume), no chat
  involvement except wake-ups. Transition when: chaos 10/10 stays green, one
  PURSUE with proven EV exists, and pilot spend is inside cap.
- One live session per role: never spawn a second scout/builder while one is
  live (check `list_subsessions` first). Every spawn/completion is recorded in
  `data/sessions.jsonl` (newest first on the desk) so the asker can open any
  session in the pi web UI under Sessions.
- The asker watches the page, never the chat log. Pivots show on the page
  because they are data (`decisions.jsonl`), not prose.

## Files

| File | Purpose |
|---|---|
| `bin/triage.py` | Jev gate: task in → scam/EV/fit/difficulty out (OpenRouter `/api/alpha/decisions`) |
| `bin/credits.py` | Credit watcher: prints balance, exit 2 if below floor |
| `bin/loop.sh` | One idempotent pilot iteration (heartbeat → credits gate → triage → ledger) |
| `bin/heartbeat.sh` | Append heartbeat with start/end event (finished can never read LIVE) |
| `bin/watchdog.sh` | WAKEUP on true silence; tolerates parked (finished) legs up to end-limit |
| `bin/cycle.sh` | Daemon driver (30min cadence, single-instance guarded — refuses a second driver) |
| `bin/desk.py` + `bin/desk.sh` | Read-only dashboard on :8327 (verdict + pulse + pipeline stages + money + 7 native SQL tables in pipeline order; refresh ticks pulse+credits only so sort/filter state persists) |
| `bin/tables.py` | Native table renderer (stdlib only) + the ONE place where rows/columns/views are defined (pipeline stages, opportunities, ledger, decisions, sessions, trends, finds, resources, funds) |
| `bin/selfcheck.py` | Dogfood check: uses the desk as a user (page + API asserts, $0). Failures → `log/desk-issues.jsonl` |
| `bin/rendercheck.sh` | Rendered-DOM proof: real browser with JS, reads VISIBLE text, records WebGL renderer (GPU→CPU regression fails). Required before/after UI changes. |
| `bin/chaos.sh` | Pre-flight resilience suite: simulates 10 interruptions (death, floor breach, outages, corruption) and proves tripwires fire. $0 spend. Must be 10/10 before go. |
| `data/ledger.jsonl` | Append-only ledger (the money truth; folder is source of truth) |
| `log/loop.log` | Iteration log |
| `RISKS.md` | Risk register (read before activating anything) |
| `LEDGER.md` | Ledger schema |

## Inherits
- [../../e000-fundamentals/TABLE_FIRST.md](../../e000-fundamentals/TABLE_FIRST.md) — table-first rule + table_check.py
- [../../e000-fundamentals/TABLE_UX.md](../../e000-fundamentals/TABLE_UX.md) — table UX rules (sort/filter/page-size/cards, implemented natively)
- [../../e000-fundamentals/ONE_TABLE.md](../../e000-fundamentals/ONE_TABLE.md) — one entity, one table; cuts are views, never copies
- [../../e000-fundamentals/USER_TZ.md](../../e000-fundamentals/USER_TZ.md) — store UTC, show user zone (default `America/Bogota`, override `E070_TZ`)

## SQL-table rule (standing user rule, 2026-09-18)

UNSTRUCTURED DATA DUMPS ON THE PAGE ARE FORBIDDEN. Every fact lives in
a table with named atomic columns, and every table carries the functions
of SQL — with NO commands typed. SQL verbs are UI gestures:

| SQL | UI gesture (no typing) |
|---|---|
| SELECT | visible columns + cards view on narrow screens |
| WHERE / LIKE | filter input inside the column (multi-value = OR) |
| WHERE BETWEEN | min+max range inputs (numeric/date columns) |
| ORDER BY | tap column header (tap again = reverse) |
| LIMIT / OFFSET | pager + per-page control (10/25/50/all) |
| VIEW | preset chips over the same rows (e.g. 👀 needs-you) |
| UNION | one table rolled up from several sources (opportunities) |

ONE_TABLE: one entity = one table, named by its grain. New question =
column, filter, or VIEW chip — never a second table. Proven here: the old
`gates` table was the same grain as `opportunities`, so it was merged in
(take/you_do/agent_does columns) and its focused cut survives as the
needs-you VIEW chip. Zero duplicated rows.

Contributor rule: new page table? It is defined in `bin/tables.py` and
rendered with the native `render` — stdlib only, never hand-rolled HTML,
never an external table library. Every table states its row count,
paginates, persists state per table, and prints the one-line SQL legend
above it so the user knows the gestures without asking.

## Dogfood rule (agents are users of the desk too)

- Before and after every desk change: `python3 bin/selfcheck.py` (must end SELFCHECK OK).
- Every user-reported or self-found page bug goes to `log/desk-issues.jsonl` with a fix, same session if small.
- Desk work is a bounded second lane: max 10% of pilot spend, only when Track A is idle or blocked. It never outranks the cash loop.

## One mission at a time

- The two loop agents work ONE project at a time (this experiment). No parallel
  projects: the $2.50 pilot is too thin to split, and parallel lanes are how
  scope drift (R4) starts.
- New ideas wait in the ledger as PAPER notes with a Jev score, then run as
  sequential sprints — never as simultaneous second loops.

## Conventions

- Every command: timeout it. Append-only writes to ledger (never rewrite).
- If a file is missing/stale, show a stale badge instead of guessing.
- Verify: `python3 bin/credits.py`, `bash bin/heartbeat.sh && bash bin/watchdog.sh 30`,
  `bash bin/loop.sh` (ends `iteration OK`).
- Desk: `bash bin/desk.sh`, open `http://<machine-ip>:8327` from the phone.
