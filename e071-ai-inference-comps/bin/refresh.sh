#!/usr/bin/env bash
# e071 blessed refresh. NEVER run pipeline steps standalone in prod.
# Two tiers (page always serves cached output/, never blocks on fetch):
#   refresh.sh fast  — prices/quotes only (DexScreener + CoinGecko, ~2-4 min)
#   refresh.sh full  — fast + GeckoTerminal history + RPC supply (~8-12 min)
# Recommended schedule (background, non-blocking):
#   */15 * * * *  /home/vuos/code/p4/e071-ai-inference-comps/bin/refresh.sh fast
#   7,19 * * * *  /home/vuos/code/p4/e071-ai-inference-comps/bin/refresh.sh full
# flock guarantees overlapping runs never interleave; writers publish
# atomically (tmp + rename) so readers never see half files.
cd "$(dirname "$0")/.." || exit 1
MODE="${1:-fast}"
exec 9> data/.refresh.lock
flock -n 9 || { echo "=== $(date -Is) skip: another refresh holds the lock" >> refresh.log; exit 0; }
echo "=== refresh($MODE) $(date -Is)" >> refresh.log
mkdir -p output data
cp /home/vuos/code/p4/e068-tablelib/tablelib/table.css output/tablelib.css 2>/dev/null || true
cp /home/vuos/code/p4/e068-tablelib/tablelib/table.js output/tablelib.js 2>/dev/null || true
export E071_MODE="$MODE"
timeout 900 python3 bin/fetch.py >> refresh.log 2>&1
timeout 180 python3 bin/comps.py >> refresh.log 2>&1
timeout 60 python3 bin/sources.py >> refresh.log 2>&1
git log -1 --format=%h -- bin universe.json 2>/dev/null > output/.commit || echo dev > output/.commit
python3 -c "import json,time,os; print(json.dumps({'track':'e071','mode':os.environ.get('E071_MODE','fast'),'commit':open('output/.commit').read().strip(),'date':time.strftime('%Y-%m-%d %H:%M')}))" > output/.version.tmp && mv output/.version.tmp output/version.json 2>/dev/null
rm -f output/.commit
timeout 60 python3 bin/inject.py >> refresh.log 2>&1
echo "=== done($MODE) $(date -Is) rc=$?" >> refresh.log
