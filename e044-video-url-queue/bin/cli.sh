#!/bin/bash
# CLI wrapper around the queue API. Usage:
#   cli.sh submit <url> [<url> ...]
#   cli.sh status [job_id]
#   cli.sh get <job_id>            # download merged video
#   cli.sh cancel <job_id>
#   cli.sh detect <url>            # dry-run: list videos, don't enqueue
#   cli.sh config                  # show runtime config
BASE="${URLQ_BASE:-http://127.0.0.1:8177}"

case "${1:-}" in
  submit)
    shift
    [ -n "$1" ] || { echo "usage: cli.sh submit <url>"; exit 1; }
    for u in "$@"; do curl -s -X POST "$BASE/api/jobs" -H 'Content-Type: application/json' -d "{\"url\":\"$u\"}"; echo; done
    ;;
  status)
    shift
    if [ -n "${1:-}" ]; then curl -s "$BASE/api/jobs/$1" | python3 -m json.tool;
    else curl -s "$BASE/api/jobs" | python3 -c "import sys,json; [print(j['id'], j['status'], j['url'][:60]) for j in json.load(sys.stdin)['jobs']]"; fi
    ;;
  get)
    curl -sL "$BASE/api/jobs/$2/video" -o "merge-$2.mp4" && echo "saved: merge-$2.mp4" || echo "FAILED: $?"
    ;;
  cancel)
    curl -s -X DELETE "$BASE/api/jobs/$2"
    echo
    ;;
  detect)
    curl -s -X POST "$BASE/api/detect" -H 'Content-Type: application/json' -d "{\"url\":\"$2\"}" | python3 -c "import sys,json; d=json.load(sys.stdin); [print(i['index'], i['kind'], i['url'][:90]) for i in d.get('videos',[])]"
    ;;
  config)
    curl -s "$BASE/api/config" | python3 -m json.tool
    ;;
  *)
    echo "usage: cli.sh {submit|status|get|cancel|detect|config}"
    exit 1
    ;;
esac
