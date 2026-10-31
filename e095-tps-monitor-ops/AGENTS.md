# e095-tps-monitor-ops — operating the TPS Monitor, not building it

This directory exists for one reason: the PI WEB host hashes the WHOLE
`e095-tps-monitor/` package dir (except `.git`/`node_modules`) into the plugin
revision, so ANY file change there — code, docs, screenshots — 404s the TPS
tab until the session daemon restarts. High-churn ops files live HERE so
working the loop never stales the product revision again.

## Contents

- `verify-tps.sh` — codified verification (suite/revision/files/panel/watch/report).
- `restart-resume.sh` — detached daemon restart + session prompt handoff.
- `handoffs/` — resume handoffs for post-restart agents (ephemeral).
- `screenshots/` — panel evidence (high churn, keep out of the package).

## Rules

- Never put product code here; never put ops churn in `../e095-tps-monitor/`.
- `verify-tps.sh` takes the package dir as `PKGPATH` env (default
  `../e095-tps-monitor` relative to this dir) so it survives moves.
- After any change under `../e095-tps-monitor/`: restart the daemon
  (restart-resume.sh + handoff), then run verify-tps.sh and screenshot the
  tab BEFORE reporting — no exceptions.
- settings.json rewritten behind your back? Check ~/.pi/agent/extensions FIRST — sync-opencode-models.ts honors p4-models/wanted.json since 2026-10-31; do NOT file-edit + hope. Diagnose with `./doctor.sh models` and `./doctor.sh tab-missing <id>` before any restart.
