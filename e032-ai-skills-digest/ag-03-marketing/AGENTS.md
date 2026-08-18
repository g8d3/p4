# ag-03 — Marketing, selling & acquisition skills research

Research agent for e032 Stage 1. Maps what AI agents can ACTUALLY do today for
marketing, selling, and acquisition — content distribution, social
automation, funnels, email, SEO, ads, and how an AI agent runs those loops.

## Agent id
`ag-03-marketing` — use this in all Cadence heartbeats and file names.

## Cadence
- Expected check interval: 60s while WORKING, extend to 120s during long channel-comparison reads.
- Call `report.sh ag-03-marketing "<current step>"` at every milestone and after every long command.
- Write ALL deliverables to `output/`. The monitor also watches that directory.

## Inherits
- [../../AGENTS.md](../../AGENTS.md) — experiment scope, Stage 1 contract
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake, agent-browser/CDP, X.com/TikTok access

## Agent-specific mission

Produce `output/skills-marketing.md`, `output/recommendations.md`, `output/timings.log`, `output/done.txt`.

Cover:

1. **Social distribution automation** — scheduling/posting across platforms
   (X, TikTok, YouTube, IG) with the available agent tooling (agent-browser via
   Chrome profile, API clients, n8n/Make/Composio). What actually works headless.
2. **Content engines** — AI pipelines that turn one idea into many assets
   (video → clips → captions → posts → newsletter), with cloud providers for
   each step and their price/free tier.
3. **Selling & funnels** — landing pages (Open Design), email capture, payments,
   digital product delivery. What an agent can own end-to-end vs what needs a
   human.
4. **Acquisition channels** — SEO basics an agent can execute (keyword research,
   structured content), community building, and the honest ROI picture of each.
5. **The teachable + profitable angle** — what marketing skill is easiest to
   teach others AND monetize (the experiment's core goal).

**Price/quality honesty**: verify at least 3 claims directly. Mark `[verified]`
or `[unverified]`.

## Deliverables
- `output/skills-marketing.md` — full skill map
- `output/recommendations.md` — top 3-5 highest-leverage skills + cloud choices
- `output/timings.log` — command timings
- `output/done.txt` — headline findings + verdict

## Rule compliance
- Cloud-first; measurement-based timeouts; 60 min deadline.

## Notify
- On finish: `notify.sh done "ag-03 marketing research finished: <headline>"`
- On failure: `notify.sh error "ag-03 failed: <cause>"`

## Self-command
- Every blocking command runs in background: `> /dev/null 2>&1 &`
- Self-wake: `tmux send-keys -t 32-3 "check status" Enter`
- `(sleep <mean+4σ>; tmux send-keys -t 32-3 "Self-wake: check" Enter) &`