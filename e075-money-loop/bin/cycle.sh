#!/usr/bin/env bash
# Daemon driver for the never-stopping cycle. Single-instance guarded.
# v0: runs bin/loop.sh every 30 min. Does NOT place orders (no executor exists).
# Cron is PAUSED repo-wide — this daemon is the approved alternative once the
# user says RUN. Until then, run bin/loop.sh manually.
cd "$(dirname "$0")/.."
LOCK=log/cycle.lock
if [ -f "$LOCK" ] && kill -0 "$(cat $LOCK)" 2>/dev/null; then
  echo "cycle already running (pid $(cat $LOCK)). Refusing a second driver."
  exit 1
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT
while true; do
  if [ ! -f STOP ]; then
    E075_ACTOR=daemon bash bin/loop.sh || echo "$(date -u +%FT%TZ) loop failed" >> log/loop.log
  fi
  sleep 1800
done
