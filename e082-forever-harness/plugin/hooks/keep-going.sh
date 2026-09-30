#!/bin/bash
# keep-going hook: policy loader, tick wrapper, verify gate, compact helper.
# Usage: keep-going.sh load-policy|tick|verify|compact|start|stop
# Server URL from $FOREVER_HARNESS_URL, never hardcoded.
# Write calls need the owner token in $FOREVER_HARNESS_TOKEN
# (owner copies TOKEN from the server's needs.json).
BASE="${FOREVER_HARNESS_URL:-http://127.0.0.1:8342}"
AUTH=(); [ -n "${FOREVER_HARNESS_TOKEN:-}" ] && AUTH=(-H "Authorization: Bearer $FOREVER_HARNESS_TOKEN")
case "${1:-load-policy}" in
  load-policy) curl -s "$BASE/api/policy"; echo;;
  status) curl -s "$BASE/api/status"; echo;;
  start) curl -s -X POST "$BASE/api/control/start" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{}'; echo;;
  stop) curl -s -X POST "$BASE/api/control/stop" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"reason\":\"hook stop ${2:-}\"}"; echo;;
  tick)
    curl -s -X POST "$BASE/api/control/tick" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"by\":\"hook-${2:-agent}\"}"; echo;;
  verify) curl -s -X POST "$BASE/api/verify"; echo;;
  compact) curl -s "$BASE/api/summary"; echo; curl -s "$BASE/api/checkpoints?limit=5"; echo;;
  *) echo "usage: $0 load-policy|status|start|stop|tick|verify|compact" >&2; exit 1;;
esac
