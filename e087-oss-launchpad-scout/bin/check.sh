#!/usr/bin/env bash
# Gate: health + tokens roundtrip + zero-payout-when-zero-revenue + tab ids.
set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")"
BASE="http://127.0.0.1:$PORT"
FAIL=0
ok(){ echo "PASS: $1"; }
bad(){ echo "FAIL: $1"; FAIL=1; }

H="$(curl -sf "$BASE/api/health")" || { bad "health unreachable"; echo "GATE: RED"; exit 1; }
echo "$H" | grep -q '"ok"' && ok "health" || bad "health body: $H"

# tokens roundtrip
NAME="gate-$(date +%s)"
TRESP="$(curl -sf -X POST "$BASE/api/tokens" -H 'Content-Type: application/json' \
  -d "{\"name\":\"$NAME\",\"repos\":[\"https://github.com/example/gate-$NAME\"]}")"
echo "$TRESP" | grep -q "$NAME" && ok "tokens POST" || bad "tokens POST: $TRESP"
G="$(curl -sf "$BASE/api/tokens")"
echo "$G" | grep -q "$NAME" && ok "tokens GET roundtrip" || bad "tokens GET missing $NAME"

# zero-payout-when-zero-revenue: fresh repo must show earned=0/due=0
P="$(curl -sf "$BASE/api/projects")"
EARNED="$(python3 -c "
import json,urllib.request
d=json.load(urllib.request.urlopen('$BASE/api/projects'))
m={p['repo']:p for p in d['projects']}
r=m.get('https://github.com/example/gate-$NAME',{})
print(r.get('earned','MISSING'),r.get('due','MISSING'))")"
[ "$EARNED" = "0.0 0.0" ] && ok "zero-payout-when-zero-revenue ($EARNED)" || bad "zero-payout rule got: $EARNED"

# pay + refund roundtrip (documents guarantee handling)
PAY="$(curl -sf -X POST "$BASE/api/pay" -H 'Content-Type: application/json' \
  -d "{\"method\":\"fiat\",\"amount\":10,\"token\":\"$NAME\",\"repos\":[\"https://github.com/example/gate-$NAME\"]}")"
PID="$(python3 -c "import json;print(json.loads('$PAY'.replace(chr(10),' '))['payment']['id'])" 2>/dev/null || echo "")"
[ -n "$PID" ] && ok "pay stub ($PID)" || bad "pay: $PAY"
if [ -n "$PID" ]; then
  R="$(curl -sf -X POST "$BASE/api/refund" -H 'Content-Type: application/json' -d "{\"payment_id\":\"$PID\"}")"
  echo "$R" | grep -q '"refunded": *true' && ok "refund zeroes splits" || bad "refund: $R"
fi

# funding sample
F="$(curl -sf "$BASE/api/funding")"
echo "$F" | grep -q 'spreads' && ok "funding sample" || bad "funding: $F"

# every tab id present
for id in tab-launch tab-projects tab-game tab-funding tab-pay; do
  grep -q "id=\"$id\"" "$DIR/public/index.html" && ok "tab $id" || bad "tab $id missing"
done
grep -q "OSS placeholder (swap for reused OSS game)" "$DIR/public/index.html" \
  && ok "game placeholder label" || bad "game placeholder label missing"

[ "$FAIL" -eq 0 ] && echo "GATE: GREEN" || echo "GATE: RED"
exit "$FAIL"
