# Scout 1 — Chrome memory cost: one instance = 1.21 GiB, partially justified, reusable batch pattern is viable

## Question being investigated
How much RAM does each Chrome instance actually cost right now, which ones are
justified (a live experiment needs them), and is there a reusable "one instance
per task batch" pattern that would cut idle Chrome RAM? Read-only.

## What I actually did (chronological)
1. `ps -eo pid,ppid,rss,etime,args` filtered for chrome/chromium — full instance inventory + RSS per process.
2. `ss -tlnp` — full listening-port map; confirmed the only Chrome debug port is 9223 and 127.0.0.1:8787 is NOT listening (connection refused probe).
3. `ps` tree aggregation for the 167047 subtree; `/proc/<pid>/status` (VmRSS/VmHWM/Threads) for the big processes.
4. `grep` for chrome/swiftshader/render in `resource-audit.log`; confirmed `chrome_cpu_render: 1` flagged on every audit line (first at 23:30:31, 15 occurrences).
5. `grep -rn` across e030/e031/e032 for `chrome-gpu`, `9223`, `8787` — origin experiment identification.
6. Read-only CDP queries to http://127.0.0.1:9223/json/version and /json — enumerated live tabs.
7. `/proc/<pid>/cwd` + `/proc/<pid>/stat` ticks — origin dir, cumulative CPU per process.
8. `free -m` + `/proc/<pid>/cgroup` — system memory pressure and cgroup scope (read-only).

## Evidence (numbers, not vibes)

### Only ONE Chrome instance exists (PID 167047 tree, 11 processes)
| Process | PID | RSS | Role |
|---|---|---|---|
| chrome main | 167047 | 346.2 MB | browser, 30 threads, ppid=1 (orphaned launcher) |
| gpu-process | 167115 | 234.8 MB | SwiftShader (CPU), ~11.5% CPU now |
| renderer | 167316 | 201.4 MB | renderer-client-id=17 |
| network utility | 167117 | 120.7 MB | NetworkService |
| audio utility | 234286 | 91.1 MB | AudioService (7.5h old) |
| renderer | 234274 | 74.5 MB | renderer-client-id=61 (7.5h old) |
| zygote | 167069 | 66.8 MB | |
| zygote | 167068 | 66.2 MB | |
| storage utility | 167129 | 52.9 MB | StorageService |
| crashpad ×2 | 167054/167056 | 8.6 MB | |
| **Tree total** | | **1,263,084 KB ≈ 1.21 GiB** | `[measured]` |

- Launch args: `--enable-gpu --enable-unsafe-swiftshader --remote-debugging-port=9223
  --user-data-dir=/tmp/opencode/chrome-gpu http://127.0.0.1:8787/`; cwd =
  `/home/vuos/code/p4/e030-vrm-avatar/ag-01-avatar-studio` (launched from e030). `[read]`
- Original target 127.0.0.1:8787 (e030 VRM avatar WebSocket server, per
  e030 transcript) is DEAD — connection refused. `[measured]`
- However the instance currently hosts a LIVE tab: `El Sueño — A Paper-Cutout
  Dream` → `http://localhost:8788/` (CDP /json). 8788 = `node server.js` (PID
  234464, 54 MB) in `/home/vuos/code/p4/e031-wife-dream/ag-01-dream-player`,
  up 7.5h. `[measured]`
- Seed's "≈856 MB" is stale/undercounted: full tree now 1,263 MB (+47%).
  VmHWM == VmRSS on main/gpu/renderer, so those processes are at their
  lifetime peak. `[measured]`
- System memory: 15.4 GB total, 7.7 GB used, swap 511/511 MB exhausted.
  Chrome tree = **16% of used RAM**. `[measured]`
- Cumulative CPU: gpu-process 1,101,145 ticks ≈ **3h of CPU** over 26h uptime
  (SwiftShader software rendering). Main 232k ticks, renderer 235k. `[measured]`
