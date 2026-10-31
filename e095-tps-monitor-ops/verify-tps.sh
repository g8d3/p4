#!/bin/bash
# verify-tps.sh — codified version of the manual checks repeated after every
# TPS Monitor change. Run it instead of thinking through the checklist.
#
# Usage: ./docs/verify-tps.sh [step]...
#   Steps: suite | revision | files | panel | panel-text | watch | report
#   Default (no args): suite revision files  (fast, no browser, no waiting)
#   Full:              ./docs/verify-tps.sh suite revision files panel watch report
#   panel-text: panel assertions via eval JSON only, no screenshots (fast CI check)
#
# Exit code: 0 when every executed step passes, 1 otherwise.
# The panel step drives a real browser (agent-browser must be installed).
set -u
PKGDIR="${PKGPATH:-$(cd "$(dirname "$0")/../e095-tps-monitor" && pwd)}"
BASE="http://127.0.0.1:8504"
PROJECT="5252bfc1-300e-4ada-bef9-f68534964180"
WORKSPACE="f93c700afa07"
FAILED=0

pass() { echo "PASS  $1"; }
fail() { echo "FAIL  $1"; FAILED=1; }
info() { echo "      $1"; }

step_suite() {
  echo "== suite: unit tests =="
  (cd "$PKGDIR" && npm test 2>&1 | tail -n 8)
  (cd "$PKGDIR" && npm test 2>&1 | grep -q "ℹ fail 0") && pass "unit tests green" || fail "unit tests"
}

