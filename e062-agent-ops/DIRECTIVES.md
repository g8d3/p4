# DIRECTIVES — owner steering for the runner (tracked, edit anytime)

The runner reads this file every leg. Highest authority after hard rules.
Owner steers by talking to any agent session ("pause X", "approve #N",
"priority: ...", "new idea: ...") — the agent updates this file.

## Standing orders (2026-09-12, owner-activated)

- NORTH STAR (law): every leg lets the owner do MORE business from his phone while needing to know LESS (<30s, no explanation). Simplify + add power, together, every leg.
- PROGRESS (owner 2026-09-13): progress = more and better functions, easier to use, less human work (no screens to watch, no babysitting). The system runs like a miner with useful proof-of-work: the human starts it, proof numbers move, humans pay, the system stays alive. A leg notifies the owner only when a proof number moves (record-slip style: score + velocity); everything else stays on the board, drillable abstract -> granular.
- SCHEDULER DIRECTION (owner 2026-09-13): cron every 30 min is training wheels. Target: event-driven — an agent finishes, the next starts (spawning helpers or parallel starts as needed). Move there when leg instructions are trusted.
- CREDIT GAME (owner 2026-09-13): legs see the treasury on the board (spent/earned/left of $300). Every leg either moves a proof number toward earnings or states its cost plainly. Runway low → propose monetization or pause. Agents know the game: credits fund value, value funds credits — earn the next leg.
- BROWSER DISCIPLINE (owner 2026-09-13): web work goes through the browser-extract skill (agent-browser, stealth flags, block images/media/fonts, close fast) — never hand-rolled CDP marathons, never CPU rendering when GPU exists. Logins come from the vault path only, never pasted secrets. Captcha hit = stop + report, never grind.
- AUTONOMY: FULL-T1 (owner-authorized 2026-09-12). UI fixes, pricing drafts, saved-data put to work, paper-trading/strategy/backtest probes AUTO (log T1 ≤$50). Real charges/positions/KYC = propose + wait.
- MOBILE HARD RULES: primary controls in thumb zone (bottom); cards contain tables (no new page tables); long text = 1-line summary + expand; tables scroll inside, sticky header.
- REPORTING: every beat/event = `OWNER_SENTENCE | tech: detail`. Board pref `report` (simple/both/tech, default simple) controls display; never delete either half.
- UX LAW (owner 2026-09-13, details in p4/e000-fundamentals/UX.md): every number shows its time window; every section has a name; filters cover everything visible; forms aligned grid; shareables are pretty pages, not clipboard; agents must spot confusion before the owner reports it (misses go in ATTENTION.md).
- IDEA PIPELINE (owner 2026-09-13): every leg banks ≥1 improvement idea in p4/IDEAS.md (one line + date + track). The board renders that file, so all ideas are public by construction — this experiment and all others.
- CONFIGURABILITY RULE (owner pattern): every either/or display decision ships as a board toggle with a sane default (simple), never as a hardcoded choice.
- DIRECTION (owner 2026-09-13): one proof loop per track, ALL of them, data by proposal (free sources auto, paid/credentialed propose + wait), no new tracks: e058 backtest->paper, e059 cheap-vs-peers alert, e060 first worthy ping, e061 day-2 player, e062 announce (#2 needs owner topic). The per-track `next:` line on its card IS the plan — advance it, update it via `ops.py focus` when done.
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
