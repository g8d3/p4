# UX-E082-REPORT — action-first overhaul + telemetry

Experiment: e082-forever-harness · Board: http://127.0.0.1:8342 ·
LAN: http://192.168.0.177:8342 · tailnet: http://100.102.52.59:8342
(IPs resolved live via `hostname -I` / `tailscale ip -4` during this run.)
Server PID 1384756 (restarted 1317317 → 1384756 via `bin/serve.sh`, exact PID from `ss -tlnp`).
Loop daemon PID 1317232 untouched, ticking every 60s (cycle ~805, quality 100 at close).
`test/check.sh`: **PASS** (extended). Full log: `log/ux-e082.log`.

## Before / after (seen in a real browser)

BEFORE (agent-browser screenshot + a11y snapshot, :8342): wall-of-text hero
("What this does" + 3-step install + "first tick" essay, zero buttons above the
fold), install card first, goal as a one-line text `<input>`, token flow =
"copy TOKEN from needs.json", gates as unaligned flex divs
(`name … PASS · detail` run together), checkpoints as bullets, no proof
buttons, no stress, no telemetry.
AFTER (private Chrome seat — own `--user-data-dir` + CDP port + named
agent-browser session, after the shared `default` session kept flipping to
another experiment's :8383 tab): hero is 2 short lines + 3 primary buttons
above the fold (▶ Start | 🔍 Show what it did | ⬇ Install) + lock line +
live RUNNING strip (screenshot `e082-after-top.png`). Every section below is
one line + buttons. Verified by clicking, not just rendering (details below).

## The 7 charges — each with proof

1. **ACTION-FIRST.** Hero ≤2 lines + Start / Show what it did / Install.
   `Show what it did` scrolls to Proof and expands the last receipt;
   `Install` scrolls to the (now secondary, collapsed) plugin card.
   Proof: hero screenshot + `curl …/ | grep "Show what it did"` (asserted in check.sh).
2. **AI-PREFILL, never a blank box.** Goal is now a `<textarea>` with ✨ Suggest
   (server drafts 3 goals from live history) + Cautious/Normal/Aggressive
   preset buttons that fill the form (Save still applies). Clicked Suggest in
   the browser: got "Ship 10 more clean ticks holding quality >= 70 (now 100.0,
   50 shipped, $8.07 budget left)" + 2 more, rendered as one-click paste
   buttons (screenshot `e082-seat-suggest.png`). `GET /api/suggest-goals`
   asserted in check.sh (exactly 3 non-trivial goals).
3. **PROOF buttons.** "Show last tick's work" → heartbeat + gates + checkpoint
   + micro-goal + cost for the exact cycle; "Show last 5 ticks" → timeline.
   Clicked in browser: "cycle 796 · verdict shipped · quality 100 ·
   heartbeat … by loop · 6/6 ✓ gates · k898 compaction · micro-goal · $0.0024".
   Endpoints `GET /api/last-tick`, `GET /api/ticks?limit=5` asserted in check.sh.
4. **TOKEN affordance.** "Get token" mints a per-browser demo token (`fh-*`)
   via `POST /api/token/mint` → show-once box + Copy + one-line where-it-goes
   ("paste it in the board's Token field — it unlocks Start/Stop/Tick/Save/Stress").
   Clicked in browser: minted `fh-mFth…`, field auto-filled, "locked buttons
   unlocked", Start enabled. Locked buttons carry `title="needs token — Get token"`
   + the 🔒 lock line. Master TOKEN flow untouched: daemon/hook/SKILL still use
   `needs.json` TOKEN (0600); `check_auth` accepts master OR `fh-*` demo token
   (pool cap 200, 5 per session). check.sh asserts mint shape + demo-token `/api/auth`.
5. **STANDALONE FIRST.** First two cards are the built-in demo loop
   ("already running below", "runs out of the box"); plugin reframed as
   "Done with the demo? Connect YOUR harness" — collapsed `<details>`,
   download + pi/opencode snippets intact. check.sh asserts "already running" copy.
6. **ALIGNED gates + checkpoints.** Gates render as a STATUS pill | GATE |
   RESULT-one-line table with expandable full detail (screenshot
   `e082-seat-gates.png`: 6× green PASS pills, aligned columns).
   Checkpoints render as aligned rows (id·cycle·kind pill | summary | time)
   with expandable summary + `restore` on periodic rows ("digest only" on
   compaction). `POST /api/restore` (authed): periodic → appends a `restored`
   cycle (append-only, never rewrites); compaction → honest 400
   ("nothing to restore; pick a periodic checkpoint"). Both paths curled.
7. **LIMIT-PUSHER.** "🧨 Stress test" (authed) runs 7 probes in-process —
   unknown-key, 501-char goal, budget-cut-below-spent, wrong-token,
   budget-stop-armed, 50× status flood with avg ms, live verify — plus up to
   `stress_max_ticks` (needs.json, =2) real aggressive ticks. Real button click
   in browser: **HOLDING · 7/7 attacks blocked · 2 live ticks absorbed**
   (cycles 800/801, quality 100; screenshot `e082-seat-stress.png`).
   Rejected mutations land in `policy-changes.jsonl` as ok:false. check.sh
   asserts 401 without token, scoreboard with token.

## Telemetry verified (no user reports needed)

- Client snippet posts `{v:1, session, ts, page, event, detail?, ms?}` to
  `POST /api/events`: `page_view` (+load ms), `click:<button-id>` (delegated),
  `download`, `get_token`, `first_proof_seen` (first proof expand),
  `js_error` (onerror + unhandledrejection), `idle_45s` (45 s no pointer/key,
  once per view). Transport: `sendBeacon` w/ `fetch(keepalive)` fallback.
- Server appends `data/events.jsonl` — **never stores IPs** (no
  `client_address` anywhere on this path); `GET /api/funnel` returns
  `{views, installs, tokens, proofs, stuck_sessions[]}` (views-but-no-proof +
  last event). Dashboard "🐾 Stuck users" card renders it live.
- Proof: curled event posts → funnel counted them (`views 9, proofs 3`);
  live card showed `8 visits · 3 saw proof · 2 minted tokens` with real
  STUCK? rows incl. an `idle_45s` signal; check.sh asserts ingest ok,
  validation 400, funnel keys, and zero `ip/client/address` keys in the log.
  Privacy one-liner on the page + funnel link.

## Remaining gaps (honest)

- Demo-token minting re-opens writes to anyone with a browser (the exact hole
  the first-users agent closed). Deliberate per the owner's charge; mitigated
  by caps (200 pool / 5 per session) + audit trail. If abused: disable
  `/api/token/mint` and the board falls back to owner-only TOKEN.
- My own restore tests left two `restored` cycles + one self-healed 85 tick
  (cycle 805: restores pushed live cycles over the compaction cap, gate caught
  it, next tick compacted back to 100 — the system working as designed).
- `restore` advances the cycle counter (append-only by design); purists may
  want restores excluded from `/api/cycles` tails.
- No per-button latency stats yet (ms field ingested, not aggregated).
- The shared `agent-browser` default session is contested by another live
  agent (tab kept flipping to :8383) — future seat reviews should use a named
  session + private Chrome from the start, as done here.

## User-seat summary (what a visitor can do now)

Read 2 lines → Start (after one-tap Get token) → Show what it did (believe in
10 s) → Suggest + presets + Save policy → read aligned gates/checkpoints →
restore a periodic checkpoint → Stress test and watch HOLDING → check Stuck
users → Install plugin only if leaving the demo. No dead ends, no blank boxes.
