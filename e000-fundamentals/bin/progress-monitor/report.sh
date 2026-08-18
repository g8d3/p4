#!/usr/bin/env bash
# report.sh — heartbeat reporter for AGENTS.
# Every agent calls this at each milestone AND before/after long commands so the
# progress monitor can verify liveness and measure pace.
#
# Usage: report.sh <agent-id> "<step / what-I'm-doing-now>"
#   e.g. report.sh ag-01-video "step 2/5: researching TTS providers (web)"
# Extra (optional): report.sh <agent> "<step>" --data '{"n":3}'
#
# Writes one JSONL line per event. Cheap, idempotent, append-only.

source "$(dirname "$0")/lib.sh"

agent="$1"
msg="${2:-progress}"
KEY="$3"   # optional --data payload ignored for now, reserved

mkdir -p "$PROG_DIR"
echo "{\"ts\":\"$(ts)\",\"epoch\":$(now_epoch),\"agent\":\"$agent\",\"step\":\"$msg\"}" >> "$PROG_DIR/$agent.jsonl"

# also expose the agent id for the monitor's conventional output-dir discovery
echo "$agent" > "$PROG_DIR/last-agent"