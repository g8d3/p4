# Real-Chrome 390px pass — leg #19 (full tab-by-tab, closes leg-18 gap)

Method: `ops/server.py` (:8901) + `backend/server.py`, then
`google-chrome --headless=new --window-size=390,844 --screenshot`
with a fresh `--user-data-dir` per shot. Chrome lingers after writing
the PNG, so shots go through `/tmp/e076-shot.sh` (poll for PNG, kill
by PID — never `pkill -f <pattern>`: the pattern matches the caller's
own command line and kills its shell). Console re-runs with
`--enable-logging=stderr`, grepped for CONSOLE/Uncaught.

Shipped this leg (needed for verification, kept as UX):
- Hash deep links: `ext/sidepanel/index.html#labels|sync|hooks|export`
  and `ops/cycle.html#legs|blocked|inbox|keys|ext|vers` open that tab
  on load; tab clicks use `history.replaceState` (no scroll steal).

## Results — 16 screenshots, all eyeballed
- HTTP 200: all 9 pages (hub, sidepanel, landing
  index/pricing/dev/terms/privacy/refunds/contact). Trial T1: 100/100.
- Console: sidepanel zero messages. Hub: only Chrome INFO
  "Password field is not contained in a form" (Keys-tab autofill hint,
  not a page error). No Uncaught anywhere.
- English: clean (only `×` chip glyph with aria-label — a symbol,
  same class as leg-18's accepted →/§).
- Links: no dead links; the new #tab links are proven by the
  screenshots themselves (each shot landed on the right pane).

## Defects found AND fixed this leg (re-shot after fix)
1. Sync pane said "Queue undefined · never synced" (http preview has
   no background worker; `sendMessage` stub returns `{}`).
   Fixed: fall back to the local queue count → "Queue 0 · never synced".
   Extension path unchanged. Proof: sp-sync-390.png.
2. Hub Legs + Vers tables overflowed horizontally at 390px (page-level
   h-scrollbar). Fixed: ≤480px media query — smaller font/padding,
   fixed layout, word-break; Legs hides model + took columns on narrow
   (still on desktop). Proof: hub-legs-390.png, hub-vers-390.png.
3. Hub bottom tab bar could overflow with 7 tabs. Fixed: tighter
   gap/padding/font, ellipsis. Proof: one row, no scrollbar, all shots.

## Rubric verdict → PRESENTABLE true (v0.10-tabs)
1. 200s + no console errors ✓ (above). 2. Single-row bottom bars,
   no page h-overflow at 390px ✓ (landing top nav wraps to 2 lines by
   leg-18 design — no clipping; the rubric's "bars" are the bottom nav,
   the only nav). 3. Bottom bars fixed → visible on first paint in
   every shot ✓. 4. English-only ✓. 5. No dead links ✓.
Caveat: contact page email is still a placeholder — human-gated
(blocked_on_human), documented, test-mode correct.
