#!/bin/bash
# send_prompt.sh <session-id> <message-file> [cwd]
# POST con reintentos: entrega un mensaje a una sesion pi-web.
# Pensado para timers desatados (sobrevive a reinicios del daemon).
set -u
SID="${1:?sid}"; FILE="${2:?message file}"; CWD="${3:-/home/vuos/code/p4}"
[ -f "$FILE" ] || exit 1
for i in 1 2 3 4 5 6; do
  code=$(python3 - "$SID" "$FILE" "$CWD" <<'PY' 2>/dev/null
import json,sys,urllib.request
sid,path,cwd=sys.argv[1],sys.argv[2],sys.argv[3]
body=json.dumps({"cwd":cwd,"text":open(path).read()}).encode()
req=urllib.request.Request(f"http://localhost:8504/api/sessions/{sid}/prompt",
  data=body,headers={"Content-Type":"application/json"},method="POST")
try:
  r=urllib.request.urlopen(req,timeout=20); print(r.status)
except Exception as e:
  print("000")
PY
)
  [ "$code" = "200" ] && exit 0
  sleep 20
done
exit 1
