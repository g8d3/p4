#!/bin/bash
# restart_with_wakeup.sh <my-session-id> <message-file> [delay_s=75] [cwd]
# Reinicio de sessiond que NO te deja colgado:
#  1) agenda un timer DESATADO del user manager (sobrevive al restart, no es
#     un sleep de esta sesion) que te manda <message-file> al volver,
#  2) reinicia pi-web-sessiond.
# Uso: echo "verifica X y continua" > /home/vuos/code/p4/e097-night-worker/msg.txt
#      bash /home/vuos/code/p4/e097-night-worker/restart_with_wakeup.sh <MI_SID> /home/vuos/code/p4/e097-night-worker/msg.txt
set -u
SID="${1:?mi session id}"; FILE="${2:?fichero con el mensaje}"; DELAY="${3:-75}"
CWD="${4:-/home/vuos/code/p4}"
[ -f "$FILE" ] || { echo "no existe $FILE"; exit 1; }
UNIT="pi-wakeup-$(date +%s)"
systemd-run --user --quiet --unit="$UNIT" --on-active="${DELAY}s" \
  /bin/bash /home/vuos/code/p4/e097-night-worker/send_prompt.sh "$SID" "$FILE" "$CWD" || exit 1
echo "wakeup agendado: $UNIT en ${DELAY}s -> $SID"
systemctl --user restart pi-web-sessiond
echo "restart lanzado"
