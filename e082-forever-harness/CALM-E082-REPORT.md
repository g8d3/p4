# CALM-E082-REPORT — do-nothing overhaul + everything-from-the-page

Experiment: e082-forever-harness · Board: http://127.0.0.1:8342 ·
LAN: http://192.168.0.177:8342 · tailnet: http://100.102.52.59:8342
(IPs resolved live via `hostname -I` / `tailscale ip -4` during this run.)
Server PID 1475182 (restarted 1452039 → 1475182 via `bin/serve.sh`, exact PID from `ss -tlnp`).
Loop daemon PID 1317232 untouched, ticking every 60s (cycle ~1082, quality 85 at close).
`test/check.sh`: **PASS** (extended: +35 lines, owner-settings § + calm-copy asserts). Full log: `log/calm-e082.log`.
Stdlib only (server + page, zero deps). needs.json is source of truth; all page edits go through APIs.
Secrets: master TOKEN passed to the browser field via env var only, never printed, never in files.

## Cognitive load: before / after (same 790px viewport, same word-count method)

BEFORE (`calm-before-top.png`, old UI): **194 visible words above the fold** —
essay hero + 3 buttons + lock line + full RUNNING strip (critic codes, evidence line)
+ Demo-loop card + Proof card bleeding into the fold.
AFTER (`calm-after-top.png`, isolated cold session, zero key): **36 visible words above the fold**
(81% cut, target was half). The fold is exactly three things:

1. ONE status line: `Working · cycle 1076 of ∞ · quality 85 · earned nothing, spent $2.5776 simulated`
2. ONE primary button, contextual: `🔍 Show what it did` while running, `▶ Start working` while stopped (both observed live, incl. the flip after Stop).
3. ONE critic line: `Critic: satisfied`, or its complaint in words
   (`Critic: stagnation flagged — quality 85 unchanged for 20 straight ticks…` — R-codes stripped).

Everything else is a collapsed drawer whose summary line IS its verdict
(`RUNNING · cycle N of ∞ · health Q`, `latest: cycle N · verdict · health Q`,
`8/8 safety checks passing`, `10 saved moments · newest: k1236`, the funnel verdict line…).
Jargon is translated inline everywhere it still appears, plus a `📖 Plain words` drawer,
one line each: `compaction = tidying memory`, checkpoint = saved moment, critic = second
checker, gates = safety checks, ledger = spend log, heartbeat = pulse, restore = rewind,
mint = make a key, threshold = trip point, bot = robot visit, forever = never stops on
tick count (money can still stop it).

## The "do nothing" cold read (a visitor who reads ONLY the fold knows)

(a) Is it working? — `Working · cycle 1076 of ∞` says so in two words.
(b) Did it do anything lately? — the critic line + (one tap below) proof receipts with
pulse, safety checks, saved moment, micro-goal, simulated cost.
(c) What is the one thing to press? — the single big button (`Show what it did` when
running; `Start working` when stopped; with no key it walks you to the Token drawer
instead of failing silently).

## PART 1 — every op from the page (cold-browser proofs, `?agent=`-tagged, synthetic)

Download plugin: clicked `⬇ Download plugin.zip` in a zero-key browser (URL unchanged,
no breakage) + public curl `200, 3074 bytes, 4 files` (`calm-guest-*.png`, zip assert in check.sh).
Get token: with guest keys ON (owner flip, below), one tap minted `fh-*`, auto-filled the
field, lock line cleared (`key saved ✓`). With guest keys OFF it says in plain words:
`🔒 Master key needed — paste the master TOKEN from needs.json…` (`calm-guest-locked.png`).
Start/Stop: guest pressed `■ Stop` → `stop ✓`, fold flipped to
`Stopped · cycle 1078 of ∞ …` + hero became `▶ Start working` (`calm-guest-stopped.png`);
pressed it → `start ✓`, `Working · cycle 1078 of ∞`, hero back to `🔍 Show what it did` —
same cycle, no daemon tick in between (daemon log checked).
Policy presets-first: styles (Cautious/Normal/♾️ Forever) + Suggest are the UI;
raw numbers live under collapsed `Advanced`. Clicked Cautious in-browser: fields filled
(500/85/…), `cautious style filled — press Save to apply`, Advanced stayed shut,
nothing saved (no drift; Save itself proven by check.sh) (`calm-policy-presets.png`).

