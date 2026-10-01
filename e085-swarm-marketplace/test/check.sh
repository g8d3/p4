#!/bin/bash
# e085 v2 GATE — full escrow lifecycle against the live server, market left clean.
# publish temp swarm -> order -> deliver (seller) -> accept (buyer) -> review
# -> trial -> seller desk -> DELETE every temp row. Prints GATE GREEN or GATE RED.
set -u
cd "$(dirname "$0")/.."
PORT=$(python3 -c "import json,os; n=json.load(open('needs.json')); print(os.environ.get(n.get('port_env','E085_PORT'), n.get('port')))")
CURL="curl -sk --max-time 10"
BASE="https://127.0.0.1:$PORT"
$CURL -sf "$BASE/api/health" >/dev/null 2>&1 || BASE="http://127.0.0.1:$PORT"
TS=$(date +%s); SELLER="qa-seller-$TS"; BUYER="qa-buyer-$TS"; TRIER="qa-trier-$TS"; SWARM="qa-swarm-$TS"
AU="qa-auth-$TS"; AP="testpass123"; JAR="/tmp/e085-gate-jar-$TS"; AUID=""
PASS=0; FAIL=0; OID=""; TRIAL_OID=""
j() { python3 -c "import json,sys; print(json.load(sys.stdin)$1)"; }
ok() { PASS=$((PASS+1)); echo "ok: $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL: $1"; }
cleanup_rows() {
  [ -n "$AUID" ] && $CURL -s -X DELETE "$BASE/api/orders?id=$AUID" >/dev/null 2>&1 || true
  [ -n "$TRIAL_OID" ] && $CURL -s -X DELETE "$BASE/api/orders?id=$TRIAL_OID" >/dev/null 2>&1 || true
  [ -n "$OID" ] && $CURL -s -X DELETE "$BASE/api/orders?id=$OID" >/dev/null 2>&1 || true
  $CURL -s -X DELETE "$BASE/api/swarms?id=$SWARM" >/dev/null 2>&1 || true
  [ -n "$AU" ] && $CURL -s "$BASE/api/auth?handle=$AU&password=$AP" -X DELETE >/dev/null 2>&1 || true
  rm -f "$JAR" || true
}
trap cleanup_rows EXIT

H=$($CURL -sf "$BASE/api/health") || { echo "GATE RED: health unreachable at $BASE"; exit 1; }
echo "$H" | grep -q '"ok": true' && ok "health" || bad "health"
echo "$H" | grep -q 'e085-v2' && ok "build v2" || bad "build v2"
M=$($CURL -sf "$BASE/api/models") || M=""
echo "$M" | grep -q success_tip && ok "models (10-way)" || bad "models"

P=$($CURL -sf -X POST "$BASE/api/swarms" -H 'Content-Type: application/json' \
  -d "{\"id\":\"$SWARM\",\"name\":\"$SWARM\",\"by\":\"$SELLER\",\"desc\":\"temp qa swarm\",\"models\":[\"per_run\"],\"price\":{\"per_run\":7}}") || P=""
[ "$(echo "$P" | j "['id']" 2>/dev/null)" = "$SWARM" ] && ok "publish temp swarm" || bad "publish temp swarm: $P"
$CURL -sf "$BASE/api/swarms" | grep -q "$SWARM" && ok "listed" || bad "listed"

SELF=$($CURL -s -X POST "$BASE/api/orders" -H 'Content-Type: application/json' \
  -d "{\"swarm_id\":\"$SWARM\",\"model\":\"per_run\",\"qty\":1,\"buyer\":\"$SELLER\"}")
echo "$SELF" | grep -q "you cannot order your own swarm" && ok "self-order blocked" || bad "self-order blocked: $SELF"

O=$($CURL -sf -X POST "$BASE/api/orders" -H 'Content-Type: application/json' \
  -d "{\"swarm_id\":\"$SWARM\",\"model\":\"per_run\",\"qty\":1,\"buyer\":\"$BUYER\",\"brief\":\"qa order\"}") || O=""
OID=$(echo "$O" | j "['id']" 2>/dev/null || true)
[ -n "$OID" ] && ok "order $OID" || bad "order: $O"
echo "$O" | python3 -c "import json,sys; o=json.load(sys.stdin); sys.exit(0 if (o['gross']==7.0 and o['fee']==0.35 and o['net']==6.65) else 1)" 2>/dev/null \
  && ok "fee math 7.00/0.35/6.65" || bad "fee math: $O"

