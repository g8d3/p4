# Scout 2 — Persistent daemons: which long-running processes idle-cost money or RAM?

## Question (the ONLY thing scout-2 investigates)
Which long-running processes on this machine idle-cost RAM or CPU, and which
are justified? Audit every persistent daemon (transcribe servers, sway
headless, HyperFrames/OD daemon, chrome CDP instances, node servers, etc.):
their RSS, uptime, how often they are actually used, and whether a cheaper
pattern exists (lazy-start on demand, or justifiable always-on). Read-only.

## Spawned by cadence cycle 4
2026-08-17 23:52 — quiet hours, ONE scout at a time. Bounded 30 min. Read-only.
Do NOT touch any running config, cgroup, other agent window, or the
orchestrator inbox. Write `scout-report.md` + `done.txt` + notify when done.

## Evidence seed from cadence (cycles 2-3)
- The zombie avatar Chrome (PID 167047 tree, 1.21 GiB) was the first found
  waste — scout-1 covered Chrome in depth. NOW look at the OTHER daemons.
- Known candidates seen in this session: node server for e031 dream-player
  (PID 234464, ~54 MB, up 7.5h, port 8788); Parakeet ASR worker + transcribe
  server (Unix socket + 127.0.0.1:9877, if running); sway headless;
  `model_worker.py` / `transcribe_server.py`; any HyperFrames/OD daemon;
  wf-recorder; Xvfb. Also opencode/`cmd` processes if they are daemons rather
  than active agents.
- Cross-check `resource-audit.log` (per-30s hygiene) and `progress/` for
  which processes belong to live experiments vs. orphans.

## Guardrails (repeated for emphasis)
- Read-only: `ps`, `ss`, RSS reads, log reads only. No installs, no kills,
  no restarts, no cgroup edits, no other-window messages.
- 30-min hard deadline. Partial answer with honest unknowns is valid.
- Do NOT re-audit Chrome in depth — that was scout-1. Focus on the rest.