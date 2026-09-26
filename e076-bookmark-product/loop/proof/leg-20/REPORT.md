# Leg #20 — store-listing assets (v0.11-store)

Rule followed (loop/VERIFY.md): real Chrome only, fresh profile per shot.

## Shipped
- Icons redrawn per size (navy #1B436E bookmark glyph, white card +
  notch, 3 lines): ext/icons/icon16.png (16x16), icon48.png (48x48),
  icon128.png (128x128). Before: solid-color placeholders.
- ext/store/listing.md: paste-ready Name, Short (<=132), Long
  description, Category Productivity / English, permissions
  justification, privacy/support placeholders flagged, 5-step publish
  checklist. English-only scanned (no Spanish accents/words).
- ext/store/screenshots/01-saved-1280.png, 02-sync-1280.png,
  03-labels-1280.png: real Chrome 1280x800, same panes verified at
  390px in leg-19 (pixel-variance check matches leg-19 shots:
  sparse white panes, means ~250-252, 77-132 gray levels).
- ext/README.md: new Store listing section.

## Verification
- HTTP 200: all 9 pages (hub, sidepanel, landing index/pricing/dev/
  terms/privacy/refunds/contact).
- Console: hub + sidepanel re-runs, grep CONSOLE/Uncaught → zero page
  messages (only dbus/environment noise).
- Trial T1 re-run: 100/100.
- No behavior change to hub/tabs/sidepanel (static + docs + icons only),
  so leg-19's 390px tab-by-tab pass still stands.

## Rubric verdict → PRESENTABLE true (v0.11-store)
1. 200s + no console errors ✓. 2. Single-row bars, no h-overflow ✓
   (unchanged since leg-19). 3. Bottom bars visible first paint ✓.
   4. English-only ✓ (store copy scanned). 5. No dead links ✓.
Caveats (human-gated, documented): contact email placeholder; store
privacy/support URLs wait on owner domain.
