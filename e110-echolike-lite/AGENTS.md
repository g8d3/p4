# e110 — EchoLike Lite (rewrite from scratch)

The same product as `echolike-extension` with the minimum possible code:
capture X likes/bookmarks, send them to your inbox. Nothing else.

## What it is, what it's worth

A browser extension + one-file inbox server in ~350 lines total (the old
pair is ~6000). Install-and-done: two steps and one button, near-zero browser
cost: one click listener, no observers, no timers, no background traffic.

## Use (install-and-done)

1. `chrome://extensions` → Developer mode → Load unpacked → `extension/`.
2. Like a post on X. Done: the first capture claims a tenant on the hosted inbox
   (`https://inbox-lite.echolike.app`) by itself and everything after it flows there.
   For an inbox on your own machine instead: click the toolbar icon (it opens the
   one extension page), then **Find my inbox**. No address, no token, no account.

That is the whole setup; everything below is optional paths, not steps. The
popup's **Find my inbox** prefers an inbox on your own machine (loopback
`127.0.0.1`/`localhost`, 8931 then 8911) and falls back to the hosted one;
The popup's **Settings** button opens `options.html` for anything else (address, token, recovery code, account).

Why there is no secret to paste: a pasted token was the number-one setup failure —
a truncated paste looks exactly like a network problem and nothing in the UI can
tell them apart. Now the server mints the token (`POST /api/claim`) and the
extension keeps it. A private network (loopback, RFC1918, link-local, Tailscale
100.64/10) is itself the credential; the hosted inbox accepts open claims but
caps them per IP (`CLAIM_PER_IP_HOUR` 20, `DEVICES_PER_IP` 20) and per tenant per
month (`FREE_PER_MONTH` 3000).

The popup says ✓ Connected when the inbox answers. Failed sends wait in
the browser and retry on the next like or with Retry — nothing is lost, and an
install with no network at all still keeps every capture locally.

## Hosted inbox (the default path, multi-tenant)

`inbox-worker/` — one Cloudflare Worker + one D1 database, serving
`https://inbox-lite.echolike.app`. **One tenant per install**: a claim mints
`u_<12 hex>` + a 32-hex device token (stored as sha256 only), and every row is
scoped by `user_id`, so no tenant can read another's captures (proven by
`tests/review_inbox_worker.py`, which claims two and checks isolation both ways).

| Endpoint | Auth | What it does |
|---|---|---|
| `GET /api/health` | none | api version, `claim: open`, free quota |
| `POST /api/claim` | none (rate-limited) | new tenant + device token (`CLAIM_PER_IP_HOUR` 20) |
| `POST /api/likes` | Bearer | stores up to 500 **encrypted blobs**; plaintext only from a pre-4 client (flagged `legacy`), 402 when the month is spent |
| `GET /api/likes?limit=n` | Bearer | the caller's own blobs, JSON (ciphertext only) |
| `GET /` | none | the reader page; token + key arrive in the fragment |

