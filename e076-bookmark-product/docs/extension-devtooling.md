# Extension dev-tooling options (record, 2026-09-26)

Context: BookmarkVault is a vanilla-JS MV3 extension, installed unpacked on
desktop Chrome and on mobile Quetta. Owner pain: every code change seems to
require a file refresh + extension reload. Evaluated: our homegrown remote-logic
lane vs Extension.js, CRXJS, WXT.

## Baseline: our remote-logic lane (shipped, v0.2.0)

- `ext/loader.js` (thin bootstrapper) asks the background worker for
  `ext-dev/panel.js` when devMode is ON (else the bundled `ext/panel.js`
  snapshot), and evals it. `background.js`
  pulls `:8901/ext-dev/tuning.json` into storage (pushed to `page-tap.js`
  via postMessage). Logic + tuning updates land with just an F5 on x.com.
- Server side verified live 2026-09-26 (`/ext-dev/panel.js` served,
  `tuning.json` v2). Telemetry (`ops/telemetry.jsonl`) distinguishes
  lanes: `devnote` entries = remote lane active; bare `capture` = frozen
  bundled copy (devMode OFF — this was the owner's state, hence "nothing
  auto-updates").
- Hard MV3 limits (no tool bypasses these): `manifest.json`, background
  service worker code, bundled `page-tap.js`, sidepanel files always need a
  file refresh + extension reload. Manifest now covers all of x.com, so that
  one-time cost is paid.

## Option A: Extension.js (extension.js.org)

- Zero-config framework, cross-browser. Dev loop is a tiered system
  (source: https://extension.js.org/docs/features/reload-and-hmr):
  HMR only "when module updates are safe" (extension pages, CSS, userScripts);
  `manifest.json`/`_locales` edits force a FULL extension reload; background
  chunk changes restart the service worker; content-script changes re-inject;
  entrypoint-structure changes report "restart required".
- Entire pipeline is development-only, no-op in production builds.
- Verdict: best-in-class dev-loop automation, but every tier that matters to
  us (manifest, background, content scripts) still reloads — and it does
  nothing for an already-installed extension on mobile. Doesn't solve the
  owner's pain.

## Option B: CRXJS (@crxjs/vite-plugin)

- Thin Vite plugin, true Vite HMR for isolated-world content scripts.
- Critical limitation for OUR architecture
  (source: https://crxjs.dev/concepts/content/): IIFE / MAIN-world scripts —
  exactly what `page-tap.js` is (fetch/XHR interception must run in page
  context at document_start) — "do not receive in-place Vite HMR… the
  updated script only runs after the host page reloads or navigates again."
  Their own guidance: keep the MAIN-world part a "small bridge" and put
  logic in the isolated script — which is precisely our loader/page-tap
  split already.
- Verdict: would give HMR to the parts we already hot-update remotely, while
  leaving the MAIN-world hook (our hardest part) on page-reload — same as
  today, plus a Vite build pipeline to maintain. No gain for installed-mobile.

## Option C: WXT (wxt.dev)

- Full framework: file-based entrypoints, generated manifest, zip/publish
  tooling, dev mode. Own homepage wording is telling: "HMR for UI development
  and **fast reloads** for content/background scripts" — HMR for pages, plain
  reloads for the rest.
- Operational risk: Chrome 126+ broke WXT's dev setup around background
  service workers (service worker invisible to Target.getTargets; requires
  workarounds). MV3 service-worker dev UX is fragile across Chrome versions.
- Verdict: nicest project scaffolding of the three, but same reload physics
  for content/background/manifest, and zero effect on installed extensions.

## Shared truth (all three + ours)

| Change | Extension.js | CRXJS | WXT | Our lane |
|---|---|---|---|---|
| Extension page JS/CSS (dev) | HMR | HMR | HMR | reload (acceptable: sidepanel changes are rare) |
| Content script logic (dev) | re-inject | HMR (isolated) / page-reload (MAIN-world IIFE) | fast reload | F5 (remote logic) |
| Background SW (dev) | SW restart | reload | fast reload | reload |
| manifest.json (dev) | FULL reload | reload | reload | reload (now stable: all of x.com) |
| Installed ext, no dev server | reinstall | reinstall | reinstall | logic+tuning update live; rest reinstalls |
| Needs dev-server connection | yes (localhost) | yes (localhost) | yes (localhost) | yes for remote lane (:8901 over Tailscale) |

## Decision (2026-09-26): stay vanilla + remote lane

1. All three optimize the laptop dev loop; none changes what an installed
   (especially mobile) extension can receive without reinstall. Our remote
   lane is the production equivalent of their dev HMR — same principle as
   Code Push/Shorebird — and it already exists.
2. Migration cost (rewrite into their pipelines, Node/Vite toolchain,
   generated-manifest lock-in) buys nothing for the owner's actual pain.
3. Revisit if: we outgrow vanilla (multi-page UI, TS, unit tests — then WXT
   first, it's the best scaffold), or Chrome ships real SW hot-swap.

## Immediate follow-ups (not framework work)

- Lane indicator: DONE 2026-09-26 — sidepanel Sync → "This build" shows
  installed vs published version (update verdict), logic lane
  (remote/auto-updates vs frozen), tuning v, and server version; in-page HUD
  pill stays minimal (expand for detail).
- Keep owner installs on devMode ON while iterating; store builds stay frozen.

## 2026-09-26 — in-page panel (v0.3.0)

Sidepanel UI transplanted into the page (shadow DOM): the pill opens the
full 5-tab app in-page, so the WHOLE UI rides the hot lane (remote
`ext-dev/panel.js` via background fetch + eval; bundled `ext/panel.js`
snapshot offline). Backend calls go through a `bv-api` worker proxy
(mixed-content safe). Legacy `sidepanel/` stays as fallback until parity
is proven on-device. Pill is draggable (position persists).

## 2026-09-26 — CSP verdict (Quetta on x.com, DevTools Issues screenshot)

`Content Security Policy of your site blocks the use of 'eval' in
JavaScript` inside our content-script context. Consequence: the remote-CODE
lane (fetch + eval) is dead on this browser — no framework or trick
bypasses the site's CSP from an isolated world (CRXJS/WXT dev runtimes
would die the same way here). What survives: static manifest delivery
(`panel.js` declared in manifest, runs natively — v0.3.2), remote DATA
(`tuning.json`: match patterns, scroll speed, name paths — plain JSON,
no eval), and backend-side changes. Rule of thumb going forward: behavior
tuning without reinstall; code changes need file refresh + reload.

## 2026-09-26 — eval attempt removed (v0.3.8)

Since remote eval is CSP-dead on x.com, the loader no longer attempts it:
no more console error, no 4s wait. Boot is static-manifest only;
`tuning.json` (data) still flows remotely. `bv-fetch-*` handlers removed.

## 2026-09-26 — templates, zero innerHTML (v0.3.10)

Owner critique: HTML-in-JS soup. Item skeleton now lives in
ext-dev/panel.html as <template id="t-item">; rows are built with
createElement/textContent (auto-escaped, no esc() needed); label dropdown
uses the Option API. panel-app.js contains zero innerHTML. Same rule for
any future dynamic markup: structure in HTML, data via DOM.
