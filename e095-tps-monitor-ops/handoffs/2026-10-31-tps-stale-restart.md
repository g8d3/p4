# Handoff after PI WEB session-daemon restart for TPS tab (read first, then act)

## What happened
- `e095-tps-monitor` v0.12.0 @ `f4e17ed` (2026-10-30 22:42 -0500). `npm run build` + `npm test`: 96/96 pass.
- `GET /api/plugins` showed `tps-monitor` stale: active `sha256:1a5ce…` vs desired `sha256:a7f0a…`, `staleRevision:true restartRequired:true`. Browser entry withheld → workspace TPS tab 404s/missing. Backend healthy, history/turns files 500/500 valid.
- `pi-web.service` was restarted 09:10 (new PID, HTTP 200) — safe but does NOT fix stale server revision.
- The session daemon was restarted via detached `restart-resume.sh` to activate the desired revision. You are a fresh agent in session `Restart pi web` (id `01a1924a-e370-779f-bae8-4add51acf770`, cwd `/home/vuos/code/p4`). All prior agent processes were killed by the restart — that is expected.

## Verify now (in order, no exceptions)
1. `curl -s http://127.0.0.1:8504/api/plugins | python3 -c "import json,sys; d=json.load(sys.stdin); print([(p['id'],p.get('server',{}).get('activeRevision'),p.get('server',{}).get('desiredRevision')) for p in d['plugins'] if p['id']=='tps-monitor'])"` — active MUST equal desired, stale false.
2. `cd /home/vuos/code/p4 && ./e095-tps-monitor-ops/verify-tps.sh suite revision files` — all PASS.
3. Real browser user-seat review (mandatory): open `http://127.0.0.1:8504/?project=5252bfc1-300e-4ada-bef9-f68534964180&workspace=f93c700afa07`, click workspace tab `TPS`. Confirm Messages/Turns/Tools/Fleet tables populate, no header block above tables (v25: sparkline → view switcher → filter → table only). Screenshot all four views to `/home/vuos/code/p4/e095-tps-monitor-ops/screenshots/` (NOT inside `e095-tps-monitor/` — that dir's churn stales the revision again).
4. `ss -tlnp | grep 8504`, `systemctl --user status pi-web.service pi-web-sessiond.service --no-pager`, `hostname -I`, `tailscale ip -4`. Record PIDs.

## Then report to the owner (in English, one verdict sentence first)
- Verdict first: TPS tab restored/missing + what the user can do there (Messages/Turns/Tools/Fleet actions).
- Attach the four screenshots as proof. Full server URLs (127.0.0.1, LAN, tailscale :8504) + both PIDs.
- Anything changed goes to the OPS dir or needs another restart via this same script + a new handoff. Leave PI WEB running. Never `pkill -f`.
