#!/bin/bash
# e079 thinker: chained intelligent legs — finish one cycle, start the next
# immediately, up to MAX_LEGS per invocation. Cron (*/5) is only the
# supervisor that restarts the chain if it ever dies. Lane-busy ticks exit
# at ~$0, so tight cron costs nothing idle.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")
MAX_LEGS="${MAX_LEGS:-8}"
# cron has a starved PATH (nvm bins missing) — earlier cron legs died with
# exit 127 on `pi`. Resolve once, fail LOUD if absent (never silent).
export PATH="$HOME/.nvm/versions/node/v24.16.0/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
PI_BIN="$(command -v pi || echo /home/vuos/.nvm/versions/node/v24.16.0/bin/pi)"
[ -x "$PI_BIN" ] || { echo "FATAL: pi not found (PATH=$PATH)"; exit 127; }

[ -f "$DIR/data/STOP" ] && { echo "STOP set, thinker stands down"; exit 0; }
[ -f "$DIR/data/THINKER" ] || { echo "thinker not armed, exit"; exit 0; }

n=0
while [ "$n" -lt "$MAX_LEGS" ]; do
  [ -f "$DIR/data/STOP" ] && { echo "STOP appeared, chain ends"; break; }

  GOAL=$(curl -s --max-time 10 127.0.0.1:$PORT/api/goals | python3 -c "import json,sys; g=json.load(sys.stdin); q=[x for x in g if x.get('status')=='queued']; print(q[0]['goal'] if q else '')" 2>/dev/null)
  [ -z "$GOAL" ] && { echo "queue empty, chain ends after $n leg(s)"; break; }

  STARTED=$(curl -s --max-time 10 -X POST 127.0.0.1:$PORT/api/cycle/start \
    -H 'Content-Type: application/json' -d "{\"goal\":\"$GOAL\"}")
  ID=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('id',''))" <<<"$STARTED" 2>/dev/null)
  if [ -z "$ID" ]; then echo "lane busy, chain ends: $STARTED"; break; fi
  # claim the goal in the queue so the next leg never re-picks it
  CYCLE="$ID" GOAL="$GOAL" GFILE="$DIR/data/goals.jsonl" python3 -c 'import json,os; p=os.environ; rows=[json.loads(l) for l in open(p["GFILE"]) if l.strip()];
for r in rows:
 if r.get("status")=="queued" and r.get("goal")==p["GOAL"]: r["status"]="active"; r["cycle"]=p["CYCLE"]; break
open(p["GFILE"],"w").write("".join(json.dumps(r)+"\n" for r in rows))' 2>/dev/null || true

  n=$((n + 1))
  echo "=== leg $n/$MAX_LEGS: $ID: $GOAL ==="

  mkdir -p "$DIR/public/legs"
  WHY=$(curl -s --max-time 10 127.0.0.1:$PORT/api/goals | python3 -c "import json,sys; g=json.load(sys.stdin); m=[x for x in g if x.get('cycle')=='$ID']; print((m[0].get('why') or '') if m else '')" 2>/dev/null)
  CYCLE="$ID" GOAL="$GOAL" WHY="$WHY" LEGDIR="$DIR/public/legs" python3 -c 'import json,os,time; d=os.environ; json.dump({"cycle":d["CYCLE"],"goal":d["GOAL"],"why":d["WHY"],"state":"working","phase":"starting","note":"leg started","started_ts":int(time.time()),"updated_ts":int(time.time())}, open(d["LEGDIR"]+"/"+d["CYCLE"]+".status.json","w"))'
  echo "watch live: /live.html?cycle=$ID"

  "$PI_BIN" --print "You are an e079-agent-cycles leg working cycle $ID with goal: $GOAL.
Repo: $DIR. Your work is watched LIVE on /live.html?cycle=$ID, which renders
$DIR/public/legs/$ID.log (your stdout) and $DIR/public/legs/$ID.status.json.
Rules: smallest change earning a version bump; run test/check.sh; open the page
yourself in a browser; finish via POST /api/cycle/finish {id:$ID,notes}; metered endpoint is source of truth for cost (self-report retired); then exit. One goal only.
As you work, keep watchers informed: update the status json phase
(starting>plan>implement>verify>finish) with a short note of what you are doing
right now, and narrate briefly in stdout as you go." \
    > "$DIR/public/legs/$ID.log" 2>&1
  EC=$?
  LEGF="$DIR/public/legs/$ID.status.json"
  [ -f "$LEGF" ] && python3 -c 'import json,time,sys; p=sys.argv[1]; d=json.load(open(p)); d.update({"state":"done","phase":"finish","updated_ts":int(time.time())}); json.dump(d,open(p,"w"))' "$LEGF"

  echo "=== leg $n done (exit $EC) ==="
done
echo "chain over: ran $n leg(s)"
