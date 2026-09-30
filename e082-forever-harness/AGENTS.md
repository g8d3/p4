# e082 — Forever Harness (keep-going loop + plugin)

Agent harness the user configures once and the agent keeps working
indefinitely — tools + policies prevent quality collapse.
Ships as a plugin for existing harnesses (pi / opencode) to reuse their distribution.

## Product

| Surface | User action |
|---|---|
| Board `/` | ONE page. Edit keep-going policy, Start / Stop / Tick the loop, Verify now, read live status (running, cycle #, quality, budget bar), checkpoints, gates. No login. |
| Plugin `plugin/` | Install into pi or opencode: policy loader, tick wrapper, verify gate, compact helper + hooks script. Same policy, your own harness. |

Rule: the loop only advances through `tick` (heartbeat → verify → compact → ship).
Stop conditions always win: user stop, budget out, quality floor breach, goal done.

## Architecture

```
server/app.py    stdlib only: static public/ + /api/*
public/index.html  single-file UI, mobile-first, 5s refresh, zero deps
needs.json       ALL machine values (port, bind, loop interval, budget,
                 quality thresholds, compaction limits)
data/policy.json web-saved policy overrides (wins over needs.json)
data/loop_state.json  running, cycle, last_tick, last_quality, stopped_reason
data/heartbeat.json   last tick heartbeat (stuck detection)
data/cycles.jsonl     append-only per-tick log (cycle, quality, verdict, notes)
data/ledger.jsonl     append-only token/credit spend per tick
data/checkpoints.jsonl append-only periodic + compaction checkpoints
data/summary.json     rolling summary of compacted cycles (context budget)
data/verify.json      last gate run
data/version.json     seed v1
plugin/plugin.json    pi-style manifest
plugin/skills/keep-going/SKILL.md  the 4 tools documented for agents
plugin/hooks/keep-going.sh  load-policy|start|stop|tick|verify|compact|status
plugin/opencode.json  opencode-compatible install + tool snippet
bin/serve.sh     start/stop + live URL report (LAN/tailnet resolved live)
bin/loop.sh      one | daemon — start if stopped, then one tick
test/check.sh    API + first-paint smoke
```

## Collapse-proof policies (each is a tool endpoint + a plugin tool)

| Policy | Mechanism | Endpoint |
|---|---|---|
| Heartbeat + stuck detection | every tick writes `heartbeat.json`; status flags `stuck` when running with no fresh tick | `GET /api/health`, `GET /api/status` |
| Per-cycle verify gates | 6 gates per tick: policy_valid, budget_remaining, heartbeat_fresh, diff_size_cap, checkpoint_fresh, context_budget. Quality = 100 − 15 × fails | `POST /api/verify` |
| Checkpoint + compaction | checkpoint every N cycles; oldest cycles folded into `summary.json` past the cap, history preserved as digests | `GET /api/checkpoints`, `GET /api/summary` |
| Budget ledger | every shipped micro-goal appends tokens + cost; tick refuses when spend ≥ budget | `GET /api/ledger` |
| Stop conditions | user stop, budget out, quality floor breach, goal done (cycle ≥ max_cycles). Tick enforces, status reports | `POST /api/control/start\|stop\|tick` |

## Run

```bash
bash bin/serve.sh            # start + URL report
bash bin/loop.sh one         # start if stopped + one tick
bash bin/loop.sh daemon      # never stops (polls every 60s, PID in data/loop.pid)
bash test/check.sh
FOREVER_HARNESS_URL=http://127.0.0.1:8342 bash plugin/hooks/keep-going.sh tick
```

## DONE ladder

1. WORKING — :8342 serves board, start→tick→verify→checkpoints work, check.sh PASS.
2. DEPLOYED — tailnet URL, loop daemon alive, survives reboot.
3. TESTED — stuck flagged, budget stop fires, quality breach stops, compaction folds.
4. ANNOUNCED — owner ping with URL.
5. MONETIZED — only after usage proof; budget tracked in needs.json + ledger.

## Strategy context
Shared Q&A covering this experiment + its sibling: `../QA-E082-E083-DEX-TRADING.md` (new ideas, improvements, DEX maker/taker connections, bear-market businesses).
