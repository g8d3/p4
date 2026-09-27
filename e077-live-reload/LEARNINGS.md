# e077 — Learnings

Goal: kill the download/uninstall/reinstall/reload loop when developing a browser
extension for the Queta mobile browser. Result: a loader installed once that
receives a server-declared URL list and hot-injects it (~1s, no page reload).

## What was built (v1.0 → 1.9)

- `server/server.js` — zero-dep Node: static files + `/version` + `/config.json` +
  `/api/report` + `/api/reports` + full CORS. Binds `0.0.0.0:8080`.
- `ext/` — MV3 loader: storage-configured server address (popup), background
  network relay, execution ladder, phone-home diagnostics, lab mode (DNR CSP strip).
- `live-reload.user.js` — same loader as userscript (GM_xmlhttpRequest + fetch fallback).
- `index.html` — the experiment page: what/status/run, dynamic scripts table,
  agent contract, diagnostics table, pricing, legal.
- Install artifacts served by the server itself: `/live-reload-ext.zip`, `/live-reload.user.js`.

## Architecture evolution (each step forced by evidence)

1. Polling `/version` (not WebSocket): zero deps, survives phone sleep. Good enough at 1s.
2. Background relay: x.com `connect-src` blocks content-script fetch → all network
   moved to the service worker (extension context, exempt).
3. Execution ladder (isolated eval → page `<script>` injection → amber note):
   `script-src` without `unsafe-eval` kills eval; strict pages fail silently, so a
   run-token detects refusal.
4. Phone-home telemetry (`boot`/`applied`/`unreachable`/`eval-blocked` with install
   ID, versions, page, transport, error text): removed the human screenshot relay.
5. Lab mode (opt-in per-host CSP-header strip via DNR): correct machinery, wrong
   theory — see below.

## Engine findings (the real payload of this experiment)

|                    | Extension          | Userscript         |
|--------------------|--------------------|--------------------|
| Network            | ✅ everywhere (relay) | ❌ strict pages (page CSP, no GM bridge in Queta) |
| JS execution       | ❌ everywhere on modern engines | ✅ where it can fetch |
| HTML live          | ✅ everywhere      | ✅ everywhere      |

Evidence:
- x.com console: content-script fetch refused by `connect-src` (→ relay).
- `VM2538`/`VM2857` sources in DevTools = userscript context, not the extension.
- Desktop Chrome 153 seals isolated-world eval on **every** page (even CSP-less ones)
  and blocks extension-attributed inline scripts via a default
  `script-src 'self' 'wasm-unsafe-eval' 'inline-speculation-rules' … chrome-extension://<id>/`.
  Queta's engine seals the extension context the same way (amber note even on our
  own headerless index page) but leaves the userscript VM context alone.
- Lab verdict: with `lab: ["x.com"]` confirmed in boot reports, JS still blocked —
  the seal sits below the page header, so stripping headers can't lift it.
- CORS footnote: JSON POSTs need `Allow-Headers` + preflight handling; `text/plain`
  POSTs are preflight-proof. Defaults now use the stable Tailnet hostname, not DHCP LAN IP.

## Boundaries (proven, not assumed)

- Edit-JS-watch-it-on-x.com inside an extension sandbox: impossible on these engines
  without gutting site security (per-load nonces make surgical CSP edits impossible;
  only wholesale removal works, and the engine seal remains anyway).
- HTML/CSS live: works everywhere, all formats. JS live: permissive pages only.
- If JS-on-strict-sites is ever required, the remaining honest path is a JSON-spec
  renderer (static interpreter, zero eval) — the marketplace format arriving early.

## Phone vs PC (closing conclusion)

The phone holds a *copy*; fresh code lives on the PC — no `runtime.reload()` crosses
that gap, which is why every executable-code bridge got sealed. On the PC the files
and the browser share a machine, so the classic watcher → `runtime.reload()` loop
works for all extension code with no fight. Phoneuso: HTML-live everywhere + JS on
permissive pages. PC: the full loop. Nothing here was wasted — URL list, telemetry,
diagnostics, page rule all transfer.

## Process (extracted to root AGENTS.md as standing rules)

- Report server status unasked, full URLs, IPs resolved live.
- User-seat review before delivering; a page with no user action is a bug.
- Config over hardcode; bump version labels with every loader change.
- Kill by exact PID from `ss`, never broad `pkill -f` (it killed the live server once).
- Browsers lie by omission: branded Chrome ignores `--load-extension`; agent-browser
  forces `--disable-extensions`. Self-test with unbranded Chromium + CDP.
