# Handoff after session-daemon restart: TPS split migration + doctor/slim-verify (read first, then act)

## What happened
- `e095-tps-monitor` v0.13.0: plugin entry SPLIT (`tps-monitor` server-only +
  `tps-monitor.panel` browser-only, same pattern as p4.cycles/p4.models). The
  panel no longer uses the in-process `context.peer`; it calls the backend
  over the paired proxy (HTTP POST + WebSocket open/ready/data envelopes,
  see `src/browser/paired.ts`). `src/server.ts` UNCHANGED. `npm run build` +
  `npm test`: 97/97 pass. CHANGELOG entry written, version bumped to 0.13.0.
- `e095-tps-monitor-ops/doctor.sh` (new): `tab-missing <id>` | `models` |
  `report`. `scripts/models.py` gained `sync-daemon --sid --cwd` (daemon-API
  trim, never touches settings.json). `verify-tps.sh` gained `panel-text`
  (browser asserts, no screenshots).
- Earlier today: `~/.pi/agent/extensions/sync-opencode-models.ts` fixed to
  respect `wanted.json` picks (was re-enabling all 161 models on every pi
  launch); model picker holds 4 since 09:34, daemon catalog reads 4.
- The daemon was restarted detached to activate the new split registration.
  You are a fresh agent in session `Restart pi web`
  (id `01a1924a-e370-779f-bae8-4add51acf770`, cwd `/home/vuos/code/p4`).
  Prior agent processes died with the restart — expected.

## Verify now (in order)
1. `curl -s http://127.0.0.1:8504/api/plugins` → BOTH `tps-monitor` (server
   active==desired, healthy, stale false) AND `tps-monitor.panel`
   (browser-only) listed. No other entry may be stale (p4.* entries may show
   stale from ops-script edits — harmless: their panels are browser-only and
   their backends keep running; only flag it, do not restart again).
2. `cd /home/vuos/code/p4 && ./e095-tps-monitor-ops/verify-tps.sh suite revision files panel-text` — all PASS.
   (`revision` checks `tps-monitor` server; `panel-text` = new slim step.)
3. User-seat review (mandatory): open
   `http://127.0.0.1:8504/?project=5252bfc1-300e-4ada-bef9-f68534964180&workspace=f93c700afa07`,
   click workspace tab `TPS`. All four views must render tables from live
   data (Messages/Turns/Tools/Fleet). Screenshot all four to
   `/home/vuos/code/p4/e095-tps-monitor-ops/screenshots/v26-split-*.png`
   (NOT inside `e095-tps-monitor/`). While a stream runs, the newest table
   row must advance without reload (live push over the new WS transport).
4. Models still 4: `doctor.sh models` → exact match; daemon catalog enabled
   count is 4.
5. `ss -tlnp | grep 8504`, both service PIDs, `hostname -I`, `tailscale ip -4`.

## Then finish (in order)
- If everything passes: commit `e095-tps-monitor` (message like
  `v0.13.0: split panel + server, paired-proxy transport`) and push to origin
  (public mirror per that repo's rules: never commit `dist/`). If the push
  fails, report the exact retry command. Do NOT commit from `/home/vuos/code/p4`
  (that repo ignores `e095-tps-monitor/`; ops-side files
  `e095-tps-monitor-ops/doctor.sh`, `verify-tps.sh`, `AGENTS.md`,
  `e105-piweb-plugins/scripts/models.py`,
  `e105-piweb-plugins/docs/current-models.md` are intentionally uncommitted
  working files — leave them, mention them).
- Report to the owner in English, verdict first: TPS tab restored via split
  (what survives updates now), doctor + slim-verify delivered, models still 4.
  Attach the four screenshots. Full server URLs + both PIDs. Leave PI WEB running.
