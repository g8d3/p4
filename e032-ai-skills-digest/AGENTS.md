# e032 — AI Skills Digest (research → teaching → profit pipeline)

**Mission**: an agent pipeline that researches and organizes information about
**AI-agent skills** for (1) content/video creation, (2) digital product
creation, (3) marketing, selling & acquisition — and (4) crypto trading only if
the first three are insufficient for the real goal: **teach others and be
profitable**. Output: organized skill maps per domain, a synthesis, and
eventually a polished teaching video (Open Design-driven, per user choice).

The pipeline runs in four stages:

```
Stage 1  ag-01..04  research agents (parallel, cloud research) → output/*.md
Stage 2  ag-05      synthesis: cross-domain skill maps, gaps, synergies
Stage 3  ag-06      teaching + profitability plan (what to teach, how to sell)
Stage 4  video      Open Design-driven explainer of the findings (HyperFrames HTML→mp4)
```

Stages 2–4 launch only after Stage 1 reports. The filesystem is the
orchestrator: each agent reads `../<agent>/output/` and writes its own.

## MANDATORY system rules (learned from past pain — EVERY agent obeys)

### Rule 1 — Cloud-first over local software (the "STT lesson")

Local tooling has caused more pain than it saved. When a capability exists as
a cloud service, **prefer the cloud** — even paying per-use or using free
credits — unless the local tool is proven simpler.

- **Detect the headache, don't suffer it**: any time a local install, compile,
  GPU pipeline, or native module fights back (like the node-pty build, the
  Wayland/VAAPI quirks, the ffmpeg OOM traps), STOP fighting it and switch to
  the cloud equivalent. This applies to: transcription (pick the cheapest STT
  with generous free credits — Deepgram, Gemini, etc.), TTS, video rendering,
  image generation, hosting.
- **The vendor-choice loop** (mandated by the user): search which cloud
  provider has the best price + free credits for the exact task, then use it.
  Document price, free tier, and the decision in the output.
- **Local is allowed only as a fallback** when no cloud service fits or the
  cloud is blocked (secrets, privacy, testnet-only data).

### Rule 2 — Measurement-based timeouts (the "stuck command" lesson)

Agents get stuck waiting far too long on commands. The fix is to **measure the
baseline and time out from data, not guesswork**:

- First time a command runs, note its duration + approximate variance.
- A command that "usually takes 3s with σ≈0.5s" must not be waited on past
  **mean + 4σ ≈ 5s** — after that, it's hung; kill it and retry or skip.
- Build a small per-agent `timings.log` (command, count, avg, σ) and consult it
  before every wait. If unknown, use a 10s ceiling, then re-measure.
- On timeout, decide from evidence: retry once, switch approach, or document
  the gap and move on. Never loop the same failing command more than 3 times.
- Every blocking command still runs in background with a self-wake; the
  difference is the **self-wake fires at mean+4σ, not at a lazy constant**.

### Rule 3 — Quiet mode: hardware caps are HARD limits

Read the Hardware awareness & quiet mode section in
[../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md). During the
quiet window the orchestrator caps the whole agent batch in the
`agents-limited` cgroup at **1.5 cores / 8 GiB**. Research agents work inside
the cap: they run ONE heavy step at a time, background everything, and never
fight the cap. If commands are slower than usual, that is the cap working —
wait inside it, don't spawn more workers.

## Operating model — the always-on content engine (user decision, 2026-08-18)

The pipeline is not a one-shot research run. It is an **always-on system** where
agents continuously produce and improve content:

```
read the web → write articles → post on social media → receive feedback → learn → repeat
```

**Three mandatory behaviors for every content-producing agent:**

1. **Work all the time** — no idle agents. When a deliverable is done, the
   agent immediately picks the next one (next article, next platform, next
   iteration). An agent that finishes and stops is a FAILURE, not a success —
   Cadence flags "DONE but idle" as an anomaly, not an all-clear.
