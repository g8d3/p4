# Handoff after session-daemon restart: restart-proof marker + session continuity test

## What happened
- Restart-proof marker added (uncommitted in /home/vuos/code/p4): `models.js`
  `report()` now includes `backend:{pid,startedAt}` (module-load timestamp),
  `panel.js` shows a `backend pid X · up since …` row. Panel part already
  verified hot-loading on the OLD backend (renders, row hidden until backend
  restarts — new code tolerates the old report).
- Continuity probe session `01a19305-aeeb-70a5-82c9-454ee13559d8` (name starts
  "Continuity probe", cwd /home/vuos/code/p4) did pre-restart work: 7 msgs,
  wrote /tmp/probe-restart.txt with 3 lines (sid / timestamp / PROBE-WORK-DONE).
- Pre-restart pids: sessiond 2881887. p4 sessions: 429+. Models: 4/4 exact.
- The session daemon was restarted detached. You are a fresh agent in session
  `Restart pi web` (id `01a1924a-e370-779f-bae8-4add51acf770`,
  cwd `/home/vuos/code/p4`). Prior agent processes died — expected.

## Verify now (in order)
1. Backend marker = proof of restart: open
   `http://127.0.0.1:8504/?project=5252bfc1-300e-4ada-bef9-f68534964180&workspace=f93c700afa07`
   in a real browser, click workspace tab `Models`. The header card must show
   `backend pid <NEW> · up since …` with NEW pid != 2881887. (If the row is
   missing, the backend change did not activate — report FAIL, do not commit.)
2. Sessions persisted: `curl .../sessions?cwd=%2Fhome%2Fvuos%2Fcode%2Fp4` still
   lists 01a19305 (7 msgs) and 01a1924a. No prompts to fleet sessions.
3. Resume the probe (continuity proof):
   `curl -s -X POST .../sessions/01a19305-aeeb-70a5-82c9-454ee13559d8/prompt -H 'Content-Type: application/json' -d '{"cwd":"/home/vuos/code/p4","text":"Read /tmp/probe-restart.txt, append a 4th line: RESUMED-OK <current time>. Then reply with all 4 lines verbatim."}'`
   Wait ~60s, then `cat /tmp/probe-restart.txt` — 4 lines with your session
   referencing its own earlier work = continuity proven. If it cannot recall
   the earlier work, report that honestly as FAIL.
4. Models still 4: `./e095-tps-monitor-ops/doctor.sh models`. TPS still
   healthy: `doctor.sh tab-missing tps-monitor`.
5. Inventory: both service PIDs, `ss -tlnp | grep 8504`, `hostname -I`,
   `tailscale ip -4`.

## Then finish
- If ALL green: commit the marker change in /home/vuos/code/p4
  (`e105-piweb-plugins/models/models.js`, `e105-piweb-plugins/models/panel.js`;
  message like `p4.models: backend pid/uptime row, restart-proof marker`) and
  push origin/master. If push fails, report the retry command.
- Report to the owner in English, verdict first: restarted (old pid 2881887 →
  new pid N, marker visible), probe session resumed with its own earlier work
  (quote the 4 lines), pre-existing sessions persisted, models 4, TPS healthy.
  Attach or describe the Models-tab evidence. Full server URLs + both PIDs.
  Leave PI WEB running. Never `pkill -f`.
