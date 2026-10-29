# Handoff after an external PI WEB restart (read this first, then act)

## What happened
- `e095-tps-monitor` v11 + fixes, main @ `1b9ea9d`. 87/87 tests pass.
- The user circled the streaming header on their phone: it eats half the
  screen AND the STALLED chip is cryptic. Fix (in this build):
  - headline single-line ellipsis at 1.15em on phones (was 1.6em wrapping),
    status line 0.85em, sparkline 32px (was 48px), buttons no-wrap;
  - stalled streams now read "stalled mid-stream (no new tokens for a
    while), still connected" instead of just "STALLED"; the chip carries the
    same as a tooltip. Pinned in test/css.test.mjs.
- Row-density fix (32px table buttons) is also in this build, unverified.
- The daemon was restarted EXTERNALLY. You are a fresh agent in session
  `Revisa el plugin TPS de pi` (cwd `/home/vuos/code/p4`).

## Verify now (in order)
1. `e095-tps-monitor-ops/verify-tps.sh suite revision files` — all PASS.
2. Phone check (the point): viewport 390x844, TPS tab. While IDLE: headline
   fits one line, buttons in one row, sparkline short. While STREAMING
   (start any reply): stalled-or-live status reads as a plain sentence.
   Screenshot both states to /tmp/tps-verify/ and ATTACH them in the report.
3. Row density: Messages rows clearly denser than the user's ~60px shot.
4. Quick desktop sanity: headline + `● live` + turn badges.

## Then report to the user (in English, one verdict sentence first)
- Screenshots attached as proof (mobile idle + mobile streaming + row
  close-up). Server URLs + PIDs. Anything changed goes to the OPS dir or
  needs another restart via the ops script + a new handoff.
- Leave PI WEB running.