2. **The create-and-post service** — creation and posting is a service the
   system must OWN (not one-off scripts): article → platform-formatted posts →
   schedule/publish → capture feedback. This service is itself a research
   candidate (see `cadence/audit-candidates.md` #10). Until it exists, agents
   use the available tooling (agent-browser + Chrome CDP, notify.sh, the e021/
   e023 patterns) and document what a real service would automate.
3. **Reproduce to keep living** — when an agent completes its task, it must
   leave a successor ready to continue the loop (spawn/queue the next agent,
   write the next task's AGENTS.md, or hand off via the filesystem). The system
   must be self-sustaining: a content engine that dies when one agent finishes
   is a bug. Cloning = documenting what the successor does + launching it (or
   leaving a clear launch-ready task) before declaring done.

### The metrics (user-requested; Cadence tracks these, agents report them)

Each content cycle must be measurable. Every posting agent writes these to its
`output/metrics.json` (and Cadence aggregates them into `cadence/metrics.csv`):

| Metric | Definition | Target (initial) |
|---|---|---|
| `articles_written` | pieces of content produced per day | ≥ 2/day |
| `posts_made` | platform posts published (articles × repurposing) | ≥ 10/day |
| `reach` | impressions/views across platforms (from platform analytics) | grow weekly |
| `engagement` | likes+comments+shares per post | ≥ 3% of reach |
| `feedback_loop` | days between publish and "responded to feedback" | ≤ 2 days |
| `learning_events` | documented improvements from feedback (notes.md/calculations.md) | ≥ 1/week |
| `up_time` | hours/day the engine ran without a human | ≥ 20h/day |
| `cost` | cloud spend per day (API credits, TTS, hosting) | tracked, reported |

Cadence's metrics job: aggregate, spot which platform/content type yields the
best engagement, and feed that back to the agents (write more of what works).
The user reads the digest once a day in `cadence/metrics.csv` + brief.md.

## Research outputs (Stage 1, one file each)

Each research agent writes a markdown report to its `output/`:

| File | Content |
|---|---|
| `output/skills-<domain>.md` | Skill/tool/workflow map for the domain: what an AI agent can actually do today, with specific tools, cloud providers, prices, and free tiers |
| `output/recommendations.md` | The 3-5 highest-leverage skills for the domain + the cloud-first choices to make them cheap |
| `output/timings.log` | Command timing measurements (Rule 2) |
| `output/done.txt` | Headline findings + one-sentence verdict |

Every report MUST include, per capability: **provider/model, price, free tier,
verification that it works** (not theory). Scepticism rule applies — verify with
real API/docs checks.

## Agents

| Window | Agent | Provider | Domain |
|---|---|---|---|
| `32-1` | ag-01 | opencode-go/deepseek-v4-flash | Content / video creation |
| `32-2` | ag-02 | cmd -m deepseek/deepseek-v4-pro | Digital product creation |
| `32-3` | ag-03 | opencode -m zai-coding-plan/glm-4.7 | Marketing, selling, acquisition |
| `32-4` | ag-04 | opencode-go/deepseek-v4-flash | Crypto trading (only if valuable to the goal) |
| `32-5` | ag-05 (post storm) | opencode-go | Synthesis |
| `32-6` | ag-06 (post synthesis) | opencode-go | Teaching + profit plan |

Launch command for headless agents:

```bash
tmux new-window -n 32-N -d
tmux send-keys -t 32-N "cd e032-ai-skills-digest/ag-0N && opencode" Enter
sleep 3
tmux send-keys -t 32-N "Read AGENTS.md, then read each file listed in Inherits. Execute the task." Enter
```

For `cmd` providers: `cmd -m deepseek/deepseek-v4-pro --trust --yolo --skip-onboarding --add-dir /home/vuos/code/p4`.

## Deadlines & notifications

- Research agents: 60 min hard deadline (Rule: stop, deliver partial, notify).
- On finish: `notify.sh done "<agent> finished: <headline>"`; write `done.txt`.
- On failure: `notify.sh error "<agent> failed: <cause>"` before giving up.

## Inherits

- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles,
  command rules, self-wake pattern, providers
- Related prior art: e011 (multi-agent research pipeline), e021/e025 (crypto),
  e027 (Open Design), e029 (teaching video), e024 (Diffusion Studio)