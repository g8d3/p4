# Outreach kit — copy-paste blocks, ALL [NEEDS OWNER TAP]

Nothing below has been posted, sent, or published. Every item needs the
owner's explicit tap. Links are tailnet URLs (verified live 2026-09-29);
they open for anyone on the tailnet. Public launch waits on a domain (see
`DOMAINS.md`) — do not post these links to the open internet until then.

- e082 board: `http://100.102.52.59:8342` · share proof page: `.../share`
- e083 dashboard: `http://100.102.52.59:8383` · dataset pages: `.../dataset/<id>?ref=<CODE>`

Hero screenshots (captured via agent-browser, viewport 1366×900, 2026-09-29):
- `.growth-shots/e082-hero.png`
- `.growth-shots/e083-hero.png`

---

## e082 — Forever Harness [NEEDS OWNER TAP]

### X post (copy-paste)

```
I built a keep-going loop for coding agents: heartbeat, verify gates,
checkpoints, budget ledger. Configure once, it works indefinitely.
Live board: http://100.102.52.59:8342
```

### Reply-DM for people the owner knows (copy-paste)

```
hey — been hacking on a harness that keeps agents working long runs
without quality collapse (heartbeat + verify + budget stops). live here:
http://100.102.52.59:8342 — would love your take, brutal feedback welcome
```

### Referral mechanics (e082)

No referral codes on e082 — credit works through the **share page**:
`/share` is a public read-only proof page (live cycle, quality, version).
Sender posts *their* share URL; views count in `share_views`
(`GET /api/proof`). There is no per-sender attribution beyond that — if the
owner wants referrer credit on e082, that's a feature request for UX agents,
not something that exists today.

---

## e083 — ScrapeNet [NEEDS OWNER TAP]

### X post (copy-paste)

```
Turn any site you visit into a paid API: install the extension, scrape
pages you already browse, publish the dataset, earn per record.
Dashboard: http://100.102.52.59:8383
```

### Reply-DM for people the owner knows (copy-paste)

```
hey — we're testing ScrapeNet: a browser extension that turns pages you
visit into publishable data APIs, you earn per record. 2-min setup here:
http://100.102.52.59:8383 — sign up and I'll send you my referral code
so we're both credited. keen to hear what breaks
```

### Referral mechanics (e083) — how senders get credited

1. Sender signs up → server returns `{node_id, token, referral_code}`
   (token shown ONCE). Their code is on the dashboard + `GET /api/leaderboard`.
2. Sender shares a link with their code:
   - Dataset page: `/dataset/<id>?ref=<CODE>` (shows "You arrived via
     referral code **CODE**" banner + Join link), or
   - Front page: `/?ref=<CODE>`.
3. Friend signs up with `{name, referral_code: "<CODE>"}`.
4. Referrer earns **20% of the platform commission** on every record the
   referred node produces (needs.json: `commission_pct=10`, `referral_pct=20`
   → referrer ≈ 2% of referred gross, on top — the friend keeps full net).
5. Rankings are public: `GET /api/leaderboard` (referred signups, referred
   records, referral earnings). **Owner action before outreach:** mint YOUR
   referral code first (sign up on the dashboard, save the token), then paste
   it into the X post / DMs above replacing the generic URLs with
   `?ref=YOURCODE` links.

---

## Telemetry loop — first-funnel-reading procedure (LIVE, verified 2026-09-29)

Both `/api/funnel` endpoints return HTTP 200 (servers restarted by UX agents
today; earlier 404s were stale pre-restart processes). Proven end-to-end:
agent-browser visits → `POST /api/events` (`{"ok": true}`) → funnel counts move.

### e082 — where users stall

```bash
curl -s http://127.0.0.1:8342/api/funnel | python3 -m json.tool
# {views, installs, tokens, proofs, stuck_sessions[{session, last_event, last_detail, last_at}], sessions_tracked}
```

Read it as: `views` (first paint) → `installs` (plugin.zip download) →
`tokens` (owner token minted) → `proofs` (proof section expanded).
`stuck_sessions` = visited but never saw proof — each row is a person to
unblock, with their last event telling you where. Reading today:
4 sessions, 1 proof; the `growth-probe` + `check-*` stuck rows are **my own
QA probes** (curl without JS), not real users — ignore them.

### e083 — where users stall

```bash
curl -s http://127.0.0.1:8383/api/funnel | python3 -m json.tool
# {views, downloads, signups, publishes, stuck_sessions, sessions_total}
# publishes is server-truth (audit log), the rest are client events.
```

Read it as: `views` → `downloads` (extension.zip) → `signups` → `publishes`.
Reading today: 1 view (my QA visit), 23 publishes (seed/test data).
Note the asymmetry: e083 `stuck_sessions` was empty while e082 lists mine —
the two funnels define "stuck" differently (UX agents own both; ask them for
one definition before comparing numbers across apps).

### Owner's silent-watch routine (no word from users needed)

1. After any outreach tap, wait 1h, `curl` both funnels.
2. If `views>0` and downstream is 0 → open the app, check the stuck rows'
   `last_event`, fix that step first.
3. If `stuck_sessions` names a session whose `last_event` is `js_error`,
   that's a bug report written by the app itself — forward to UX agents.
4. Track `publishes` (e083) and `proofs` (e082) as the two numbers that mean
   "a stranger got value".
