# EchoLike Lite

Your X likes and bookmarks, saved in your browser, sent to your inbox **encrypted**. ~350 lines, no build step.

Nothing you like leaves the browser in readable form: each capture is sealed with AES-256-GCM and the key
stays in your browser. The inbox server stores blobs it cannot open — ours included.

## Install (one step, then just use X)

1. `chrome://extensions` → Developer mode → Load unpacked → pick `extension/`.
   (Edge/Brave: same. Firefox: `about:debugging` → Load Temporary Add-on → `manifest.json`.)
2. Like or bookmark a post on X. That is it — the first like claims your own tenant
   on the hosted inbox and everything after it lands there. No address, no token,
   no account, nothing to configure.

Click the toolbar icon: it opens the extension page, which shows your captures and has a
**Settings** tab for everything else. The list sorts by any of the four dates it keeps (my interaction,
captured in the browser, arrived in the inbox, post published) or by any of the five counts (reposts, likes,
replies, bookmarks, views), either direction, and remembers your choice; a filter next to it picks one slice —
including **not in the inbox yet**, which the count in the status line opens with one click. **Open on echolike.app** opens the web reader for the full list, which: with the hosted inbox that
opens a normal web page on echolike.app (any device, nothing to install); with your own server it opens the
extension's inbox page. Either way it decrypts in your browser, tells you what is *in* the inbox versus what this
browser holds, and exports JSON. Free hosted quota: 3000 captures/month per install.

**Your key**: shown in the extension's **Settings** tab as a recovery code (43 characters, masked until you press Reveal). It never leaves
your browser. Save it — it is the only way to read your inbox on another device, and nobody, us
included, can regenerate it.

**Bring in your history** (optional): the **Import** tab walks your existing likes or bookmarks on X — pick how
many, press start, keep that tab open. It stops at your count, when the list ends, or after ten minutes, dedupes by
post, and encrypts everything on the way out. It is a button on purpose: scroll-walking history on a timer is what a
scraper looks like.

**Nothing to press.** The first like connects an inbox by itself, and a queue that could not go out is sent by the
next event: another like, an X tab loading, the browser coming back online, opening this page, or a browser
start. No timers, no "retry" to remember, and the page repairs itself on load: what this browser holds and the
inbox lacks goes out without a click. A re-sent capture never duplicates (the server keeps one row per capture).

**Two browsers, one account** (optional): install in both, sign in with the same email in each, and back up the
key with a passphrase in the first one. In the second, sign in and press **Restore key** with that passphrase —
its own catches are then re-encrypted with the account key and sent, and both browsers show one merged list with
duplicates removed.

**Getting your inbox back** (optional): open the extension page and its **Settings** tab (the popup's Settings button) → enter your email → *Email me a code* → type the
6 digits. That links this install to an account. Then choose a passphrase and *Back up key*: your key is uploaded
wrapped with that passphrase, so a new phone can restore it and nothing on the server can open it. Without a
backup, nobody — including us — can recover a lost recovery code.

**Prefer your own server?** Run `python3 server.py` (stdlib only, prints its
address) and press **Find my inbox** — it takes the inbox on your own machine
before the hosted one. Address + token live in **Settings → 1 · Inbox**. The popup
says ✓ Connected either way.

No network at all? Captures are saved in the browser and sent when it can be.

## Ads

Promoted posts and trends are hidden on X (CSS only — no observer, no timer). The popup switch `Hide ads on X` turns it off; liking an ad still captures it, flagged `"ad": true`.

## No inbox yet?

Captures are still saved in the browser: the popup lists the last 30 with a link to each post. Connect later — the waiting ones send on Save.

## Cost in the browser

One click listener. No observers, no timers, no polling, zero background traffic. The service worker sleeps until you click.
