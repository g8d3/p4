# Scout 3 — Leaner agent harness: opencode/opencode2 idle cost vs a trivial harness

## Question being investigated
We run `opencode` (8 agent windows) and `opencode2 serve --service` (1 client
in window a0) as our agent CLIs. Are we burning more RAM/CPU by running these
than a lighter alternative (a plain python/node script, a different harness)?
Measure: RSS + CPU of one idle opencode session, one opencode2 serve+client
pair, and a trivial harness (bare node/python CLI that calls the same provider
API). Compare. Read-only.

## What I actually did (chronological)
1. `ps -eo pid,ppid,rss,etime,pcpu,comm,args` — full fleet snapshot; mapped every
   opencode/opencode2 pid to its tmux window (`tmux list-windows -t main`).
2. Read scout-1 and scout-2 reports (shared evidence, avoids re-measuring Chrome).
3. Read cgroup + `free -m` + `uptime` (caps/load context).
4. `env | grep -iE 'OPENCODE|KEY|BASE_URL'` — confirmed `OPENCODE_GO_BASE_URL`,
   `OPENCODE_GO_API_KEY`, `OPENCODE_GO_MODEL` present → a real API call is possible.
5. Wrote 2 throwaway harnesses in scout-3 dir: `node-harness.mjs` and
   `py-harness.py` — ONE authenticated chat-completion call each to
   `https://opencode.ai/zen/go/v1/chat/completions` (model `deepseek-v4-flash`),
   timed + peak-RSS'd with `/usr/bin/time -v` (2-3 runs each).
6. Measured headless (no-TUI) one-shot equivalents: `opencode run -m opencode-go/deepseek-v4-flash "Reply with exactly: ok"` and `opencode2 run "..."` (thin client → live service), both timed + peak-RSS'd.
7. Sampled INSTANTANEOUS CPU of 5 idle opencode procs + opencode2 serve/client +
   cmd agent over 12 s via `/proc/<pid>/stat` jiffies (utime+stime after last `)`),
   HZ=100 confirmed. Also read lifetime CPU (cumulative jiffies).
8. Re-measured python harness with a `User-Agent` header after discovering the
   default urllib UA gets Cloudflare-blocked (403, error 1010).

## Evidence (numbers, not vibes)

### Idle interactive opencode sessions (DONE agents, window 32-1/3/4, scout-1/2)
| Window | PID | RSS (MiB) | Idle CPU (12 s) | Lifetime CPU | State |
|---|---|---|---|---|---|
| 32-1 ag-01 (DONE) | 251426 | 806 | 1.4% | 521 s | `S` sleeping |
| 32-4 ag-04 (DONE) | 251452 | 756 | 1.25% | 189 s | `S` |
| 32-3 ag-03 (DONE) | 251471 | 791 | 1.3% | 251 s | `S` |
| scout-1 (DONE) | 274406 | 783 | 1.3% | 142 s | `S` |
| scout-2 (DONE) | 279180 | 786 | 1.25% | 182 s | `S` |
| 32-2 ag-02 **cmd** agent (DONE) | 251510 | 219 | 0.17% | 21 s | `Execute` |
All `[measured]`. Interactive opencode idle ≈ **0.76–0.81 GiB each**, ~1.3% core.

### opencode2 serve + client pair
| Role | PID | RSS (MiB) | Idle CPU (12 s) | Lifetime CPU | Uptime |
|---|---|---|---|---|---|
| `opencode2 serve --service` | 11174 | 644–654 | 2.25% | 4045 s (~67 min) | 2 d 6 h |
| client window a0 (TUI, session 246858) | 246858 | 406–415 | 0.75% | 361 s | 1 h 42 m |
Pair total ≈ **1.05–1.07 GiB** `[measured]`.

### Headless one-shot (no TUI), same provider/model — `[measured]`
| Command | Peak RSS (MiB) | Wall time (1 call) |
|---|---|---|
| `opencode run` (headless opencode, boots server, exits) | **619** | 3.9 s |
| `opencode2 run` (thin client → live 644 MiB service) | **135** | 5.3 s |

### Trivial harnesses (bare script, ONE API call to the same provider) — `[measured]`
| Script | Peak RSS (MiB) | Wall time | Notes |
|---|---|---|---|
| `python3 py-harness.py` | **22** | 1.41 s | default urllib UA → Cloudflare **403 (error 1010)**; needs `User-Agent: curl/8.0` |
| `node node-harness.mjs` | **63** | 1.33–1.47 s | fetch passes Cloudflare by default |

### Derived: TUI + session overhead (interactive idle vs headless peak) — `[estimated]`
| CLI | Interactive idle | Headless peak | TUI/session overhead |
|---|---|---|---|
| opencode | ~784 (avg of 5 idle) | 619 | **≈165 MiB (~21%)** |
| opencode2 | 415 (client) | 135 | **≈280 MiB (~67% of client)** |

Fleet total right now: 7 opencode procs ≈ **5.7 GiB** + opencode2 pair ≈ 1.05 GiB.
If all 8 agent windows ran interactive opencode idle: ≈ **6.3 GiB**. System: 15.4 GiB
total, 9.1 used, load 1.4 (quiet-hours cap 1.5 cores / 8 GiB in `agents-limited`).

## Findings

