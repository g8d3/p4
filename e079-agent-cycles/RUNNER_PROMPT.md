# RUNNER_PROMPT.md — intelligent legs (LLM, spends AI budget — OFF by default)

The dumb loop (`bin/loop.sh` on cron, $0) keeps the lane moving:
auto-starts queued goals, auto-finishes stale cycles, self-heals the
server, beats into `data/loop_log.jsonl`. It does NOT write code.

An intelligent leg (agent session like this one, or `pi --print` on
cron) writes code. Install only with owner approval — it burns margin.

## Intelligent leg prompt (one bounded leg, then exit)

```
You are leg N of e079-agent-cycles. Lane rules:
1. GET /api/cycles + /api/version + /api/goals. One running cycle max.
2. If a cycle is running and YOU did not start it, do NOT touch its code.
   Heartbeat and exit.
3. If none running: start the oldest queued goal, do the SMALLEST work
   that earns a version bump, run test/check.sh, open the page yourself,
   finish with notes. Never stack two goals in one version.
4. If the board is presentable-gated (owner holds social key until it is),
   prefer visual polish + proof over new features.
5. Append one improvement idea to the goals queue via /api/goals/add
   (owner law: every leg banks ≥1 idea). Exit.
```

## Install (owner call — spends AI quota 24/7)

```bash
# example: intelligent leg hourly (NOT installed by default)
# 0 * * * * cd /home/vuos/code/p4/e079-agent-cycles && pi --print "$(cat RUNNER_PROMPT.md)" >> data/runner.log 2>&1
```

## Cost honesty

Every intelligent leg must log its AI cost into Admin → Metrics.
Hiding inference spend is lying about margin (see SUCCESS.md).
