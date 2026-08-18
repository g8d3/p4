# Scout 3 — Leaner agent harness: is opencode/opencode2 the right CLI?

## Question (the ONLY thing scout-3 investigates)
We run `opencode` (8 agent windows) and `opencode2 serve --service` (1
client in window a0) as our agent CLIs. Are we burning more RAM/CPU by
running these than a lighter alternative (a plain python/node script, a
different harness)? Measure: RSS + CPU of one idle opencode session, one
opencode2 serve+client pair, and a trivial harness (e.g. time a bare
node/python CLI that calls the same provider API). Compare. Read-only.

## Spawned by cadence cycle 5
2026-08-18 00:03 — quiet hours, ONE scout at a time. Bounded 30 min. Read-only.
Do NOT touch any running config, cgroup, other agent window, or the
orchestrator inbox. Write `scout-report.md` + `done.txt` + notify when done.

## Evidence seed from cadence (cycles 2-5)
- scout-2 measured: `opencode2 serve --service` = 643 MiB RSS (up 2d 6h),
  serving ONE client (opencode2 session 246858, window a0, ~404 MiB, idle).
- 8 agent windows run `opencode` (ag-01..04 opencode ~760-895 MiB each while
  DONE/idle; scout-2's "4 DONE agents = 2.6 GiB").
- System: 15.4 GiB RAM, ~8 GiB used, quiet-hours cap 1.5 cores / 8 GiB.
- The user holds opencode-go, cmd, and Z.AI subscriptions (all paid).

## What "lighter" means for this audit
- Measure, do not install: a trivial harness is a bare `node`/`python3`
  script that makes ONE authenticated API call to the same provider
  (OPENCODE_GO_BASE_URL/KEY) — time it, RSS it. If an API key is required
  and you lack one, compare idle RSS only and say so honestly.
- Report how much of each CLI's RSS is the interactive TUI vs the API
  client; whether the TUI could be detached (headless) to save RAM.
- e032 agents run headless in tmux — the interactive TUI may be pure
  overhead for them. Quantify that.

## Guardrails (repeated for emphasis)
- Read-only + throwaway test files in YOUR OWN scout dir only. No installs,
  no kills, no restarts, no cgroup edits, no other-window messages.
- Do NOT touch window a0 or any running agent window.
- 30-min hard deadline. Partial answer with honest unknowns is valid.
- Report the API-call measurement only if cheap and safe; otherwise measure
  idle RSS and startup time only.