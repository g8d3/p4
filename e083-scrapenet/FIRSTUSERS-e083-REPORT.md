# FIRSTUSERS-e083-REPORT — stranger-to-first-dataset, fixed + verified

Server: http://127.0.0.1:8383 · LAN http://192.168.0.177:8383 · tailnet
**http://100.102.52.59:8383** (live-resolved, also in `needs.json:public_url`).
`test/check.sh` → **PASS**. Watchdog `overnight-tester.log` → e083
health/check/flow **PASS every round, zero FAILs introduced**.
Log of this work: `log/firstusers-e083.log`.

## Journey gaps found + fixed (each with curl proof)

1. **No install path (the reported blocker).** Dashboard only mentioned
   `extension/` (server-local). Fixed: `GET /download/extension.zip` zips
   `extension/` on the fly (stdlib `zipfile`, `Content-Disposition:
   attachment`), plus a green “Install extension (.zip)” card on `/` with
   numbered steps Download → `chrome://extensions` → Load unpacked, and the
   collector URL auto-filled from `location.origin`.
   Proof: zip downloads; contains `background.js, content.js, manifest.json,
   options.html, popup.html, popup.js`; embedded `manifest.json` parses with
   `manifest_version: 3`.
2. **Cold landing explained nothing.** Rewrote `/`: hero states what this is
   (people-powered scraping network → public APIs → paid per record), the 3
   steps Install → Signup → Publish are above the fold, then signup, records,
   recipes, publish, earnings, leaderboard, ideas.
   Proof: cold `curl /` contains the pitch, install card, signup, publish;
   old grey paragraph gone.
3. **No auth (write endpoints open).** Added `POST /api/signup {name,
   referral_code?}` → `{node_id, token, referral_code}` (token issued once).
   `/api/ingest`, `/api/recipes` POST/PUT/DELETE, `/api/publish` require the
   token (`Authorization: Bearer` or JSON/header/query `token`), matched
   against sha256 in `data/auth.json` (mode **0600**). Reads stay public.
   Tokens appear in no other response (asserted for records/earnings/audit).
   Proof: signup returns token+code; unknown node without token → 401 with
   signup hint; wrong token → 401; auth'd ingest/publish/recipe roundtrip OK.
4. **No shareable dataset surface (no UGC engine).** Added `GET
   /dataset/<id>`: stats, sample-rows table, Copy-API-link + Subscribe
   (copy-curl) buttons, install/signup CTAs, `?ref=CODE` banner with join link.
   Proof: page 200s with stats/table/buttons; `?ref=` echoed; unknown id 404s.
5. **No referral mechanics.** `?ref=` pre-fills signup on `/` and dataset
   pages; `POST /api/signup` records `referred_by`; `GET /api/leaderboard`
   ranks referrers (signups, referred records, earnings); earnings split
   redirects `referral_pct`% of commission to referrers (documented
   `referral_rule` in `needs.json`: 10% commission × 20% referral → referrer
   gets 2% of referred gross, invitee keeps full net). Dashboard §5 shows the
   leaderboard live.
   Proof (labeled alice/bob run): bob's 2 records → gross 0.02, commission
   0.002, `referral_share_to_referrer` 0.0004; leaderboard credits alice
   0.0004 with 1 signup / 2 records.
6. **Watchdog compatibility (self-found during testing).** The 15-min tester
   posts tokenless ingest as `node-tester`. Design answer: sealed
   `legacy_nodes` snapshot (ids with pre-auth records/ledger rows) may write
   without a token — documented migration with sunset (delete the list to
   enforce signup for all). Also fixed a real bug this exposed: referrers with
   zero own records showed 0 earnings (bonus map only covered nodes with
   records); leaderboard now attributes from referred nodes directly.
   Proof: exact watchdog ingest (`node-tester`, no token) → `accepted: 1`,
   records+earnings verify; all watchdog rounds PASS.
7. **Extension couldn't authenticate.** `options.html` gained an API-token
   field; `background.js` sends it on ingest. Old tokenless installs on legacy
   nodes keep working.

`needs.json` additions (all machine values there, none hardcoded):
`referral_pct` (20), `referral_rule`, `auth_path`, `public_url`
(refreshed by `bin/serve.sh` on every start). Restarts done via `bin/serve.sh`
with the exact PID from `ss -tlnp` (pids 1311687 → 1317618 → 1317944);
`test/commission_test.py` untouched and passing (`compute_earnings` signature
unchanged — referral split lives in `earnings()` only).

User-seat review of `/`: all 9 action buttons wired (signup, refresh, ingest,
test/sandbox/refine/save, publish, ideas), both selects wired, download anchor
+ collector-URL copy field + dataset copy buttons verified. No dead controls.

## Auth design (summary)

Self-serve, no passwords: name → `node_id` (slug + 3 random bytes) + 32-hex
token + 6-hex referral code. Server stores only the sha256 (0600 file);
the token is returned exactly once. Every write checks
(node_id, token) with `secrets.compare_digest`; failures are 401s pointing at
`/api/signup`. Referral codes are validated at signup; bad codes 400.
Migration carve-out above; sunset = empty `legacy_nodes`.

## Launch kit (`LAUNCH.md`)

X thread (5 posts), Reddit post for **r/webscraping** (most topical: tool
post with honest question), IndieHackers post, directory checklist, UGC loop
diagram + metrics table (signups, ref rate, datasets, referred records,
referral paid) mapped to `/api/leaderboard` + dashboard §4/§5.

## Exact [NEEDS OWNER] steps to get users 1–10

1. Post the X thread from the owner account; pin; reply to comments 24h.
2. Post to r/webscraping from a warmed account after checking self-promo rules.
3. Post to IndieHackers + r/SideProject + r/beermoney (same account hygiene).
4. Join 2–3 scraping/data Discords, read #promo rules, share one dataset page.
5. Pay $5 + accept ToS for the Chrome Web Store listing (I staged the zip).
6. Submit Product Hunt + AlternativeTo (accounts + screenshots).
7. Personally onboarding: reply to every first dataset page posted; feature
   the best one on X. Nothing here needs code — all blockers are accounts,
   payments, or human presence, listed per-item in `LAUNCH.md`.
