# e077-live-reload

Live-reload loader extension: install ONCE, edit files on PC, see changes instantly on mobile (Queta browser). No reinstall loop.

## Structure

- `server/` — zero-dependency Node dev server (serves `public/`, watches for changes, exposes `/version`)
- `server/public/live.js` — the JS file you edit continuously (demo: floating box)
- `server/public/card.html` — the HTML fragment you edit continuously
- `ext/` — Chromium extension (MV3) source, install as `.zip` in Queta
- `live-reload.user.js` — same loader as userscript (`.user.js` format in Queta, simplest)
- `dist/` — built `.zip` goes here

## How it works

```
PC (:8080)                        Phone (Queta)
───────────                       ──────────────
live.js + card.html ──watch──> /version++
                                  │
ext/content.js ──poll /version every 1s──┘
   version changed? → fetch live.js?ts=.. + card.html?ts=.. → re-inject → toast "v12"
```

Install the loader once. After that you NEVER touch the extension. You only edit
`server/public/*` and the phone updates in ~1s, keeping page state (no full reload).

## Standing rule
End every turn that touches servers with one line: each running experiment server as full URLs. Resolve `hostname -I` (LAN) and `tailscale ip -4` (tailnet) at report time — never hardcode addresses. Report the experiment's server, not pi-web.
Bump loader version strings (`manifest.json`, `live-reload.user.js`) on every loader change — the label must never lie about the content.
