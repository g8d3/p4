# FIRSTUSERS-e082-REPORT — first-visitor readiness

Experiment: e082-forever-harness · Server: http://127.0.0.1:8342 ·
LAN: http://192.168.0.177:8342 · tailnet: http://100.102.52.59:8342
(IPs resolved live via `hostname -I` / `tailscale ip -4` during this run.)
Loop daemon: PID 1317232, ticking every 60s (cycle 65, quality 100 at close).
`test/check.sh`: **PASS**. Full log: `log/firstusers-e082.log`.

## Journey gaps found + fixed (each verified with curl)

1. **No install path for strangers.** There was a `plugin/` directory but no
way to fetch it; a visitor with pi/opencode could not reach installed in
<5 min. Fixed: `GET /download/plugin.zip` zips `plugin/` on the fly
(stdlib `zipfile`) with `Content-Disposition: attachment`, plus a prominent
Install card with copy-paste snippets for pi AND opencode (origin
auto-filled by JS), download button, and link to the SKILL doc at
`GET /skill`. Proof: `curl …/download/plugin.zip` →
`application/zip`, contains `plugin/hooks/keep-going.sh`,
`plugin/opencode.json`, `plugin/plugin.json`,
`plugin/skills/keep-going/SKILL.md` (4 files).

2. **Landing said nothing to strangers.** First paint was "No login" + bare
controls — no what/install/after. Fixed: hero answers (a) what (keep-going
loop, why agents die), (b) install (3 numbered steps, <5 min), (c) after
install (the first tick explained step by step: heartbeat → gates →
compact → ship, "press Tick and watch"). Proof: cold `curl …/` matches
`what this does`, `plugin.zip`, `first tick` (also asserted in check.sh).

3. **Zero write protection (adversary's #1 fix).** Anyone on the tailnet could
Start/Stop/rewrite policy. Fixed: `TOKEN` in `needs.json`, minted with
`secrets.token_urlsafe(32)` on first boot if absent, file kept `0600`;
`POST /api/policy` + `POST /api/control/*` require
`Authorization: Bearer TOKEN` (401 otherwise). Reads (`/api/status`,
`/api/proof`, `/share`, board) stay public; `POST /api/verify` stays public
(deliberate: it is a read-only gate check, and the board's "Verify now"
works token-free). No signup endpoint — documented single-user flow: owner
copies TOKEN from `needs.json` into the board's Token field (persisted in
localStorage), which unlocks Start/Stop/Tick/Save (buttons render
`disabled` until a token is stored). `bin/loop.sh`, the plugin hook
(`$FOREVER_HARNESS_TOKEN`), SKILL.md, and `test/check.sh` all carry the
token. Proof: no-token tick → `401 unauthorized…`; wrong token → 401;
reads → 200; authed policy/tick → 200; check.sh PASS.

4. **No social proof / UGC hook.** Fixed: public `GET /share` — live cycle,
quality, version, budget, "powered by" + install link + SKILL/proof links;
board has "Copy share link" (with non-secure-context fallback) + Open
/share. Proof: `curl …/share` shows `cycle 64 · quality 100`, powered-by,
`/download/plugin.zip`, `/skill`; share views counted in
`data/stats.json`.

5. **No value proof for the $8–15/mo pitch.** Fixed: `GET /api/proof`
(uptime_seconds, server_booted_at, cycles_shipped/logged, quality_now +
30-tick quality_history, ledger used/total/left/entries, version,
downloads, share_views) linked from the landing Proof card, which renders
uptime, shipped count, quality history, spend, downloads, share views with
raw links to `/api/proof|ledger|cycles|checkpoints`. Proof: curled JSON
shows 50 shipped, uptime ticking, ledger `$0.1536 / $10.0`.

6. **Bonus bug found live: `context_budget` gate permanently red.**
`maybe_compact` compacted to the cap and `do_tick` then appended one more
cycle, so the loop sat at cap+1 forever (51 vs 50 → quality 85, pass false
on every tick). Fixed by compacting down to cap−1 so post-ship lands
exactly on cap. Proof: after fix, `POST /api/verify` →
`quality 100, pass true`, all 6 gates PASS, steady-state 50 live cycles.
(The pre-fix 85-era remains honestly visible in quality_history.)

7. **Bonus UX bug: copy buttons threw on plain-HTTP LAN/tailnet URLs**
(`navigator.clipboard` is undefined outside secure contexts). Fixed with an
`execCommand` fallback. Proof: headless DOM harness — clipboard path and
fallback path both end in "copied".

## Auth design (summary)

Single-owner shared-token: one `TOKEN` in `needs.json` (0600, stdlib
`secrets`, minted on first boot). Public reads, Bearer-gated writes
(policy + control). No signup/login/session machinery — deliberately the
smallest thing that fixes unauthenticated writes on a single-user box.
Owner UX: Token field on board → localStorage → `Authorization` header on
every mutating fetch; `GET /api/auth` reports `{protected, ok}` for the
"Check token" button. Daemon/hook/SKILL flows use env/file token, never
hardcoded. Trade-off accepted: token travels over plain HTTP on LAN/tailnet
(same exposure class as before; Tailscale WireGuard covers the tailnet URL).

## User-seat review (headless + DOM harness, node)

What the visitor can do on `/`: read what/install/first-tick hero →
download plugin.zip → copy pi/opencode snippet (origin prefilled) → open
SKILL doc → paste Token (unlocks Start/Stop/Tick/Save) → Start, Tick,
Verify now, Refresh → edit + Save policy → read live status, budget bar,
gates, checkpoints, proof metrics → copy share link / open /share.
Harness-verified: status renders RUNNING, proof renders shipped count,
buttons locked without token, Bearer sent on Start + policy save, token
check + share copy + save all succeed, UI JS passes `node --check`.
(I did not split a browser into the user's terminal; render verified via
served HTML + stub-DOM execution instead.)

## Coordination with running flows

- No `log/overnight-tester.log` and no 15-min tester watchdog exist on this
box (searched) — nothing to adapt there; noted, not assumed.
- 60s loop daemon: killed exact PID 1308210, updated `bin/loop.sh` for the
token, restarted (PID 1317232); server restarts done by exact PID each time
(1311219 → 1317143 → 1317317), never broad-pkill; e083's server (PID
1311687) untouched. Daemon ticked successfully through both restarts; zero
`401` in loop logs; `test/check.sh` PASS twice, last at cycle 64–65.
- `needs.json` holds all machine values (port/bind/intervals/budget/TOKEN);
no IPs or ports hardcoded in new code.

## Launch kit (`LAUNCH.md`)

X thread (5 posts), opencode-Discord #showcase post (community picked for
native opencode plugin support), r/SideProject post — all specific to this
app with live URL placeholders; checklist with 5 explicit [NEEDS OWNER]
items (X/Discord/Reddit/HN/directory — all need human accounts I don't
have); measurement table (downloads via zip counter, active loops via
heartbeat, shares via share_views) mapped to board locations + targets
(≥10 downloads, ≥3 concurrent ticking loops, ≥5 share views).

## Exact [NEEDS OWNER] steps to get users 1–10

1. Confirm the public URL (`bash bin/serve.sh`; tailnet IP can rotate) and
paste it over every `HARNESS_URL` in `LAUNCH.md`.
2. Post the X thread from the owner account.
3. Post in opencode Discord #showcase (human account).
4. Post in r/SideProject (human account + karma).
5. Keep `bin/loop.sh daemon` + server alive; watch Proof card/downloads —
reply to every tester; at 10 users decide on Show HN + $8–15/mo plugin.
