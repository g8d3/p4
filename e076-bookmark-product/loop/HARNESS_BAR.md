# Harness bar — what e076 is measured against

Research 2026-09-25 (winder.ai comparison + best-of-Agent-Harnesses list).
Field consensus: harness quality moves scores more than model upgrades
(SWE-bench Pro: same model 23%→52% pass@1 across harnesses).

## The bar (dominant harnesses)

| Harness | Loop | Tools+approvals | Memory | Triggers | Cost/metrics | Our gap |
|---|---|---|---|---|---|---|
| Claude Code / Codex | yes | yes, scoped | thin by design | manual+hooks | partial | hooks, sandbox |
| OpenCode (MIT, 199k★) | yes | yes, 75+ providers | sessions | manual | partial | providers, polish |
| Pi (this session's engine) | yes | yes, skills+subagents | session files | manual/spawn | tokens.py | event triggers |
| OpenClaw (always-on) | yes | yes + browser | durable | cron+events | yes | presence, chat surface |
| e062 runner (house) | legs+beats | T1 auto / propose+wait | ops.db | cron (paused) | SPEND.md | phone-first UX |
| **e076 runner (ours)** | legs+state | none yet | state.json+legs | watcher (new) | tokens/leg (new) | approvals, sandbox, trial protocol |

## What "enough" means (ordered)
1. Event-driven: message → leg, no button. DONE (watcher, 60s grace).
2. Live progress on page. DONE (/api/log + poll).
3. Truthful states (running row, consumed inbox). DONE.
4. Approvals: propose → human approve/reject → leg executes. NEXT.
5. Self-verify: frontend claims ship with screenshots. NEXT (rule, not yet habit).
6. Trial protocol: same task across versions, scored. NEXT (versions table).
7. Sandbox + cost caps per leg. LATER.

## Embed decision
The app already embeds the harness that matters: legs run on `pi --print`
JSON mode — the same engine as this session. No separate harness to embed;
the work is closing the 6 gaps above, newest first.
