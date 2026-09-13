# ATTENTION — do the agents think like the owner?

Every issue the owner finds first is a miss. Log it: what, where,
who found it, hours it sat unnoticed, why the legs walked past it.
Goal: owner-found rows get rarer and faster; agent-found rows (legs
fixing confusion before it is reported) are the real score.

| date | app | issue | found_by | hrs_unnoticed | why missed |
|------|-----|-------|----------|---------------|------------|
| 2026-09-13 | e058 | signals show no time window (from→to present, why qualified) | owner | ~8 | legs polished copy, never asked "does the owner know what this signal IS" |
| 2026-09-13 | e058 | `urgent if bigger ×` label unreadable | owner | ~8 | config box shipped without read-aloud test |
| 2026-09-13 | e058 | filter covers main table only, silently skips signals | owner | ~8 | filter tested on one section, honesty rule didn't exist |
| 2026-09-13 | e058 | main section untitled (top/filters/alerts/signals named, main not) | owner | ~8 | no section-names rule |
| 2026-09-13 | all | config boxes stacked vertically, unaligned | owner | ~8 | no forms rule; AI-default stacking accepted |
| 2026-09-13 | all | paper slip = clipboard trick, never used; sharing needs a pretty page | owner | — | slip built for dev convenience, not human sharing |
| 2026-09-13 | e058 | top section undecodable: bare `flippy/legs swapping`, `(new)`, unlabeled `\|/·` stats, bare `v` hash, `paper 75 logged` with no when | owner | ~8 | dense line never read aloud by a leg; fixed direct 2026-09-13 |
| 2026-09-13 | e058 | paper ballot invisible: 75 predictions only in SQLite, /api/paper serves counts, no list anywhere | owner | ~8 | legs logged predictions but never asked "can the owner see the ballot"; queued as ISSUES #8 |
| 2026-09-13 | e058 | 4 signal pings in 2h: dedup keyed on sliding window, persistent payers re-pinged as URGENT | owner (screenshot) | ~2 | alert tested for sending, never for silence; 24h rule worked but 3 different coins pinged in 1h → escalated to digest-only (no owner action exists for any ping) |
| 2026-09-13 | e062 | board STALE—restart survives restarts | owner (screenshot) | ~1 | version scoped to whole dir incl. docs — my own doc commits re-dirtied after every restart; fixed: code-only scope (app.py/webauthn.py/static) |
| 2026-09-13 | e061 | game frozen for hours, same win screen | owner (screenshots) | hours | day-2 metric unmeasurable (localStorage, no server log) so legs polished while blocked; decoded dead-ends direct, server log + metric redesign queued |
| 2026-09-13 | e060 | trades link promises trades tab, tables fixed/read-only | owner | — | free API has no trades-tab URL (pair page only) → honest `pair ↗` label; SQL-grade grid + self-explaining scores queued (UX §9) |

## Rules for legs

- Open each app as the owner from the phone; ask the confused
  questions before the owner does. Fixes land in the app's ISSUES.md
  as agent-found rows here.
- An owner review like 2026-09-13 must produce rows here AND fixes
  in the app — never fixes without rows (rows are the learning).
