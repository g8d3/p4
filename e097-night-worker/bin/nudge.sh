#!/bin/bash
# Auto-despertador: si la cola del night worker tiene items abiertos, inyecta un
# nudge para que continúe. Guardarraíles: STOP, cooldown, sin items = silencio.
# All paths come from needs.json (same dir pattern as e082 bin/loop.sh).
HERE="$(cd "$(dirname "$0")/.." && pwd)"
NJ="$HERE/needs.json"
get(){ python3 -c "import json;print(json.load(open('$NJ')).get('$1',''))"; }
STATE=$(get state_file);      STOP=$(get stop_file)
TOUCH=$(get touch_file);      SIDFILE=$(get sid_file)
LOG=$(get log_file);          CWD=$(get cwd)
COOLDOWN_S=$(get cooldown_s); ROTATE_PCT=$(get rotate_ctx_pct)
BRIEF=$(get worker_brief)
STALL_STATE_S=$(get stall_state_s); STALL_SESS_S=$(get stall_sess_s)
SESSDIR=/home/vuos/.pi/agent/sessions/--home-vuos-code-p4--
log(){ echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }
[ -f "$STOP" ] && exit 0
[ -f "$STATE" ] || exit 0
[ -f "$SIDFILE" ] || exit 0
SID=$(cat "$SIDFILE")
# 0) guardián: si el modelo encadena errores, cambia a fallback y sigue
bash "$HERE/bin/worker_guard.sh" >> "$HERE/data/guard.log" 2>&1
# Rotación por presión de contexto REAL (API status), no por tamaño de fichero
pct=$(curl -s -m 12 "http://localhost:8504/api/sessions/$SID/status?cwd=$CWD" \
  | python3 -c "import json,sys;
print(json.load(sys.stdin).get('contextUsage',{}).get('percent',0))" 2>/dev/null || echo 0)
if python3 -c "import sys; sys.exit(0 if float('${pct:-0}') > $ROTATE_PCT else 1)"; then
  bash "$HERE/bin/rotate_worker.sh" >> "$HERE/data/rotate.log" 2>&1
  exit 0
fi
# 0b) stall: hay trabajo pero NI state NI sesion avanzan -> la conexion se
# rompio a mitad de camino sin dejar error contable (el caso que antes no
# tenia salvacion). Rotar a sesion fresca en vez de nudgear un cadaver.
transcript=$(ls -t "$SESSDIR"/*"$SID".jsonl 2>/dev/null | grep -v activity | head -1)
now=$(date +%s)
state_age=$(( now - $(stat -c %Y "$STATE") ))
if [ "$state_age" -gt "$STALL_STATE_S" ] && [ -n "$transcript" ]; then
  sess_age=$(( now - $(stat -c %Y "$transcript") ))
  if [ "$sess_age" -gt "$STALL_SESS_S" ]; then
    log "stall: state quieto ${state_age}s + sesion quieta ${sess_age}s -> roto"
    bash "$HERE/bin/rotate_worker.sh" >> "$LOG" 2>&1 && exit 0
    log "stall: rotate fallo, sigo con nudge normal"
  fi
fi
# ¿queda trabajo accionable? No lo es: (humano)=gusto/decisión solo-humana,
# (espera-llave)=falta una key o registro que solo el humano puede crear
# (las keys viven en /home/vuos/.secrets/.env; si la key ya esta ahi, el item
# vuelve a ser accionable: quita la etiqueta y sigue). Todo lo demas esta
# autorizado por politica permanente: publicar, comprar dominios, borrar,
# registrar, gastar hasta el techo. Sin pedir permiso nunca.
grep "^- \[ \]" "$STATE" 2>/dev/null | grep -qv "(humano)" | grep -qv "(espera-llave)" || exit 0
if [ -f "$TOUCH" ]; then
  age=$(( $(date +%s) - $(stat -c %Y "$TOUCH") ))
  [ "$age" -lt "$COOLDOWN_S" ] && exit 0
fi
touch "$TOUCH"
# prompt con reintento: antes un fallo de red aqui era silencio total
attempt=1
while [ "$attempt" -le 3 ]; do
  code=$(curl -s -m 20 -o /dev/null -w "%{http_code}" -X POST "http://localhost:8504/api/sessions/$SID/prompt" \
    -H "Content-Type: application/json" \
    -d "{\"cwd\":\"$CWD\",\"text\":\"[nudge] Sin mensaje humano: revisa $STATE y $BRIEF, toma el siguiente item accionable (o inventa uno que acerque a dinero y anotalo), ejecutalo y marca [x]. No pares mientras haya trabajo. Si de verdad no queda nada, responde IDLE.\"}" 2>/dev/null) || code="000"
  if [ "$code" = "200" ]; then log "nudge ok a $SID (intento $attempt)"; break; fi
  log "nudge fallo http=$code a $SID (intento $attempt/3)"
  sleep $((attempt * 15))
  attempt=$((attempt + 1))
done
echo
