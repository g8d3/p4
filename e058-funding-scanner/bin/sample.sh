#!/usr/bin/env bash
# e058 sampler: capture funding snapshot -> load into SQLite.
# Cron: */15 * * * * .../bin/sample.sh >> .../sample.log 2>&1
# Writes: data/ (ignored cache), data.db (ignored, rebuilt by loader).
set -uo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
export E058_DATA="$DIR/data"
export E058_DB="$DIR/data.db"
mkdir -p "$E058_DATA"
[ "${SKIP_JITTER:-0}" = "1" ] || sleep $((RANDOM % 150))
echo "== sample $(date -u +%Y%m%dT%H%M%SZ) =="
"$DIR/bin/capture.sh" cron
python3 "$DIR/bin/load.py"
# conclusions-only alert (deduped inside alert.py) + fleet heartbeat; never fail the sample
python3 "$DIR/bin/alert.py" --no-endpoint --threshold-bps 50 --sink ntfy >> "$DIR/sample.log" 2>&1 || true
python3 /home/vuos/code/p4/e062-agent-ops/bin/ops.py beat e058 ok "cron sample" >> "$DIR/sample.log" 2>&1 || true
echo "sample OK"
