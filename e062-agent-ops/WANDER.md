# WANDER — the agent that roams the apps like the owner (UX LAW §13)

A capture cron takes phone-width screenshots twice daily; legs review them
with eyes, fix what confuses, and record every miss. Success looks like
this: ATTENTION.md owner-found rows get rarer, agent-found rows grow, and
no confusion survives two wanders.

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles, quiet mode, hardware awareness
- [../e000-fundamentals/UX.md](../e000-fundamentals/UX.md) — the 15 laws (the checklist)
- [DIRECTIVES.md](DIRECTIVES.md) — north star, autonomy, versions, reporting
- [ATTENTION.md](ATTENTION.md) — where misses are scored

## The loop

1. **Capture (cron, dumb).** `bin/wander.sh` at 11:15 + 16:15 local (day
   window — headless Chrome spikes CPU, never in quiet 21:00–10:00). Shots
   land in `wander/shots/<date>/` (ignored by git, heavy). It also runs
   cheap tripwires (non-200, unknown tracks, mixed `data_through`) into
   `wander/latest.json` and emits one `wander` event + heartbeat. It never
   fixes anything and never pings ntfy (findings are not proof moves).
2. **Claim (before touching).** Write `wander/claim.json` `{"ts","by"}`.
   If a claim is fresher than 6h, work on something else — agents never
   collide. Delete it when done. (The capture cron never touches this file;
   it owns `wander/capture-claim.json` — run134 split, so leg claims can no
   longer starve capture.)
3. **Review (leg, eyes).** Open the newest shots with a vision-capable
   model, phone-first: is every number readable in <30s, thumb-reachable,
   its time attached? Walk the UX laws, especially §1 (time on numbers),
   §7 (read aloud), §12 (taps give), §14 (no truncation without expand).
   Wander with no purpose — scroll, tap, mistype — per §13.
4. **Fix (leg, T1-auto).** UI fixes are pre-authorized (AUTONOMY FULL-T1):
   land on NEXT, e2e PASS, promote to BEST per VERSIONS. Real charges,
   positions, KYC = propose + wait, as always.
5. **Record.** Every confirmed miss becomes one ATTENTION.md row
   (date, app, issue, found_by=wander, hrs_unnoticed estimate, why missed)
   plus the fix in the app's ISSUES.md with its finding story — a fix
   without its story is half a fix (§13). Bank ≥1 improvement line in
   `p4/IDEAS.md` when the wander earns one.

## Seeded checklist (2026-09-15 owner review — re-check until gone)

- Board projects table: blank NAME/URL for tracks missing from TRACKS;
  truncated cells with no expand; LATEST identical across rows (leg time,
  not data time); `open` link contrast in dark mode.
- e059: badge contrast + nowrap; LIVE vs `data_through` lag; mixed `thru`
  dates; all-thin alert set sold as strong signal; table below the fold
  on phones; `copy top 3` still clipboard (§6 target = share page).
- Thumbbar crowding at 360px; persona taps that take context away (§12);
  `waiting` control visible but empty; SQL/jargon leaking into simple mode.

## Pitfalls

- Screenshots are local-only (tailnet/IPs, auth cookies): never commit
  shots, never attach them to pushes — describe, don't leak.
- Headless Chrome leaves zombies: `close` fast, verify zero chrome
  processes at end (same discipline as browser-extract).
- Don't grade the same N twice (STUCK RULE): a finding that survives two
  wanders unfixed becomes data (new source/column) or gets killed in
  writing — never re-logged.
