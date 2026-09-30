# FUNNEL-E082-REPORT — stuck-card stops crying wolf (bot filter + verdict + R4)

Experiment: e082-forever-harness · Board: http://127.0.0.1:8342 ·
LAN: http://192.168.0.177:8342 · tailnet: http://100.102.52.59:8342
(IPs resolved live via `hostname -I` / `tailscale ip -4` during this run.)
Mirror: e083-scrapenet http://127.0.0.1:8383 (same LAN/tailnet hosts, :8383).
Server e082 PID 1423520 (restarted 1415925 → 1422143 → 1423520 via kill-by-exact-PID
from `ss -tlnp`, same start method as `bin/serve.sh`). Server e083 PID 1422524
(restarted 1393670 → 1422435 → 1422524, same method).
Loop daemon PID 1317232 untouched, ticking every 60s (cycle ~959 at close).
Quality is 85 at close — R4 firing on FAILING persistence (streak 5 > 3), exactly
the enforcement the spec orders; the 100-recovery and the R4-B trip were both
observed live (see fix 4).
`test/check.sh`: **PASS** on both experiments (extended with bot/verdict/R4 asserts).
Full log: `log/funnel-e082.log`.

## The owner's charges — all four confirmed live before the fix

Before-state (real browser, named session `e082before`, :8342 stuck card):

- `16 visits · 5 saw proof · 3 minted tokens · 0 downloads`, then **10 STUCK? rows**,
  of which 6 were `check-179070…` (our own check.sh polls), 1 was `growth-probe`
  (QA probe), 1 was `20b42ab878d0… · last: idle_45s none` (the dangling-detail bug),
  and only ~3 were plausibly human. Screenshot `e082-funnel-before-top.png` +
  a11y snapshot in log.
- Row hygiene bugs: literal `none` rendered as a signal, timestamps wrapped
  mid-string (`2026-09-29T18:40:…` broken across lines), ids truncated with no way
  to see the full session, no way to say "not a human".
- The real signal — 0 installs across all human visits — was row #11, invisible.

## The 5 fixes — each with proof

1. **BOT FILTER (ingest tag + default exclusion + toggle).** `POST /api/events`
   now derives `synthetic:true` when the session matches `check-*` / `*-probe`
   (`growth-probe` included) or the User-Agent looks like curl/python/loop/daemon/
   health-poll junk (real browsers explicitly exempted, so seat reviews stay human).
   Only the boolean is stored — still no IPs, no UAs, privacy assert unchanged.
   `GET /api/funnel` excludes synthetic + dismissed rows by default and reports
   `bots_hidden` / `bots_total`; `?bots=1` reveals them with a visible
   `show bots (N hidden)` toggle. Backfill: all 101 pre-fix events rewritten once
   with the flag (7 synthetic), backup at `data/events.jsonl.bak-20260929-135213`.
   Proof: after fix, default funnel showed 9 views / 4 human stuck / 7 hidden;
   check.sh posts fresh `check-r4-*` bots and asserts they are hidden by default,
   revealed with `synthetic:true` under `?bots=1`, and that a curl-UA poll is flagged.
2. **VERDICT LAYER (rules, not vibes).** Every funnel response carries
   `verdict{level,line}` rendered as the card's first line, computed from
   `needs.json` thresholds (`funnel_min_visits=5`, `funnel_download_alarm_ratio=0.05`,
   `funnel_bot_noise_ratio=0.5`, `funnel_proof_healthy_ratio=0.3`):
   NOISE (bots bury humans) > FAILING (0 / near-0 installs past min visits) >
   HEALTHY (proofs keep pace) > QUIET (too little data) > WATCH.
   The owner never has to ask a human whether the card looks right — the card says
   so itself. Proof: live transitions observed NOISE: 7/11 → (after dismissing all
   17 bot sessions) FAILING: 0 downloads after 10 visits (screenshots
   `e082-funnel-after-hidden.png`, `e082-funnel-after-shown.png`,
   `e082-funnel-after-failing.png`).
3. **ROW HYGIENE.** `none`/`null`/`-` details normalize to empty at ingest AND at
   read (backfills the old `idle_45s none` row); timestamps carry `nowrap` CSS;
   ids render truncated with a `full id` expander holding the complete session;
   per-row **not a human** button (owner token, like all writes) persists to
   `data/dismissed.json`, with a dismissed list + per-row restore.
   Proof: zero `idle_45s none` strings in the after snapshot; check.sh asserts
   dismiss (401 without token), persistence, undismiss restore, all self-cleaning.
