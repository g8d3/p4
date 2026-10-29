# Handoff after an external PI WEB restart (read this first, then act)

## What happened
- `e095-tps-monitor` v11 + small fixes, main @ `b20defa`. 87/87 tests pass.
- The user sent a phone screenshot of the live TPS tab: works, but every
  table row is ~60px tall — the 44px coarse-pointer touch rule hit table
  cells too. Fix (in this build): `.tps td button` capped at 32px /
  tighter padding on touch; 44px stays on panel-level controls. Pinned by
  `test/css.test.mjs`.
- The daemon was restarted EXTERNALLY (any product-dir change stales the
  revision). You are a fresh agent in session `Revisa el plugin TPS de pi`
  (cwd `/home/vuos/code/p4`).

## Verify now (in order)
1. `e095-tps-monitor-ops/verify-tps.sh suite revision files` — all PASS.
2. Phone check (the point of this build): viewport 390x844, TPS tab,
   Messages view — rows must be clearly denser than ~60px, session buttons
   single-line truncated, no page-level overflow. Screenshot to
   /tmp/tps-verify/ and ATTACH it in your report (ops screenshots dir only
   if the UI changed — it did slightly, so copy this one over).
3. Quick desktop sanity: headline + `● live` + turn badges.

## Then report to the user (in English, one verdict sentence first)
- Mobile row density fixed (or not — say what the screenshot shows).
- Server URLs + PIDs. Commit + push anything changed (ops dir only unless
  product code moved). Leave PI WEB running.
