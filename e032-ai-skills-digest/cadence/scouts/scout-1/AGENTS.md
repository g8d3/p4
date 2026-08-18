# Scout 1 — Chrome memory cost

## Question (the ONLY thing scout-1 investigates)
We run Chrome instances for browser automation. How much RAM does each
Chrome instance actually cost right now, which ones are justified (a live
experiment needs them), and is there a reusable "one instance per task
batch" pattern that would cut idle Chrome RAM? Investigate read-only.

## Spawned by cadence cycle 2
2026-08-17 23:34 — quiet hours, ONE scout. Bounded 30 min. Read-only.
Do NOT touch any running config, cgroup, other agent window, or the
orchestrator inbox. Write `scout-report.md` + `done.txt` + notify when done.

## Evidence seed from cadence (cycle 2 health pass)
- One zombie Chrome: PID 167047 (uptime 1d 2h), args include
  `--enable-unsafe-swiftshader --remote-debugging-port=9223
  --user-data-dir=/tmp/opencode/chrome-gpu http://127.0.0.1:8787/`.
- Its target server (127.0.0.1:8787) is NOT listening — the page it points
  at is dead. Total RSS across its process tree ≈ 856 MB.
- resource-audit.log flags `chrome_cpu_render: 1` for it (swiftshader).
- Per-instance RSS + port map is the live evidence to collect (`ps`,
  `ss -tlnp`, `/proc/<pid>/status`).

## Guardrails (repeated for emphasis)
- Read-only: `ps`, `ss`, RSS reads, log reads only. No installs, no kills,
  no restarts, no cgroup edits, no other-window messages.
- 30-min hard deadline. Partial answer with honest unknowns is valid.