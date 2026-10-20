# e099 — FiloEterno (self-improving crypto builder, operator-aware)

Build and audit real-value dapps, spending Go credits on 1.3 (see DIRECTION.md).
The loop sees what the operator sees: credits, providers, models, list prices,
context use, tokens/sec, empirical scores — and routes work accordingly.
Brain: `muse-spark-1.3-contributor` on `opencode-go`.

## Product

| Surface | User action |
|---|---|
| Glass wall (port in `needs.json`, all interfaces) | Read build tasks, audit findings, deploy receipts, lesson book, operator view. Run the free red-first probe. Flag confusing lines (penalty signal). |
| `bin/loop.py probe` | Red-first mutation check on task 01: breaks fee math in a copy, tests must go red. Free, no model calls. |
| `bin/loop.py today\|score\|propose` | Retired signal-loop bench commands (kept for side experiments). |
| `bin/op.py` | Operator snapshot: credits, 37 live models + prices, empirical table. |
| `bin/serve.sh` / `bin/stop.sh` | Start/stop the glass wall by exact PID. |
| `LESSONS.md` | The asset: every lesson + probe verdict in plain words. |


The edge that stays sharp. A loop that improves its own trading rule book,
paper-only, inside a cage, behind glass. Harness² ideas + Prime Agent safety,
own lean code (neither repo's code is used — see DESIGN.md for why).

## Product

| Surface | User action |
|---|---|
| `site/index.html` | The glass wall: read every brain version, every score, every lesson, today's paper signal. Served on all interfaces (port in `needs.json`); buttons run the loop, the flag form penalizes unclear lessons. |
| `bin/serve.sh` / `bin/stop.sh` | Start/stop the glass wall by exact PID. |
| `GET /api/status` | Live JSON: current brain, scores, calls used vs daily cap. |
| `bin/loop.py fetch` | Check market data link (no model call, free). |
| `bin/loop.py score` | Score current brain on last N past days (costs N model calls). |
| `bin/loop.py propose` | Ask for a better rule, test it on past data, adopt only if it wins + plain note passes. |
| `bin/loop.py today` | Record today's paper signal with the current brain (1 call). |
| `bin/loop.py render` | Rebuild the glass wall page. |
| `LESSONS.md` | The asset: every adopted/rejected lesson in plain words. |

## Architecture

```
needs.json     machine values (provider envs, caps, paths) — never hardcoded
bin/loop.py    stdlib: Kraken OHLC + gateway + score + adopt + cage
bin/render.py  stdlib: state/lessons/signals -> site/index.html
prompts/       every brain version kept forever (v1.txt, v2.txt, ...)
data/          state.json, signals.jsonl, call counts (gitignored)
LESSONS.md     append-only lesson book (tracked — this is the asset)
```

Model access: `$OPENCODE_GO_BASE_URL` + key from key envs in needs.json, Responses API, session header.
Key lives in env only, never in files.

## The cage (locked in bin/loop.py, the loop cannot edit it)

paper only · position size 0 · daily call cap · backtest-before-paper (new
rules must beat current brain on past data) · plain-note gate (<=140 chars or
rejected) · append-only lessons · human gate before anything real.

## Forever cycle (unattended)

`bin/cycle.sh` + systemd user timer `filoeterno-cycle.timer` (every 2h):
today signal + propose round + render. Guarded by weekly 80% + 200/day caps.
Logs: `data/cycle.log`. Own-brain rounds only — contracts change only with
human approval until the automated red-first mutation gate ships (task-02 job).

```bash
bin/loop.py fetch     # free, no model
bin/loop.py score     # 6 model calls
bin/loop.py propose   # ~7 model calls, adopts only winners
bin/loop.py today     # 1 call, tomorrow it gets scored
bin/loop.py render    # rebuild page
```
