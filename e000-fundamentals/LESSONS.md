# LESSONS — distilled from the 2026-09-13 owner review marathon

Nine hours, five apps, one chat. Everything the owner taught the
system today, indexed so no future chat repeats it. Details live in
the linked files; this is the map.

## The owner's laws (define PROGRESS)

- **Progress = more and better functions, easier to use, less human
  work.** The system runs like a miner with useful proof-of-work: the
  human starts it, proof numbers move, humans pay, the system lives.
  (DIRECTIVES PROGRESS)
- **UX LAW** (`UX.md` §§1–15): time on every number; agents out-think
  the owner; named sections; honest filters; aligned forms; shareables
  are pretty pages; plain words first; decode dense lines; SQL-grade
  tables; tables grow both ways with agent-suggested columns; tap
  gives never takes; wandering tests; adaptive columns; lineage
  visible; viewer-local times.
- **Notifications = progress only** (record-slip: score + velocity),
  then silence. A ping with no owner action is noise by definition.
  e058 is digest-only. (DIRECTIVES PROGRESS)
- **Money**: T1 ≤$50 auto+logged, bigger = propose + wait. Never open
  positions without an approved proposal. **Clone-before-pay**: any
  paid need arrives with a build-the-subset quote first. (SPEND.md)
- **Ladder discipline**: HYPOTHESIS → BACKTEST → PAPER → PROPOSE, never
  skip. N<20 = THIN, never propose real money on THIN. (per-track
  STRATEGIES.md)

## Operating agreements (how work ships)

- Legs read DIRECTIVES + ops state, advance lowest rung / revive
  stale, beat `OWNER_SENTENCE | tech: detail`, exit. Continuity from
  state, not stamina.
- After editing ANY served app: restart, check version endpoint
  (running == latest, code-scoped), then claim done. Docs never fake
  STALE (code-only version scope — learned the hard way, §STALE saga).
- e2e asserts new wording, not old (tests check the fix, never the bug).
- Every owner-found miss lands in `ATTENTION.md` with hrs-unnoticed +
  why-missed. Fixes without rows are half fixes.
- Every leg banks ≥1 idea in `p4/IDEAS.md` (public by construction —
  the board renders it). New tracks only on owner yes.
- Static files need cache-bust (`no-store` + timestamp) or phones
  show yesterday. (e061 lesson)

## Taxonomy proposal (60+ experiments need order)

- **Time-blocks**: the ops-board fleet (e058–e063 + runner) is one
  block — the currently-managed set. New owner interests form the
  next block; the queue (directories, player, wanderer) waits behind.
- **Categories** (orthogonal to blocks): money/earn, radar/measure,
  play/engage, infra/ops, data/sell. Tag tracks; let the board filter
  by either axis. (To be enacted — owner to bless.)
- Rule: a track belongs to exactly one block and ≥1 category.

## Session stats (measure to decide)

- Exists: `bin/tokens.py` — start→end context, hola-share, in/out,
  cache, cost per session file. Runner logs per-leg ctx
  (e.g. `ctx=10620->56476`).
- This session (live proof): **186 turns, 8,768 → 232,747 tokens
  (+224k, hola-share 4%), $0.24.** The hola cost is fixed overhead;
  growth rate is the optimizable number.
- Missing (queued): per-session stats surfaced on the board (legs +
  interactive), hola-share trend per leg (prompt-trim feedback loop),
  quota meter (needs owner cookie paste), fill-% (needs model window).

## Board control gaps (total session control, not yet achieved)

- The board shows legs/runs but doesn't *control* sessions (pause,
  kill, branch, budget-cap a live session). Visualization for total
  control is still missing — the nested-tables-max-space grail.
- Direction (owner-blessed): finish v2 (:8325, patch render, SSE,
  inbox-zero) to parity, cut daily driving over, keep v1 as admin.
- Scheduler direction: cron/30min is training wheels → event-driven
  (finish → next starts, spawning helpers).

## Open threads (not closed today)

- Quota probe waits on cookie paste (`~/.config/e062/opencode_cookie`).
- Share pages (UX §6): ballot sections are the data, links come later.
- e060 social pipe: free first (Alternative.me), paid quoted.
- Candidate tracks: web3 dev-services directory, social-API directory,
  player experiment (L1 works / L2 earns), wanderer agent.
- e061 metric redesign: server play log + verifiable day-1 proof.