Two read surfaces, both decrypting in the browser: the extension page
`inbox.html` (the popup's **Open my inbox**) and the hosted `/#t=…&k=…` for a
device without the extension. Neither sends a key to a server.

```sh
export CLOUDFLARE_API_TOKEN=...            # never committed
cd inbox-worker
wrangler d1 execute echolike-inbox --remote --file migrations/0001_init.sql   # once
wrangler deploy                            # worker + custom domain inbox-lite.echolike.app
python3 ../tests/review_inbox_worker.py    # live: two tenants, isolation both ways
```

Do **not** name the worker `echolike-inbox`: that name already belongs to another
lane (a queue consumer). `DEFAULT_INBOX` in `extension/background.js` is the only
place the hosted URL lives, so changing hosts is a one-line change plus a release.

Honest limits, in the order they must be fixed: the hosted inbox stores captures
in plaintext, so its operator can read them (self-hosting or client-side
encryption is the answer); a tenant is a device, not a person — no account, no
recovery, a reinstall is a new tenant; the free quota is enforced but nothing is
sold yet (payment + credits are the next product step).

## Encryption (1.2.0, non-negotiable: nothing ships without it)

Captures are sealed in the browser before they leave it. AES-256-GCM, a 32-byte
key generated on first run, one random IV per capture. What the inbox receives is
`{uid, iv, ct}` and nothing else — no handle, no text, no url. The worker stores
the blob verbatim (`likes.iv`, `likes.ct`, `likes.bytes`); `POST /api/likes`
refuses any item without `iv`+`ct` (400), so a plaintext client cannot slip in.
`GET /api/likes` returns blobs. A stolen tenant token is therefore worth nothing:
it buys ciphertext.

Where it is read: in the user's browser, never on a server.

| Reader | Key comes from |
|---|---|
| extension popup (last 30) | the local plaintext mirror kept in `chrome.storage.local` — same browser, no network |
| extension page `inbox.html` (own server) | the key in `chrome.storage.local`; it fetches `/api/likes` and decrypts |
| `https://inbox-lite.echolike.app/#t=&k=` (**Open my inbox** for the hosted inbox) | the URL fragment |
| hosted `/#t=<token>&k=<key>` | the URL fragment — never sent to the server, never in a log |
| self-hosted `server.py` | it cannot read anything: its page says so and points at the extension |

* **Recovery code**: the base64url (unpadded, 43 chars) form of the key, shown in
  `options.html` (popup → Settings) masked behind Reveal, with a Copy button. It is the only way to open the
  inbox on another device. There is no reset and no escrow — losing it loses the
  old captures, and the worker cannot help. base64url matters: `+` in a fragment
  comes back as a space through `URLSearchParams` and silently corrupts the key.
* The local mirror (`items` in `chrome.storage.local`) stays readable on purpose:
  the popup must work offline, and it is the user's own profile. `outbox` holds
  blobs, so a restart never re-sends plaintext.
* A v2 client or a pre-encryption blob still renders (`inbox.html` and the reader
  page show readable items as they are), so nothing breaks mid-upgrade.

## Account (1.3.0, optional by design)

Capturing never needs an account. An account exists for one thing: **getting your
inbox back** on a new phone, and holding a key backup the inbox cannot open.

- `POST /api/account/start {email}` → 6-digit code, 10 minutes, 5/hour per address,
  mailed through Resend (`RESEND_API_KEY` secret; `from` = `MAIL_FROM` or
  `EchoLike <hello@echolike.app>`, a domain already verified in the zone). The key
  used lives in the CORREO repo (`~/code/p4/e092-echolike/.secrets/resend_api_key`,
  36 chars, `GET /domains` answers 200) and is pushed with
  `tr -d '\r\n' < that_file | wrangler secret put RESEND_API_KEY` — the value is
  never printed, pasted or committed. Without the secret the endpoint answers 503
  "email is not configured on this inbox yet"; it never pretends to have sent.
  Verified end to end on 2026-11-12: `/api/account/start` with a real address →
  Resend → mail landed (`correo/inbox/*.json`, subject carries the code) → that
  code verified and minted an account token.
- `POST /api/account/verify {email, code}` + the device token as Bearer → account
  token (32 hex, stored hashed) and the device's tenant is linked to the account.
- `GET /api/account` → email, linked tenants, capture count, whether a key backup exists.
- `POST|GET /api/account/key` → the **wrapped** key backup.

**The key backup can never be opened by us.** The extension derives
PBKDF2-SHA256 (210k iterations, 16-byte salt) from a user passphrase, encrypts the
43-char key code with AES-256-GCM, and uploads `{salt, iterations, iv, ct}`. The
passphrase is never sent. Restore = same passphrase on any device → the key comes
back; a wrong one fails locally ("wrong passphrase"), not at the server.

Why a passphrase and not the emailed code: a code changes every login, so a key
wrapped with one could never be reopened. Why not the account token: the server
sees that token on every request, so wrapping with it would hand us the key.

`ECHO_DEV_CODE=1` in `.dev.vars` makes `POST /api/account/start` return the code
instead of mailing it, for `tests/review_account.py` and `review_account_ui.py`.
It is only ever set in local dev; production has no such flag.

Local worker for those tests (the local workerd binary lags the deployed one on
compatibility date, hence the override):

```sh
cd inbox-worker && wrangler dev --port 8788 --local --compatibility-date 2026-10-30
```

## Diagnostics (1.7.0)

`POST /api/telemetry` + a card in Settings. The rule that makes it usable: record
the **shape** of an attempt, never its content — action, ok, http code, host, ms,
error text (160 chars), client version. No post text, no handle, no url, no email.

* Extension: `tel(action, info)` keeps the last 200 events in
  `chrome.storage.local.telemetry` and queues them in `telq`; `telFlush()` uploads
  up to 20 with the same pass as a send, so diagnostics add no traffic of their own.
  Instrumented: `claim`, `claim.unreachable`, `send`, `send.unreachable`, `read`,
  `read.unreachable`, `account.start`, `account.verify`, `key.backup`,
  `key.restore`. A Send diagnostics toggle (default on) and a Copy button exist in
  Settings → 5 · Diagnostics, so a user can hand over the log even offline.
* Worker: whitelisted columns only (`telemetry`: at, ip_hash, user_id, version,
  action, ok, code, ms, host, error). Unknown actions are dropped, strings are
  truncated server-side, 20 events / 8 KB per request, IP stored as a salted hash.
  `tests/review_telemetry.py` proves a client that sends `text`/`handle`/`url`
  cannot get them stored — the columns do not exist.
* Reading it, when someone reports "I pressed the button and nothing happened":

```sh
cd inbox-worker
wrangler d1 execute echolike-inbox --remote --command \
  "SELECT at, version, action, ok, code, ms, host, error FROM telemetry ORDER BY id DESC LIMIT 40"
```

Two bugs this found within minutes of existing: `/api/telemetry` was answered 404
by `server.py` without draining the request body, and on a keep-alive connection
the leftover body was parsed as the next request line — the inbox read then failed
with a 501 that looked like a server outage. The cached body also leaked across
requests on one connection, so a POST after a bodyless request stored nothing
(silent data loss). Both fixed in `server.py` (`_safe` resets `self._body` and
drains it); `tests/review_drain.py` covers the whole path.

## Structure

```
extension/manifest.json   3 permissions lines, X hosts only
extension/content.js      one click listener: like/unlike/bookmark/unbookmark
extension/background.js   local save + POST outbox to /api/likes, retry on event,
                          loopback discovery + claim, DEFAULT_INBOX (hosted)
extension/popup.html/js   status + one button + Retry + the list. Nothing else.
extension/app.html        the extension's own page, two tabs: Inbox (decrypts,
                          export, retry) and Settings (1 · Inbox, 2 · recovery
                          code, 3 · account). `tabs.js` routes by hash.
extension/inbox.js        panel scripts, each wrapped in an IIFE: both used to
extension/options.js      declare `const $` at top level, which in one document
                          is a duplicate-declaration SyntaxError and kills the
                          second script whole.
extension/inbox.html/js   the full inbox page: fetches the blobs, decrypts here, exports
server.py                 self-hosted inbox, stdlib only: /api/health, /api/claim,
                          POST /api/likes, GET /
inbox-worker/             hosted inbox: Cloudflare Worker + D1 (src/index.js,
                          migrations/, wrangler.toml)
```

Deliberately dropped vs the old extension: voice/text notes, ntfy pipe,
auto-claim, link enrichment, diagnostics, drive mode, i18n, badges, alarms.
Each can return as its own experiment if someone pays for it.

## Servers

- Hosted inbox: `https://inbox-lite.echolike.app` (Cloudflare Worker + D1; worker
  `echolike-lite-inbox`, database `echolike-inbox`). Redeploy: `cd inbox-worker && wrangler deploy`.
- Self-hosted inbox (dev): `python3 server.py --port 8911` → http://127.0.0.1:8911 (see `GET /api/health`). Log file: `likes.jsonl`. Restart: kill PID, run again.

## Import (1.11.0): history is a button, on purpose

EchoLike captures from now on; the Import tab walks the list you already have.
Deliberate design decisions, so they are not "improved" later:

* **A button, not a schedule.** Scroll-walking someone's history on a timer looks
  exactly like a scraper and burns X rate limits. It runs only when pressed, on an
  X tab the user already has open.
* **The content script does the walking** (`import-start` / `import-cancel`), the
  background only receives batches (`capture-batch`) — the scraping code never runs
  in the service worker, and the worker never touches the DOM.
* **Growth is an event**: a MutationObserver on `document.body`, plus a 2.5 s "no
  new nodes" guard. Bounded: stops at the requested count, when the list ends, or
  after ten minutes. `xScroller()` finds the scrollable *ancestor of a tweet*, not a
  testid — X moves that container between layouts.
* **Dedupe by post**: `captureBatch()` drops anything whose `(kind, id)` the browser
  already has, so importing twice — or importing what was captured live — adds
  nothing. The quota still bounds a huge import honestly.
* Progress is written to `chrome.storage.local.import_progress` by the content
  script; the tab renders it from `storage.onChanged`. No polling anywhere.
* **The list URLs** (confirmed by the owner, not guessable): likes live at
  `https://x.com/i/history/likes` and bookmarks at `https://x.com/i/history` — the
  obvious `/likes` and `/i/bookmarks` are wrong. Both places: `import.js` (the link
  the tab offers) and `importStart()` (the tab it opens when none is open).
* `tests/review_import.py` builds a list that only grows when scrolled and asserts
  all of it: nothing runs by itself, 30 of 120, no duplicates, scroll happened,
  progress reports the end, cancel works.

## Automation (1.10.0): events, never a schedule

Nothing in the product is on a timer. Every send is caused by an event that already
exists, and the events that mean "work is worth doing now" are:

| Event | What happens |
|---|---|
| a capture (like/bookmark) | the queue is sent; if nothing is configured, it *connects itself* first (local candidates, then the hosted inbox) — no button |
| an X tab finishing loading (`hello` from the content script) | pending queue is sent, diagnostics backlog flushed |
| the browser's own `online` event (content script on x.com, or the extension page) | `syncAll()`: send what waited **and** repair anything the mirror holds that the inbox never received |
| opening the extension page | `syncAll()` once per load |
| `chrome.runtime.onStartup` / `onInstalled` | `syncAll()` — an update that fixes a queue repairs it by itself |
| any diagnostics event | the batch is uploaded immediately, if the user left diagnostics on |

There is **no `alarms` permission** and no retry timer: `tests/review_online.py`
asserts `typeof chrome.alarms === "undefined"`. The consequence is deliberate and
worth saying out loud: an install that is offline and never used again sends its
queue when it *is* used again (a like, an X tab, opening the page, a browser
start, or the network coming back). If the browser is closed at that exact moment,
the next start covers it.

## Rules

- The extension never invents data: unlike/unbookmark are sent as such.
- No traffic on its own: nothing is probed or sent until the user presses Find my
  inbox, or a capture is queued and an inbox is already configured ("already
  configured" includes the silent hosted claim on the first capture of a fresh
  install). Loopback discovery touches loopback only.

## Site (echolike.app)

Live page sources are `site/index.html` (one button + one line) and
`site/docs.html` (install guide). `echolike-lite.zip` is the shipped
artifact, built with `(cd extension && zip -qr ../echolike-lite.zip . -x ".*")`.
Publish = copy those four files + `server.py` into `g8d3/echolike-site`,
commit, push, `wrangler pages deploy --project-name echolike`, verify
`echolike.app` serves them. Old `extension_echolike.*` files in that repo
are left untouched (existing installs keep their update channel).

## Tests (real browser, no mocks of chrome.*)

```sh
xvfb-run -a python3 tests/review_capture.py   # content script vs X-shaped DOM (quoted tweet, kinds, double-inject)
xvfb-run -a python3 tests/review_popup.py     # popup renders the list, XSS-safe, Find my inbox, bad connect reported
xvfb-run -a python3 tests/review_e2e.py       # extension -> server.py round trip, claim with no token, 401 shown
bash bin/live-test-reset.sh                  # clears the hosted claim window (the live tests claim a lot)
python3 tests/review_telemetry.py               # diagnostics contract + no capture content in the log
xvfb-run -a python3 tests/review_two_browsers.py # two browsers, one account, one list (local worker)
python3 tests/review_import.py                  # the old-likes walk: stops at the count, dedupes, never starts itself
python3 tests/review_drain.py                  # a plaintext backlog drains itself and arrives sealed
python3 tests/review_claim.py                 # /api/claim over HTTP: private gate, cap, sha256-only storage
python3 tests/review_inbox_worker.py          # the LIVE hosted inbox: two tenants, isolation both ways
python3 tests/review_ads.py                   # ads hidden; Grok answers and real posts never hidden
python3 tests/review_inbox_page.py            # the LIVE reader page: fragment key, decrypts, wrong key refused
python3 tests/review_account.py               # accounts over HTTP (LOCAL wrangler dev): code, link, wrapped key
xvfb-run -a python3 tests/review_account_ui.py # the same from the popup, backup and restore included
# the promise in one test: fresh browser, no configuration, one like -> hosted inbox
# (real network, real tenant: it leaves one tenant behind per run)
xvfb-run -a python3 tests/review_zero.py
# a local inbox that refuses must not stop discovery (needs port 8931 free):
# systemctl --user stop echolike-lite-inbox && xvfb-run -a python3 tests/review_find_fallback.py
xvfb-run -a python3 tests/review_app.py       # the one page: tabs, find, ads switch, list, bad connect
# the real user seat: no configuration at all, one button, inside a throw-away netns
# so the live inbox on 8931 is untouched
unshare -rn sh -c 'ip link set lo up; xvfb-run -a python3 tests/review_find.py'
```

Headless must be `False` under xvfb: Chrome's old headless does not load extensions.

## Version history

- 1.0.0 — capture + send, popup was status only (a list was needed: no inbox meant no way to *see* anything).
- 1.0.1 — popup lists the last 30 captures with links (works with no inbox); `host_permissions` declared
  instead of `chrome.permissions.request` (the runtime prompt blocked the popup); server writes its data
  in the directory it is launched from; Save verifies the connection even with an empty queue.
- 1.11.1 — the import list URLs corrected to `x.com/i/history/likes` (likes) and `x.com/i/history` (bookmarks).
- 1.11.0 — Import tab: bring in old likes or bookmarks (100/300/1k/5k, or stop at the end), one deliberate button,
  MutationObserver-driven scrolling, dedupe by post, bounded at ten minutes, cancellable. Options on that tab say
  why it is not automatic.
- 1.10.0 — nothing needs a click any more: the first capture connects itself (local inbox if there is one, hosted
  otherwise), the queue is sent by the next event (capture, X tab load, browser `online`, page open, startup,
  update), and the page repairs diverged mirrors on open. The retry alarm and the `alarms` permission are gone —
  the owner asked for events, not a schedule — and diagnostics upload themselves when enabled.
  `tests/review_online.py` proves the offline → online path with Playwright's own offline switch.
- 1.9.0 — **the account is the unit of reading**. The reported symptom: the same X account in two browsers, and
  switching browsers hides likes. Cause: every install claimed its own tenant with its own key, and both readers
  fetched one tenant. Now `GET /api/account/likes` (account token) returns every device the account has linked,
  `GET /api/account` lists them, the extension's inbox tab and the hosted reader use it when signed in, and both
  dedupe by `(kind, id)` *after decrypting* — the server cannot dedupe sealed blobs, and the same like captured in
  two browsers has two different uids. Restoring the account key on a device re-seals that device's local mirror
  with the account key and pushes it (`keyRestore` → `syncAll`), so the two browsers converge on one list. The
  settings card warns when an account has no key backup, because without it a second device can never decrypt.
  `tests/review_two_browsers.py` builds exactly that: two tenants, one account, one shared like, 3 rows not 4.
- 1.8.0 — **the lost-captures bug**. `flush()` cleared the whole outbox on success, so a capture taken while the
  POST was in flight disappeared from the queue and stayed in the local mirror for ever: the owner's screen said
  `1 in the inbox · 18 in this browser` and 28 tenants held one or two captures each, every request answering 200.
  Now it removes only the uids it actually sent, serializes concurrent flushes (no double upload), and the inbox
  tab has **Send N missing**: it compares the mirror with `GET /api/likes`, re-seals and re-queues whatever the
  inbox lacks, then sends — the repair path for anything a broken queue dropped. `tests/review_drain.py` covers
  both, including a mirror holding captures that never reached the queue.
- 1.7.2 — the version is visible in two places a user actually looks at: the header of the extension page
  (`v1.7.2`, from `chrome.runtime.getManifest()`) and the toolbar icon's title (`stampVersion()` on install,
  startup and load). There is no popup since 1.6.0 — the icon opens the page.
