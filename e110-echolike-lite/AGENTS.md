# e110 — EchoLike Lite (rewrite from scratch)

The same product as `echolike-extension` with the minimum possible code:
capture X likes/bookmarks, send them to your inbox. Nothing else.

## What it is, what it's worth

A browser extension + one-file inbox server in ~350 lines total (the old
pair is ~6000). Install-and-done in 3 steps, near-zero browser cost: one
click listener, no observers, no timers, no background traffic.

## Use (3 steps)

1. `python3 server.py` on your computer → prints address + token.
2. `chrome://extensions` → Developer mode → Load unpacked → `extension/`.
3. Extension popup → paste address + token → Save & send. Like any post.

The popup says ✓ Connected when the inbox answers. Failed sends wait in
the browser and retry on the next like or with Retry — nothing is lost.

## Structure

```
extension/manifest.json   3 permissions lines, X hosts only
extension/content.js      one click listener: like/unlike/bookmark/unbookmark
extension/background.js   local save + POST outbox to /api/likes, retry on event
extension/popup.html/js   status + 2 fields + Save + Retry
server.py                 stdlib only: /api/health, POST /api/likes, GET / list
```

Deliberately dropped vs the old extension: voice/text notes, ntfy pipe,
auto-claim, link enrichment, diagnostics, drive mode, i18n, badges, alarms.
Each can return as its own experiment if someone pays for it.

## Servers

- Inbox (dev): `python3 server.py --port 8911` → http://127.0.0.1:8911 (see `GET /api/health`). Log file: `likes.jsonl`. Restart: kill PID, run again.

## Rules

- The extension never invents data: unlike/unbookmark are sent as such.
- No outbound traffic before the user pastes an inbox address.