4. **R4 DATA-TRUTH GATE (critic watches dashboard honesty).** `review_tick` gained
   R4: bot share of the stuck list above threshold, or a FAILING verdict persisting
   past `funnel_critic_fail_streak=3` ticks (counted in `data/funnel_streak.json`,
   advanced only on real ticks — never on reads/probes), REJECTS, which fails the
   `critic_accept` gate (−15 quality) with the dashboard's own verdict line quoted
   in the reason. Proven three ways: (a) `test/funnel_polluted.jsonl` replays
   today's shape → `NOISE: 7/8 stuck are bots`; (b) scoring the live tick while
   polluted → `reject` with R1+R2 passing and only R3+R4 firing; (c) the loop
   itself: the first post-deploy tick stored an R4 reject and quality dropped
   100 → 85 with `Critic REJECTED cycle 948: R4: data-truth — bot share 8/13…`
   on the strip and in the gate detail. After dismissing all 17 bot sessions the
   next tick recovered to 100 with `flag` + `R4 note: FAILING (2/3 ticks…)` —
   the full sense→judge→recover loop, live.
5. **E083 MIRROR (lighter touch, same schema).** Same `is_bot_session` / UA rules,
   same `synthetic` tagging, same default-exclusion + `?bots=1` + `bots_hidden` +
   `verdict{level,line}` (metric mapping documented in code: installs→downloads,
   proofs→signup+publish actions; thresholds added to its `needs.json`).
   `stuck_sessions` changed from bare strings to
   `{session,short,synthetic,last_event,last_detail,last_at}` rows; the e082 loop's
   backlog consumer already handles both shapes (verified live — evidence lines
   still log). Its `check-sess-2` idle row is now hidden with `NOISE: 3/3 stuck
   are bots` instead of crying wolf (screenshot `e083-funnel-after.png`).
   No dismiss endpoints on e083 (deliberately lighter). e083 `check.sh` updated
   for the new shape and now asserts bot exclusion + toggle + verdict rules.

## Incident log (honest): I broke demo-token auth mid-fix and check.sh caught it

My first server edit replaced the `def demo_tokens():` header line with the new
helper block, leaving a dead `return` and no function — demo-token `/api/auth`
returned `ok:false` while master-TOKEN paths still passed. `test/check.sh`
failed on `legacy demo token auth`; I restored the header, verified
master/demo/wrong-token auth directly, restarted by exact PID, and re-ran to
PASS. No data lost (append-only logs untouched); the episode is why the suite
asserts legacy-token auth before PASS.

## User-seat summary (what a visitor can do now — verified in the browser)

Read the verdict line first (`NOISE`/`FAILING`/`HEALTHY` — no interpretation
needed) → see human-only counts → expand a row for the full session id → flip
`show bots (N hidden)` to audit what was filtered → (owner, one tap after token)
mark rows `not a human` or restore them. Everything else on the board is
unchanged; locked buttons still explain they need the token.

## WHAT I STILL DISTRUST (mandatory)

- **FAILING is now the true signal, and R4 will punish it within ~4 ticks.**
  After dismissing all bots the board honestly says `0 downloads after 10 visits`
  and the streak file is already at 2/3 — the next ticks will R4-reject on
  FAILING persistence and quality will sit at 85 until a real install happens
  (or thresholds are re-tuned). That is the spec working as ordered, but the
  owner should expect the 85 and treat it as "fix the install path", not noise.
- **Server-truth downloads (24+ zip hits) disagree with telemetry installs (0) —
  and both are CI-polluted.** check.sh curls `/download/plugin.zip` every run, so
  the 24 is mostly us; the 0 is real-button-clicks-only. Neither number is clean;
  the verdict uses telemetry (bot-excluded) and ignores zip hits entirely.
- **My own verification polluted the human signal.** Two of the five current
  human-stuck rows (`29a51…`, `30ea5…`) are my before/after seat visits — real
  browser rows the filter correctly keeps. I left them (deleting real visits
  would be faking the signal); dismiss them from the board if they annoy you.
- **Stress reads STRAINED while R4 fires.** The `gates: live verify green` probe
  fails when `critic_accept` is red, so the scoreboard shows 6/7 STRAINED — honest
  (the server IS under data-truth strain) but it will alarm anyone who expects
  a permanent HOLDING.
- **`dismissed.json` grows ~10 entries per check.sh run** (fixtures self-dismiss
  to keep `bots_hidden` flat). No cap, no TTL — needs a prune or the file becomes
  archaeology. Same for `events.jsonl`: bots are hidden, never deleted.
- **The UA heuristic is a blocklist, not an identity.** A real human driving curl
  (or the owner's own health polls from a laptop) gets flagged synthetic; a bot
  driving real Chrome with a clean session id passes as human. Session-pattern
  matching is the strong signal; UA is the weak one — kept weak on purpose
  (browsers exempt first).
- **R3 stagnation was already flagging before this change** (quality 100 × 20+).
  The long green run the PROACTIVE report warned about is here; R4 just made it
  louder. Watch the evidence lines, not the number — still true.
- **e083's `stuck_sessions` type change (strings → objects) is the one
  cross-experiment break.** Only the e082 loop consumes it and it handles both —
  but anything else scraping that endpoint (dashboards, the DEX notes) must
  re-read the shape.
