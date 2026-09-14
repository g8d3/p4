#!/bin/bash
# e062 health monitor (cron, every 15 min). Silent on success (conclusions-only
# contract); on failure logs + beats ops bus so errors are never silent. T0 free.
LOG="$HOME/code/p4/e062-agent-ops/server.log"
OPS="$HOME/code/p4/e062-agent-ops/bin/ops.py"
code=$(curl -sk -m 10 -o /dev/null -w "%{http_code}" https://127.0.0.1:8322/api/board 2>/dev/null) || code="000"
if [ "$code" = "200" ]; then
  exit 0
fi
# restart-race guard: one retry after 10s before crying blocked (2026-09-12:
# 15:00 healthcheck raced a server restart -> false blocked beat)
sleep 10
code=$(curl -sk -m 10 -o /dev/null -w "%{http_code}" https://127.0.0.1:8322/api/board 2>/dev/null) || code="000"
if [ "$code" = "200" ]; then
  exit 0
fi
echo "$(date -u '+%F %T') e062 HEALTH FAIL (code=$code) — self-heal: one restart attempt" >> "$LOG"
# SELF-HEAL (run #75, ships banked run-#74 idea): e059's static server died
# 19:41 and sat dark ~5h until a runner leg revived it. A dead port must heal
# in 15 min with no human. ONE restart attempt (same command as @reboot),
# then re-probe before crying blocked.
# Kill by PORT, never pkill app.py: e058/e060/e063 run the same argv.
DIR="$HOME/code/p4/e062-agent-ops"
PID=$(ss -tlnp 2>/dev/null | grep -E ':8322\s' | grep -oP 'pid=\K[0-9]+' | head -n 1)
if [ -n "$PID" ]; then kill "$PID" 2>/dev/null || true; sleep 2; kill -9 "$PID" 2>/dev/null || true; sleep 1; fi
cd "$DIR" && nohup python3 app.py >> "$LOG" 2>&1 &
sleep 12
code=$(curl -sk -m 10 -o /dev/null -w "%{http_code}" https://127.0.0.1:8322/api/board 2>/dev/null) || code="000"
if [ "$code" = "200" ]; then
  echo "$(date -u '+%F %T') e062 SELF-HEALED (restart ok)" >> "$LOG"
  python3 "$OPS" beat e062 ok "Your board fixed itself — back online with no taps | tech: self-heal: :8322 restarted, /api/board 200, score taps-to-task=0 (no owner action)" 2>>"$LOG" || true
  exit 0
fi
echo "$(date -u '+%F %T') e062 HEALTH FAIL after self-heal (code=$code)" >> "$LOG"
python3 "$OPS" beat e062 blocked "Fleet board is down, retrying | tech: health monitor: :8322 /api/board non-200 ($code) after 1 self-heal restart"
exit 1