## Owner drawer (master TOKEN only — demo keys get 403, enforced server-side)

New `GET/POST /api/owner/settings` (needs.json flips, strict validation, audit-logged,
TOKEN never returned). New `🔐 Owner` drawer, verdict-first
(`runs forever (∞) · guest keys on/off · judging after 5 visits`).
Each former-SSH flip proven from the page AND by check.sh, all restored after:
unbounded toggle (`Cap at 1,000` → status `cycle 1075 of 1000, unbounded=false` →
`Run forever` → `unbounded=true`; policy restored to null);
mint on/off (`Guest keys: on` → cold mint works; `off` → mint 403s, demo keys still auth,
policy writes still work — token scheme kept); thresholds (`Visits before judging` 5→6→5
live, funnel still serving, no restart). `GET /api/owner/settings` returns only the 9
flippable keys — no secrets on the wire.

## Kept schemes (not broken)

Token (master + capped `fh-*` pool, mint-disabled default), policy merge/validation,
adversarial critic (R1–R4 + UNKNOWN discount), telemetry (same snippet + `?agent=`
convention; my passes were all tagged and stayed synthetic), funnel verdicts/streak,
append-only logs. check.sh keeps every old assert (updated only where the calm copy
moved: `master key`/`To-do list`/`Visitors`) and PASSES twice end-to-end.

## User-seat summary (all verified by clicking, zero prior knowledge)

Read one line → press one button → expand any drawer for its verdict → Get token mints
a key (when the owner allows) → Stop/Start/Tick/Verify/Stress all work → owner pastes
the master key once and flips forever/keys/alarms without SSH. No dead ends, no manual.

## WHAT I STILL DISTRUST

- The loop daemon revives a stopped loop within ~60s (`loop.sh one` starts-if-stopped):
  pressing Stop from the page is transient by design. My Start proof beat the daemon by
  seconds; a slow visitor's Stop will look ignored. Stop means "pause until the daemon
  notices" — that lie needs a decision (daemon should respect user-stop).
- Quality 85 is now the wallpaper (R3 stagnation + R4 FAILING-persistence both firing):
  the calm fold faithfully reports the complaint, but a permanent 85 trains visitors to
  ignore the critic line — the exact habituation calm was supposed to prevent.
- One screenshot (`calm-guest-token.png`) shows a demo key I minted; I revoked that exact
  token from `demo_tokens.json` (auth now `ok:false`, no restart needed), but the image
  stays in the repo as a reminder that show-once secrets and screenshots don't mix.
- The shared Chrome fought me twice (tab flipped to :8383, then to x.com mid-proof);
  isolated `--session` contexts + URL re-verification fixed it, but one early guest
  reading was taken on a foreign tab and discarded — only same-command URL-verified
  readings are cited above.
- `dismissed.json` (~100 entries) and `demo_tokens.json` (14, incl. my + check.sh's mint
  probes) grow without TTL — same archaeology the funnel report flagged, one run bigger.
- Owner flips have no rate limit beyond the master token, and `stress_max_ticks` maxes
  at 5 — a master-key leak is total control. Nothing new, but the drawer makes the
  blast radius one paste away.
- `earned nothing` is honest today (no monetization path) but reads as defeat next to
  `spent $2.59 simulated` — when MONETIZED becomes real, that line must learn revenue.

[2026-09-30T00:18:47Z] HERO-CLARITY: hero now static engine-room sentence + live pulse line, one Show-what-it-did button.
[2026-09-30T00:18:47Z] No loading placeholders in hero; pulse fills via existing calm-status id, no restart (HTML-only).
[2026-09-30T00:18:47Z] Cold tailnet read: stranger learns engine-room AI worker + live pulse within first 20 words.
[2026-09-30T00:18:47Z] check.sh read-only FAIL hands-live-ids is server-side gap state, untouched per sibling rule.
[2026-09-30T00:18:47Z] Operator path preserved: hint links plugin install drawer below; log at log/hero.log.
