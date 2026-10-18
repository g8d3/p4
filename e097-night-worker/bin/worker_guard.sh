#!/bin/bash
# Guardián del worker: si el modelo actual encadena errores, cambia a un
# fallback y le dice que siga. Sin intervención humana.
# Uso: worker_guard.sh [--dry]
set -u
DRY=0; [ "${1:-}" = "--dry" ] && DRY=1
CWD=/home/vuos/code/p4
SIDFILE=/home/vuos/code/p4/e097-night-worker/worker.sid
LOG=/home/vuos/code/p4/e097-night-worker/guard.log
API=http://localhost:8504/api/sessions
# Cadena de fallback (probada en vivo): barato -> estable -> muy estable.
# Si la cadena se agota, el ultimo recurso es rotar a sesion fresca (limpia
# errores pegajosos del proveedor del lado del daemon).
FALLBACKS=("mimo-v2.5" "deepseek-v4.1-flash" "deepseek-v4-flash")
THRESHOLD=2   # errores consecutivos que disparan el cambio

log(){ echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }

# post_with_retry <url> <json> <etiqueta>: reintenta 3 veces con backoff.
# Cubre la rotura de conexion a mitad de camino: antes el fallo se tragaba
# en silencio (curl ... >/dev/null) y nada salvaba el turno.
post_with_retry(){
  local url="$1" payload="$2" tag="$3" attempt=1 out code
  while [ "$attempt" -le 3 ]; do
    out=$(curl -s -m 25 -o /dev/null -w "%{http_code}" -X POST "$url" \
      -H "Content-Type: application/json" -d "$payload" 2>/dev/null) || out="000"
    if [ "$out" = "200" ]; then
      log "$tag ok (intento $attempt)"
      return 0
    fi
    log "$tag fallo http=$out (intento $attempt/3)"
    sleep $((attempt * 10))
    attempt=$((attempt + 1))
  done
  log "$tag FALLO definitivo tras 3 intentos"
  return 1
}

SID=$(cat "$SIDFILE" 2>/dev/null) || exit 0
[ -n "$SID" ] || exit 0

status=$(curl -s -m 15 "$API/$SID/status?cwd=$CWD") || exit 0
cur=$(echo "$status" | python3 -c "import json,sys; print(json.load(sys.stdin).get('model',{}).get('id',''))" 2>/dev/null)
[ -n "$cur" ] || exit 0

# errores consecutivos al final del transcript
consec=$(python3 - "$SID" <<'PY'
import json,sys,glob
sid=sys.argv[1]
fs=[x for x in glob.glob('/home/vuos/.pi/agent/sessions/--home-vuos-code-p4--/*%s*.jsonl'%sid) if 'activity' not in x]
if not fs: print(0); raise SystemExit
n=0
for l in reversed(open(fs[0]).read().splitlines()):
    try:
        m=(json.loads(l).get('message') or {})
        if m.get('role')!='assistant': continue
        if m.get('stopReason')=='error':
            # Auth errors (401/expired key) are env problems, not model problems:
            # churning fallbacks cannot fix them. Alert once, loudly, and stop.
            if 'authentication' in str(m.get('errorMessage','')).lower() or 'api_key' in str(m.get('message',{})):
                print('AUTH'); raise SystemExit
            n+=1
        else: break
    except SystemExit: raise
    except Exception: pass
print(n)
PY
)
if [ "$consec" = "AUTH" ]; then
  log "ALERTA: el proveedor rechaza la key (auth/api_key_expired). No es fallo del modelo: no roto modelos. Revisa /home/vuos/.secrets/.env y reinicia sessiond para propagar la key (systemctl --user restart pi-web-sessiond)."
  exit 0
fi
consec=${consec:-0}
if [ "$consec" -lt "$THRESHOLD" ]; then exit 0; fi

# elige el siguiente modelo distinto al actual; si no queda ninguno,
# rota a sesion fresca (los errores pegajosos del proveedor suelen morir ahi)
next=""
for f in "${FALLBACKS[@]}"; do [ "$f" != "$cur" ] && next="$f" && break; done
if [ -z "$next" ]; then
  log "cadena agotada (actual=$cur, errores=$consec) -> roto a sesion fresca"
  [ "$DRY" = "1" ] && { echo "DRY: rotaria sesion (cadena agotada)"; exit 0; }
  bash /home/vuos/code/p4/e097-night-worker/rotate_worker.sh >> "$LOG" 2>&1 || log "rotate fallo"
  exit 0
fi

log "errores consecutivos=$consec con $cur -> cambio a $next"
[ "$DRY" = "1" ] && { echo "DRY: cambiaría $cur -> $next (errores=$consec)"; exit 0; }

post_with_retry "$API/$SID/model" "{\"cwd\":\"$CWD\",\"provider\":\"opencode-go\",\"modelId\":\"$next\"}" "model->${next}" || exit 1
post_with_retry "$API/$SID/prompt" "{\"cwd\":\"$CWD\",\"text\":\"[guard] Cambio de modelo por errores del anterior ($cur -> $next). Revisa /home/vuos/code/p4/e097-night-worker/STATE.md y continua el trabajo; si el item estaba a medias, retomalo y dejalo terminado o anotado.\"}" "nudge-guard" || exit 1
log "guardia completo: $cur -> $next"
