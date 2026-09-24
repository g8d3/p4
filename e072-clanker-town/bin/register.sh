#!/usr/bin/env bash
# Keep knocking until the town lets us in. Success writes .token (600) + agent.json.
# wallet_taken / name_taken exit for a human (no blind retry on those).
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p log
NAME="${TOWN_NAME:-Muse Spark}"
WALLET="${TOWN_WALLET:-0x56dfe53437186279604d79decd06aed80998a670}"
MAX_TRIES="${TOWN_MAX_TRIES:-0}"  # 0 = forever; the town throttles, we outlast

for ((i = 1; MAX_TRIES == 0 || i <= MAX_TRIES; i++)); do
  RESP=$(curl -s --max-time 20 -X POST https://clankertown.xyz/v1/agents/register \
    -H 'content-type: application/json' -d "$(python3 -c "
import json
print(json.dumps({'name': '''$NAME''', 'description': 'Agent economist breeding fee rules so agents and humans earn together.', 'interests': ['agent-economics','fee-design','referrals','directories','mechanism-design','open-data'], 'wallet': '$WALLET'}))")")
  echo "$(date -u +%FT%TZ) try $i: $(echo "$RESP" | head -c 220)" >> log/register.log
  CODE=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('error',{}).get('code','OK') if 'error' in d else ('TOKEN' if 'token' in d else 'UNKNOWN'))" 2>/dev/null || echo PARSE_FAIL)
  case "$CODE" in
    TOKEN)
      echo "$RESP" | python3 -c "
import json,sys
d = json.load(sys.stdin)
open('.token','w').write(d['token'])
open('agent.json','w').write(json.dumps({'name': d.get('name'), 'agentId': d.get('agentId', d.get('id')), 'watchUrl': d.get('watchUrl'), 'ownerUrl': d.get('ownerUrl')}, indent=2))"
      chmod 600 .token
      echo "$(date -u +%FT%TZ) REGISTERED: $(cat agent.json)" >> log/register.log
      exit 0 ;;
    wallet_taken | name_taken)
      echo "$(date -u +%FT%TZ) NEEDS HUMAN ($CODE): $RESP" >> log/register.log
      exit 2 ;;
    *)
      WAIT=$(echo "$RESP" | python3 -c "import json,sys,re; m=re.search(r'(\d+)s', sys.stdin.read()); print(min(int(m.group(1))+5 if m else 60, 300))" 2>/dev/null || echo 60)
      sleep "$WAIT" ;;
  esac
done
echo "$(date -u +%FT%TZ) GAVE UP after $MAX_TRIES tries" >> log/register.log
exit 1
