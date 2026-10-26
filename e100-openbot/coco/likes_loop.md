# Likes loop — diagnosis q50 (2026-10-25 ~19:55 Bogotá). Coco reviews first.

## Verdict
Likes **are being recorded now**. What is broken is the **processing** loop (`likes_loop.py`): it stopped after the Oct 24 10:10 tick and never restarted. Backlog: **52 unprocessed extension likes**.

## Evidence (all read live Oct 25 ~19:55 Bogotá, nothing changed)
- Intake works: `estado/likes_extension.jsonl` + `estado/x_items.json` (920 items) updated Oct 25 16:20; last like clicked 21:18:46Z, received 21:20:28Z (**~100 s sync latency**). `echolike_receptor.py --loop` running since 16:21. `likes_health.py`: 50 likes/24h, heartbeat 1 min old (STALE only because Nova hasn't liked in 3.6h — normal silence, not a break).
- Processing dead: `likes_loop.log` last line `2026-10-24T10:10:13-05:00 likes_loop tick 0s`; no `likes_loop` process running; `estado/likes_procesados.json` + `likes_recibidos.json` frozen at Oct 24 09:55 (543 recibidos / 820 procesados); 52 extension ids not in procesados.
- Not the cause: extension sync (works), receptor (works), migration 2.7.0 (`likes_loop.py` untouched since Oct 11; no migration code in this path). The 29.7h intake gap Oct 24 09:50 → Oct 25 15:31 is most likely Nova not liking / browser closed — receptor uptime that day is unknown, flagged not claimed.

## Cause
`likes_loop.sh` is an unsupervised `while true` background shell job — no cron entry, no systemd unit (only `alerta_topicos` has cron). Timeline: mini PC rebooted Oct 24 09:49:51 → loop restarted by hand 09:50:14 (`start pid=1969`) → shell died after the 10:10 tick (no error logged; killed with its session). Nothing revives it, so processing silently stopped while intake kept working.

## Smallest fix (needs Coco OK; I changed nothing)
1. Add the cron line (precedent: `alerta_topicos` already runs this way; each `--once` run is independent, so a crash can never wedge it again):
   `*/5 * * * * /usr/bin/python3 /home/vuos/code/p4/e092-echolike/likes_loop.py --once >> /home/vuos/code/p4/e092-echolike/likes_loop.log 2>&1`
2. Optional catch-up: the next 4 cron runs drain the 52-backlog at 15/run — **side effect: up to ~15 "❤️ Recibido" Telegram messages per run**. If that is too noisy, say so and the fix is one line in `likes_loop.py`: skip `aviso_recibido` for items older than 24h (I can do that on a branch with a test on request).
3. Verify: `python3 likes_health.py` (intake) + re-run the backlog count:
   `python3 -c "import json; p=set(json.load(open('estado/likes_procesados.json'))['procesados']); e=[json.loads(l)['id'] for l in open('estado/likes_extension.jsonl')]; print('unprocessed:', len(set(map(str,e))-set(map(str,p))))"` → expect 0 after catch-up.

No code change made (the loop code is fine; supervision is the gap), so no branch. No services enabled, nothing pushed/published.
