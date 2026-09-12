#!/bin/bash
# Timestamped Loris funding capture. Usage: loris_capture.sh <tag>
# Brief stealth run -> page JS fetches with ambient authority -> save bodies -> close.
set -u
TAG="${1:-manual}"
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT="${E058_DATA:-/tmp}/loris_cap_${TS}_${TAG}.json"
LOG="${E058_DATA:-/tmp}/loris_cap_${TS}_${TAG}.log"
SES="loris_cap"
{
echo "== $TS tag=$TAG =="
agent-browser open --session $SES --init-script /tmp/stealth.js
agent-browser network route "**/*" --abort --resource-type image,media,font --session $SES
agent-browser open "https://loris.tools/?exchanges=zo%2Caster%2Cbluefin%2Cbullet%2Cdecibel%2Cedgex%2Centropyio%2Cextended%2Cgrvt%2Chibachi%2Chotstuff%2Chyperliquid%2Ckinetiq%2Clighter%2Cnado%2Condo%2Cpacifica%2Cparadex%2Cparagon%2Cphoenix%2Cqfex%2Creya%2Crisex%2Ctradexyz%2Ctxflow%2Cvariational%2Cvest%2Cwoofipro&unit=APY" --session $SES
agent-browser wait --load networkidle --session $SES
sleep 110
ID=$(agent-browser network requests --filter "api.loris.tools/funding" --session $SES --json 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)['data']['requests']
oks=[r['requestId'] for r in d if r.get('status')==200]
print(oks[-1] if oks else '')")
echo "funding id: $ID"
if [ -n "$ID" ]; then
  agent-browser network request "$ID" --session $SES --json 2>/dev/null | python3 -c "
import json,sys
b=json.load(sys.stdin)['data'].get('responseBody','')
open('$OUT','w').write(b)
print('saved',len(b),'to $OUT')"
else
  echo "NO FUNDING CAPTURED"
fi
agent-browser close --all
} >>"$LOG" 2>&1
echo "done $OUT"
