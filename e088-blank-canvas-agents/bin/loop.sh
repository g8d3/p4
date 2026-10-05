#!/bin/bash
# Supervisor: heartbeat tick + daemon. Usage: bin/loop.sh one | daemon | stop
set -e
cd "$(dirname "$0")/.."
PIDFILE="data/loop.pid"

tick() {
  python3 -c "
import json, os, time
p = 'data/workers.json'
try: d = json.load(open(p))
except Exception: d = {'agents': {}}
cf = sum(len(f) for _,_,f in os.walk('canvas'))
d['supervisor'] = {'ts': int(time.time()), 'canvas_files': cf,
  'note': 'supervisor tick'}
json.dump(d, open(p,'w'))
"
}

case "${1:-one}" in
  one) tick; echo "tick ok";;
  daemon)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then echo "loop already running pid $(cat $PIDFILE)"; exit 0; fi
    nohup bash -c 'while true; do bash bin/loop.sh one >/dev/null 2>&1; sleep 15; done' >/dev/null 2>&1 &
    echo $! > "$PIDFILE"; echo "loop daemon pid $!";;
  stop)
    [ -f "$PIDFILE" ] && kill "$(cat $PIDFILE)" 2>/dev/null && rm -f "$PIDFILE" && echo stopped || echo "not running";;
esac
