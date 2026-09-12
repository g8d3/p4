#!/usr/bin/env bash
# e058 sampler: capture funding snapshot -> load into SQLite.
# Cron: */15 * * * * .../bin/sample.sh >> .../sample.log 2>&1
# Writes: data/ (ignored cache), data.db (ignored, rebuilt by loader).
set -uo pipefail
export PATH="/home/vuos/.nvm/versions/node/v24.16.0/bin:/usr/local/bin:/usr/bin:/bin"
# cron has no session env: load ntfy topic saved from owner shell (600-file, never logged)
[ -s "$HOME/.config/e058/ntfy_topic" ] && export NTFY_TOPIC="$(cat "$HOME/.config/e058/ntfy_topic")"
[ -s "$HOME/.config/e058/ntfy_server" ] && export NTFY_SERVER="$(cat "$HOME/.config/e058/ntfy_server")"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
export E058_DATA="$DIR/data"
export E058_DB="$DIR/data.db"
mkdir -p "$E058_DATA"
[ "${SKIP_JITTER:-0}" = "1" ] || sleep $((RANDOM % 150))
echo "== sample $(date -u +%Y%m%dT%H%M%SZ) =="
"$DIR/bin/capture.sh" cron
python3 "$DIR/bin/load.py"
# conclusions-only alert (deduped inside alert.py) + fleet heartbeat; never fail the sample
python3 "$DIR/bin/alert.py" --no-endpoint --sink ntfy >> "$DIR/sample.log" 2>&1 || true
python3 /home/vuos/code/p4/e062-agent-ops/bin/ops.py beat e058 ok "cron sample" >> "$DIR/sample.log" 2>&1 || true
echo "sample OK"
