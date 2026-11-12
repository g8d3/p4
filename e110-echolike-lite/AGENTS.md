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
* **Which tab**: the Import tab lists the open X tabs by path (an `●` marks the
  active one), prefers the one that is actually the list, and can open the list
  itself. "That tab has no EchoLike content script" now names the tab, offers
  *Reload that tab and start*, and `import.cmd` records the paths it saw — a
  message that does not say which tab is a bug, not a message.
* **Patience is the difference between 2 and 1,000**: one quiet tick never ends a
  walk (`IMPORT_QUIET_ROUNDS` 3, 3.5 s each), a visible `role="progressbar"` resets
  the count, the scroll container is found by computed `overflow-y` plus
  `scrollHeight`, and both the container and the window are nudged. The count asked
  for is the count sent: `harvest()` stops adding at `wanted`.
* **Times are the reader's**: every timestamp is stored in UTC (server, `at`,
  `received_at`) and rendered with `toLocale*` in the browser — inbox list,
  diagnostics log, import progress, hosted reader.
* **The list URLs** (confirmed by the owner, not guessable): likes live at
  `https://x.com/i/history/likes` and bookmarks at `https://x.com/i/history` — the
  obvious `/likes` and `/i/bookmarks` are wrong. Both places: `import.js` (the link
  the tab offers) and `importStart()` (the tab it opens when none is open).
* **The walk reads the DOM; it never intercepts X's API.** That is a deliberate
  trade: no auth headers to steal, nothing a redesign of the GraphQL payload breaks,
  and it keeps working in any browser that renders the page. The cost is virtualized
  lists, so the row selector is `article, [data-testid="tweet"]` (X uses both), and
  the primary link is resolved by `ownStatusLink()` — the first `/status/` anchor was
  often the **quoted** post, which collapsed several rows into one id.
* **A stale tab is a real, invisible failure**: a content script injected by the
  previous version keeps running until the tab reloads, so a fixed walk can appear
  broken (`import.cmd` present, `import.begin` missing, 7 rows collected). The
  script announces `CONTENT_API` on `hello` and in the `import-start` reply; the
  background refuses an older api, reloads the tab and starts from `pendingImport`
  when the page says `hello` again. Bump `CONTENT_API` in **both** files whenever the
  walk changes.
* **A helper on the wrong side of a template blanks the screen.** `countsLine()`
  was written next to `page()` — worker-side — while the reader script that calls it
  runs *in the browser*. `render()` threw on the first row, the status line had
  already been painted ("113 capture(s)"), and the list came back empty with no
  error shown. Two rules from it: any helper the page uses lives inside the `PAGE`
  string, and the row loop is wrapped per row so one malformed record cannot empty
  the list. `tests/review_inbox_page.py` caught it after deployment — run the full
  suite when a shared viewer changes, not just the viewer you touched.
* **Counters, not prose**: the end row always carries `rows` (what the DOM had),
  `seenRows`, `noId` (rows we could not resolve) and the scroller's tag + overflow,
  so "the tab shows more than 6" is answerable without another round trip.
* **Diagnostics, because "it did not work" is not a report.** The import path is
  instrumented at every step: `import.cmd` (mode, limit, how many X tabs, their
  paths), `import.begin` (path, article count, scroller tag, how much room is left
  to scroll), `import.batch` (`in`/`fresh`/`pending`), `import.end` and
  `import.stall` (`collected`, `sent`, `rounds`, `reason`, `scrollTop`,
  `scrollable`). `reason=end` means the list stopped appending; `reason=timeout`
  means it never did; `articles=0` means the tab was not a list.
* If no X tab exists, `importStart()` opens the right list URL, remembers
  `pendingImport`, and starts the walk when that tab's content script says `hello`
  — the page's own load is the event, no timer and no second press.
* `tests/review_import.py` builds a list that only grows when scrolled and asserts
  all of it: nothing runs by itself, 30 of 120, no duplicates, scroll happened,
  progress reports the end, cancel works.

## What a capture holds (1.16.0)

Every capture is one record, sealed whole and stored as one blob, so adding fields
needs no server migration — the inbox cannot see them anyway.

