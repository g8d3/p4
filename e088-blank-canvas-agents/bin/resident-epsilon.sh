#!/bin/bash
# resident-epsilon: LIVE shift loop. Beat every 3s, inbox watch, watchdog for bg jobs.
# Usage: bin/resident-epsilon.sh run|stop|status
cd "$(dirname "$0")/.."
PIDFILE="data/resident-epsilon.pid"
BGJOB="data/resident-epsilon.bgjob"  # "pid|start_epoch|desc"

beat() {
  python3 - "$BGJOB" <<'EOF'
import json, os, sys, time
bgfile = sys.argv[1]
now = int(time.time())
try:
    w = json.load(open('data/workers.json'))
except Exception:
    w = {'agents': {}}
# background job status
desc = "idle, watching inbox"
try:
    if os.path.exists(bgfile):
        pid, start, what = open(bgfile).read().strip().split('|', 2)
        el = now - int(start)
        alive = os.path.exists(f'/proc/{pid}')
        desc = f"bg pid {pid}: {what}, {el}s elapsed" + ("" if alive else " (EXITED, reaping)")
        if not alive:
            os.remove(bgfile)
except Exception as e:
    desc = f"idle (bgjob read err {e})"
# inbox: WATCH ONLY — this bash loop cannot think, so it must never adopt.
# Adoption/execution belongs to a live AI runner (see data/runners.json).
pending = 0
try:
    t = json.load(open('data/tasks.json'))
    pending = sum(1 for x in t if x.get('status') == 'pending')
except Exception as e:
    desc += f" [inbox err {e}]"
try:
    r = json.load(open('data/runners.json'))
    import time as _t
    live = [k for k, v in r.items() if _t.time() - v.get('ts', 0) < 120]
except Exception:
    live = []
desc += f" | inbox {pending} pending, AI runner: " + (",".join(live) if live else "NONE (queue waits)")

ag = w.setdefault('agents', {}).setdefault('epsilon', {})
ag['ts'] = now
ag['doing'] = desc
json.dump(w, open('data/workers.json', 'w'), indent=1)
EOF
  # stop check
  [ -f data/resident.stop ] && echo "stop file present, exiting" && exit 0
}

case "${1:-run}" in
  run-once) beat ;;
  run)
    echo $$ > "$PIDFILE"
    echo "resident-epsilon on shift pid $$"
    while true; do beat; sleep 3; done ;;
  stop)
    if [ -f "$PIDFILE" ]; then P=$(cat "$PIDFILE"); kill "$P" 2>/dev/null && echo "stopped $P" || echo "pid $P dead"; rm -f "$PIDFILE"; else echo "not running"; fi ;;
  status)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then echo "running pid $(cat "$PIDFILE")"; python3 -c "import json;print(json.load(open('data/workers.json'))['agents'].get('epsilon'))"; else echo "not running"; fi ;;
esac