- 1.7.0 — diagnostics: `POST /api/telemetry` + Settings card, so a button press leaves a readable record
  (action, http code, ms, host, error) and never a capture. Not-connected state now drains the queue when the
  page opens, `Find my inbox` drains it too when already connected, and a plaintext backlog is sealed before it
  is sent instead of being rejected forever with "items must carry iv + ct".
- 1.6.0 — **the tab panels refresh themselves**: a hash change is a same-document navigation, so the inbox tab kept
  showing the state from before you connected (Chrome does not reload). `tabs.js` now dispatches `echolike:tab`
  and each panel reloads its data when it becomes visible. Also: `server.py` grew `GET /api/likes`, without which a
  self-hosted inbox could never feed the inbox tab (only the hosted worker had it). Bitten once by a blind
  `s.replace("refresh();", …)`, which also rewrote `await refresh();` inside six handlers — the tests caught it
  (a 401 shown as "Connected"); edit by anchor, not by bare token.
- 1.6.0 — no popup at all: the toolbar icon opens `app.html#inbox`, which is the whole extension (two tabs).
  `Find my inbox` moved to the inbox tab, the ads switch to a settings card, and the not-connected state now
  says what to press and promises "nothing to type". **discover() no longer aborts at the first refusal**: a local
  inbox that answers /api/health but refuses the claim (device limit, old server) used to end the whole attempt
  with a dead button while a working hosted inbox was one step away. It now walks every candidate and reports
  what each said. `tests/review_find_fallback.py` reproduces exactly that case (a refusing inbox on 8931 plus the
  real hosted one). Also fixed: the inbox tab listed captures oldest-first (it reversed a list `state` already
  reversed) and `s.last.ok === false` errors were swallowed on that tab.
