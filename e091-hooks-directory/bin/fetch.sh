#!/bin/bash
# Paginated broad-query fetcher. Simple queries, deep samples (60 tweets each).
# Requires $TWITTERAPIS_API_KEY. Raw payloads -> evidence/. Then rebuild
# data/sources.json + data/signals.json (see AGENTS.md) and bump verified dates.
set -e
cd "$(dirname "$0")/.."
: "${TWITTERAPIS_API_KEY:?set TWITTERAPIS_API_KEY first}"
mkdir -p evidence
fetch60() {
  local label="$1" query="$2" out="evidence/${label}.json" cursor="" pages=0 total=0
  echo "--- $label ($query) ---"
  rm -f "$out.tmp"
  while [ "$total" -lt 60 ] && [ "$pages" -lt 4 ]; do
    local url="https://api.twitterapis.com/twitter/tweet/advanced_search?query=${query}&queryType=Latest&count=20"
    [ -n "$cursor" ] && url="${url}&cursor=${cursor}"
    resp=$(curl -s -m 30 "$url" -H "X-API-Key: $TWITTERAPIS_API_KEY")
    echo "$resp" > "/tmp/e091page.json"
    python3 -c "
import json,time
try: u=json.load(open('data/usage.json'))
except Exception: u={'calls':[]}
u['calls'].append({'ts':int(time.time()),'endpoint':'tweet/advanced_search','detail':'$label page $((pages+1))','cost':0.0008})
json.dump(u,open('data/usage.json','w'),indent=1)
"
    new=$(python3 -c "
import json
d=json.load(open('/tmp/e091page.json'))
prev=json.load(open('$out.tmp')) if __import__('os').path.exists('$out.tmp') else []
seen=set(x['id'] for x in prev)
n=0
for t in d.get('tweets',[]):
  if t['id'] not in seen: prev.append(t); seen.add(t['id']); n+=1
json.dump(prev,open('$out.tmp','w'))
print(len(prev))
print('CURSOR:'+(d.get('next_cursor') or ''), file=__import__('sys').stderr)
print('MORE:'+str(d.get('has_more')), file=__import__('sys').stderr)
")
    total="$new"
    cursor=$(python3 -c "
import json;d=json.load(open('/tmp/e091page.json'));print(d.get('next_cursor') or '')" | python3 -c "import sys,urllib.parse;print(urllib.parse.quote(sys.stdin.read().strip(),safe=''))")
    more=$(python3 -c "import json;d=json.load(open('/tmp/e091page.json'));print(d.get('has_more'))")
    pages=$((pages+1))
    echo "page $pages: total $total, has_more=$more"
    [ "$more" != "True" ] && break
  done
  python3 -c "
import json
ts=json.load(open('$out.tmp'))
json.dump({'query':'$query','queryType':'Latest','captured':'$(date -u +%F)','count':len(ts),'tweets':ts},open('$out','w'),indent=1)
print('saved $out:',len(ts),'tweets')"
  rm -f "$out.tmp"
}
fetch60 "solana-hooks-60" "Solana%20hooks"
fetch60 "uniswap-hooks-60" "Uniswap%20v4%20hooks"
fetch60 "hook-launchpad-60" "hook%20launchpad"
fetch60 "infinity-hooks-60" "Infinity%20hooks"
echo "Review evidence/, then rebuild data/sources.json + data/signals.json."
python3 bin/import_evidence.py
