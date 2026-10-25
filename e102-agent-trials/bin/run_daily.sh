#!/bin/bash
# Daily 07:00 Bogota: gather facts -> Mango Z summarizes + drafts replies -> daily/YYYY-MM-DD.md. Never sends.
set -u
P=~/code/p4; OB=$P/e100-openbot; DIR=$P/e102-agent-trials/daily; mkdir -p $DIR
DAY=$(TZ=America/Bogota date +%F); OUT=$DIR/$DAY.md; TMP=$(mktemp); STAMP=$(mktemp)
if ! pgrep -f OpenBot-x86_64.AppImage >/dev/null || ! curl -s -m 5 localhost:9222/json/version >/dev/null; then
  setsid nohup $OB/bin/launch.sh </dev/null >>$OB/logs/launch.log 2>&1 &
  for i in $(seq 60); do sleep 5; curl -s -m 3 localhost:9222/json/version >/dev/null && break; done; sleep 20
fi
bash $(dirname "$0")/gather.sh > $TMP.facts
{ cat <<'P'
Daily report task (automated, 07:00 Bogota). Using ONLY the facts below:
1. Health: list each check as OK or PROBLEM, then any unexpected services/containers. Do not run fix commands.
2. Email: summarize each new email (sender, subject, what they want) and write a short draft reply for each that needs one. Never send anything, never offer to send.
Rules: NEVER invent clock times or dates; use only the timestamps written in the facts. If something isn't in the facts, say "unknown". Reply in Markdown only, no preamble, and don't write files yourself.

P
cat $TMP.facts; } > $TMP
R=$(python3 $OB/bin/ask.py "Mango Z" @$TMP --wait 1500 2>&1); RC=$?
{ echo "# Daily report $DAY (Mango Z)"; echo
  if [ $RC -ne 0 ] || ! grep -q '^\[' <<<"$R"; then echo "**PROBLEM: Mango Z did not answer (rc=$RC):** $R"; else sed '1,2d' <<<"$R"; fi
  echo; echo "---"; echo "<details><summary>Raw facts</summary>"; echo; cat $TMP.facts; echo "</details>"; } > $OUT
[ $RC -eq 0 ] && grep -q "^\[" <<<"$R" && touch -r $STAMP $DIR/.last_run
rm -f $TMP $TMP.facts $STAMP; echo "wrote $OUT"