- 1.5.0 — one extension page, two tabs: `app.html#inbox` and `app.html#settings` (hash-routed, `tabs.js`). The
  separate `inbox.html` and `options.html` are gone; the popup's Settings button and the extensions page's
  Options both land on the settings tab. Panel scripts wrapped in IIFEs — two top-level `const $` in one document
  is a SyntaxError, and the second script died silently until `tests/review_zero.py` caught an empty recovery code.
- 1.4.1 — **Open my inbox** opens the hosted reader on echolike.app (`/#t=…&k=…`) when the inbox is the hosted
  one, and the extension page only for a self-hosted inbox (that page fetches same-origin). Both readers now
  answer the question the popup cannot: `N in the inbox · M in this browser · K waiting to send`, from
  `GET /api/likes` returning `total` and `quota` (it used to print `2/undefined`). `DEVICES_PER_IP` 20 → 50,
  because a household, an office or a CGNAT shares one address (the per-tenant monthly quota still bounds it).
  The popup cannot see `DEFAULT_INBOX` (different scope) — the hosted host is a local constant there now.
- 1.4.0 — settings left the popup. A 320px popup was holding eleven controls (address, token, save, disconnect,
  recovery code, copy, email, code, verify, passphrase, backup, restore) and read as a mess because it was one.
  Now: popup = status + one button + list; `options.html` = three cards, each with its own message line, its own
  primary action, labels above fields, recovery code masked behind Reveal, passphrase fields are real password
  inputs. Reachable from the popup's Settings button and from the extensions page (options_ui).