LOCKED=$($CURL -s -X POST "$BASE/api/accept" -H 'Content-Type: application/json' -d "{\"order_id\":\"$OID\",\"buyer\":\"$BUYER\"}")
echo "$LOCKED" | grep -q "nothing delivered yet" && ok "accept locked pre-delivery" || bad "accept lock: $LOCKED"
EMPTY=$($CURL -s -X POST "$BASE/api/deliver" -H 'Content-Type: application/json' -d "{\"order_id\":\"$OID\",\"by\":\"$SELLER\",\"text\":\"\",\"url\":\"\"}")
echo "$EMPTY" | grep -q "delivery needs" && ok "empty delivery rejected" || bad "empty delivery: $EMPTY"
D=$($CURL -s -X POST "$BASE/api/deliver" -H 'Content-Type: application/json' \
  -d "{\"order_id\":\"$OID\",\"by\":\"$SELLER\",\"text\":\"qa result done\",\"url\":\"https://example.com/qa-$TS\"}")
echo "$D" | grep -q delivered && ok "deliver as seller" || bad "deliver: $D"
WRONG=$($CURL -s -X POST "$BASE/api/accept" -H 'Content-Type: application/json' -d "{\"order_id\":\"$OID\",\"buyer\":\"intruder\"}")
echo "$WRONG" | grep -q "only the buyer accepts" && ok "accept buyer-only" || bad "accept buyer-only: $WRONG"
A=$($CURL -s -X POST "$BASE/api/accept" -H 'Content-Type: application/json' -d "{\"order_id\":\"$OID\",\"buyer\":\"$BUYER\"}")
echo "$A" | grep -q accepted && ok "accept as buyer" || bad "accept: $A"
RE=$($CURL -s -X POST "$BASE/api/reviews" -H 'Content-Type: application/json' -d "{\"order_id\":\"$OID\",\"stars\":5,\"text\":\"qa great\"}")
echo "$RE" | grep -q "qa great" && ok "review" || bad "review: $RE"
DUP=$($CURL -s -X POST "$BASE/api/reviews" -H 'Content-Type: application/json' -d "{\"order_id\":\"$OID\",\"stars\":5,\"text\":\"again\"}")
echo "$DUP" | grep -q "already reviewed" && ok "1-order-1-review" || bad "double review: $DUP"
$CURL -sf "$BASE/api/swarms" | python3 -c "import json,sys; s=[r for r in json.load(sys.stdin) if r['id']=='$SWARM'][0]; sys.exit(0 if s.get('n_reviews',0)>=1 and s.get('rating',0)==5.0 else 1)" \
  && ok "rating recomputed" || bad "rating recompute"

T=$($CURL -s -X POST "$BASE/api/trials" -H 'Content-Type: application/json' -d "{\"swarm_id\":\"$SWARM\",\"buyer\":\"$TRIER\"}")
TRIAL_OID=$(echo "$T" | python3 -c "import json,sys; print(json.load(sys.stdin).get('order',{}).get('id',''))" 2>/dev/null || true)
[ -n "$TRIAL_OID" ] && ok "trial $TRIAL_OID" || bad "trial: $T"
T2=$($CURL -s -X POST "$BASE/api/trials" -H 'Content-Type: application/json' -d "{\"swarm_id\":\"$SWARM\",\"buyer\":\"$TRIER\"}")
echo "$T2" | grep -q "already used" && ok "trial once per buyer" || bad "trial dup: $T2"
TSELF=$($CURL -s -X POST "$BASE/api/trials" -H 'Content-Type: application/json' -d "{\"swarm_id\":\"$SWARM\",\"buyer\":\"$SELLER\"}")
echo "$TSELF" | grep -q "your own swarm" && ok "self-trial blocked" || bad "self-trial: $TSELF"

S=$($CURL -sf "$BASE/api/seller?by=$SELLER") || S=""
echo "$S" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('owed',0)==6.65 and any(o['id']=='$OID' for o in d.get('orders',[])) else 1)" 2>/dev/null \
  && ok "seller desk owed 6.65" || bad "seller desk: $S"
$CURL -sf "$BASE/api/inbox?by=$SELLER" | grep -q "$OID" && ok "seller inbox" || bad "seller inbox"
$CURL -sf "$BASE/api/orders?buyer=$BUYER" | grep -q "$OID" && ok "buyer orders" || bad "buyer orders"
DISP=$($CURL -s -X POST "$BASE/api/disputes" -H 'Content-Type: application/json' -d "{\"order_id\":\"$OID\",\"buyer\":\"$BUYER\",\"reason\":\"late\"}")
echo "$DISP" | grep -q "order is accepted" && ok "dispute closed order rejected" || bad "dispute guard: $DISP"

