# HANDS-REPORT — the loop can now touch e083 (gaps + drafts, attributed)

Experiment: e082-forever-harness (:8342) acting on e083-scrapenet (:8383).
e082 server PID 1508016, e083 server PID 1505083 (both restarted via `bin/serve.sh`
after kill-by-exact-PID from `ss -tlnp`). Loop daemon alive, ticking every 60s.
`test/check.sh`: **PASS on both experiments** (extended, self-cleaning).
Full diary: `log/hands.log`.

## What changed

- **e083 new endpoints (stdlib, token-authed = owner key OR node token):**
  `POST /api/gaps` files one backlog row `{at, source:"e082-loop", item,
  evidence, priority, by}` to `data/gaps.jsonl` (needs.json `gaps_path`);
  `GET /api/gaps` reads public, test rows hidden unless `?include_test=1`;
  `DELETE /api/gaps` (owner any row, node token test-rows only).
  `POST /api/growth/draft` queues ONE post `{source:"loop", approved:false}`
  — the scheduler only posts approved rows, so it can never auto-post;
  at most one pending loop draft (second call returns the waiting one);
  drafts survive the daily queue regeneration; `DELETE /api/growth/draft`
  removes unposted drafts. Reads never leak tokens.
- **e082 hands (rules in needs.json `hands_*`, never hardcoded):** every tick
  observes e083 (`/api/health` records + `/api/funnel` publishes/verdict) and
  then: publishes stalled vs last tick → file gap (priority high when the e083
  funnel verdict is FAILING, which also escalates on its own); records grew →
  queue ONE draft (source:loop, needs approval); unreachable → log honestly to
  `log/hands.log` and skip, claiming nothing. Dedupe: one open gap per stall
  level, one pending draft. State in `data/hands.json`, creds in
  `data/loop_creds.json` (0600, signed up once as `e082-loop-8f009a`).
- **Gate/critic wiring (R1b):** `check_hands_claim()` — a tick saying
  "filed gap"/"queued post" without an id is rejected; an id not found in the
  e083 store (phantom) is rejected. Called from `review_tick`, stored reviews
  fail the `critic_accept` gate exactly like R1–R4.
- **Board proof:** tick receipts carry `🤝 hands: <summary>` + links
  (`/#secGaps`, `/#secAuto`); e083 growth rows and the new `Loop backlog` card
  render `LOOP` source badges (`hands-e083-gaps.png`, `hands-e082-receipt.png`).

## Live tick transcript (cycle 1120, real ids, both artifacts fresh)

Baseline seeded `{publishes:11, records:233}`, one real test row ingested
(`hands-proof-60bc25`, accepted:1 → records 234), then:

`POST /api/control/tick {"by":"hands-proof"}` → cycle 1120, quality 85.
hands: **filed gap `gap-20260929-211910-2aff`** (priority normal, publishes
stalled at 11); **queued post `loop-2026-09-29-dd74`** (records grew to 234,
needs approval). Links: `/#secGaps`, `/#secAuto`.

e083 side: gap row `{source:"e082-loop", evidence:"e083 funnel: NOISE:
35/35 stuck are bots…; publishes 11 (unchanged since last tick), records 234",
by:"e082-loop-8f009a"}`; draft `{source:"loop", approved:false,
rejected:false, posted:false, text:"ScrapeNet just hit 234 records banked
(11 publishes) — …", fact:"records=234 publishes=11"}`.

Gate/critic on 1120 (before cleanup): `evidence_present` **pass**;
`POST /api/review {"cycle":1120}` → reject on **R3 + R4 only, zero R1 hands
reasons** — the acted claim verified. Cleanup: both deleted via owner auth,
`GET` confirms `gaps: []`, `loop drafts: []`. No permanent junk
(except two `hands-proof-*` test ingest rows, test:true, audit-hidden — see
distrust #5).

Fixtures in `check.sh`: id-less gap/post claims rejected, phantom ids
(`gap-20990101-…`, `loop-2099-…`) rejected, rules documented in needs.json
asserted, full live-tick→attribute→gate→critic→receipt→cleanup cycle green.

## User-seat review (headless Chrome, 390px)

A visitor can: read the hero → open Proof → see the `🤝 hands:` line with
clickable gap/post links; on e083: open `Loop backlog` (gap table with
`normal`/`LOOP` pills + evidence) and `Auto-posts` (draft row with
`NEEDS OK` + `LOOP` badge, OK/Park buttons work with a token). Every card
keeps a user action; locked buttons still explain the token.

## WHAT I STILL DISTRUST (mandatory)

1. **Gaps never close.** Dedupe caps steady state at ~1 open gap + 1 pending
   draft, but there is no resolve/close path or TTL — the same "items never
   close" disease the PROACTIVE report named. Needs a close endpoint + owner
   button before the backlog reads as spam.
2. **One dying loader kills the whole e083 dashboard.** Found live during seat
   review: today's anonymous free-tier quota hit 100/100 (429), `loadRecords`
   threw, `refresh()` died before `loadGrowth`/`loadGaps` — my new cards sat at
   "loading…" for logged-out visitors. Pre-existing chain fragility, but my
   cards inherit it. Refresh needs per-card try/catch.
3. **R1b is same-machine coupled.** Id-existence is verified by reading e083's
   store files directly. If the collector ever goes remote (`hands_e083_url`
   override), R1b silently downgrades to id-presence-only. Logged nowhere.
4. **Escalation never fired live.** e083 funnel read NOISE all evening, so
   FAILING→high-priority is proven by fixtures + code path only. The next real
   FAILING tick is the test to watch.
5. **Two proof ingest rows remain** (`hands-proof-*`, test:true, hidden from
   public counts). Left deliberately — `purge-test` would wipe other harnesses'
   test rows too. Revisit with a single-record delete or a scoped purge.
6. **`hands.json` has no lock.** Daemon + manual + suite ticks interleave;
   last-writer-wins could skip one stall comparison (self-heals next tick;
   dedupe still prevents duplicates — missed, never double-filed).