- 1.3.1 — accounts live: Resend key installed as a worker secret, real code delivered and verified; health reports
  `email_configured: true`.
- 1.3.0 — optional account by email: 6-digit code login (Resend), tenant linking for recovery, and a key
  backup wrapped with a user passphrase (PBKDF2 210k + AES-GCM) that the inbox cannot open; popup gets
  "Email me a code / Verify / Back up key / Restore key". Without `RESEND_API_KEY` the endpoint says so (503).
- 1.2.1 — protocol handshake: the client sends `x-echolike-api: 4` and the inbox refuses plaintext from it (400),
  while an older client (1.1.x) is accepted and its row flagged `legacy` — a queued capture is never dropped to
  enforce a rule. Health reports `min_client_api`. This is the fix for "9 waiting to send. inbox HTTP 400":
  1.1.1 spoke plaintext to a 1.2.0 inbox.
- 1.2.0 — end-to-end encryption: AES-256-GCM in the browser, the inbox stores `{uid,iv,ct}` and cannot read
  a word, plaintext uploads refused; extension page `inbox.html` (full list, decrypts locally, JSON export),
  hosted reader `/#t=&k=` with both secrets in the fragment, base64url recovery code in the popup; worker
  api 3, `CLAIM_PER_IP_HOUR` 20.
