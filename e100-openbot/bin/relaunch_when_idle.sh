#!/bin/bash
# Relaunch OpenBot only if its window (CDP page) is gone, after in-flight turns finish (max ~10 min).
# Usage: relaunch_when_idle.sh [cmd-to-run-after]
D="$(cd "$(dirname "$0")/.." && pwd)"; DB="$HOME/.config/OpenBot/openbot.db"
haspage(){ curl -s 127.0.0.1:9222/json/list | grep -q "\"type\": \"page\""; }
if haspage; then echo "window ok, nothing to do"; else
  for i in $(seq 1 120); do
    n=$(sqlite3 "file:$DB?mode=ro" "select count(*) from projection_turns where status=\"running\" and started_at > datetime(\"now\",\"-1 hour\")" 2>/dev/null || echo 0)
    [ "$n" = "0" ] && break; sleep 5; done
  echo "$(date "+%F %T %z") relaunching OpenBot (window gone, running=$n)" >> "$D/coco/dispatcher.log"
  bash "$D/bin/launch.sh"; for i in $(seq 1 60); do haspage && break; sleep 2; done; sleep 10
fi
[ -n "$1" ] && bash -c "$1"
