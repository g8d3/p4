# Audit candidates — questions worth a Scout

Seed list of "are we doing this wastefully?" hypotheses. Cadence picks from
these (or adds its own) and spawns ONE scout at a time. Add candidates as the
system evolves; remove closed ones.

Each candidate: **hypothesis → evidence to gather → where the answer lives**.

## Resource / runtime efficiency

1. **opencode vs lighter harnesses** — "Are we burning more RAM/CPU by running
   opencode/`cmd` as our agent CLI than a lighter alternative (e.g. a plain
   `python`/`node` script, a different harness)?"
   Evidence: measure RSS + startup time of `opencode`, `cmd` under identical
   simple prompts; compare with a trivial harness (e.g. time a bare node CLI).
   Where: live measurement in a scout dir; read `timings.log` of any agent.
2. **Persistent daemons** — "Which long-running processes idle-cost money or
   RAM? (transcribe servers, sway headless, OD daemon, chrome CDP instances)"
   Evidence: `ps` RSS of every service; how often each is used per day.
   Where: `ps`, `/proc/<pid>/status`, app logs.
3. **Chrome memory cost** — "A Chrome instance with the main profile eats RAM;
   is HEADLESS-X always justified, or could we reuse one instance per task
   batch?"
   Evidence: per-instance RSS, number of Chrome shells running now.
   Where: live `ps`, e000 fundamentals browser-automation notes.

## Cloud vs local

4. **Transcription/TTS double-spend** — "We keep both Parakeet (local) and
   Deepgram/KIE (cloud) paths alive. Which is actually cheaper/faster for the
   volume we really do?"
   Evidence: usage counts + latency + cost (credits/bucket) for last N runs.
   Where: e026/e029/e030 run logs, e018 PARAKEET.md, company pricing pages.
5. **GPU encoding reliance** — "VAAPI is great for final encodes, but are we
   using the GPU for *everything* that could be, or are some intermediates
   still on CPU?"
   Evidence: encoder tags in recent outputs (`ffprobe stream_tags=encoder`).
   Where: e023+ output dirs.

## Process / methodology

6. **Subscription utilization** — "We hold opencode-go, cmd, and Z.AI plans;
   are any underused while others carry the load?"
   Evidence: cost/usage per provider from run logs + their dashboards.
   Where: agent `timings.log`s, provider stats.
7. **Where do agent hours go?** — "Agents spend most time on what: thinking,
   waiting, or repeated retries? Which phase is the biggest time sink?"
   Evidence: session-log.md files across e021/e024/e025 (start/end + problem
   notes); classify time buckets.
   Where: `session-log.md` in every experiment's agents.
8. **Notification noise** — "Do we push too many notifications to the phone?
   What fraction was ignored, duplicated, or could have been batched?"
   Evidence: notifications.log volume by hour, NTFY/Telegram history.
   Where: `~/.opencode/notifications.log`.

## Cadence itself

9. **Cadence cost vs value** — "Is the monitor overhead (clock Python + mind
   LLM tokens) worth the stagnation it prevents?"
   Evidence: cadence.out + resource-audit.log volume; count of catches that
   materialized.
   Where: progress-monitor dir, notes.md.

## How to propose a new candidate

Format like the ones above: **hypothesis → evidence → where**. If it needs a
scout to inspect live processes, mark it `[live]`; if it can be answered by
reading existing logs, mark it `[logs]` and it may not need a scout at all.

## 10. Create-and-post service (the always-on content engine)

Hypothesis → "Posting content by hand (or one-off scripts) is the bottleneck:
an agent writes an article, then someone must format, schedule, and publish it
per platform. A service that owns creation → platform-format → schedule →
publish → feedback-capture would let the content engine run all day."
Evidence → measure the current per-article cycle: agent time to write, manual
steps to publish, per-platform format differences, feedback capture (likes/
comments) today vs achievable via APIs/CDP.
Where → `[live]` + `[logs]`: measure a real publish cycle on the available
tooling (agent-browser + Chrome CDP with the logged-in profile, notify.sh);
read e023 build-in-public notes + ag-01/ag-03 reports for platform details.
Output → a concrete service spec: endpoints, scheduling model, per-platform
adapters, feedback-collection contract — plus the honest build-vs-buy call
(hosted schedulers exist; what is the unique value here?).

## 11. Agent reproduction / successor handoff

Hypothesis → "The engine dies when an agent finishes and stops. If each
completing agent spawns/queues its successor (writes the next task, launches
it, or hands off via the filesystem), the system is self-sustaining."
Evidence → count how many completed agents actually left a successor vs how
many just stopped; measure the time gap between 'agent done' and 'next agent
started' across experiments.
Where → `[logs]`: read done.txt + session-log.md across e011/e021/e024/e025/e032.
Output → a reproduction protocol: what 'leaving a successor' means concretely,
when the orchestrator should spawn vs the agent itself, and the metric
`successor_gap` (minutes between agent done and next launched).