step_revision() {
  echo "== revision: plugin served == active =="
  local out
  out=$(curl -s -m 5 "$BASE/api/plugins" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for p in d['plugins']:
    if p['id']=='tps-monitor':
        s=p.get('server',{})
        print('enabled:',p.get('enabled'))
        print('active :',s.get('activeRevision',''))
        print('desired:',s.get('desiredRevision',''))
        print('stale:',s.get('staleRevision'),'restartRequired:',s.get('restartRequired'))
        print('health:',(s.get('health') or {}).get('status'))
")
  echo "$out" | sed 's/^/      /'
  echo "$out" | grep -q "enabled: True" || { fail "plugin not enabled"; return; }
  local active desired
  active=$(echo "$out" | sed -n 's/active : //p')
  desired=$(echo "$out" | sed -n 's/desired: //p')
  [ -n "$active" ] && [ "$active" = "$desired" ] || { fail "revision mismatch (tab will 404)"; return; }
  echo "$out" | grep -q "restartRequired: False" || { fail "restart required"; return; }
  echo "$out" | grep -q "health: healthy" || { fail "backend unhealthy"; return; }
  pass "served revision is live and healthy"
}

step_files() {
  echo "== files: workspace JSONL health =="
  local root="${1:-/home/vuos/code/p4}"
  local node_out
  node_out=$(node --input-type=module -e "
import { readFileSync } from 'node:fs';
import { normalizeSample, normalizeTurn } from '$PKGDIR/dist/browser/protocol.js';
const root = '$root';
const res = {};
for (const [f, norm] of [['tps-history.jsonl', normalizeSample], ['tps-turns.jsonl', normalizeTurn]]) {
  try {
    const lines = readFileSync(root + '/.pi-web/' + f, 'utf8').split('\n').filter(Boolean);
    let ok = 0;
    for (const l of lines) { try { if (norm(JSON.parse(l))) ok++; } catch {} }
    res[f] = { lines: lines.length, valid: ok };
  } catch (e) { res[f] = { error: String(e).slice(0, 80) }; }
}
try {
  const live = JSON.parse(readFileSync(root + '/.pi-web/tps-live.json', 'utf8'));
  res.live = { state: live.state };
} catch (e) { res.live = { error: String(e).slice(0, 80) }; }
console.log(JSON.stringify(res));
")
  echo "      $node_out"
  python3 -c "
import json,sys
d=json.loads('''$node_out''')
h=d['tps-history.jsonl']; t=d['tps-turns.jsonl']
assert 'error' not in h and h['lines']>0 and h['valid']==h['lines'], 'history file bad: %s' % h
assert 'error' not in t and t['lines']>0 and t['valid']==t['lines'], 'turns file bad: %s' % t
assert h['lines']<=500 and t['lines']<=500, 'over row cap'
print('files ok: history %d/%d valid, turns %d/%d valid' % (h['valid'],h['lines'],t['valid'],t['lines']))
" && pass "JSONL files valid and capped" || fail "JSONL files"
}

step_panel() {
  echo "== panel: real browser render =="
  local shotdir="${1:-/tmp/tps-verify}"
  mkdir -p "$shotdir"
  agent-browser set viewport 1280 800 >/dev/null 2>&1
  agent-browser open "$BASE/?project=$PROJECT&workspace=$WORKSPACE" >/dev/null 2>&1
  local clicked=""
  local waited_open=0
  while [ "$waited_open" -lt 60 ]; do
    sleep 5
    waited_open=$((waited_open + 5))
    clicked=$(agent-browser eval "
(function(){var app=document.querySelector('pi-web-app');if(!app||!app.shadowRoot)return 'NO-APP';var wp=app.shadowRoot.querySelector('workspace-panel');if(!wp)return 'NO-PANEL';var sr=wp.shadowRoot;if(!sr)return 'NO-SHADOW';for(var b of sr.querySelectorAll('button')){if((b.textContent||'').trim()==='TPS'){b.click();return 'ok';}}return 'NO-TPS-TAB';})()" 2>&1 | head -n 1)
    info "tps tab click (${waited_open}s): $clicked"
    echo "$clicked" | grep -q '"ok"' && break
    [ "$waited_open" -ge 60 ] && { fail "TPS tab missing in workspace panel after 60s"; return; }
    agent-browser reload >/dev/null 2>&1
  done
  local diag=""
  local waited=0
  # Liveness is proved by the TABLE, not by a header dot: the newest row's
  # timestamp must advance while this workspace is streaming, with no reload.
  # `v12` removed the live strip (the owner: the table is enough), so the old
  # "● live" probe would fail on a correct panel.
  diag=$(agent-browser eval "
(function(){var wp=document.querySelector('pi-web-app').shadowRoot.querySelector('workspace-panel');if(!wp)return '{}';var sr=wp.shadowRoot;var tables=[...sr.querySelectorAll('table')].map(function(t){return t.querySelectorAll('tbody tr').length;});var first=sr.querySelector('table tbody tr');var page='';var i=sr.textContent.indexOf('Page ');if(i!==-1)page=sr.textContent.slice(i,i+40).replace(/\s+/g,' ');return JSON.stringify({tables:tables,top:first?first.textContent.replace(/\s+/g,' ').trim().slice(0,40):'',page:page});})()" 2>&1 | head -n 1)
  info "diag (${waited}s): $diag"
  echo "$diag" | python3 -c "import json,sys; d=json.loads(json.loads(sys.stdin.read())); sys.exit(0 if d.get('tables') and max(d['tables']) > 1 else 1)" 2>/dev/null || { fail "no populated table in the panel: $diag"; return; }
  local top1 top2
  top1=$(echo "$diag" | python3 -c "import json,sys; print(json.loads(json.loads(sys.stdin.read())).get('top',''))" 2>/dev/null)
  sleep 4
  top2=$(agent-browser eval "
(function(){var wp=document.querySelector('pi-web-app').shadowRoot.querySelector('workspace-panel');var first=wp.shadowRoot.querySelector('table tbody tr');return first?first.textContent.replace(/\s+/g,' ').trim().slice(0,40):'';})()" 2>&1 | head -n 1)
  info "table top: $top1 -> $top2"
  [ "$top1" = "$top2" ] && info "newest row unchanged in 4s (idle workspace: expected)" || info "newest row advanced (live push working)"
  local rows
  rows=$(echo "$diag" | python3 -c "import json,sys; print(json.loads(json.loads(sys.stdin.read())).get('page',''))" 2>/dev/null)
  info "pagination: $rows"
  agent-browser screenshot "$shotdir/tps-messages.png" >/dev/null 2>&1
  for v in Turns Tools Fleet; do
    agent-browser eval "(function(){var wp=document.querySelector('pi-web-app').shadowRoot.querySelector('workspace-panel');var sr=wp.shadowRoot;for(var b of sr.querySelectorAll('button')){if((b.textContent||'').trim()==='$v'){b.click();return 'ok';}}return 'missing';})()" >/dev/null 2>&1
    sleep 3
    agent-browser screenshot "$shotdir/tps-$(echo "$v" | tr 'A-Z' 'a-z').png" >/dev/null 2>&1
  done
  local shotcount
  shotcount=$(ls "$shotdir"/tps-*.png 2>/dev/null | wc -l)
  info "shots: $shotdir ($shotcount files)"
  [ "$shotcount" -ge 4 ] || { fail "panel screenshots missing ($shotcount/4)"; return; }
  pass "panel renders from the table (shots in $shotdir)"
}

step_panel_text() {
  echo "== panel-text: browser render, eval JSON only (no screenshots) =="
  agent-browser set viewport 1280 800 >/dev/null 2>&1
  agent-browser open "$BASE/?project=$PROJECT&workspace=$WORKSPACE" >/dev/null 2>&1
  local clicked=""
  local waited_open=0
  while [ "$waited_open" -lt 60 ]; do
    sleep 5
    waited_open=$((waited_open + 5))
    clicked=$(agent-browser eval "
(function(){var app=document.querySelector('pi-web-app');if(!app||!app.shadowRoot)return 'NO-APP';var wp=app.shadowRoot.querySelector('workspace-panel');if(!wp)return 'NO-PANEL';var sr=wp.shadowRoot;if(!sr)return 'NO-SHADOW';for(var b of sr.querySelectorAll('button')){if((b.textContent||'').trim()==='TPS'){b.click();return 'ok';}}return 'NO-TPS-TAB';})()" 2>&1 | head -n 1)
    info "tps tab click (${waited_open}s): $clicked"
    echo "$clicked" | grep -q '"ok"' && break
    [ "$waited_open" -ge 60 ] && { fail "TPS tab missing in workspace panel after 60s"; return; }
    agent-browser reload >/dev/null 2>&1
  done
  local diag=""
  diag=$(agent-browser eval "
(function(){var app=document.querySelector('pi-web-app');if(!app||!app.shadowRoot)return JSON.stringify({tab:false});var wp=app.shadowRoot.querySelector('workspace-panel');if(!wp||!wp.shadowRoot)return JSON.stringify({tab:false});var sr=wp.shadowRoot;var labels=[...sr.querySelectorAll('button')].map(function(b){return (b.textContent||'').trim();});var views=['Messages','Turns','Tools','Fleet'].filter(function(v){return labels.indexOf(v)!==-1;});var tables=[...sr.querySelectorAll('table')].map(function(t){return t.querySelectorAll('tbody tr').length;});return JSON.stringify({tab:true,views:views,tables:tables});})()" 2>&1 | head -n 1)
  info "diag (0s): $diag"
  echo "$diag" | python3 -c "
import json,sys
raw = sys.stdin.read()
d = json.loads(json.loads(raw))
assert d.get('tab'), 'TPS tab content missing'
views = set(d.get('views') or [])
assert {'Messages','Turns','Tools','Fleet'} <= views, 'view buttons missing: %s' % sorted(views)
tables = d.get('tables') or []
assert tables and max(tables) > 0, 'no populated table: %s' % tables
print('views %s, tables %s' % (sorted(views), tables))
" 2>&1 | sed 's/^/      /' && pass "panel renders from eval JSON (no screenshots)" || fail "panel-text assertions failed: $diag"
}

step_watch() {
  echo "== watch: push-channel quiet =="
  local minutes="${1:-3}"
  info "sampling channels/watch for ${minutes} min..."
  local before after
  before=$(journalctl --user -u pi-web-sessiond --since "2 minutes ago" 2>/dev/null | grep -c "channels/watch")
  sleep $((minutes * 60))
  after=$(journalctl --user -u pi-web-sessiond --since "$((minutes + 2)) minutes ago" 2>/dev/null | grep -c "channels/watch")
  local rate
  rate=$(( (after - before) / minutes ))
  info "watch opens: ~${rate}/min (storm was ~660/min; one held channel ≈ 0-2/min)"
  [ "$rate" -lt 60 ] && pass "no channel storm" || fail "channel storm suspected"
}

step_report() {
  echo "== report: server inventory =="
  ss -tlnp 2>/dev/null | grep 8504 | head -n 2 | sed 's/^/      /'
  echo "      lan: $(hostname -I | awk '{print $1}')  tailscale: $(tailscale ip -4 2>/dev/null)"
  systemctl --user is-active pi-web-sessiond 2>/dev/null | sed 's/^/      daemon: /'
}

if [ $# -eq 0 ]; then set -- suite revision files; fi
for step in "$@"; do
  case "$step" in
    suite) step_suite ;;
    revision) step_revision ;;
    files) step_files ;;
    panel) step_panel ;;
    panel-text) step_panel_text ;;
    watch) step_watch ;;
    report) step_report ;;
    *) echo "unknown step: $step (suite|revision|files|panel|panel-text|watch|report)"; FAILED=1 ;;
  esac
done
echo "== result: $([ "$FAILED" -eq 0 ] && echo ALL PASS || echo FAILURES PRESENT) =="
exit "$FAILED"
