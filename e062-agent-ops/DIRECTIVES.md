# DIRECTIVES — owner steering for the runner (tracked, edit anytime)

The runner reads this file every leg. Highest authority after hard rules.
Owner steers by talking to any agent session ("pause X", "approve #N",
"priority: ...", "new idea: ...") — the agent updates this file.

## Standing orders (2026-09-12, owner-activated)

- NORTH STAR (law): every leg lets the owner do MORE business from his phone while needing to know LESS (<30s, no explanation). Simplify + add power, together, every leg. Full statement: `VISION.md` — the wheel that spins forever.
- PROGRESS (owner 2026-09-13): progress = finished work the owner can use from his phone in <30s with no explanation. The ladder (rungs 1-5) is scaffolding for agents, never reported as progress. A leg with no visible change = FAILED leg, even if e2e PASS. Every leg ships ONE visible thing: tables everywhere, zero loose text, one more data column or intelligence on real rows.
- STUCK RULE (owner 2026-09-13): same proof number 2 legs = blocked. Third leg must add data (free source auto) or kill the line and move. Never re-grade the same N to fake +0.3pp.
- TAX (owner 2026-09-14): initiative never waits on tax fear. Legs transact freely inside risk bounds; the fleet builds and maintains the tax-reporting app (every money action logged with tx hash, timestamp, amounts → report-ready export), so the owner never untangles anything by hand.
- VERSIONS (owner 2026-09-14, corrected): every track has BEST (stable, serves users) + NEXT (experimental). Legs break NEXT freely. NEXT auto-promotes to BEST when its proof number beats BEST with e2e PASS — the market and the agents decide, never the owner. The board button only forces it early; the owner keeps a veto (revert), never a bottleneck.
- SCHEDULER DIRECTION (owner 2026-09-13): cron every 30 min is training wheels. Target: event-driven — an agent finishes, the next starts (spawning helpers or parallel starts as needed). Move there when leg instructions are trusted.
- CREDIT GAME (owner 2026-09-13): legs see real wallet funds on the board (funds, in/out). Every leg either moves a proof number toward earnings or states its cost plainly. Wallets empty → owner gets one `no money — send more` ping, legs wait. Agents know the game: credits fund value, value funds credits — earn the next leg.
- BROWSER DISCIPLINE (owner 2026-09-13): web work goes through the browser-extract skill (agent-browser, stealth flags, block images/media/fonts, close fast) — never hand-rolled CDP marathons, never CPU rendering when GPU exists. Logins come from the vault path only, never pasted secrets. Captcha hit = stop + report, never grind.
- AUTONOMY: FULL-T1 (owner-authorized 2026-09-12). UI fixes, pricing drafts, saved-data put to work, paper-trading/strategy/backtest probes AUTO (log T1 ≤$50). Real charges/positions/KYC = propose + wait.
- EVERYTHING MANDATE (owner 2026-09-13, correcting the record): the agents' job is EVERYTHING — improve what exists, fix what exists, AND invent new projects unprompted. UI work is never "not their job". A leg that finds nothing to improve didn't look (open every app as the owner, from the phone).
- WANDER (owner 2026-09-15): twice daily the wander cron photographs every app at phone width (`e062/wander/shots/`, spec in `WANDER.md`). Every leg starts by claiming `wander/claim.json` and reviewing the newest shots with eyes before other work — confusion found becomes a fix (T1-auto, NEXT→e2e→BEST) plus one ATTENTION.md row with its finding story. A finding alive after two wanders becomes data or dies in writing, never a third log.
- MOBILE HARD RULES: primary controls in thumb zone (bottom); cards contain tables (no new page tables); long text = 1-line summary + expand; tables scroll inside, sticky header.
- REPORTING: every beat/event = `OWNER_SENTENCE | tech: detail`. Board pref `report` (simple/both/tech, default simple) controls display; never delete either half.
- NOTIFY (owner 2026-09-14): ntfy only on proof-number moves or money events — conclusions-only, one ping per move. While debugging, small results may ping; once running, only big results. A ping with no moved number and no money = flood = leg failure.
- UX LAW (owner 2026-09-13, details in p4/e000-fundamentals/UX.md): every number shows its time window; every section has a name; filters cover everything visible; forms aligned grid; shareables are pretty pages, not clipboard; agents must spot confusion before the owner reports it (misses go in ATTENTION.md).
- IDEA PIPELINE (owner 2026-09-13): every leg banks ≥1 improvement idea in p4/IDEAS.md (one line + date + track). The board renders that file, so all ideas are public by construction — this experiment and all others.
- CONFIGURABILITY RULE (owner pattern): every either/or display decision ships as a board toggle with a sane default (simple), never as a hardcoded choice.
- DIRECTION (owner 2026-09-13, extended 2026-09-14 with e064+e065+e066): one proof loop per track, ALL of them, data by proposal (free sources auto, paid/credentialed propose + wait): e058 backtest->paper, e059 cheap-vs-peers alert, e060 first worthy ping, e061 day-2 player, e062 announce (#2 needs owner topic), e064 login-then-sync, e065 ideas table, e066 numeric coverage. The per-track `next:` line on its card IS the plan — advance it, update it via `ops.py focus` when done.
- Focus text format (owner 2026-09-14): `score <metric>=<n> (<delta>) · next: <12 plain words max>`. Never paren-chains, never `+`-joined clauses. The card shows 90 chars + tap-expand; a focus that needs expanding to be understood failed.
- Advance the lowest rung first; revive stale before starting new.
- e058 (live money): conclusions-only ntfy; never open positions without
  an approved proposal, no matter the APY.
- e060: DECIDED 2026-09-12 (owner: cheapest/free) -> Dexscreener-only radar; v1 live :8323 rung 1.
- Spend caps: T1 ≤$50/action auto; anything bigger = propose + wait.
- New ideas go to p4/IDEAS.md first, new tracks only on owner yes.

## Accounts + TLS (owner 2026-09-13)
- Auth is app accounts, not tailnet: register/login/logout (90-day cookie).
  First account ever = admin; money (approve/reject/promote) = admin only.
  Passkeys: add per device while logged in, then name + touch logs in.
  Passwords stay as fallback. Old shared board-token is retired.
- Board serves https :8322 with Tailscale cert (Secure Context -> passkeys
  work from the phone). Renew monthly via cron (e062-cert-renew); expires 2026-11-22.
- After editing ANY served app: restart it, check its version endpoint
  (running == latest per-track), then claim done.

## Paused

- (none)

## One-shot orders (runner deletes after executing)

- (none)
