#!/bin/bash
# Detached: restart the session daemon, then wake the night-worker session with a prompt.
# Launched by a systemd --user timer (survives the restart; not a sleep owned by the session).
SID="${1:?session id}"; FILE="${2:?message file}"; WAIT="${3:-25}"
CWD="${4:-/home/vuos/code/p4}"
systemctl --user restart pi-web-sessiond
sleep "$WAIT"
for i in 1 2 3 4 5 6 7 8; do
  bash /home/vuos/code/p4/e097-night-worker/send_prompt.sh "$SID" "$FILE" "$CWD" && exit 0
  sleep 15
done
exit 1
