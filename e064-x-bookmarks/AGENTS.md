# e064 — X Bookmarks (novaisabuilder signal pipe)

Authenticated X pipe for the owner's account (@novaisabuilder).
Reads the account's likes + bookmarks and publishes a timestamped
snapshot other experiments mine. First link of the chain:
e064 (signal) → e065 (ideas) → e066 (builds, e.g. Arc directory).

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles, browser discipline, quiet mode
- [../e062-agent-ops/DIRECTIVES.md](../e062-agent-ops/DIRECTIVES.md) — runner rules, reporting format
- [../e060-social-memecoin-radar/AGENTS.md](../e060-social-memecoin-radar/AGENTS.md) — X-access costs/ToS context

## Goal

Every 30-min leg (via the e062 runner): verify X login, renew it if
expired, pull new likes + bookmarks since last sync, append to the
series, publish `output/latest.json`.

## Login rule (hard)

- Login state lives in the persistent browser profile / vault path only.
  Never paste secrets, never commit them.
- Each leg: open X, check logged-in as @novaisabuilder. If expired,
  renew via the vault recipe (see e041-web-access-agents), then continue.
- Captcha / challenge hit = stop + `notify.sh error` + beat `blocked`.
  Never grind challenges.
- Browser discipline: browser-extract skill, block images/media/fonts,
  `close --all`, 0 chrome processes at end.

## Data

- Raw append-only cache: `data/` (ignored, never committed).
- Published snapshot: `output/latest.json` — array of
  `{id, url, author, text, ts, likes, reposts, src: like|bookmark,
  synced_at}` + `output/sync_state.json`
  (`{last_ok, counts, login: ok|renewed|expired}`).
- Dedupe by X id. `latest.json` keeps the last ~500 items max.

## Proof number

Freshness: `last_ok` age < 60 min and item count delta vs previous leg.
Beat tech half ends with `score freshness=<age>`.

## DONE ladder

1. WORKING — `latest.json` + `sync_state.json` written from a live login.
2. DEPLOYED — fresh via the 30-min runner, stale-badged in UI.
3. TESTED — login-expiry drill (force logout → renew → sync) documented.
4. ANNOUNCED — owner ping with counts.
5. MONETIZED — never (internal pipe).