- Audit log: `chrome_cpu_render: 1` on every line since 23:30:31 (15 lines). `[read]`
- e032 stage-1 agents (ag-01..04): zero browser-automation references — pure
  CLI pipeline. e032 needs no Chrome instances. `[read]`

## Findings

### Waste found
- **Orphaned launcher + dead original URL** — ppid=1, points at dead 8787;
  survived 26h with no watchdog because nothing reaped it. 1.21 GiB held
  regardless of usefulness. `[measured]`
- **SwiftShader CPU rendering on a GPU box** — `--enable-unsafe-swiftshader`
  is present even though `/dev/dri/renderD128` exists and
  `--render-node-override` is set. GPU process has burned ~3 CPU-hours and
  still runs at ~11.5% CPU idle. This is the audit's `chrome_cpu_render` flag. `[measured]`
- **Idle second renderer + audio service** (7.5h old, 74 MB + 91 MB) with no
  new tab activity — per-browser-session drift that a fresh per-batch instance
  would not accumulate. `[measured]`

### What is already fine
- Only ONE instance exists — no instance fleet, no multiplication of the
  ~985 MB fixed process set. `[measured]`
- The one instance is partially justified: it is the display target for the
  live e031 dream-player server (8788 tab). Killing it blind could break a
  running experiment. `[measured]`
- Remote debugging is bound to 127.0.0.1 (localhost), not exposed. `[measured]`
- Instance count is not the current problem; instance hygiene is.

## Recommendations (ranked by value ÷ effort)
1. **Decide kill-vs-repoint for PID 167047** — expected saving 1.21 GiB RAM +
   ~11% background CPU + clears the `chrome_cpu_render` audit flag. Effort:
   low (one decision, one kill). Risk: medium — it hosts the live e031 tab.
   Evidence: tree RSS [measured], dead 8787 [measured], live 8788 tab [measured].
   If e031 still needs the display: relaunch WITHOUT `--enable-unsafe-swiftshader`
   (GPU exists). If not: kill the whole tree and its 2 crashpads.
2. **Adopt the "one instance per task batch" pattern** for any future browser
   automation — one long-lived instance with a single user-data-dir, open N
   tabs via CDP (`Target.createTarget` / `/json/new`), close tabs per task,
   kill the instance at batch end, and add a watchdog that auto-kills when the
   target URL stops listening. Expected saving: ~985 MB per avoided parallel
   instance plus zero zombie survivors (this zombie lived 26h because no such
   watchdog existed). Effort: low–medium (wrapper script, reusable). Risk: low.
   Evidence: fixed process set [measured], zombie survival 26h [measured].
3. **Launch-template rule: never `--enable-unsafe-swiftshader` on this box** —
   expected saving: ~3 CPU-hours/day and removal of a permanent audit warning.
   Effort: trivial (flag check). Risk: low. Evidence: renderD128 exists [read],
   gpu-process 3h cumulative CPU [measured].

## Honest limits
- Could not launch a fresh Chrome to measure the true idle baseline (read-only
  rule). The "fixed set ≈985 MB / minimal ≈540 MB" figures are component
  breakdowns of the live instance, marked estimated.
- Could not confirm whether e031 still actively needs the Chrome display —
  that belongs to e031's owner. I read the server's existence and the tab, not
  its access log.
- The 856 MB → 1.26 GB delta is either seed undercounting or genuine post-seed
  growth; VmHWM == VmRSS on the big processes so they are at lifetime peak now.
- Did not inspect opencode/agent RAM (out of scope); the 6 opencode processes
  (~5.4 GB) dwarf Chrome but are not this scout's question.

## Meta
- Duration: ~6 min, commands run: 8, wait-bound: ~3 s (curl timeout), rest CPU-local.
- Verification: `[measured]` = read live from /proc / ps / ss / CDP; `[read]` = file/log; `[estimated]` = derived.