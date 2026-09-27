# Live-reload extension — README

Yes, what you describe makes sense. It has a name: **live reload / hot reload**.
Vite, webpack-dev-server, Tampermonkey all do exactly this: a dev server watches
files and pushes a "changed" signal; the browser re-fetches and re-injects without
reinstalling anything.

The AI's WebSocket idea is correct but heavier than you need to start. This demo
uses **1-second polling of `/version`** instead, because:

- zero dependencies (pure Node stdlib, no `ws` npm package),
- works in all 3 Queta formats (`.zip` extension AND `.user.js`),
- survives phone sleep / network drops (polling just resumes; sockets don't),
- good enough: you see edits in ~1s. Upgrade to WebSocket/SSE later if you want
  instant push or two-way messaging.

## Files

| File | Purpose |
|---|---|
| `server/server.js` | dev server: serves `public/`, bumps `/version` on save |
| `server/public/live.js` | **you edit this continuously** — must define `window.__LIVE_RENDER(host)` |
| `server/public/card.html` | **you edit this too** — HTML fragment appended under the box |
| `ext/manifest.json` + `ext/content.js` | extension source (zipped for Queta) |
| `live-reload.user.js` | same loader as userscript — simplest in Queta |
| `dist/live-reload-ext.zip` | built, ready to install in Queta |

## Use (phone + PC on the same WiFi)

1. **PC — find your LAN IP:** `hostname -I` (Linux) or `ipconfig` (Windows).
   Example: `192.168.1.50`.
2. **PC — put that IP in two files** (one-time): `ext/content.js` and
   `live-reload.user.js` (`const SERVER = "http://<IP>:8080"`). Rebuild zip:
   `cd ext && zip -r ../dist/live-reload-ext.zip manifest.json content.js`.
3. **PC — start server:** `node server/server.js 8080`.
4. **Phone (Queta) — install ONCE, pick the easiest:**
   - `.user.js`: open `live-reload.user.js` URL / send via chat, Queta prompts to install, or
   - `.zip`: transfer `dist/live-reload-ext.zip`, install as extension.
   (Skip `.crx` — needs signing, obsolete for dev.)
5. **Phone — open any page** (e.g. `example.com`). Bottom-left shows a green box,
   top-right toasts `🔌 live connected`.
6. **PC — edit `server/public/live.js`** (change emoji/text/color), save.
   Phone shows `⚡ updated → v2` in ~1s. Same for `card.html`. **Never reinstall.**

## Try the loop (30 seconds)

1. Change `box.textContent` to `"🔴 LIVE v2 — it works!"`, save → phone updates.
2. Change background to `#7c3aed`, save → phone updates.
3. Edit `card.html` text → phone updates.
4. Open phone DevTools/console if Queta has it; `fetch("http://<IP>:8080/version")`
   shows the counter going up each save.

## Going further

- **Multiple URLs:** add more files to `public/` and fetch them in `refresh()`
  the same way (`/style.css`, `/panel.html`, …). The pattern scales to N files.
- **No page reload needed:** we re-inject code instead of `location.reload()`,
  so the test page keeps its state (forms, scroll, login).
- **When to use WebSocket:** when polling each second feels slow, or you need
  PC→phone push under ~100ms, or bidirectional RPC. Swap `setInterval(poll)`
  for `new WebSocket("ws://<IP>:8080")` + `ws.onmessage = refresh`. Server needs
  the `ws` package or a manual upgrade handler. Same `refresh()` function works.
- **HTTPS pages:** `http://<IP>` fetch from an `https://` page is mixed-content
  and may be blocked. For testing prefer `http://` pages, or serve the dev
  server over LAN-HTTPS (mkcert) later.
