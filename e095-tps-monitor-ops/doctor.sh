#!/bin/bash
# doctor.sh — diagnose the two ways an ops loop silently breaks: a stale
# plugin tab (revision drift 404s the tab) and models scope drift (the daemon
# holds more enabled models than your picks).
#
# Usage: ./doctor.sh tab-missing <plugin-id> | models | report | --help
#   tab-missing <plugin-id>  plugin health from /api/plugins; exit 1 when the tab will 404
#   models                   settings.json vs wanted.json picks; trims the live daemon when SID+CWD are set
#   report                   server inventory (same as verify-tps.sh report)
#
# Exit code: 0 when the checked thing is healthy, 1 otherwise.
set -u
BASE="http://127.0.0.1:8504"
OPSDIR="$(cd "$(dirname "$0")" && pwd)"
SETTINGS="${P4_PI_SETTINGS:-$HOME/.pi/agent/settings.json}"
WANTED="${PI_WEB_DATA_DIR:-$HOME/.pi-web}/plugin-data/p4-models/wanted.json"
FAILED=0

pass() { echo "PASS  $1"; }
fail() { echo "FAIL  $1"; FAILED=1; }
info() { echo "      $1"; }

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \?//'
}

step_tab_missing() {
  local id="${1:?plugin id required (e.g. tps-monitor)}"
  echo "== tab-missing: $id =="
  local out
  out=$(curl -s -m 5 "$BASE/api/plugins" | python3 -c "
import json,sys
d = json.load(sys.stdin)
for p in d.get('plugins', []):
    if p.get('id') == sys.argv[1]:
        s = p.get('server', {}) or {}
        print('enabled:', p.get('enabled'))
        print('source :', p.get('source'))
        print('active :', s.get('activeRevision', ''))
        print('desired:', s.get('desiredRevision', ''))
        print('stale:', s.get('staleRevision'), 'restartRequired:', s.get('restartRequired'))
        print('health:', (s.get('health') or {}).get('status'))
        break
else:
    print('NOT-FOUND')
" "$id")
  echo "$out" | sed 's/^/      /'
  echo "$out" | grep -q "NOT-FOUND" && { fail "plugin '$id' not in /api/plugins"; return; }
  local active desired
  active=$(echo "$out" | sed -n 's/active : //p')
  desired=$(echo "$out" | sed -n 's/desired: //p')
  local stale restart health
  stale=$(echo "$out" | sed -n 's/stale: \([^ ]*\).*/\1/p')
  restart=$(echo "$out" | sed -n 's/.*restartRequired: \([^ ]*\)/\1/p')
  health=$(echo "$out" | sed -n 's/health: //p')
  if [ -n "$active" ] && [ "$active" = "$desired" ] && [ "$stale" = "False" ] \
    && [ "$restart" = "False" ] && [ "$health" = "healthy" ]; then
    pass "'$id' tab healthy (revision $active)"
    return
  fi
  fail "'$id' tab will 404 (active/desired mismatch or stale) — remediate:"
  local srcdir
  srcdir=$(echo "$out" | sed -n 's/source : //p')
  [ -z "$srcdir" ] && srcdir="<package-dir>"
  echo "      cd $srcdir && npm run build && npm test"
  echo "      systemd-run --user --on-active=10s --unit=pi-web-restart-resume \\"
  echo "        $OPSDIR/restart-resume.sh <session-id> <cwd> <handoff>"
}

step_models() {
  echo "== models: settings.json vs wanted.json picks =="
  local out
  out=$(python3 -c "
import json
s = json.load(open('$SETTINGS'))
w = json.load(open('$WANTED'))
cur, want = s.get('enabledModels') or [], (w.get('models') or [])
print('settings:', len(cur))
print('wanted  :', len(want))
for m in [m for m in want if m not in cur]: print('missing:', m)
for m in [m for m in cur if m not in want]: print('extra  :', m)
")
  echo "$out" | sed 's/^/      /'
  local nsettings nwanted nextras
  nsettings=$(echo "$out" | sed -n 's/settings: //p')
  nwanted=$(echo "$out" | sed -n 's/wanted  : //p')
  nextras=$(echo "$out" | grep -c "extra  :" || true)
  info "enabled=$nsettings picks=$nwanted extras=$nextras"
  if [ "$nextras" -eq 0 ]; then
    echo "$out" | grep -q "missing:" && { fail "picks missing from settings (guard will repair within a minute)"; return; }
    pass "exact match ($nsettings enabled = $nwanted picks)"
    return
  fi
  fail "$nextras extra model(s) outside your picks"
  if [ -n "${SID:-}" ] && [ -n "${CWD:-}" ]; then
    info "SID+CWD set — trimming the live daemon scope:"
    python3 /home/vuos/code/p4/e105-piweb-plugins/scripts/models.py sync-daemon --sid "$SID" --cwd "$CWD"
  else
    info "remediate with the daemon trim (keeps memory+file consistent):"
    echo "      SID=<session-id> CWD=<cwd> ./doctor.sh models"
    echo "      # or directly:"
    echo "      python3 /home/vuos/code/p4/e105-piweb-plugins/scripts/models.py sync-daemon --sid <session-id> --cwd <cwd>"
  fi
}

step_report() {
  echo "== report: server inventory =="
  ss -tlnp 2>/dev/null | grep 8504 | head -n 2 | sed 's/^/      /'
  echo "      lan: $(hostname -I | awk '{print $1}')  tailscale: $(tailscale ip -4 2>/dev/null)"
  systemctl --user is-active pi-web-sessiond 2>/dev/null | sed 's/^/      daemon: /'
}

if [ $# -eq 0 ]; then usage; exit 2; fi
case "$1" in
  tab-missing) step_tab_missing "${2:-}" ;;
  models) step_models ;;
  report) step_report ;;
  --help|-h|help) usage ;;
  *) echo "unknown command: $1 (tab-missing|models|report|--help)"; FAILED=1 ;;
esac
echo "== result: $([ "$FAILED" -eq 0 ] && echo OK || echo NEEDS ATTENTION) =="
exit "$FAILED"
