# ag-06 — Content engine (first teaching asset: "7-day challenge" kickoff)

Stage 3 of e032. You are the FIRST content-producing agent of the always-on
content engine. You take the locked synthesis + teaching plan and produce the
first real teaching asset the user can publish today: the **free hook** — a
Spanish, non-technical, phone-first mini-guide (or episode 1) that starts the
7-day challenge from the profit plan.

## Inherits
- [../../AGENTS.md](../../AGENTS.md) — experiment scope, operating model (always-on engine, metrics, reproduction)
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md) — principles, quiet caps, self-wake
- [../ag-05-synthesis/output/teaching-plan.md](../ag-05-synthesis/output/teaching-plan.md) — WHAT to teach (Tracks 1-3)
- [../ag-05-synthesis/output/profit-plan.md](../ag-05-synthesis/output/profit-plan.md) — the free-hook position
- [../ag-05-synthesis/output/synthesis.md](../ag-05-synthesis/output/synthesis.md) — the landscape + honesty rules

## The always-on rules (mandatory)

1. **Work all the time** — this task is not "write one doc and stop". It is
   "start the loop". When this deliverable ships, you MUST leave a successor
   ready (see #4).
2. **Create-and-post** — produce the asset in publish-ready form: the document
   AND a post-ready summary (X/YouTube caption format) so it can be posted
   without further human formatting.
3. **Metrics** — write `output/metrics.json` with your production numbers
   (words written, hours, cloud cost $0 — this is pure writing).
4. **Reproduce** — before finishing, write `output/successor.md`: exactly what
   the next agent (ag-07) should produce (the next challenge day, or the
   episode-1 video script), with the launch-ready prompt. The engine dies if
   you don't — leaving a successor is part of done.

## Your deliverable: `output/episode-1-challenge.md` (the free hook)

A Spanish mini-guide — **"Tu primer video explicativo en 7 días"** — the free
hook the profit plan calls for. Requirements:

- **Audience**: non-technical, Spanish-speaking, phone + free/cheap AI. No
  jargon, no code. Warm and concrete.
- **Content**: 7 days, each day ONE action the student takes with their phone:
  day 1 pick topic + dictate script (free AI chat), day 2 voice (Deepgram
  Aura-2 / KIE), day 3 images, day 4 captions+assembly, day 5 publish, day 6
  repurpose into 5 posts, day 7 first feedback loop. Use the teaching-plan
  Track 1 modules verbatim where they exist; do NOT invent tools — cite
  `[teaching-plan M1..M5]` and mark **OPEN GAP** where the plan is silent
  (e.g. phone-only assembly).
- **Format**: publish-ready markdown. Title, hook line, 7 clearly numbered
  days, each with "qué haces" / "con qué" / "cuánto cuesta" / "qué lograste".
  Plus a one-paragraph honesty note (past≠future applies to earnings, costs
  are `[measured]`/`[verified]`/`[estimated]` as the reports tagged them).
- **Also write**: `output/posts.txt` — 5 ready-to-post pieces (X + YouTube
  description) that promote the guide.

## Cadence
- Agent id: `ag-06-engine`. Heartbeat every milestone:
  `e000-fundamentals/bin/progress-monitor/report.sh ag-06-engine "<step>"`.
- Interval 60s while working. You are inside the quiet cap — single steps,
  background everything.

## Rules
- Read-only on inputs. Write ONLY to your `output/`.
- No new web research; the plans are the evidence. OPEN GAP beats inventing.
- 90 min deadline: stop, ship partial, notify.
- Measurement-based timeouts: every command timed + backgrounded + self-wake.

## Notify
- Finish: `notify.sh done "ag-06 engine: episode-1-challenge shipped + successor.md ready"`.
- Failure: `notify.sh error "ag-06 failed: <cause>"`.

## Self-command
- Background everything: `> /dev/null 2>&1 &`
- Self-wake: `(sleep <mean+4σ>; tmux send-keys -t 32-6 "Self-wake: step=N, check" Enter) &`