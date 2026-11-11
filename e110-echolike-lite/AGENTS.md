# e110 — EchoLike Lite (rewrite from scratch)

The same product as `echolike-extension` with the minimum possible code:
capture X likes/bookmarks, send them to your inbox. Nothing else.

## What it is, what it's worth

A browser extension + one-file inbox server in ~350 lines total (the old
pair is ~6000). Install-and-done: two steps and one button, near-zero browser
cost: one click listener, no observers, no timers, no background traffic.

## Use (2 steps, one click)

1. `python3 server.py` on your computer → prints address + token.
2. `chrome://extensions` → Developer mode → Load unpacked → `extension/`.
3. Extension popup → **Find my inbox**. That is all: no address, no token.

Discovery is loopback only (`127.0.0.1` / `localhost`, 8931 then 8911); the first
inbox that answers takes `POST /api/claim`, which mints a device token and stores
its sha256 in `.devices.json` (0600). The extension keeps the token; the user
never sees or copies one. Address + token still exist under **Advanced** for an
inbox on another machine, or a hosted one that hands out its own token.

Why: a pasted token was the number-one setup failure — a truncated paste looks
exactly like a network problem and nothing in the UI can tell them apart. A
private network (loopback, RFC1918, link-local, Tailscale 100.64/10) is itself
the credential; a public server needs `--open-claim`, and even then the device cap
(`ECHO_MAX_DEVICES`, default 5) and per-IP rate limit (`ECHO_CLAIM_PER_HOUR`,
default 5) hold. The printed server token keeps working — it is the admin path.

Next step toward true install-and-done: put a hosted inbox in `DEFAULT_INBOX`
(`extension/background.js`) and the first capture claims there by itself, with no
popup action at all. That is a hosting + payment decision, not a code one.

The popup says ✓ Connected when the inbox answers. Failed sends wait in
the browser and retry on the next like or with Retry — nothing is lost.

## Structure

```
extension/manifest.json   3 permissions lines, X hosts only
extension/content.js      one click listener: like/unlike/bookmark/unbookmark
extension/background.js   local save + POST outbox to /api/likes, retry on event,
                          loopback discovery + claim (no token to paste)
extension/popup.html/js   status + Find my inbox + Retry; Advanced = address/token
server.py                 stdlib only: /api/health, /api/claim, POST /api/likes, GET / list
```

Deliberately dropped vs the old extension: voice/text notes, ntfy pipe,
auto-claim, link enrichment, diagnostics, drive mode, i18n, badges, alarms.
Each can return as its own experiment if someone pays for it.

## Servers

- Inbox (dev): `python3 server.py --port 8911` → http://127.0.0.1:8911 (see `GET /api/health`). Log file: `likes.jsonl`. Restart: kill PID, run again.

## Rules

- The extension never invents data: unlike/unbookmark are sent as such.
- No traffic on its own: nothing is probed or sent until the user presses Find my
  inbox (or a capture is queued for an inbox that is already configured).
  Discovery touches loopback only.

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
| promoted post wrapper | `[data-testid="placementTracking"]` |
| its timeline cell (removes the gap) | `[data-testid="cellInnerDiv"]:has([data-testid="placementTracking"])` |
| promoted trend | `[data-testid="trend"]:has(path[d^="M19.498 3h-15"])` |

To re-check after X changes its DOM: like a promoted post, inspect it in
devtools, and look for the `placementTracking` wrapper. If it is gone, the fix
is one selector in `ADS_CSS` in `extension/content.js` plus `tests/fixture.html`.

Never hide ads from the *capture* path: liking an ad is a real like, so it is
still sent, with `ad: true` so the inbox can tell them apart.