- 1.1.1 — hosted multi-tenant inbox (`inbox-worker/`, Cloudflare Worker + D1, `inbox-lite.echolike.app`),
  `DEFAULT_INBOX` claims a tenant on the first capture (truly install-and-done), popup link **Open my
  inbox**, quota shown in the popup, 402 surfaced as "free quota spent"; ads no longer hide Grok
  answers (a placement is an ad only when it holds a tweet and shows no Grok marker).
- 1.1.0 — zero-typing pairing: `POST /api/claim` issues a device token to a private-network client, the popup
  finds the loopback inbox and claims by itself (one button), address/token moved under Advanced, the server
  accepts the printed token or any claimed device token, device cap + per-IP claim limit, `.devices.json`
  stores sha256 only (bit-for-bit the same product, minus the thing people failed at).

## Update channel (why the Update button works — or does not)

The Update button in a browser's extensions page only exists for a **packaged
.crx whose manifest has `update_url`**. The browser then fetches that XML,
compares its `version` with the installed one, and installs the crx only if it
is newer. A "load unpacked" zip has no update_url: Update can only re-read the
local files, it can never download anything.

Lite ships both:

| File | Serves | Updates itself |
|---|---|---|
| `echolike-lite.zip` | desktop dev-mode install | no |
| `echolike-lite.crx` | phones (Quetta), anyone wanting self-update | yes, via `extension_update_lite.json` |

