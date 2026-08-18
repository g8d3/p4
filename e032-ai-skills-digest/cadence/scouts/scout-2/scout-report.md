# Scout 2 — Persistent daemons: which long-running processes idle-cost RAM/CPU?

## Question being investigated
Which long-running processes on this machine idle-cost RAM or CPU, and which
are justified? Audit every persistent daemon (transcribe servers, sway headless,
HyperFrames/OD daemon, chrome CDP instances, node servers, etc.): their RSS,
uptime, how often they are actually used, and whether a cheaper pattern exists
(lazy-start on demand, or justifiable always-on). Read-only.

## What I actually did
1. `ps aux --sort=-rss` + `ps -eo pid,ppid,etime,%cpu,rss,stat,cmd` — full snapshot, ranked.
2. `/proc/<pid>/cwd`, `cmdline`, `status` (VmRSS/State/Threads) for every candidate.
3. `ss -tlnp` / `ss -lxnp` — listeners (TCP + unix); `ss -tnp` — established connections.
4. `curl` probes to 8787/8788/9090/9877/9223/44435/35587 — which servers actually answer.
5. `tmux list-windows -t main` + PPid walk — mapped every opencode pid to a window/agent.
6. `resource-audit.log` + `progress-monitor.log` tails — DONE status, load, mem.
7. `find` recent-writes in e030-vrm-avatar and e031-wife-dream; read `server.log`, `done.txt`, `server.js` (port/role).
8. `systemctl --user` — confirmed filex is an intentional enabled service.
9. 5s instantaneous CPU delta on all candidates (jiffies from /proc/pid/stat) — idle vs spinning.
10. `pgrep` for model_worker / wf-recorder / Xvfb / od daemon — confirmed none present.

## Evidence (numbers, not vibes)
System: 15.4 GiB RAM, 8.3 GiB used, 7.1 GiB available. Load 0.2–2.7 (quiet hours, capped 1.5 cores/8 GiB). All candidates measured with 5s CPU delta → **0–2% CPU, all sleeping**; the cost is pure RSS.

| PID | Role / owner | RSS (MiB) | Uptime | State | Last real activity | Instant. CPU (5s) |
|---|---|---|---|---|---|---|
| 251426 | ag-01-video `opencode` | 895 | 49 min | Sl+ ep_poll | DONE (done.txt, monitor log) | +9 jiffies (~2%) |
| 251471 | ag-03-marketing `opencode` | 790 | 49 min | Sl+ ep_poll | DONE (done.txt, monitor log) | +8 jiffies |
| 251452 | ag-04-crypto `opencode` | 762 | 49 min | Sl+ ep_poll | DONE (done.txt, monitor log) | +9 jiffies |
| 251510 | ag-02-products `cmd` agent | 212 | 49 min | Sl+ ep_poll | DONE (done.txt, monitor log) | 0 |
| 167047+ | Chrome tree (avatar, user-data-dir chrome-gpu) | **1233** (11 procs) | 1d 2h | sleeping | Page target http://127.0.0.1:8787 **dead**; outputs Aug 16 17:55 | ~2% |
| 166832 | sway headless (sway-headless.conf) | 103 | 1d 2h | ep_poll | hosts the idle Chrome only | +11 jiffies (~2%) |
| 156432 | agent-browser-l (CDP client → Chrome 9223) | 13 | 1d 2h | futex_wait | connected to Chrome 9223, idle | +1 jiffy |
| 97325 | transcribe_server.py (Parakeet ASR, 127.0.0.1:9877, nice) | 19 | 1d 7h | do_poll | no log; last output mtimes Aug 16 17:55 | 0 |
| 234464 | node server.js — e031 dream-player (0.0.0.0:8788) | 52 | 7h 42m | ep_poll | no connections; log = 1 start line; done.txt: "no client needed to keep it alive" | 0 |
| 1940 | filex (0.0.0.0:9090, serves /home/vuos) | 76 | 2d 11h | do_poll | no current connections; **enabled systemd user service** (intentional) | 0 |
| 11174 | opencode2 serve --service | 643 | 2d 6h | ep_poll | 1 client (246858, window a0) + outbound API | +9 jiffies |
| 246858 | opencode2 session (window a0) | 404 | 1h 20m | Sl+ | idle, connected to 11174 | — |
| 270893 | cadence-monitor.py | 13 | 24 min | — | cadence clock, running now | — |
| 265967 / 274406 | cadence agent / scout-1 | 864 / 788 | 27 / 18 min | working | active | — |

