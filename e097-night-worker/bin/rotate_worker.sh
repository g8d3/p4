#!/bin/bash
# Rotación de night worker: cierra el worker actual y abre uno fresco
# (contexto nuevo, mismo brief). STATE.md es el testigo; nada se pierde.
set -e
SIDFILE=/home/vuos/code/p4/e097-night-worker/worker.sid
HIST=/home/vuos/code/p4/e097-night-worker/worker.history
CWD=/home/vuos/code/p4
MODEL=deepseek-v4.1-flash
API=http://localhost:8504/api/sessions

old=$(cat "$SIDFILE" 2>/dev/null || echo "")
[ -n "$old" ] && echo "$(date -u +%FT%TZ) retired $old" >> "$HIST"

resp=$(curl -s -m 20 -X POST "$API" -H "Content-Type: application/json" \
  -d "{\"cwd\":\"$CWD\",\"startupToken\":\"night-worker\"}")
new=$(echo "$resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))")
[ -n "$new" ] || { echo "rotate: no session id"; exit 1; }

curl -s -m 20 -X POST "$API/$new/model" -H "Content-Type: application/json" \
  -d "{\"cwd\":\"$CWD\",\"provider\":\"opencode-go\",\"modelId\":\"$MODEL\"}" >/dev/null

echo "$new" > "$SIDFILE"
echo "$(date -u +%FT%TZ) started $new" >> "$HIST"

curl -s -m 25 -X POST "$API/$new/prompt" -H "Content-Type: application/json" \
  -d "{\"cwd\":\"$CWD\",\"text\":\"Eres el relevo del night worker anterior (contexto nuevo, mismo trabajo). Lee /home/vuos/code/p4/e097-night-worker/WORKER_BRIEF.md y /home/vuos/code/p4/e097-night-worker/STATE.md, toma el primer item accionable o inventa uno que acerque a dinero anotandolo en STATE.md, y trabaja en bucle sin parar. Deja el estado escrito tras cada item para el proximo relevo.\"}" >/dev/null

echo "rotated: $old -> $new"