| Field | Where it comes from | Notes |
|---|---|---|
| `kind`, `id`, `handle`, `url`, `text` | the row | the original four |
| `lang` | `[lang]` on `tweetText` | cheap, useful for filters |
| `author_name` | `User-Name` | display name, not verified status |
| `published_at` | `<time datetime>` | **the only date that cannot be recovered later** |
| `counts.replies/reposts/likes/bookmarks` | each action button's `aria-label` | localized; `review_counts.py` pins the parser |
| `counts.views` | the `/analytics` link's `aria-label` | X only renders it on some layouts |
| `quotes` | the quoted tweet's own `/status/` link | id of the quoted post |
| `is_repost` | `socialContext` text | repost vs original |
| `ad` | `placementTracking` ancestor | a liked ad is still a like |
| `media/photos/videos/card` | `tweetPhoto`, `videoPlayer`, `card.wrapper` | what the post carries |
| `captured_at`, `clicked_at` | the browser clock | ISO UTC; **rendered in the reader's timezone** |
| `source` | like or bookmark | how it entered |
| `page` | `location.pathname` | which view it was captured from |
| `received_at` | the inbox, plaintext column | when the server stored it (only non-secret field) |

Deliberately **not** stored: the liker's own identity, follower counts (not on the
row), and anything that needs a second request — a capture must cost zero extra
traffic. `liked_at` does not exist on X's DOM: for a live capture `captured_at` is
the like moment, for an import it is the import moment, and the field name says so.

## Ordering and filtering (1.17.0)

Arrival order is not a user-meaningful order, and shipping only arrival order made
a fresh like look lost: a repair pass re-sent old captures, their new rows took the
top of the list, and the like the user had just liked sank out of sight. Both
surfaces — the extension page and the hosted reader — now sort explicitly and
remember the choice (`el_sort` / `el_sort_desc` in `localStorage`).

| Sort by | Field | Kind |
|---|---|---|
| my interaction | `clicked_at` | date |
| captured in the extension | `captured_at` | date |
| arrived in the inbox | `received_at` | date |
| post published | `published_at` | date |
| reposts, post likes, replies, bookmarks, views | `counts.*` | number |

The direction button says "newest/oldest" for dates and "most/least" for counts.
A row with an unknown value is always last, whichever direction is chosen — an old
capture with no counts never pretends to be the largest. Each row prints all four
dates (`liked`, `saved`, `arrived`, `published`) so the sort can be verified by eye.

Three server-side rules keep that list honest:

* **A read covers the whole inbox.** `GET /api/likes?limit=&offset=` pages the
  list (max 500 per page) and reports `total` on every page. The client walks it
  to the end. A capped window is what made the page claim captures were missing
  when they were only further down, and the repair pass then re-uploaded them.
* **One capture, one row.** A partial unique index on `(user_id, uid)` plus
  `INSERT OR IGNORE` makes a retry idempotent; the response reports `received`
  (stored now) and `duplicates` (already there), and only `received` charges quota.
* **Nothing to press.** Opening the page reads the inbox and sends by itself
  whatever this browser holds and the inbox lacks; the "Send N now" button exists
  only to skip the wait until the next event. Live proof: `tests/review_sort.py`
  seeds an unsent capture, opens the page and expects it in the inbox.

## Spaces (1.18.0): the collaborative unit, and why the pairing code was not it

The owner rejected the pairing code as the answer to "two phones, same account", and he
was right on the design: it shares a **permanent** secret, which cannot be rotated and
cannot be revoked for one person. What replaced it is a space.

| Concept | What it is |
|---|---|
| a **space** | a list several people write to: `spaces` + `space_members`, both server-side |
| **joining** | an invite with **`max_uses`** (1..25) and a lifetime (1..168 h): one code for my two phones and three friends, revocable at any moment |
| **the key** | generated by the creator, carried in the invite code, known only to members: the server stores ciphertext + member ids |
| **revoking** | the owner deletes the membership row; the member's API access ends immediately (`403`) |
| **leaving** | a member deletes their own row; their local copy stays (it is their browser) |
| **sharing** | `POST /api/spaces/:id/likes` with the capture re-sealed with the space key, so personal and shared copies coexist |

Two schema rules make that work: `likes.space_id` (`NULL` = personal), and **two** unique
indexes instead of one (`(user_id, uid) WHERE space_id IS NULL`, `(space_id, uid) WHERE
space_id IS NOT NULL`). The single `(user_id, uid)` index silently swallowed the first
share of your own capture — `INSERT OR IGNORE` — and the space stayed empty with nobody
to blame. Personal reads also filter `space_id IS NULL`: a shared row is sealed with the
space key, and showing it in the personal list read as "sealed with another key".

