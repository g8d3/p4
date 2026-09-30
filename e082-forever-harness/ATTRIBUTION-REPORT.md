# ATTRIBUTION-REPORT — agent traffic out of the human funnel (2026-09-29)

Server :8342 · PID 1452039 (restarted 1423520 → 1452039 via `bin/serve.sh`,
exact PID from `ss -tlnp`). `test/check.sh`: **PASS**. Full log: `log/attribution.log`.

## Problem (proven from live rows)

Driven browsers were exempt from synthetic tagging, so UX/seat-review passes counted
as "visits" and the verdict `0 downloads after 10 visits` condemned agent traffic,
not humans. Worse: the disk code already contained the fix but the running server
predated it — live `/api/funnel` returned no `human_attributed`/`agents_hidden`
until the restart. Restarting was the fix's fix.

## Before / after proof (fixtures, all dismissed after)

| Probe | Before (stale server) | After (restarted) |
|---|---|---|
| `page_view` + `agent=seat-review-test` (browser UA) | hidden (via curl-UA rule only), name lost (`agent:''`) | hidden by default; `?bots=1` → `synthetic:true` + `agent:'seat-review-test'` |
| click-path `page_view → click:show-proof`, no flag (browser UA) | unattributed | `human_attributed` 5→6, row `synthetic:false` |
| polluted-only (`attribution_gate(...,0)`) | n/a | **UNKNOWN** `not enough human traffic — unattributed (0/3…)` |
| `review_tick` with UNKNOWN funnel | n/a | verdict `flag`, R4 notes `discounting (no penalty)` — **no reject, no −15 quality** |

One real click-path restores normal scoring (`attribution_gate(...,3)` → FAILING
passthrough). Threshold from `needs.json` `min_human_sessions` (default 3, already
present — never hardcoded).

## Changes (tiny, one endpoint area)

- `test/check.sh`: §1b agent hidden/tag/validation asserts + §1c attribution-rules,
  click-path-human, UNKNOWN-no-penalty asserts; `UNKNOWN` added to allowed verdict
  levels. All fixtures self-dismiss (bots_hidden flat across the run).
- `BROWSER-CAPABILITY.md` (repo root): `?agent=<reason>` convention — all future
  driven-browser passes open `<url>?agent=<reason>`; untagged browsers still count
  as human.
- Server/`needs.json`/snippet: already on disk, activated by the restart (no new
  server edit this run).

## What a visitor can do (seat-checked shape, unchanged + one line)

Read the verdict first — now also `UNKNOWN: not enough human traffic` (watching,
not scoring) — → human-only counts → expander for full ids → `show bots+agents`
toggle (agent names shown as `AGENT:<name>` pills) → owner dismiss/restore.

## Still distrust

- `dismissed.json` keeps growing (~74 entries; every fixture run appends) — needs a
  prune/TTL, same as `events.jsonl` (bots hidden, never deleted).
- Untagged driven-browser passes still count as human by design — the convention
  only works if every future pass uses `?agent=`.
- Live verdict is FAILING with streak 82/3 — R4 keeps quality at 85 until a real
  install happens; that is the spec working, not noise.
