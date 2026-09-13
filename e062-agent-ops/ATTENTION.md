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

## Rules for legs

- Open each app as the owner from the phone; ask the confused
  questions before the owner does. Fixes land in the app's ISSUES.md
  as agent-found rows here.
- An owner review like 2026-09-13 must produce rows here AND fixes
  in the app — never fixes without rows (rows are the learning).
