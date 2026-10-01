#!/bin/bash
# start e085 on port from needs.json (E085_PORT overrides, E085_TLS=0 = plain HTTP)
set -e
cd "$(dirname "$0")/.."
PORT=$(python3 -c "import json,os; n=json.load(open('needs.json')); print(os.environ.get(n.get('port_env','E085_PORT'), n.get('port')))")
python3 server/app.py >>server.log 2>&1 &
echo $! > /tmp/e085-serve.pid
echo "e085 on 0.0.0.0:$PORT (pid $(cat /tmp/e085-serve.pid), E085_TLS=${E085_TLS:-1})"
