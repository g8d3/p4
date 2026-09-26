# Real-Chrome 390px pass — leg #18 (first pass under loop/VERIFY.md)

Method: `ops/server.py` (:8901) + `backend/server.py`, then
`google-chrome --headless=new --window-size=390,844 --screenshot`
with a fresh `--user-data-dir` per shot. Console re-runs with
`--enable-logging=stderr`, grepped for CONSOLE/Uncaught.

## Results
- HTTP 200: all 9 pages (hub, sidepanel, landing index/pricing/dev/
  terms/privacy/refunds/contact). Trial T1 re-run: 100/100.
- Console: no page errors (only headless dbus environment noise).
- English: clean (scan hits were JS `el` vars, template `${l}`, and
  typographic →/§ — no non-English user text).
- Internal links: no dead links (one `${l}` template-literal false +).

## Defects found AND fixed this leg (proof: *-390b/c.png)
1. Landing top nav clipped at 390px ("Developers" cut off — links had
   no wrap opportunity). Fixed: flex-wrap nav on all 7 landing pages.
   Verified in landing-390c.png (wraps to 2 lines, no overflow).
2. Sidepanel over http stuck on "Loading…" (bare `chrome.storage`
   calls throw outside the extension). Fixed: localStorage-backed
   `chrome.storage` fallback at top of sidepanel.js. Verified in
   sidepanel-390b.png (renders "0 saved locally" + empty state,
   5-tab bar on one row, no overflow).
3. Hub live-log `<pre>` dumped raw runner JSON with no label.
   Fixed: "Live leg log (raw, newest last):" caption, hidden idle.

## Still open (why NOT presentable)
Only hub Status pane + sidepanel Saved pane + 3 landing pages were
screenshotted. Labels/Sync/Hooks/Export panes and hub Legs/Todo/
Inbox/Keys/Ext/Vers tabs still need the same visual pass.
Next leg: finish the tab-by-tab 390px screenshots, then flip.
