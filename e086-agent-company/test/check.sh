#!/bin/bash
# GATE: health + roles + auto-start loop + verify + timeline
cd "$(dirname "$0")/.."
PORT=$(python3 -c "import json,os;print(json.load(open('data/settings.json' if os.path.exists('data/settings.json') else 'needs.json'))['port'])")
B="http://127.0.0.1:$PORT"
fail(){ echo "FAIL: $1"; exit 1; }
curl -s $B/api/health | grep -q '"ok": true' || fail "health"
curl -s $B/api/roles | grep -q reviewer || fail "roles seed"
curl -s $B/api/timeline | grep -q present || fail "timeline"
curl -s $B/api/verify | grep -q '"pass": true' || fail "verify"
# kill all agents -> tick must auto-start >=1
IDS=$(python3 -c "import json,urllib.request;print(' '.join(a['id'] for a in json.load(urllib.request.urlopen('$B/api/agents'))))")
for id in $IDS; do curl -s -X POST $B/api/agents -d "{\"delete\":\"$id\"}" -H 'Content-Type: application/json' >/dev/null; done
curl -s -X POST $B/api/loop/tick | grep -q working_after || fail "tick"
curl -s $B/api/health | python3 -c "import json,sys;d=json.load(sys.stdin);assert d['working']>=1,'no auto-start'" || fail "auto-start"
curl -s $B/ | grep -q "Company OS" || fail "first paint"
# UI consistency: nav targets == sections, no duplicate ids, JS parses
python3 - <<'EOF' || fail "ui consistency"
import re
html = open('public/index.html').read()
nav = re.findall(r'data-t=([a-z]+)', html)
secs = re.findall(r'<section id=t-([a-z]+)', html)
assert sorted(nav) == sorted(secs), f"nav {nav} != sections {secs}"
ids = re.findall(r'\bid=([A-Za-z_][\w-]*)', html)
dupes = sorted({i for i in ids if ids.count(i) > 1})
assert not dupes, f"duplicate ids: {dupes}"
for token in ['renderOps', 'opsSnap', 'addFuture', 'planFuture', 'reopen', 'sess', 'taskHist']:
    assert token in html, f"missing {token}"
handlers = set(re.findall(r'onclick="([a-zA-Z]+)\(', html))
defined = set(re.findall(r'(?:async )?function ([a-zA-Z]+)\(', html))
missing = sorted(h for h in handlers if h not in defined)
assert not missing, f"dead buttons: {missing}"
print("UI CONSISTENCY OK")
EOF
python3 -c "open('/tmp/gate.js','w').write(open('public/index.html').read().split('<script>')[1].split('</script>')[0])"
node --check /tmp/gate.js || fail "js syntax"
echo "GATE GREEN"
