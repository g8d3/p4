# Growth Report — e082 (:8342) + e083 (:8383), 2026-09-29

## Server status (live IPs resolved today)

| App | Local | LAN | Tailnet | PID |
|---|---|---|---|---|
| e082 Forever Harness | http://127.0.0.1:8342 | http://192.168.0.177:8342 | http://100.102.52.59:8342 | 1384756 (restarted by UX agents today) |
| e083 ScrapeNet | http://127.0.0.1:8383 | http://192.168.0.177:8383 | http://100.102.52.59:8383 (= `public_url` in needs.json) | 1384712 (restarted by UX agents today) |

## User-seat review (opened both pages via agent-browser myself)

- **e082 board `/`**: one page — edit keep-going policy, Start/Stop/Tick,
  Verify now, live status (running, cycle 783+, quality, budget bar),
  checkpoints, gates, plugin download, share link. User actions: configure →
  start → tick → verify → download plugin → share. Verdict: actionable.
- **e083 dashboard `/`**: hero + extension install (3 steps), signup
  (name → node_id + token), live records table (populated, 64 records),
  test-record sender, recipes, publish, earnings, ideas, leaderboard.
  User actions: install → sign up → scrape → publish → share dataset.
  Verdict: actionable. (Extension popup/options themselves are a
  `chrome://` flow — not openable headless; load-test remains manual.)

## 1. Capability proof

`BROWSER-CAPABILITY.md` (repo root). agent-browser + Chrome 153 drive both
apps with humanized delays/scroll/viewport; screenshots captured.
Measured detection (bot.sannysoft.com): everything passes **except
`navigator.webdriver=true` (flagged)** + SwiftShader software-GL headless
tell. So: honest automation — fine for QA/outreach-prep, not for strict bot
walls. Headed mode (`--headed`, Xvfb present) is the untested upgrade path.
e020 prior art summarized in the same file. No accounts created, nothing
published, nothing spent.

## 2. Jev — RESOLVED (not stuck)

`JEV.md` (repo root). Jev = TypeSafe's System One decision model; signup via
`typesafe.ai` (possible waitlist) or OpenRouter key (`typesafe/jev-1.13`,
Decisions API, ~$0.025/1k decisions). Benchmarks-with-alternatives page =
`langwatch.ai/compare/jev-benchmark` (Jev vs 7 open models, 15 tasks incl.
**web-agent actions 70.8%** — the reason to use Jev as judge over
browser-test agents). Proposed integration (Jev-as-judge, confidence ≥ 0.8)
needs an owner-minted key; no code touched.

## 3. Domains — ranked, not bought

`DOMAINS.md` (repo root). Umbrella brand proposed: **Everloop**.
5 available, in-budget (RDAP-checked, Porkbun-priced):
1. `everloop.cc` ($3.40→$8.55), 2. `everloopagent.com` ($11.08),
3. `keeploop.cc`, 4. `foreverloop.cc`, 5. `meshloop.cc`.
`.io` excluded with receipts ($51.80 renewal > $15 cap). Purchase steps written
for the owner; day-one total ~$14.48. **Bought nothing.**

## 4. Outreach kit

`OUTREACH.md` (repo root): per app, one X post + one known-contact DM as
copy-paste blocks, each [NEEDS OWNER TAP], hero screenshots in
`.growth-shots/`. Referral mechanics documented from server code:
e083 `?ref=` codes → 20%-of-commission credit + public leaderboard;
e082 has no referral codes (share-page views only — feature request if wanted).
**Owner must mint their own e083 referral code before any send.**

## 5. Telemetry loop — CONFIRMED LIVE

Both `/api/funnel` = HTTP 200, proven end-to-end (visits → events → funnel
numbers move). First-reading procedure + silent-watch routine in
`OUTREACH.md`. Current state: e082 4 sessions/1 proof (stuck rows are my QA
probes — disclosed, ignore); e083 1 view/23 publishes (seed data). The two
funnels define "stuck" differently — flagged for UX agents to unify.

## What still needs the owner's hand

1. **[TAP] Outreach**: approve/edit the 4 copy blocks in `OUTREACH.md`, then
   post/send them yourself (or explicitly authorize each send).
2. **[TAP] Referral**: sign up on e083, save token, give agents your code for
   `?ref=` links.
3. **[TAP] Domains**: create Porkbun account, buy `everloop.cc` (+ optionally
   `everloopagent.com`) — ~$14.48; then tell agents to wire DNS/`public_url`.
4. **[KEY] Jev**: mint OpenRouter or TypeSafe key if you want Jev-judged
   browser tests; hand to UX agents for the `llm_model_endpoint` slot.
5. **[DECIDE] Brand**: Everloop vs keep-loop vs forever-loop naming.
6. **[MANUAL] e083 extension** load-test on a live shop page (can't be done headless).

Files: `BROWSER-CAPABILITY.md`, `JEV.md`, `DOMAINS.md`, `OUTREACH.md`,
`GROWTH-REPORT.md` (this), log in `log/growth.log`. Experiment code untouched
(read-only); no servers started/stopped by me (UX agents restarted theirs
mid-session — I measured before and after).
