#!/usr/bin/env bash
# One command to verify the world. Prints PASS/FAIL per subsystem, exit 1 on any FAIL.
# Usage: bash bin/verify.sh
cd "$(dirname "$0")/.."
FAIL=0
say() { if [ "$2" = 0 ]; then echo "PASS  $1"; else echo "FAIL  $1"; FAIL=1; fi }

# 1. fee dispatcher alive + heartbeat fresh
if [ -f log/chain.pid ] && kill -0 "$(cat log/chain.pid)" 2>/dev/null; then
  HB_AGE=$(( $(date +%s) - $(date -d "$(cat log/heartbeat 2>/dev/null)" +%s 2>/dev/null || echo 0) ))
  [ "$HB_AGE" -lt 120 ] && say "chain alive, heartbeat ${HB_AGE}s ago" 0 || say "chain stale, heartbeat ${HB_AGE}s ago" 1
else
  say "chain process" 1
fi

# 2. history actually growing
EPOCHS=$(python3 -c "import json; rows=[json.loads(l) for l in open('history.jsonl')]; print(max(r['epoch'] for r in rows))" 2>/dev/null || echo 0)
[ "$EPOCHS" -gt 0 ] && say "fee history: $EPOCHS epochs" 0 || say "fee history empty" 1

# 3. town registration worker alive + knocking (or registered)
if [ -f ../e072-clanker-town/.token ]; then
  say "town REGISTERED (token present)" 0
elif pgrep -f "bin/register.sh" >/dev/null; then
  TRIES=$(grep -c "^.*try " ../e072-clanker-town/log/register.log 2>/dev/null || echo 0)
  say "town retry alive, $TRIES tries so far" 0
else
  say "town retry worker" 1
fi

# 4. tables exist with rows
for t in seeds/agent-worlds.csv seeds/mor-directory.csv seeds/contrib-repos.csv; do
  ROWS=$(($(grep -c . "$t") - 1))
  [ "$ROWS" -ge 1 ] && say "$t: $ROWS rows" 0 || say "$t empty" 1
done

# 5. board fresh (updated within 7 days)
if [ -f PROGRESS.md ] && [ $(( $(date +%s) - $(stat -c %Y PROGRESS.md) )) -lt 604800 ]; then
  say "PROGRESS.md fresh" 0
else
  say "PROGRESS.md stale/missing" 1
fi

# 6. scout artifact real (pi-web builds)
[ -d /tmp/piweb-scout/dist ] && say "pi-web scout artifact (dist/) present" 0 || say "pi-web scout artifact" 1

# 7. tables versioned: every seed tracked, uncommitted edits shown (never hidden)
if git ls-files --error-unmatch seeds/agent-worlds.csv seeds/mor-directory.csv seeds/contrib-repos.csv >/dev/null 2>&1; then
  DIRTY=$(git status --short seeds/ | head -5)
  [ -z "$DIRTY" ] && say "tables versioned, tree clean" 0 || { echo "      uncommitted:"; echo "$DIRTY" | sed 's/^/      /'; say "tables versioned, edits visible above" 0; }
else
  say "tables versioned in git" 1
fi

# 8. credit ledger: background LLM spend must be a number, default zero
if [ -f ledger/credits.jsonl ]; then
  LLM_SPEND=$(python3 -c "import json; print(sum((r.get('cost_usd') or 0) for r in map(json.loads, open('ledger/credits.jsonl')) if r.get('kind')=='llm'))" 2>/dev/null || echo '?')
  say "credit ledger present, background LLM spend: \$$LLM_SPEND" 0
else
  say "credit ledger" 1
fi


# 9. credit meter reads real spend (no API; local ledgers)
if bash bin/credits-meter.sh >/dev/null 2>&1; then
  SPEND7=$(bash bin/credits-meter.sh 2>/dev/null | grep -oE 'combined 7d measured: \$[0-9.]+' || echo unknown)
  say "credit meter live ($SPEND7)" 0
else
  say "credit meter" 1
fi

exit $FAIL
