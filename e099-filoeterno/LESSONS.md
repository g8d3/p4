# FiloEterno lesson book — append-only, the loop writes, humans read.

_Entries carry full date+time in your local zone (Bogota -05:00). Older entries are date-only (rule did not exist yet).

Every entry: date, version, ADOPTED or REJECTED, score vs old brain, and the
change in plain words (max 140 chars). If you don't understand an entry, say
which line — that lesson gets rewritten or dropped.

## 2026-10-18 v2 ADOPTED (score 0.083 vs v1 0.083)
- change: also check ten day average so flat price gives flat call and cut bad moves


## 2026-10-18 task-01 BLIND GATE (caught by human, fixed)
- lesson: Never trust green tests until you prove the test file cannot pass with broken code. The model embedded a stale contract copy inside the test file, so 5/5 passed against the wrong code through audit AND fix rounds.
- rule added: every new test file must fail at least once on purpose (mutation probe: change fee math, test must go red) before it counts as a gate. No red-first, no trust.
- evidence: fee /100 -> /50 still green exposed it; after import fix, gas numbers moved on all 5 tests.

## 2026-10-19 v3 REJECTED (score 0.083 vs v2 0.083)
- change: need four up days not three and price must be clear of average so flat days give flat

## 2026-10-19 v4 REJECTED (score 0.083 vs v2 0.083)
- change: also look at five day rise and cut high trust so far moves stay flat

## 2026-10-19 v5 REJECTED (score 0.083 vs v2 0.083)
- change: make short need more proof and small moves give flat so we trade less

## 2026-10-19 v6 REJECTED (score 0.083 vs v2 0.083)
- change: also check five day average lines up so choppy days give flat and keep trust low

## 2026-10-19 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 HUMAN FLAG (must beat AND explain better)
- confusing: audit: 6 findings cal:1, igh:1, ium:1, low:2, nfo:1

## 2026-10-19 HUMAN FLAG (must beat AND explain better)
- confusing: Probe = free mutation check (no model calls)

## 2026-10-19 HUMAN FLAG (must beat AND explain better)
- confusing: Is Tok per s in table average of all calls?

## 2026-10-19 flag RESOLVED: audit severity gibberish
- resolves: "audit: 6 findings cal:1, igh:1, ium:1, low:2, nfo:1"
- resolves: "Probe = free mutation check (no model calls)"
- cause: page code chopped the last 3 letters off each word. Now shows full words: critical:1, high:1, medium:1, low:2, info:1.
- confusing: Probe = free mutation check (no model calls) — RESOLVED with a plain-words fire-drill explanation on the page.

## 2026-10-19 flag RESOLVED: tok/s question — YES, average over all calls.
- resolves: "Is Tok per s in table average of all calls?"
- tok/s = every token that model ever produced ÷ every second it ever took, across all its calls. Column renamed and footnoted on the page.

## 2026-10-19 mutation probe: PROBE-OK (gate caught the mutation)


## 2026-10-19 10:26 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 10:28 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 10:41 -0500 bench lineage note (human)
- v1-v6 scores (0.083) were daily-BTC; v2 now scores 0.25 on hourly BTC/ETH/SOL. Different tests, not improvement — do not compare across the switch.

## 2026-10-19 11:34 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 13:35 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 15:36 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 17:37 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 18:26 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 18:31 -0500 02-lottery-coin mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 18:31 -0500 02-lottery-coin BUILT (human-supervised)
- audit found blockhash-grind + sybil entries; fixed with commit-reveal finalize + winner-balance check; test updated to the secured flow (spec changed by audit, referee-approved).
- red-first probe PROBE-OK; deployed locally. Builder loop works end to end.

## 2026-10-19 18:40 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 18:56 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 19:12 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 19:28 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 19:44 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 19:59 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 20:15 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 20:30 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 20:45 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 21:00 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 21:15 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 21:31 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 21:47 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 22:03 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 22:19 -0500 mutation probe: PROBE-OK (gate caught the mutation)

## 2026-10-19 22:25 -0500 03-gated-tool-coin mutation probe: GATE-BROKEN

## 2026-10-19 22:26 -0500 mutation probe: PROBE-OK (gate caught the mutation)
