# e088 — Blank-Canvas Agents (no questions, agents build everything)

User correction 2026-10-05: asking the user for decisions is a bug. This
experiment is an agent system that starts from a BLANK canvas and builds
everything itself — decisions included. No ask_user, no verification gates,
no waiting. Agents perceive, decide, build, verify.

## System

- `canvas/` — the blank canvas. Starts with only `README.md`. Agents add
  everything else. This is the product.
- `server/app.py` — stdlib only. Shows canvas file tree, activity log,
  iterations. Reads `needs.json` for port/bind.
- `public/index.html` — single file: Canvas tree + Activity + Iterations.
- `data/log.jsonl` — every agent action appended (who/when/what).
- `data/iterations.json` — version cuts with notes.
- `bin/worker.sh <name>` — runs one autonomous builder pass (used by
  subsessions and cron): read canvas, pick next smallest shippable step,
  write files, log, cut iteration if shippable.
- `bin/serve.sh`, `test/check.sh` — serve + gate.

## Rules

- Agents NEVER ask the user. Decide with best judgment, log the decision.
- Smallest shippable step always. Stdlib + CDN only (ponytail discipline).
- Target product (decided, not asked): OSS-backed token launchpad on
  Solana (from e087 trends): tokens bound to OSS repos, revenue-share
  payouts only from real payments, fiat MoR stub + crypto stub with
  refunds, one playable game, funding widget. Agents may reshape it as
  they learn — log why.
- Standing rules apply: live IPs/URLs, user-seat review, config from
  needs.json, kill by exact PID.
