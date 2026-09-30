# PROACTIVE-E082-REPORT — forever ceiling, real workload, auth decision, adversarial critic

Experiment: e082-forever-harness · Board: http://127.0.0.1:8342 ·
LAN: http://192.168.0.177:8342 · tailnet: http://100.102.52.59:8342
(IPs resolved live via `hostname -I` / `tailscale ip -4` during this run.)
Server PID 1415925 (restarted 1384756 → 1415629 → 1415925 via `bin/serve.sh`, exact PID from `ss -tlnp`).
Loop daemon PID 1317232 untouched, ticking every 60s (cycle ~924, quality 100 at close).
`test/check.sh`: **PASS** (extended: +unbounded, +evidence gate, +mint-disabled, +critic rejection).
Budget $2.21/$10. Full log: `log/proactive-e082.log`.

## Auth/token scheme (unchanged core, one default flipped)

Master `TOKEN` in `needs.json` (0600) still gates all writes; reads stay public;
`POST /api/verify` and `POST /api/review` stay public (read-only checks, like verify).
Previously minted `fh-*` demo tokens still authenticate. What changed: public
**minting** is now disabled by default (`needs.json demo_mint_enabled=false` →
`POST /api/token/mint` returns 403 owner-only). Re-enable with one flag flip.

## The 4 fixes — each with proof

1. **FOREVER CEILING.** `max_cycles` now accepts `null`/`0` = unbounded
   (`needs.json` + `data/policy.json` validation + coercion of integral floats
   from browser number inputs). Live policy set to `null`; status exposes
   `unbounded` + `cycles_remaining` (null when infinite). Board strip renders
   `Cycle 922/∞ · ♾️ unbounded`, and when finite with <100 left it screams
   (`⚠️ only 68 cycles left — raise max_cycles or go unbounded (0 = ∞)!`).
   New `♾️ Forever` preset fills `max_cycles=0`. Proof: check.sh posts
   `null`→accepted, `0`→accepted, status asserts `unbounded==true`;
   real-browser screenshots `e082-proactive-top.png` (unbounded strip) and the
   finite-990 run showing the 68-left scream (policy restored to null after).
2. **REAL WORKLOAD (metric theater killed).** The loop's micro-goal source is now
   the e083 backlog (`GET /api/backlog`): `e083-stuck-drilldown`,
   `e083-google-proxy`, `e083-x-login` (the exact gaps in ADAPTERS-E083-REPORT:
   stuck-list drill-down, Google proxy decision, x.com login). Each tick pulls
   the top item, hits the **live** e083 server (funnel / recipes / records),
   and appends `data/evidence.jsonl` (`cycle, item, rows, detail, ok`).
   New `evidence_present` gate FAILS ticks without verifiable output, so quality
   can actually drop — proven when the first post-deploy verify scored the old
   theater-era cycle 916 at quality **85** (honest history, still in the log).
   Real cycles since: c917 `e083 recipes live: 4 recipes {'client': 3, 'server': 1}`
   (proxy-decision input), c921 `50 rows {'product-prices': 30, ...} — no x rows
   in tail sample` (an honest negative finding), c922 `6 views, 1 stuck
   (check-sess-2), 34 publishes` (names the stuck session). Board shows a
   `🎯 Real backlog` card (NOW/QUEUED) + per-tick evidence line.
3. **AUTH DECISION (single-user, dated).** Demo-mint disabled by default (403 +
   owner-only message naming the 2026-09-29 decision and the re-enable flag);
   Token card copy now says owner-only and points at `needs.json`. Multi-user
   signup is documented here as a decision, not code: no sessions, no roles,
   no half-built signup — when a second real user appears, build signup then.
4. **ADVERSARIAL REVIEWER.** `POST /api/review` (public, like verify) + a loop
   step after every ship: separate rule-set re-scores the tick trying to REJECT
   it — R1 no evidence→reject, R2 trivial diff (<80 chars)→reject, R3 quality
   unchanged 20 straight→flag stagnation. Verdicts append `data/reviews.jsonl`;
   rejects FAIL the new `critic_accept` gate (quality −15, loud). Board shows
   `Critic: <verdict> · <reasons>` on the strip and `🧐 critic:` in every proof
   receipt. Proof: `{"notes":"tick done"}` → **reject** (R1+R2), asserted in
   check.sh; live ticks show `Critic accept … no stagnation`.

## User-seat review (real browser, named session `e082proactive`)

A visitor can now: read the 2-line hero → see `RUNNING · Cycle N/∞ · ♾️ unbounded`
+ Critic + evidence lines → expand proof receipts (heartbeat, 8 gates, e083
evidence, critic verdict, cost) → read the live backlog card → see Token is
owner-only → Suggest/Forever-preset/Save policy → Stress test (7/7 HOLDING).
Clicked "Show last tick's work" in the browser: full receipt for c921 rendered.
No dead ends; locked buttons still explain they need the owner token.

## WHAT I STILL DISTRUST (mandatory — ceilings approaching, theater risks remaining)

- **Budget is the next ceiling.** Unbounded cycles + $10 budget + $0.0024/tick =
  ~3,200 ticks left (~2 days at 60s). "Forever" currently means "until the money
  runs out, then STOPPED." No refill path, no spend-throttle, no alert before it
  fires. The stop will be correct but sudden.
- **Evidence fetches are localhost-only.** All three backlog slices query
  127.0.0.1:8383. If e083 dies, every tick logs `ok:false`, quality craters to
  70-floor breach, and the loop STOPS — correct behavior, but a single local
  dependency now gates the "forever" story. No retry, no degraded mode.
- **The critic is rules, not judgment.** R1/R2 catch hollow ticks; a verbose but
  vacuous tick (long notes, real fetch, zero insight) still passes. R3 stagnation
  needs 20 identical qualities — a slow sawtooth (100,85,100,85…) evades it.
- **Backlog is 3 static items.** Rotation is round-robin; items never close, so
  "progress" is evidence volume, not gap closure. The Google-proxy and x-login
  decisions still need a human to actually decide.
- **Quality 100 is suspicious again.** Post-fix ticks sit at 100 because e083 is
  healthy and fetches succeed. The gate *can* fail (proven at 85), but a long
  green run will look like the old theater — watch the evidence lines, not the number.
- **Mint-disabled is one flag away from re-opening.** `demo_mint_enabled=true`
  restores stranger-writes; nothing rate-limits the flip itself beyond the owner token.