# DELETE every temp row, then prove the market is clean.
$CURL -s -X DELETE "$BASE/api/orders?id=$TRIAL_OID" | grep -q '"ok": true' && ok "delete trial order" || bad "delete trial order"
$CURL -s -X DELETE "$BASE/api/orders?id=$OID" | grep -q '"ok": true' && ok "delete order" || bad "delete order"
$CURL -s -X DELETE "$BASE/api/swarms?id=$SWARM" | grep -q '"ok": true' && ok "delete temp swarm" || bad "delete swarm"
OID=""; TRIAL_OID=""; trap - EXIT
$CURL -sf "$BASE/api/swarms" | grep -q "$SWARM" && bad "temp swarm lingers" || ok "market clean (swarm gone)"
$CURL -sf "$BASE/api/orders" | grep -q "$TS" && bad "temp orders linger" || ok "market clean (orders gone)"
$CURL -sf "$BASE/api/reviews?swarm_id=$SWARM" | grep -q "qa great" && bad "temp review lingers" || ok "market clean (reviews gone)"

SU=$($CURL -s -c "$JAR" -X POST "$BASE/api/auth/signup" -H 'Content-Type: application/json' -d "{\"handle\":\"$AU\",\"password\":\"$AP\"}")
echo "$SU" | grep -q "$AU" && ok "auth signup" || bad "auth signup: $SU"
$CURL -s -X POST "$BASE/api/swarms" -H 'Content-Type: application/json' -d "{\"id\":\"$SWARM\",\"name\":\"$SWARM\",\"by\":\"qa-other-$TS\",\"models\":[\"per_run\"],\"price\":{\"per_run\":3}}" >/dev/null 2>&1 || true
$CURL -s -b "$JAR" "$BASE/api/me" | grep -q "$AU" && ok "auth session (/api/me)" || bad "auth session"
DUP=$($CURL -s -X POST "$BASE/api/auth/signup" -H 'Content-Type: application/json' -d "{\"handle\":\"$AU\",\"password\":\"$AP\"}")
echo "$DUP" | grep -q "taken" && ok "duplicate signup rejected" || bad "duplicate signup: $DUP"
WRONG=$($CURL -s -X POST "$BASE/api/auth/login" -H 'Content-Type: application/json' -d "{\"handle\":\"$AU\",\"password\":\"wrongpass\"}")
echo "$WRONG" | grep -q "wrong password" && ok "wrong password rejected" || bad "wrong password: $WRONG"
SHORT=$($CURL -s -X POST "$BASE/api/auth/signup" -H 'Content-Type: application/json' -d "{\"handle\":\"qa-short-$TS\",\"password\":\"123\"}")
echo "$SHORT" | grep -q "8+" && ok "short password rejected" || bad "short password: $SHORT"
SPOOF=$($CURL -s -b "$JAR" -X POST "$BASE/api/orders" -H 'Content-Type: application/json' -d "{\"swarm_id\":\"$SWARM\",\"model\":\"per_run\",\"qty\":1,\"buyer\":\"intruder\"}")
AUID=$(echo "$SPOOF" | j "['id']" 2>/dev/null || true)
echo "$SPOOF" | grep -q "\"buyer\": \"$AU\"" && ok "session buyer enforced (spoof blocked)" || bad "spoof guard: $SPOOF"
$CURL -s -X DELETE "$BASE/api/orders?id=$AUID" | grep -q '"ok": true' && ok "delete spoof order" || bad "delete spoof order"
AUID=""
$CURL -s -X DELETE "$BASE/api/swarms?id=$SWARM" | grep -q '"ok": true' && ok "delete re-published swarm" || bad "delete re-published swarm"
$CURL -s "$BASE/api/auth?handle=$AU&password=$AP" -X DELETE | grep -q '"ok": true' && ok "delete temp user" || bad "delete temp user"
$CURL -s -b "$JAR" "$BASE/api/me" | grep -q null && ok "session dead after delete" || bad "session lingers"
rm -f "$JAR"

python3 - <<'EOF' >/dev/null 2>&1 || JS_MISSING=1
import re
html = open('public/index.html').read()
m = re.findall(r'<script>(.*?)</script>', html, re.S)
open('/tmp/e085-gate.js', 'w').write(m[0])
EOF
if command -v node >/dev/null 2>&1 && [ -f /tmp/e085-gate.js ]; then
  node --check /tmp/e085-gate.js && ok "UI JS syntax" || bad "UI JS syntax"
else
  echo "skip: UI JS syntax (node unavailable)"
fi

echo "pass=$PASS fail=$FAIL"
[ "$FAIL" -eq 0 ] && echo "GATE GREEN" || { echo "GATE RED"; exit 1; }