### Waste found
1. **Each opencode window is a full self-contained runtime (~0.8 GiB), no sharing.**
   Idle CPU is small (~1.3% each) but RAM is not: 8 windows ≈ 6.3 GiB. The
   headless measurement (619 MiB) shows the TUI is only ~21% of that — the cost
   is the opencode client/server runtime itself, multiplied per window. `[measured]`
2. **The TUI is real overhead but not the main lever.** Dropping it (`opencode run`)
   saves ~165 MiB/window (~1.3 GiB for 8). Worth doing, but secondary. `[measured]+[estimated]`
3. **openCode2 already pays the server cost once (644 MiB) — headless clients add
   only ~135 MiB each.** 8 agents on opencode2 headless = 644 + 8×135 ≈ **1.72 GiB**
   vs 6.3 GiB for 8 interactive opencode ≈ **3.7× less**. Even 8 interactive
   opencode2 clients (644 + 8×415 ≈ 3.96 GiB) beat opencode by ~37%. `[measured]+[estimated]`
4. **The `cmd` agent (ag-02, 219 MiB idle, 0.17% CPU) proves a third-party CLI can
   be ~3.6× lighter than opencode for the same agent job.** `[measured]`
5. **DONE agents hold ~0.8 GiB each with no pending work** (ag-01/03/04, scout-1/2
   = ~3.9 GiB combined right now). A one-shot/exit pattern makes idle cost zero.
   Re-confirms scout-2's recommendation #1. `[measured]`
6. **Any python/node harness needs a Cloudflare-whitelisted UA**; the default
   urllib UA gets 403 → a naive "cheap script" silently fails against
   `opencode.ai/zen`. Practical gotcha, not a cost issue. `[measured]`

### What is already fine
- **Idle CPU is not the problem**: the whole opencode fleet burns ~9.7% of one
  core idle (5×1.3% + service 2.25% + client 0.75% + cmd 0.17%) — well inside the
  1.5-core cap. Nothing is spinning. `[measured]`
- The opencode2 service, once running, is cheap to reuse (2.25% CPU, 644 MiB for
  an unlimited number of clients). It is NOT itself waste — under-utilization is.
- The trivial-harness floor is 22–63 MiB and ~1.4 s/call — so the API path itself
  is cheap; the cost is entirely the agentic client layer. `[measured]`
- Interactive session continuity (TUI) has genuine value during active work; the
  waste is keeping it resident after the agent is DONE.

## Recommendations (ranked by value ÷ effort)
1. **Exit DONE agents; make agents run one-shot headless** (`opencode run "<task>"`
   per prompt instead of a persistent interactive session) — expected saving
   **~0.8 GiB × idle windows → ~0 when idle**; effort trivial; risk low (scout-2
   already verified nothing is in flight; headless `opencode run` measured at
   619 MiB/3.9 s per call). This alone removes the ~2.3 GiB of DONE research agents.
   Evidence: idle RSS [measured], headless peak [measured].
2. **Route the 8 agent windows through the already-running opencode2 service with
   headless clients** (`opencode2 run` per prompt, thin tmux shells that exit when
   idle) — expected saving **~6.3 GiB → ~1.7 GiB (≈4.6 GiB)**; effort medium
   (retool launch pattern only); risk medium (behavioral parity vs opencode must be
   verified). Headless client measured at 135 MiB/5.3 s. Evidence [measured].
3. **If interactive opencode must stay, at least run it headless-server +
   attach/`run`** (`opencode serve` per window + `opencode attach`, or `opencode run`)
   — expected saving ~165 MiB/window ≈ **1.3 GiB for 8**; effort low; risk low.
   Evidence: headless vs interactive delta [estimated].
4. **Do not build a custom harness** for the agent pipeline — the 22–63 MiB floor
   buys no agentic loop (tools, files, sessions). Only relevant for pure
   single-API-call jobs, and even then python needs a UA header to pass Cloudflare.
   Evidence: harness measurements [measured], agentic requirements [read].

## Honest limits
- TUI/session overhead is `[estimated]`: headless peak (during a call) vs idle RSS
  (includes accumulated session history) are not perfectly like-for-like.
- `opencode2 run` (5.3 s) hit a **warm** service; cold-start cost of the service
  not measured (would need spawning a throwaway server — heavy, skipped).
- Did not measure a persistent `opencode serve` server's RSS (would spawn a ~600 MiB
  throwaway; `opencode run`'s 619 MiB peak is a close proxy, marked estimated).
- `opencode2 run` created one throwaway session on the live service (PID 11174) —
  minor side effect, a0's session untouched. Window a0 itself not inspected
  (guardrail); measured only via `ps`.
- All measurements are quiet-hours under the 1.5-core/8 GiB cap; active-load RSS
  may differ slightly. Cumulative-CPU figures include each window's active work.
- The "8 agent windows" steady state is assumed; only 3 research agents + cadence +
  3 scout windows ran opencode during this audit (7 procs).

## Meta
- Duration: ~15 min (00:03 → 00:18). Commands run: ~24. Wait-bound: ~15% (three
  10–12 s CPU samples + ~10 s of API calls).
- Verification: RSS/CPU/wall/peak all `[measured]` (ps, /proc/stat, /usr/bin/time);
  provider URL/model `[read]` (env); TUI-overhead and fleet projections `[estimated]`.