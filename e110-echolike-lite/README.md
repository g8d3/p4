# EchoLike Lite

Your X likes and bookmarks, saved in your browser, sent to your inbox. ~350 lines, no build step.

## Install (3 steps)

**1. Start the inbox** (one command, stdlib Python only):

```sh
python3 server.py
# prints: address (http://<your-ip>:8911) + token
```

**2. Load the extension:** `chrome://extensions` → Developer mode → Load unpacked → pick `extension/`. (Edge/Brave: same. Firefox: `about:debugging` → Load Temporary Add-on → `manifest.json`.)

**3. Connect:** click the EchoLike icon → paste address + token → Save & send. The popup says ✓ Connected.

Like or bookmark any post on X: a green "✓ sent" toast confirms it. Open `http://<your-ip>:8911/` to see everything captured.

## No inbox yet?

Captures are still saved in the browser (popup shows the count). Connect later — the waiting ones send on Save.

## Cost in the browser

One click listener. No observers, no timers, no polling, zero background traffic. The service worker sleeps until you click.
