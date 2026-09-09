#!/bin/bash
# ci-watch v1 — poll gh pr checks for fleet PRs; on NEW failing check:
#   1. ntfy push to the user's phone (notify.sh)
#   2. POST a prompt into the e054 agent session (pi-web sessiond),
#      so the agent wakes up and fixes it without the user relaying.
# When every check of a PR passes again: clear state + recovery notice.
#
# Escape hatch: kill by PID file /tmp/ci-watch.pid; state in /tmp/ci-watch-<PR>.fails.

REPO=tursodatabase/turso
PRS="${PRS:-8812 8819 8844}"
SOCK=/home/vuos/.pi-web/sessiond.sock
CWD=/home/vuos/code/p4
SESSION_ID="${CI_WATCH_SESSION:-01a08192-2d20-71c2-95f8-68a2120e125c}"
DIR=/home/vuos/code/p4/e054-money-agent
LOG=$DIR/results/ci-watch.log
NOTIFY=/home/vuos/code/p4/e000-fundamentals/bin/notify.sh
INTERVAL="${CI_WATCH_INTERVAL:-300}"

say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG"; }

wake() {
  local payload
  payload=$(python3 -c 'import json,sys; print(json.dumps({"cwd":sys.argv[1],"text":sys.argv[2]}))' "$CWD" "$1")
  curl -s --unix-socket "$SOCK" -X POST -H 'Content-Type: application/json' \
       -d "$payload" "http://localhost/sessions/$SESSION_ID/prompt" >/dev/null
}

echo $$ > /tmp/ci-watch.pid
say "ci-watch started (pid $$, PRs: $PRS, session: $SESSION_ID)"

while true; do
  for PR in $PRS; do
    out=$(gh pr checks "$PR" --repo "$REPO" 2>/dev/null)
    fails=$(echo "$out" | awk -F'\t' '$2=="fail"{print $1}' | sort)
    statef=/tmp/ci-watch-$PR.fails
    prev=$(cat "$statef" 2>/dev/null)

    if [ -z "$fails" ]; then
      if [ -n "$prev" ]; then
        rm -f "$statef"
        say "PR#$PR recovered (checks green again; previously: $(echo $prev | tr '\n' ','))"
        "$NOTIFY" done "PR #$PR: checks verdes de nuevo" -s e054-money-agent \
          --url "https://github.com/tursodatabase/turso/pull/$PR" >/dev/null
        wake "CI RECOVERY: PR #$PR vuelve a estar verde (antes fallaban: $(echo $prev | tr '\n' ' ')). Si no hay nada mas pendiente en este PR, continua con el resto del loop."
      fi
      continue
    fi

    new=$(comm -13 <(echo "$prev") <(echo "$fails") 2>/dev/null | sed '/^$/d')
    if [ -n "$new" ]; then
      echo "$fails" > "$statef"
      say "PR#$PR NEW FAIL: $(echo $new | tr '\n' ',')"
      "$NOTIFY" error "PR #$PR check fallando: $(echo $new | tr '\n' ',' | sed 's/,$//')" -s e054-money-agent \
        --url "https://github.com/tursodatabase/turso/pull/$PR" >/dev/null
      wake "CI ALERT: PR #$PR tiene checks fallando nuevos: $(echo $new | tr '\n' ' '). Detalle con: gh pr checks $PR --repo $REPO. Logs de un job: gh api repos/$REPO/actions/jobs/<job-id>/logs. Si es culpa de nuestro diff, arreglalo y empuja; si es rotura ya presente en main upstream, verificalo contra main y documentalo en el PR."
    else
      echo "$fails" > "$statef"
    fi
  done
  sleep "$INTERVAL"
done
