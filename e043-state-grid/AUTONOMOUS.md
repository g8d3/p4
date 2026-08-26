# e043 — AUTONOMOUS: the research system design (user's goal)

A governed, multi-agent research system that runs the disciplined edge-finding
loop autonomously, across multiple models, surviving context resets via
handoffs. The user is present only for escalations.

## The core principle (repeat this forever)

Autonomy multiplies **throughput**, not **wisdom**. A fleet of agents freely
chatting about markets is a noise generator + overfit machine. The ONLY thing
that makes autonomy valuable is **automating the SOLO_PROTOCOL gates**:

1. One hypothesis at a time, written as a card BEFORE testing.
2. Minimal A/B that can fail it (same data, on/off).
3. Fees charged in every test. Out-of-sample check on every claim.
4. Per-campaign budget + stopping rule, declared BEFORE starting.
5. Reject log owned by the system, not by any single agent's memory.
6. A **falsifier** role whose job is only to try to break the claim.

An autonomous system without these six is worse than no system.

## Roles (filesystem is the message bus — p4 pattern)

| Role | Model (defaults) | Job | Writes |
|---|---|---|---|
| **Researcher** | `deepseek-v4-flash` (fast/cheap) | Proposes ONE hypothesis card (mechanism + "would convince me if"). Discouraged from touching code. | `fleet/hypotheses/h_<n>.md` |
| **Falsifier** | `deepseek-v4-flash-vision-exp` (careful) | Gets the card, builds the minimal A/B, runs it, tries to BREAK it, OOS-checks, writes verdict. | `fleet/results/r_<n>.md` |
| **Auditor/Guardian** | `deepseek-v4-pro` (rarest) | Periodically re-runs the "kept" list on unseen data; catches overfit drift that accumulated. | `fleet/audits/a_<n>.md` |
| **Scribe (Cadence-like)** | deterministic scripts | Owns the queue, budgets, reject log, handoff merges, notifications, spawning. Enforces stopping rules. | `fleet/reject_log.md`, `HANDOFF.md`, `fleet/state.json` |

Different models per role = hypothesis diversity + independent compute (the
three-provider habit: opencode-go / cmd / zai).

## Harness (decided with the user)

Spawned agents run **opencode INTERACTIVE** in a tmux window
(`opencode -m <model>` in the window, prompt sent via send-keys with Enter)
— user decision: interactive, NOT `opencode run`, and NOT pi. The pi TUI is
what was failing; opencode interactive in its own window is the p4 standard.

- Launch: `./continue.sh <window>` (window `43-*`), or
  `tmux new-window` + `opencode -m opencode-go/deepseek-v4-flash-vision-exp`.
- Rollover: HANDOFF.md + continue.sh (full resets); opencode sessions
  (`-c` / `--session`) for continuity.
- Scribe/monitor: pane capture + done.txt + output files (cadence pattern),
  NOT command exit codes (interactive agents don't exit).
- Models per role via `-m`; roles can spread across providers
  (opencode-go / cmd / zai).

## The loop (one cycle)

```
Scribe: budget ok? -> spawn Researcher (window) -> wait h_<n>.md
Researcher: write ONE hypothesis card, done.txt
Scribe: spawn Falsifier (window) -> wait r_<n>.md
Falsifier: A/B + OOS + verdict (keep/reject + why), done.txt
Scribe: append to reject_log.md (or kept list), update state.json,
        merge cycle summary into HANDOFF.md (context rollover per cycle),
        close windows. Next cycle.  -- until stopping rule.
```

## Stopping rules (in fleet/config.json, per campaign)

- `find-edge`: a config in the user's parameterized family beats e022's
  baseline (5m +3.65% / 1h +1.71%) OOS after fees → escalate to user (--ask).
- `budget-exhausted`: n hypotheses or runtime or tokens reached → stop, write
  FINAL_REPORT.md, notify.
- `n-consecutive-rejections`: e.g. 5 in a row → stop that campaign, propose a
  different data direction.

## Context rollover (the reset mechanism — already built)

Every cycle ends with the Scribe merging a summary into `HANDOFF.md`. A window
dies or context fills → kill the window, run `./continue.sh` → fresh agent
reads AGENTS.md + HANDOFF.md and continues. **The system's memory is the
filesystem + handoff file, never a chat window.**

## Data directions to mine first (untapped, per Fase-2 findings)

1. **Order book walls / imbalance** — e021 collects these (top-10 watchlist,
   hourly). Hypothesis: "buy dips only where the book shows real support".
2. **Funding extremes** — e021 samples funding hourly. Hypothesis: "funding
   extreme predicts short-term reversion (mostly for shorts)".
3. **Volatility-adaptive geometry** — spacing/targets as a function of realized
   vol (the spec's Tier-3 mapping). Hypothesis: "wider grid in high vol cuts
   churn enough to pass fees".
4. **Timeframe/asset scanning** — same grid on ETH/SOL to test family
   robustness (e021 watchlist).

Each becomes ONE hypothesis card. Pilot = 3 cards (one per direction 1-3),
falsified on real BTC with the existing fast harnesses (sim.py / range_grid.py);
survivors get a Nautilus check.

## Guardrails (inherited, mandatory)

- One agent at a time per cycle (quiet machine). Windows named `43-*`; kill by
  window. Every command timeout-wrapped.
- No agent touches live money, ever. No agent edits another agent's files
  (read-only cross-agent). Escalations only via `notify.sh --ask` with evidence.
- Commit + notify per cycle.

## State of implementation

- ✅ Built: HANDOFF.md, continue.sh (rollover), AGENTS.md Model section,
  SOLO_PROTOCOL gates, fast harnesses, visualizer.
- ⏳ Next: fleet scaffolding (config, prompts, run_cycle.sh) — see
  `fleet/`; then the pilot (3 hypothesis cards → falsified → verdicts).