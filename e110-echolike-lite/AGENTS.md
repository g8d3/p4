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
   No address, no token, no popup action.

That is the whole setup; everything below is optional paths, not steps. The
popup's **Find my inbox** prefers an inbox on your own machine (loopback
`127.0.0.1`/`localhost`, 8931 then 8911) and falls back to the hosted one;
**Advanced** holds address + token for anything else.

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
| extension page `inbox.html` (**Open my inbox**) | the key in `chrome.storage.local`; it fetches `/api/likes` and decrypts |
| hosted `/#t=<token>&k=<key>` | the URL fragment — never sent to the server, never in a log |
| self-hosted `server.py` | it cannot read anything: its page says so and points at the extension |

* **Recovery code**: the base64url (unpadded, 43 chars) form of the key, shown in
  the popup under Advanced with a Copy button. It is the only way to open the
  inbox on another device. There is no reset and no escrow — losing it loses the
  old captures, and the worker cannot help. base64url matters: `+` in a fragment
  comes back as a space through `URLSearchParams` and silently corrupts the key.
* The local mirror (`items` in `chrome.storage.local`) stays readable on purpose:
  the popup must work offline, and it is the user's own profile. `outbox` holds
  blobs, so a restart never re-sends plaintext.
* A v2 client or a pre-encryption blob still renders (`inbox.html` and the reader
  page show readable items as they are), so nothing breaks mid-upgrade.

## Structure

```
extension/manifest.json   3 permissions lines, X hosts only
extension/content.js      one click listener: like/unlike/bookmark/unbookmark
extension/background.js   local save + POST outbox to /api/likes, retry on event,
                          loopback discovery + claim, DEFAULT_INBOX (hosted)
extension/popup.html/js   status + Find my inbox + Retry + Open my inbox; Advanced
                          (address, token, recovery code)
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
python3 tests/review_claim.py                 # /api/claim over HTTP: private gate, cap, sha256-only storage
python3 tests/review_inbox_worker.py          # the LIVE hosted inbox: two tenants, isolation both ways
python3 tests/review_ads.py                   # ads hidden; Grok answers and real posts never hidden
python3 tests/review_inbox_page.py            # the LIVE reader page: fragment key, decrypts, wrong key refused
# the promise in one test: fresh browser, no configuration, one like -> hosted inbox
# (real network, real tenant: it leaves one tenant behind per run)
xvfb-run -a python3 tests/review_zero.py
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