**"Who else saved this post"** comes from the members' own rows: the extension decrypts
every member's blob with the space key, groups by `kind|id`, and the card says
`saved by N people here`. The server learns nothing — it never sees a post id. A member
who is removed stops counting (their capture stays in the space, labelled
*N no longer in this space*): un-sharing what somebody already shared is not our call.

The UI is X's, deliberately (owner's requirement): rounded avatar with the author's
initial (no avatars are stored, so the initial does the work), bold name, grey
`@handle · time`, the post text, then X's action row — reply, repost, like, bookmark,
views — with our four dates and the space signal under it. The card CSS is scoped to
`.cards`, not `#list`: the space view is a second list, and scoping it to one container
made the space view render unstyled (screenshot-reviewed before shipping).

Honest gaps: no per-member revoke **button** (the API supports it: `POST
/api/spaces/:id/leave {user}`), the space key is not rotated after a removal (a removed
member can still read what they already downloaded — inherent to a local mirror), and
the hosted reader cannot open spaces yet (it has no space keys).

## One code, one list (1.17.5)

The first cut of pairing (below) shipped **two** secrets — a recovery code and a pairing
code — plus a paste box three cards away, and a "see both phones →" link that only
switched tabs. The owner's verdict was right: *"no pasó nada"* and *"P8 lo volviste muy
horrible"*. A link that looks like an action but is a navigation is worse than no link.

Rules the product now follows:

* **One code, N uses.** (1.18.2) The first cut made an invite single-use, which is a
  product bug, not a safety feature: connecting my own two phones or opening a space to
  three people meant one round trip per person. `max_uses` + a use counter (migration
  0011) and an *Active codes* view with **Revoke** per code. Rejoining as an existing
  member never spends a use; when the counter reaches the limit the code answers 409;
  revoked codes are a timestamp (`expires_at = 0`), so the row still explains itself.
* **Discovery, next.** Finding people by interest needs a delivery channel, not a code
  you cannot address: per-device ECDH (P-256) public keys, an **opt-in blind index**
  (`sha256(kind|post id)`, never text or handle), an overlap ranking, and an invitation
  addressed to that user with the space key wrapped to their public key. Migration 0010
  was written for it and deliberately **not** shipped half-built; the server and client
  land together or not at all. Honest limit to state then: the server can group equal
  hashes, and could enumerate X's public ids to guess what a hash is — hence the opt-in.
* **One code is one list.** The single code in `P8` is the pairing code: `{v,u,t,k}` —
  where the list lives, how to reach it, and the key that opens it. The raw 43-char key
  is no longer shown anywhere (it is derived for the reader URL), because two codes for
  one thing is a riddle, not a feature.
* **The action lives where the doubt is.** `P1` says `list u_… · this phone only` next to
  a real button, **＋ Add my other phone**, which opens the field inline and joins the
  list without leaving the tab. When two phones share the list, the same line says
  `2 phones` and the button disappears.
* **The paste box validates before it changes anything** (inbox answers, and the key
  decrypts an existing blob), and a refusal says why: *not a pairing code* vs *that key
  does not open the other phone's captures*. On success the phone gets its own device
  token, its own captures are re-sealed into the shared list, and the page reloads with
  the merged one.
* **No new concepts.** One X account per list today; several X accounts inside one list
  would need captures to carry which account they came from — **not** more codes.

## Two phones, one list (1.17.4)

Reported as: two phones on the same X account, likes made on the old one do not appear
on the new one. It was structural: **each install claims its own tenant and seals with
its own key**, so "the same account" was two private lists, and nothing in the UI said
so. The account (email + wrapped key) was the only bridge, and it was invisible.

What exists now:

* **The identity is on screen** — `P1` and `I1` say which list you are looking at
  (`list u_8c60…`, or `account me@x · 2 phones`), how many phones write to it, and when
  some captures are sealed with another key. "Which account is active" is no longer a
  question the user has to answer by guessing.
* **Pairing code** (`P8`): base64url of `{v:1, u:url, t:token, k:key}` — the list's
  address, its token and its key. Pasting it on the second phone makes both read and
  write the **same tenant with the same key**: one list, both directions, no account,
  no passphrase, no server change beyond the two endpoints below.
* **A paired phone gets its own device token** (`POST /api/devices`, max 8 per list),
  so one phone can be revoked without touching the other and "2 phones share it" is a
  fact from the server, not a claim from the UI.
