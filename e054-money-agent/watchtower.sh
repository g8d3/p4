#!/bin/bash
# e054 watchtower v2: polls PRs #8812 and #8819 every 5 min, logs changes, alerts on reviews/state changes. 24h lifetime.
LOG=/home/vuos/code/p4/e054-money-agent/results/pr-watch.log
ALERT=/home/vuos/code/p4/e054-money-agent/results/PR-ALERT.txt
END=$((SECONDS + 86400))
declare -A prev
while [ $SECONDS -lt $END ]; do
  for PR in 8812 8819 8844; do
    snap=$(gh pr view $PR --repo tursodatabase/turso --json state,reviews,comments,mergeStateStatus --jq '[.state,.mergeStateStatus,(.reviews|length),(.comments|length),([.reviews[].author.login]|join(",")),(.state)+"|"+([.reviews[].state]|join(","))]|@tsv' 2>/dev/null)
    if [ -n "$snap" ] && [ "$snap" != "${prev[$PR]}" ]; then
      echo "$(date -u +%FT%TZ) PR#$PR $snap" >> "$LOG"
      rev=$(echo "$snap" | cut -f3); st=$(echo "$snap" | cut -f1)
      ncom=$(echo "$snap" | cut -f4)
      rstate=$(echo "$snap" | cut -f6)
      # alert on: review appears, state change, or new comment (maintainer ping)
      if [ "$rev" != "$(echo "${prev[$PR]}" | cut -f3)" ] || [ "$ncom" != "$(echo "${prev[$PR]}" | cut -f4)" ] || [ "$st" != "OPEN" ]; then
        echo "$(date -u +%FT%TZ) ALERT PR#$PR state=$st reviews=$rev comments=$ncom reviewStates=$rstate" >> "$ALERT"
      fi
      prev[$PR]="$snap"
    fi
  done
  sleep 300
done
echo "$(date -u +%FT%TZ) watchtower v2 exit (24h lifetime)" >> "$LOG"
