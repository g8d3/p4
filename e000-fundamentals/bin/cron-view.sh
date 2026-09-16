#!/bin/bash
# cron-view.sh — read the crontab through 4 combined axes. No registry here:
# everything is derived live from `crontab -l` + section headers.
# Axes: FUNCTION (section header) x EXPERIMENT (path) x LAYER (command kind)
#       x FOLDER (experiment dir). Views: --by function|experiment|layer (default: function).
set -uo pipefail
MODE="${1:---by}"
BY="${2:-function}"
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
FUNC=""
crontab -l 2>/dev/null | while IFS= read -r line; do
  case "$line" in
    "# ---"*) FUNC=$(echo "$line" | sed 's/# --- //; s/ ---//; s/^[^ ]* //') ;;
    ""|"#"*|"#"*) ;; # blank, header, retired/disabled notes
    *)
      sched=$(echo "$line" | awk '{if ($1 ~ /^@/) print $1; else print $1" "$2" "$3" "$4" "$5}')
      cmd=$(echo "$line" | awk '{if ($1 ~ /^@/) {$1=""; print $0} else {$1=$2=$3=$4=$5=""; print $0}}' | sed 's/^ *//; s/ #.*//')
      exp=$(echo "$cmd" | grep -oE 'e[0-9]{3}-[a-z0-9-]+' | head -n 1)
      [ -z "$exp" ] && exp="-"
      case "$cmd" in
        *healthcheck*) LAYER="probe" ;;
        *app.py*|*serve.py*|*http.server*) LAYER="frontend" ;;
        *sample.sh*|*refresh.sh*|*snapshot.py*|*resolve.py*|*paper_*) LAYER="backend" ;;
        *) LAYER="ops" ;;
      esac
      printf '%s\t%s\t%s\t%s\t%s\n' "$FUNC" "$exp" "$LAYER" "$sched" "$cmd" >> "$TMP"
      ;;
  esac
done
case "$BY" in
  experiment) SORT1="-k2,2"; SORT2="-k1,1" ;;
  layer) SORT1="-k3,3"; SORT2="-k1,1" ;;
  *) SORT1="-k1,1"; SORT2="-k2,2" ;;
esac
printf 'FUNCTION\tEXPERIMENT\tLAYER\tSCHEDULE\tCOMMAND\n'
sort -t "$(printf '\t')" "$SORT1" "$SORT2" "$TMP" | cut -c1-160