* **Adopting a code is validated before it is adopted**: the inbox answers, the key
  actually decrypts an existing blob, and only then does the configuration change. A
  code from a different key is refused with the reason — adopting it would otherwise
  produce a list of unreadable rows. `tests/review_pair.py` checks both refusals and
  the happy path (old phone's 2 + new phone's 1 = 3, and nothing lost).
* **One unreadable blob never reads as "wrong recovery code"** any more: the reader
  decrypts row by row, counts what came from another key, and says so. Before, a
  single blob sealed elsewhere blanked the whole page with "wrong key".

Known limit, said out loud: a phone that pairs a list keeps its own local mirror and
its old tenant is simply abandoned (nothing is deleted), and a list accepts up to 8
phones. Device revocation has a server endpoint but no button yet.

## Where the boxes are (1.17.3): every control block has a code

The owner reports a failure by code, not by prose ("P2 fails"). Every box of
controls carries a visible chip in its top-left corner, and `data-section="…"` in the
DOM, so a bug report and the code that produced it point at the same thing.

The numbering is **stable — never renumber, only add**:

| Code | Surface | What it holds |
|---|---|---|
| `P1` | extension page | what the page is, where it writes, the status line and the last error |
| `P2` | extension page | sort by + direction + filter |
| `P3` | extension page | actions: Find my inbox / Send N now / Download JSON / Open on echolike.app |
| `P4` | extension page | the list itself |
| `P12` | extension page · Spaces | what a space is (the explanation is a box too) |
| `P13` | extension page · Spaces | start a space |
| `P14` | extension page · Spaces | join with an invite |
| `P15` | extension page · Spaces | my spaces (open / invite / share / leave) |
| `P16` | extension page · Spaces | the space view |
| `P5` | extension page | Import: which X tab, refresh, open the list |
| `P6` | extension page | Import: what to import, how many, start/cancel, status |
| `P7` | extension page | Settings · 1 Inbox (address, token, save, disconnect) |
| `P8` | extension page | Settings · 2 Recovery code |
| `P9` | extension page | Settings · 3 On X (ads switch, the circle) |
| `P10` | extension page | Settings · 4 Account and key backup |
| `P11` | extension page | Settings · 5 Diagnostics |
| `I1` | hosted reader | status |
| `I2` | hosted reader | sort |
| `I3` | hosted reader | actions (download JSON) |
| `I4` | hosted reader | the list |
| `X1` | the circle on x.com | its whole panel |

Rules for keeping it useful: one chip per box, never two boxes with the same code,
a hidden box takes its chip with it (the wrapper is hidden, not just the contents),
and `review_sort.py` fails if a code is missing, repeated or unbordered. **Explanatory
paragraphs are boxes too** (1.18.1): the owner pointed at the two help blocks that were
floating outside any border and could not be named. Inside a panel the codes ascend in
reading order; adding a box appends a code rather than renumbering the ones around it,
except within the Spaces panel while it is still new.

## The "not sent for ever" bug (1.17.3)

Reported as: a like shows *not in the inbox yet*, then it appears in the inbox, then
pressing send says it went, and it still shows as unsent. Server side was clean (221
rows, all with a `uid`, every send 200), so it was the page's arithmetic:

* the reader dedupes **the list** by post (`kind|id`) so two browsers show one row;
* "already sent" was built from that **deduped** list, so any row folded away — the
  same post captured twice, e.g. a re-like, or a live capture plus an import — left
  its uid out of the sent set;
* the send compares **uids** server-side, found nothing missing, did nothing, and
  returned 200. The red line therefore never cleared: a permanent false alarm.

Now two different sets, both built from the rows **before** the display dedupe:
`sentUids` (server truth, from the blob rows) and `sentPosts`. A capture is:

| Situation | Shown as | Sent? |
|---|---|---|
| its uid is in the inbox | a normal row | no need |
| its post is there under another copy | *also in this browser*, counted in the status, filter **second copies in this browser** | **no** — the inbox already has that post |
| neither | *waiting to send* (red), filter **not in the inbox yet** | yes, by itself |

That last distinction is only visible after decrypting, so the page now sends
exactly the uids it decided are missing (`send-uids`) instead of asking the worker to
recompute from ciphertext: the two sides cannot disagree about what "missing" means.


## The circle on x.com (1.17.2)

The version belongs where the user already is. A small draggable circle sits on
x.com (bottom right by default), carries the version, and opens the actions that
make sense from a page you are reading:

| Action | What it does |
|---|---|
| My inbox / Settings | opens `app.html#inbox` / `#settings` in a tab |
| Export likes / bookmarks / everything | writes a JSON file from the local mirror, labelled with how many |
| Hide this button | sets `fab_on: false`; the **On X** card in Settings turns it back on |

The shell is a **shadow root** in one host element appended to
`document.documentElement` (not `body`: X re-renders the app root and this must
outlive it). No X CSS can restyle it and none of ours can leak into X.

Rules it follows, because a floating thing on a live page is where products become
rude:

* **No timers, no observers.** Mounted once, positioned from storage, free until
  pressed. Position (`fab_x`/`fab_y`) is written on `pointerup` after a real drag;
  5 px of travel means drag, not press.
* **It cannot steal an interaction.** Every handler stops propagation and the capture
  listener only reacts to `data-testid` action buttons, so liking under the circle
  still works (`review_fab.py` proves it).
* **It stays on screen.** Stored coordinates and every move are clamped to the
  viewport; a resize re-clamps instead of pushing it off the edge.
* **A broken icon is not a state.** The icon comes from the package; if it fails to
  load, a lettermark replaces it (an inline `onerror` would be blocked by X's CSP).
* **The panel never covers its own button**: above the circle when there is room,
  below otherwise, measured from the circle's edges. It closes on Escape, on a press
  anywhere else, or on a second press, and the circle is a real `role=button` with
  Enter/Space.
* **Export needs no inbox, no server, no account.** The mirror is in this browser, so
  the file is built from it and a user with no connection still gets their data out.

The red badge is the outbox count: the one number a user wants without opening
anything ("did my like make it?"). Bump `CONTENT_API` (now 8) whenever the page script
changes — the background refuses to start an import on a tab running an older script
and reloads it instead.

The roadmap he asked for is one honest line in the panel — *next on this button: AI
on the post, profile edits, writing posts with images and video, comments* — because
a disabled button pretending to be a feature is worse than a sentence.

## The row is a card (1.17.1)

The sort and filter block also carries a **filter**: all captures,
**not in the inbox yet**, likes, bookmarks, unlikes, ads, with media. The status
line's "N not in the inbox yet" is a button that opens exactly those N — the answer
to "which ones are missing?" without scrolling for them.

Before 1.17.1 a row was one run of text with `·` separators, which wrapped wherever
the width decided: the counts on one line, the dates on another, the post text
starting in the same visual mist, and the text touching the border so selecting it
was a fight. Now every capture is four blocks:

| Block | Holds | Layout |
|---|---|---|
| head | kind, `@handle` link, tags (ad, N media, waiting to send, unencrypted) | inline; tags are pills |
| stats | replies · reposts · likes · bookmarks · views | **`repeat(5, minmax(0,1fr))`**: always five cells, value over label, `tabular-nums`, unknown rendered as `–` so nothing shifts |
| dates | liked · saved · arrived · published | `repeat(auto-fit, minmax(132px,1fr))`: 4 columns on a desktop, 2 on a phone, each cell `nowrap` with the exact second in `title` |
| body | the post text | `white-space:pre-wrap`, `overflow-wrap:anywhere`, `user-select:text`, and the card carries 12 px of padding so the text never touches the border |

The five-fixed-column rule is the part worth keeping: `auto-fit` looked fine on a
desktop and produced 4 + a stray fifth cell on a phone. `tests/review_sort.py`
asserts five cells on one line at 760 px **and** 390 px on both surfaces, plus the
card padding and the wrapping, because "it looks organised" is exactly the kind of
thing that silently regresses.

That review also found a real bug: the hosted reader **never had `received_at`** —
the blob carries the sealed record, the arrival time is the plaintext column next to
it, and the reader's `decrypt()` dropped it. "Arrived in the inbox" was therefore a
sort key with nothing to sort in the web reader. It is attached on decrypt now.

## Automation (1.10.0): events, never a schedule

Nothing in the product is on a timer. Every send is caused by an event that already
exists, and the events that mean "work is worth doing now" are:

| Event | What happens |
|---|---|
| a capture (like/bookmark) | the queue is sent; if nothing is configured, it *connects itself* first (local candidates, then the hosted inbox) — no button |
| an X tab finishing loading (`hello` from the content script) | pending queue is sent, diagnostics backlog flushed |
| the browser's own `online` event (content script on x.com, or the extension page) | `syncAll()`: send what waited **and** repair anything the mirror holds that the inbox never received |
| opening the extension page | the inbox is read to the end, then anything the mirror holds and the inbox lacks is re-sealed and sent — no button; `syncAll()` also runs on demand for "now" |
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
python3 tests/review_sort.py                  # LIVE: one capture one row, offset pages, sort/filter both readers, self-repair
xvfb-run -a python3 tests/review_fab.py       # the circle on x.com: version, drag, exports, hide, capture still works
xvfb-run -a python3 tests/review_pair.py      # two phones, one list: identity, pairing code, refusals, nothing lost
xvfb-run -a python3 tests/review_spaces.py    # spaces: create, one-time invite, join, share, who else saved it, revoke
# the real user seat: no configuration at all, one button, inside a throw-away netns
# so the live inbox on 8931 is untouched
unshare -rn sh -c 'ip link set lo up; xvfb-run -a python3 tests/review_find.py'
```

Headless must be `False` under xvfb: Chrome's old headless does not load extensions.
`tests/review_sort.py` needs the extension page too, so it runs under
`xvfb-run -a` as well.

## Version history

- 1.18.2 — invitations are **reusable**: `max_uses` (1..25) and a use counter instead of a single use
(migration 0011), a form in the space row that asks how many people and how long (default 3 people / 24 h), the
code's message states both, and **Active codes** lists what is still usable with a **Revoke** per code. Joining
twice as a member spends no use; exhausted and revoked codes answer 409. `tests/review_spaces.py` now joins three
different tenants with the same code and checks the fourth is refused.

- 1.18.1 — the explanatory blocks are boxes too, with codes: the Inbox's own paragraph now lives inside `P1`
(what this page is, where it writes, the status), and the Spaces panel gets `P12 · what a space is`, with start /
join / list / view becoming `P13`–`P16`. Nothing else changed; the point is that every block on the page can be
named by code, including the ones that only explain.

- 1.18.0 — **spaces**, the collaborative unit the pairing code should have been: create, invite with a
one-time expiring code, join, share captures into it, leave, and the owner can revoke a member. The card now looks
like X's (avatar, bold name, `@handle · time`, text, action row with reply/repost/like/bookmark/views icons, then
our four dates), and in a space it says **saved by N people here** — computed by decrypting every member's row
locally, so the server never learns which post is which. New tab **Spaces** (`P12` start, `P13` join, `P14` list,
`P15` view). Server: `spaces`, `space_members`, `space_invites`, `likes.space_id`, two unique indexes instead of
one (the personal index silently ate the first share of your own capture), personal reads filtered to
`space_id IS NULL`, `/api/spaces…` endpoints. New test: `tests/review_spaces.py` (invite works once, a second use
is 409, a made-up token 404, an outsider 403, revocation cuts access, both members counted on the card).

- 1.17.5 (release gate) — `bin/publish.sh` now downloads the published `echolike-lite.crx` and verifies it
(CRX3, signature, appid, version) after the json check. Before, the json was verified and the artifact was only
verified locally, which cannot catch a stale or half-uploaded file — the exact shape of a browser stuck on
*Updating…*. Documented the browser-side cause (the updater runs at startup) above.

- 1.17.5 — one code, one list. `P8` collapses to a single code (the pairing code, which already carries the
key) with Reveal/Copy and one paragraph: the recovery-code field and the pair-another-phone block are gone. The
join action moves to where the doubt is: `P1` shows `list u_… · this phone only` with a real **＋ Add my other
phone** button that opens the field inline; the old "see both phones →" link only switched tabs, which read as
"nothing happened". `tests/review_pair.py` now drives that inline flow (one code, masked, reveal, broken code
refused, foreign-key code refused, join closes the box and merges the lists).

- 1.17.4 — two phones, one list. `P1`/`I1` state which list is open (`list u_…` or `account email · N
phones`), how many phones share it and whether any capture is sealed with another key; `P8` gains a **pairing
code** (address + token + key) with Copy/Reveal and a paste box — pairing validates the inbox and the key against
an existing blob before adopting anything, then gives the new phone its own device token (`POST /api/devices`, 8
max) and re-seals its own captures into the shared list. The reader decrypts row by row: one blob from another key
is counted and named instead of blanking the page with "wrong recovery code". `/api/account` reports per-phone
counts. New test: `tests/review_pair.py`.

- 1.17.3 — every box of controls carries a code (`P1..P11` extension page, `I1..I4` hosted reader, `X1` the circle)
  so a failure can be reported as a code; `review_sort.py` fails if a code is missing, repeated or unbordered.
  Fixed the permanent false alarm the owner hit: the reader deduped the list by post and then built "already sent"
  from that deduped list, so a copy folded away said "not in the inbox yet" for ever while sending did nothing
  (200), because the worker compares uids. The page now keeps `sentUids` and `sentPosts` from the rows before the
  display dedupe, names post-level copies as *second copies in this browser* (new filter) instead of unsent, and
  sends exactly the uids it decided are missing (`send-uids`) so both sides cannot disagree.
- 1.17.2 — the extension shows up on x.com: a draggable circle in a shadow root, with the version on it (hover
title, panel header, footer), a red badge with the captures that have not reached the inbox yet, and a panel with
**My inbox**, **Settings**, **Export likes / bookmarks / everything** (JSON, built from the local mirror, so no
inbox and no network are needed) and **Hide this button** — restorable from the new switch in Settings. Position
persists and is clamped to the screen; drag vs press is 5 px of travel; Escape or a press elsewhere closes it; it
is `role=button` with Enter/Space; the icon falls back to a lettermark instead of a broken image; the panel is
placed above or below the circle so it never covers it. `CONTENT_API` 8. New test: `tests/review_fab.py`.

- 1.17.1 — the row is a card: kind + handle + tags, then **five aligned count cells** (value over label,
  tabular numbers, `–` when unknown), then the four dates in their own grid (4 columns, 2 on a phone), then
  the post text with real padding, pre-wrap and anywhere-wrapping so it can be selected without fighting the
  border. `auto-fit` gave 4 + a stray fifth cell on a phone; the stats grid is `repeat(5, 1fr)` now.
  Found on the way: the hosted reader dropped `received_at` on decrypt, so "arrived in the inbox" had no
  value to show or sort by there. `tests/review_sort.py` checks the layout at 760 px and 390 px, both surfaces.

- 1.17.0 — ordering, filtering and an honest window. Both readers sort by the four dates (my interaction,
  captured in the extension, arrived in the inbox, post published) and the five counts (reposts, likes,
  replies, bookmarks, views), ascending/descending, remembered across loads; a filter picks one slice
  ("not in the inbox yet" included) and the count in the status line opens exactly those. Why it was needed:
  the read was capped at 200 rows while the mirror held 500, so the page reported captures as unsent when
  they were only past the window, and every repair re-uploaded them — 45 duplicate rows and 45 quota units in
  one afternoon, with the freshly liked post pushed out of sight. Now: `limit`+`offset` reads to the end
  (worker API 4), a partial unique index on `(user_id, uid)` with `INSERT OR IGNORE` (migration 0007, which
  also de-duplicated the existing rows and put the quota back in line), `received`/`duplicates` in the
  response, `syncAll()` paging the whole inbox, and the page repairing itself on load. `server.py` de-dupes on
  read and pages too. New test: `tests/review_sort.py`.

- 1.0.0 — capture + send, popup was status only (a list was needed: no inbox meant no way to *see* anything).
- 1.0.1 — popup lists the last 30 captures with links (works with no inbox); `host_permissions` declared
  instead of `chrome.permissions.request` (the runtime prompt blocked the popup); server writes its data
  in the directory it is launched from; Save verifies the connection even with an empty queue.
- 1.16.1 — the hosted reader showed "113 capture(s)" and an empty list: `render()` called a helper that only existed
  in the extension (`countsLine`), threw on the first row, and the counts had already been painted. The helper now
  lives inside the page, rows render in a try/catch, and `review_inbox_page.py` proves N items produce N rows.
- 1.16.0 — captures carry what the post is worth: replies/reposts/likes/bookmarks/views (locale-aware parser,
  `tests/review_counts.py`), `published_at`, `lang`, `author_name`, `quotes`, `is_repost`, media flags, `source`
  and `page`, all sealed in the same blob. Readers show the counts and the published date; the export keeps them.
  Blob caps raised (24 KB per item, 512 KB per request). `CONTENT_API` 7.
- 1.15.1 — hidden tabs, measured instead of argued: the walk listens to `visibilitychange`, pauses (no timers, no
  observer), writes `import.paused` / `import.resumed` with `hiddenFor` and `rowsDelta` — the number that answers
  "would it work unfocused?" — and hidden time stops counting against the ten-minute guard. The end row carries
  `hiddenMs` and `rowsWhileHidden`. `CONTENT_API` 6.
- 1.15.0 — the two reasons the walk stopped at 7, both evidenced in one telemetry row (`scrollTop=2284`,
  `scrollable=6655`, `rows=7`): (a) it called "end" **mid-list** after three quiet ticks — now it only ends at
  the bottom (`atBottom()`), keeps stepping while there is more below (`stuck` counter for a page that never grows),
  and (b) the likes tab was **in the background**, where Chrome throttles rendering and X's loader never fires —
  `importStart()` brings the tab to the front before the walk. The scroll is bigger (80% of the viewport), nudges
  both the window and the resolved container, and fires a wheel hint. `CONTENT_API` 5.
- 1.14.1 — the walk announces its api (`CONTENT_API` 4). A tab running the previous version's content script is
  detected, reloaded and restarted automatically — that stale script is what produced "7 collected, 1 sent", with
  no `import.begin` in the log at all.
- 1.14.0 — extraction stopped losing rows: the primary `/status/` link is chosen instead of the first one (quotes made
  several rows collapse into one id), and rows rendered as `div[data-testid="tweet"]` are read like `article`s. The end
  row now reports `rows`/`seenRows`/`noId`/`scroller`, so the next "only N came" has a number behind it.
  `tests/review_import.py` gained a second fixture with three rows quoting the same post.
- 1.13.2 — the discrepancy between screen and log: `tel()` written while an upload was in flight was stranded in
  `telq` until the next user action (so `import.batch` never appeared), and the end row was written before the last
  batch answered (`sent=0` while the UI said "5 sent"). Diagnostics now drain until empty, the end row is written
  after the final callback, it carries `skipped=`, and the Import tab says "N already in this browser, not sent
  twice" instead of leaving 6-vs-5 unexplained.
- 1.13.1 — the walk scrolls **one viewport at a time**: `scrollTop = scrollHeight` made X's virtualized list render its
  tail and discard the middle (a 1k-like account yielded 6 tweets, `sent=0`, `reason=end`). Failures now leave a row
  from both sides — `import.sendfail` (content script: `lastError` / no answer, with the batch size) and
  `import.batch` with `ok:false` if `captureBatch()` throws — because a silent 0 is what cost a round trip.
- 1.13.0 — Import picks its tab: the tab lists X tabs by path, can open the list, and names the one that failed
  (with a *Reload that tab and start* button). The walk waits out stalls (3 quiet rounds, progressbar aware, real
  scroll container), so it no longer "finishes" at 2 of 100. All displayed times are in the user's timezone.
- 1.12.0 — the import can be diagnosed: `telemetry.detail` column plus `import.cmd`/`import.begin`/`import.batch`/
  `import.end`/`import.stall` rows with counters (collected, sent, rounds, articles, scrollTop, scrollable, reason);
  the Settings log shows that detail. Patience: a list that answered nothing once gets up to four rounds before
  "end" is believed, and a missing X tab is opened and started by the page's own `hello`.
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

## Update channel: a stuck "Updating…" is usually the browser, not the release

Seen in the wild (2026-11-12, a phone): the extensions menu said *Updating…* and stayed
there. Checked from the outside, the release was perfect — `echolike-lite.crx` served as
`application/x-chrome-extension`, no redirect, valid CRX3, signature matching the appid in
`extension_update_lite.json`, manifest inside 1.17.5, same as advertised. A browser
restart fixed it: Chromium runs its extension updater **at startup** and then roughly
every five hours, so a manual click right after a publish can sit in that state.

`bin/publish.sh` now proves both halves before calling a release live: the json advertises
`$VER`, **and the artifact downloaded from echolike.app** passes `bin/check_crx.py
--appid … --version $VER`. A json advertising a version the served crx does not carry is
exactly how a browser loops on *Updating…*, and no local check can see it.

When it happens again, in this order:

1. `curl -sI https://echolike.app/echolike-lite.crx` → 200, `application/x-chrome-extension`, no redirect.
2. `curl -s https://echolike.app/extension_update_lite.json` → the version you published.
3. `bin/check_crx.py <downloaded crx> --appid … --version …`.
4. If all three are right: restart the browser (or wait for its next check). The FAB on
   x.com shows the running version, which is the fastest way to confirm the update landed.

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