Cross-checks: `resource-audit.log` (23:51–23:53) quiet_hours=true, encoders_cpu=0, mem ~8 GiB.
`progress-monitor.log` 23:46–23:53: ag-01/02/03/04 all `DONE`, `done.txt present`.
No `model_worker.py`, `wf-recorder`, `Xvfb`, or HyperFrames/OD daemon running anywhere.
Chrome total 1233 MiB matches scout-1's 1.21 GiB (not re-audited, counted once).

## Findings

### Waste found
1. **Four DONE research agents left open in tmux — ~2.6 GiB idle.**
   ag-01 (895), ag-03 (790), ag-04 (762), ag-02 cmd (212) all have `done.txt`, are
   marked DONE by the monitor, and sit idle in windows 32-1..32-4. No pending work.
2. **Orphaned avatar-studio stack (e030-vrm-avatar) — ~1.37 GiB idle.**
   sway + Chrome(1.23 GiB) + agent-browser + transcribe_server. Its serving
   `server.js` (port 8787) is **not running** — Chrome is displaying a dead URL.
   Last outputs Aug 16 17:55, ~30 h before this audit. All procs sleeping.
3. **e031 dream-player node server on 0.0.0.0:8788 — 52 MiB + exposed port.**
   Agent finished (done.txt); server.log shows only the startup line; zero
   established connections; done.txt itself says it stays up with no client.

### What is already fine
- `cadence-monitor.py` (13 MiB), cadence agent, scout-1 — active, justified.
- `filex` (76 MiB) — intentional enabled systemd service (user's own file server).
- `opencode2 serve --service` — infrastructure for the opencode2 client in window a0;
  heavy but in-use. (Client itself sits in a0 = orchestrator/user window — not audited per guardrails.)
- Xorg / sddm-greeter / pipewire — desktop stack, outside agent scope.
- Nothing is spinning CPU: quiet-hours load is 0.2–2.7, all daemons ≤2%.

## Recommendations (ranked by value÷effort)
1. **Close the 4 DONE agent processes (ag-01..04)** — save **~2.6 GiB RAM**, near-zero effort,
   low risk (all done.txt verified, nothing in flight). The single biggest idle cost.
2. **Tear down the avatar-studio stack (sway + Chrome + agent-browser + transcribe)** —
   save **~1.37 GiB**, lazy-start on demand if e030 is resumed. Its page server is dead and
   it has been idle ~30 h. Medium effort, low risk (pure orphan; nothing produces output).
3. **Stop the dream-player node server (0.0.0.0:8788)** — save 52 MiB and close a LAN port.
   Trivial effort, zero risk (done.txt: no client needed).
4. **Review opencode2 service (643 MiB) for a single idle client** — 8 agent windows run
   `opencode`, only window a0 runs `opencode2`. If a0 can use `opencode`, the service +
   client pair (~1 GiB) could be dropped. This is the "leaner harness" question — worth its
   own scout (candidate for cadence's audit list). Medium effort/risk, big potential save.
5. **filex: keep (intentional), but bind it to LAN IP instead of 0.0.0.0** — it serves the
   entire /home/vuos unauthenticated to the network. Not an idle-cost issue (0 CPU), but a
   security hardening note. User-owned service — do not change without intent.

## Honest limits
- Transcribe server (97325) has **no log**; I could not verify its request history. Its
  start (Aug 16 21:14) postdates the last output files (17:55), so it may have served nothing yet.
- Chrome root-cause/ownership details left to scout-1 (already covered).
- opencode2 client 246858 is in window a0 (orchestrator) — not investigated per guardrails.
- The "waste" judgment for the avatar stack and dream-player assumes e030/e031 are finished;
  if they are being resumed, recommendations 2–3 change to "keep but lazy-start".
- Port 0.0.0.0:35587 has no owner shown by `ss` and did not answer a probe — likely a
  kernel/Tailscale listener; not investigated further.

## Meta
- Duration: ~4 min (23:52 → 23:56). Commands run: ~12. Wait-bound: ~5% (two 3–5s CPU samples).
- Verification: RSS/uptime/state/CPU all `[measured]` (ps, /proc); listener/probe results
  `[measured]` (ss, curl); "intentional service" `[read]` (systemctl); activity recency
  `[read]` (file mtimes, done.txt, logs); usage history of transcribe/filex `[estimated]`.