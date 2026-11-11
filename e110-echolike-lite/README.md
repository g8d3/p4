# EchoLike Lite

Your X likes and bookmarks, saved in your browser, sent to your inbox. ~350 lines, no build step.

## Install (2 steps, one button)

**1. Start the inbox** (one command, stdlib Python only):

```sh
python3 server.py
# prints: address (http://<your-ip>:8911) + token
```

**2. Load the extension:** `chrome://extensions` → Developer mode → Load unpacked → pick `extension/`. (Edge/Brave: same. Firefox: `about:debugging` → Load Temporary Add-on → `manifest.json`.)

**3. Connect:** click the EchoLike icon → **Find my inbox**. Nothing to paste: the inbox on this computer issues a device token by itself, and the popup says ✓ Connected.

Inbox on another machine? Open **Advanced** in the popup, type its address, and press Save — the server issues the token there too. Paste a token only when a hosted inbox handed you one.

No inbox? The popup lists your last 30 captures anyway, each with a link to the post.

Like or bookmark any post on X: a green "✓ sent" toast confirms it. Open `http://<your-ip>:8911/` to see everything captured.

## Ads

Promoted posts and trends are hidden on X (CSS only — no observer, no timer). The popup switch `Hide ads on X` turns it off; liking an ad still captures it, flagged `"ad": true`.

## No inbox yet?

Captures are still saved in the browser: the popup lists the last 30 with a link to each post. Connect later — the waiting ones send on Save.

## Cost in the browser

One click listener. No observers, no timers, no polling, zero background traffic. The service worker sleeps until you click.
