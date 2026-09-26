# Self-verify rule — screenshot proof for frontend claims (e076)

From leg #18 on. No leg may claim a frontend change "works at 390px",
"loads clean", or "is presentable" from code inspection alone.

## The rule
1. Serve the tree: `python3 ops/server.py` (hub on :8901) + `python3 backend/server.py`.
2. Real Chrome only: `google-chrome --headless=new --no-sandbox
   --user-data-dir=/tmp/e076-chrome-<name> --window-size=390,844
   --screenshot=loop/proof/leg-<N>/<page>-390.png <url>`.
   (Fresh `--user-data-dir` per shot; the shared profile hangs.)
3. Capture at minimum: hub (`/ops/cycle.html`), sidepanel
   (`/ext/sidepanel/index.html`), landing index + pricing + dev.
   Sidepanel over http uses the built-in `chrome.storage` fallback
   (localStorage) so it renders outside the extension.
4. Console check: re-run key pages with `--enable-logging=stderr`
   and grep the log for `CONSOLE` / `Uncaught`. Only dbus/environment
   noise is acceptable; page errors must be fixed in the same leg.
5. Judge against the leg-prompt rubric (200s, no wrap at 390px,
   bottom bars visible on first paint, English only, no dead links).
   When in doubt: NOT presentable.

## Proof layout
- `loop/proof/leg-<N>/*-390.png` — the screenshots.
- `loop/proof/leg-<N>/REPORT.md` — per-page verdicts + defects found.
- `loop/versions.json` — bump rank, set presentable true/false with
  a one-line why. Never `true` without real-Chrome shots in proof/.

## History
- leg #18: rule created; first real-Chrome 390px pass found 2 defects
  (landing top nav clipped at 390px → wrapped; sidepanel stuck on
  "Loading…" over http → storage fallback). v0.9 stay NOT presentable:
  trial re-run + full tab-by-tab pass still pending.
