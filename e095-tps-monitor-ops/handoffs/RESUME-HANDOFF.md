# Handoff after an external PI WEB restart (read this first, then act)

## What happened
- `e095-tps-monitor` v11 is DONE: 87/87 tests pass. No product code changed.
- Ops split: volatile files moved to `e095-tps-monitor-ops/` (verify script,
  restart script, screenshots, handoffs) because the host hashes the whole
  package dir — every doc edit staled the tab. Product dir now changes only
  on real releases. Rule in both AGENTS.md files.
- `docs/verify-tps.sh` hardened: 60 s tab wait with reload retry, live-dot
  poll loop, screenshot count assertion.
- The daemon was restarted EXTERNALLY to serve the post-move tree. You are a
  fresh agent in session `Revisa el plugin TPS de pi` (cwd `/home/vuos/code/p4`).

## Verify now (in order)
1. Run `e095-tps-monitor-ops/verify-tps.sh suite revision files` — all PASS.
   (Revision FAIL ⇒ tree changed again: `git status`, then restart via the
   ops `restart-resume.sh` + a new handoff here in `handoffs/`.)
2. Run `e095-tps-monitor-ops/verify-tps.sh panel` — tab exists, `● live` on,
   4 shots to /tmp/tps-verify. If UI changed, copy shots to the ops
   screenshots dir (NOT the package dir).
3. Run `e095-tps-monitor-ops/verify-tps.sh watch report` — no storm.
4. Mobile pass only if panel code changed (it did not).

## Then report to the user (in English, one verdict sentence first)
- Paste the verify PASS/FAIL table. State: tab broke from doc commits under
  the package dir; ops split prevents recurrence; the tab rule (restart +
  self-verify before reporting) stands. Server URLs + PIDs. Proving shots
  already exist; re-take only on real UI change.
- Commit + push anything you changed (note: product-dir commits need another
  restart; ops-dir commits do not). Leave PI WEB running.