- appid `jmfddigdennhnndgaecgppajnjabhlgm`, key `.secrets/echolike_lite_crx.pem` (never committed).
  The same public key is in `manifest.json` as `key`, so a zip install and a crx
  install are the SAME extension (one storage, one id).
- The old extension keeps its own lane: `extension_update.json` → `idadgdnihpcaeamkkjpglmbcnabkjinc`,
  2.20.1. Publishing here would replace every install of that id, which is a
  product decision, not a release step.
- Release: `bin/publish.sh` (zip + crx + update json + verify + deploy + verify live),
  `--build` for local only. `bin/check_crx.py` verifies CRX3 exactly as Chrome
  does (signature over signed_header_data + payload, crx_id == appid); it was
  validated against the old crx this browser already accepts.
- Bump `version` in `extension/manifest.json` before publishing, always upward:
  a browser will not install a crx older than what it has.

## Server

```sh
mkdir -p inbox && cd inbox && nohup python3 -u ../server.py --port 8931 > server.log 2>&1 &
# prints the token; data lands in inbox/likes.jsonl
```

## Durability (2026-11-11: the inbox died mid-test)

A `nohup python3 server.py &` started from a tool call is killed with the run
that started it, silently, with no traceback: the captures stopped arriving and
the page answered nothing. It now runs as a user unit, which also restarts it
if the interpreter dies:

```sh
cp echolike-lite-inbox.service ~/.config/systemd/user/ && systemctl --user daemon-reload
systemctl --user enable --now echolike-lite-inbox     # start + survive logout
systemctl --user status echolike-lite-inbox           # state, PID, memory
journalctl --user -u echolike-lite-inbox -n 50        # log (stdout of server.py)
systemctl --user restart echolike-lite-inbox          # restart (token and data are kept)
```

Token and `likes.jsonl` live in `inbox/`, so a restart never breaks a phone that
was already connected. `tests/review_abuse.py` proves the server survives
hanging-up clients, garbage requests, truncated bodies and parallel posts.

## Ads toggle (1.0.2)

One switch in the popup (`hide_ads`, default on) hides promoted posts and
promoted trends on X. Implementation is a single injected `<style>` tag, removed
when off: no observer, no timer, no per-node work — the cost when off is zero and
when on is the browser's own style matching.

Markers (verified 2026-11-11 against the maintained extension
`insin/control-panel-for-twitter`, which uses the same container):

| What | Selector |
|---|---|
| promoted post wrapper | `[data-testid="placementTracking"]` **that holds a tweet** |
| its timeline cell (removes the gap) | `[data-testid="cellInnerDiv"]:has([data-testid="placementTracking"] [data-testid="tweet"])` |
| promoted trend | `[data-testid="trend"]:has(path[d^="M19.498 3h-15"])` |

**Grok lives in the same wrapper** (1.1.1): X puts Grok answer modules inside
`placementTracking` too, so hiding every placement also erased Grok's answers —
the reported bug. A placement is now an ad only if it holds a tweet *and* shows no
Grok marker (`[data-testid*=Grok]`, `[data-testid*=grok]`, `a[href*="/grok"]`,
`[aria-label*=Grok]`). `tests/review_ads.py` pins both directions down: promoted
post and promoted trend hidden, Grok answer (plain module and Grok-post form) and
real posts visible, and the switch reversible.

To re-check after X changes its DOM: like a promoted post, inspect it in devtools,
and look for the `placementTracking` wrapper. If it is gone, the fix is one
selector in `ADS_CSS` in `extension/content.js` plus `tests/fixture.html`. If a
Grok answer disappears again, paste this in the console on the offending page and
send the JSON — it prints structure only, no content:

```sh
copy(JSON.stringify([...document.querySelectorAll('[data-testid="placementTracking"]')]
  .filter(e => !e.getClientRects().length)
  .map(e => [...e.querySelectorAll('[data-testid],[aria-label],a[href]')].slice(0,25)
    .map(n => [n.tagName, n.getAttribute('data-testid') || n.getAttribute('aria-label') || n.getAttribute('href')]))))
```


Never hide ads from the *capture* path: liking an ad is a real like, so it is
still sent, with `ad: true` so the inbox can tell them apart.
