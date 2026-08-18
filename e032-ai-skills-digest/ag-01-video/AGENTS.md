# ag-01 — Content / Video creation skills research

Research agent for e032 Stage 1. Maps what AI agents can ACTUALLY do today for
content and video creation, with verified cloud providers, prices, and free
tiers. The goal of the digest is "teach others and be profitable" — so focus
on cheap, effective, teachable workflows.

## Agent id
`ag-01-video` — use this in all Cadence heartbeats and file names.

## Cadence
- Expected check interval: 45s while WORKING, extend to 90s during long web-research stretches.
- Call `report.sh ag-01-video "<current step>"` at every milestone and after every long command (see Inherits → fundamentals → Cadence section).
- Write ALL deliverables to `output/`. The monitor also watches that directory.

## Inherits
- [../../AGENTS.md](../../AGENTS.md) — experiment scope, Stage 1 contract
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake pattern, GPU/VAAPI, KIE API, video pipeline

## Agent-specific mission

Produce `output/skills-video.md`, `output/recommendations.md`, `output/timings.log`, `output/done.txt`.

Cover:

1. **Modern AI video pipelines** — text-to-video, image-to-video, talking
   avatars/VRM, faceless explainers, screen-capture workflows, HTML→MP4
   (HyperFrames), programmatic composition (ffmpeg, Diffusion Studio).
2. **Cloud providers & cost** — for EACH capability, find the cheapest modern
   provider with a workable free tier. Include at least: TTS, STT/transcription,
   image generation, video generation, subtitles/translation. This is the
   cloud-first rule: the answer to "how do we transcribe" is a provider
   comparison, not a local install. Use web research + verified pricing pages.
3. **The teachable angle** — what can a beginner produce today with a phone +
   cheap AI subscription? Realistic quality bar, common failure modes, and the
   "detect the headache, switch to cloud" decision rule.
4. **Profit potential** — what video/content skills are actually monetizable
   (youtube automation, faceless channels, client work, digital products).

**Price/quality honesty**: verify at least 3 claims per section directly
(pricing page, doc page, or a live API test if free credits allow). Do NOT
trust a summary you did not check. Mark each entry as `[verified]` or
`[unverified]` next to the claim.

## Deliverables
- `output/skills-video.md` — the skill map (see e032 AGENTS.md for file contract)
- `output/recommendations.md` — top 3-5 highest-leverage skills + cloud choices
- `output/timings.log` — timings of every command you run (Rule 2)
- `output/done.txt` — headline findings + verdict

## Rule compliance
- Cloud-first for everything (STT/TTS/video/image).
- Measurement-based timeouts: every command logged, waits ≤ mean+4σ.
- Deadline 60 min: stop, ship partial, notify.

## Notify
- On finish: `notify.sh done "ag-01 video skills research finished: <headline>"`
- On failure: `notify.sh error "ag-01 failed: <cause>"`

## Self-command
- Every blocking command runs in background: `> /dev/null 2>&1 &`
- After each: `tmux send-keys -t 32-1 "check status" Enter`
- Self-wake with context: `(sleep <mean+4σ>; tmux send-keys -t 32-1 "Self-wake: step=N, PID=X, check progress/errors/done" Enter) &`