#!/bin/bash
# Watchdog: alarms on true silence, tolerates parked (finished) legs.
# Usage: watchdog.sh [max_min_beat, default 35] [max_min_end, default 240]
# - latest activity is start/beat and stale > max_min_beat -> WAKEUP (rc 3)
# - latest is end and older than max_min_end -> WAKEUP (nothing scheduled)
# - otherwise OK. Spends $0 (no model calls).
MAX_MIN="${1:-35}"
END_MAX="${2:-240}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
HB="$DIR/log/heartbeat.jsonl"
if [ ! -s "$HB" ]; then echo "WAKEUP: no heartbeat ever recorded"; exit 3; fi
timeout 20 python3 - "$HB" "$MAX_MIN" "$END_MAX" <<'PY'
import json, sys, time, calendar
hb, maxb, maxe = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
now = time.time()
latest = None  # (ts, event, who)
for line in open(hb):
    line = line.strip()
    if not line:
        continue
    try:
        r = json.loads(line)
        ts = calendar.timegm(time.strptime(r["ts"], "%Y-%m-%dT%H:%M:%SZ"))
    except (ValueError, KeyError):
        continue
    if latest is None or ts >= latest[0]:
        latest = (ts, r.get("event", "beat"), r.get("who", "?"))
if latest is None:
    print("WAKEUP: heartbeat file has no parseable lines")
    sys.exit(3)
age = (now - latest[0]) / 60
ev, who = latest[1], latest[2]
if ev == "end" and age <= maxe:
    print("watchdog OK (parked: %s finished %.1fm ago)" % (who, age))
    sys.exit(0)
if age > (maxe if ev == "end" else maxb):
    print("WAKEUP: last heartbeat %s (%s, %.1fm ago, limits beat=%s end=%s)"
          % (who, ev, age, maxb, maxe))
    sys.exit(3)
print("watchdog OK (%s %s %.1fm ago)" % (who, ev, age))
PY
