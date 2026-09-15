#!/usr/bin/env bash
# wander.sh — the wanderer capture pass (UX LAW §13).
# Screenshots every board/app at phone width + runs cheap functional
# tripwires. Dumb by design: capture + detect, never fix here.
# Reviewing + fixing is leg work (WANDER.md) under T1/UI-auto + BEST/NEXT.
set -uo pipefail
E062="$(cd "$(dirname "$0")/.." && pwd)"
P4="$(dirname "$E062")"
W="$E062/wander"
SHOTS="$W/shots/$(date +%F-%H%M)"
mkdir -p "$SHOTS"

# Capture sentinel is capture-claim.json (run134: legs claim claim.json every
# 30min and never delete it, so the old shared-file skip starved capture for
# 2 days — capture must never be suppressed by review claims, and must never
# delete a leg's active review claim on release).
if [ -f "$W/capture-claim.json" ]; then
  age=$(( $(date +%s) - $(date -d "$(python3 -c "import json;print(json.load(open('$W/capture-claim.json')).get('ts','2000-01-01T00:00:00'))")" +%s 2>/dev/null || echo 0) ))
  [ "$age" -lt 21600 ] && { echo "capture-claim fresh (${age}s) — skip"; exit 0; }
fi
date -u +%FT%TZ | python3 -c "import json,sys;json.dump({'ts':sys.stdin.read().strip(),'by':'wander-cron'},open('$W/capture-claim.json','w'))"

# port:label:scheme — mirrors rungs (https only where the tailnet cert serves).
APPS="8320:e058:http 8321:e061:http 8322:e062:https 8323:e060:http 8324:e059:http 8325:e063:https 8326:e067:http"
: > "$SHOTS/checks.txt"
for spec in $APPS; do
  port="${spec%%:*}"; rest="${spec#*:}"; label="${rest%%:*}"; scheme="${rest##*:}"
  if [ "$scheme" = https ]; then opts="--ignore-certificate-errors"; else opts=""; fi
  code=$(curl -sk --max-time 10 -o /dev/null -w "%{http_code}" "$scheme://127.0.0.1:$port/" 2>/dev/null || echo 000)
  echo "$label :$port $code" >> "$SHOTS/checks.txt"
  # One headless shot at phone width. Brief CPU spike only; cron runs day-window.
  timeout 60 google-chrome --headless --disable-gpu --no-sandbox $opts \
    --hide-scrollbars --window-size=390,844 \
    --screenshot="$SHOTS/$label.png" "$scheme://127.0.0.1:$port/" >>"$E062/server.log" 2>&1 || echo "$label shot FAILED" >> "$SHOTS/checks.txt"
done

python3 - "$SHOTS" "$E062" << 'EOF'
import json, os, re, sqlite3, sys
shots, e062 = sys.argv[1], sys.argv[2]
p4 = os.path.dirname(e062)
findings = []
checks = open(os.path.join(shots, 'checks.txt')).read()
for line in checks.splitlines():
    m = re.match(r'(\S+) :(\d+) (\d+|000|FAILED)', line)
    if m and m.group(3) != '200':
        findings.append(f"{m.group(1)} :{m.group(2)} serves {m.group(3)} (not 200) — board link or app down?")
# Unknown-track tripwire (the 2026-09-14 blank-NAME class): events mention
# tracks that TRACKS doesn't define -> blank NAME + dead note/pause/run paths.
app = open(os.path.join(e062, 'app.py')).read()
m = re.search(r'TRACKS = \{([^}]+)\}', app, re.S)
known = set(re.findall(r"'(\w+)':", m.group(1))) if m else set()
db = sqlite3.connect(os.path.join(e062, 'ops.db'))
seen = {r[0] for r in db.execute("SELECT DISTINCT track FROM events").fetchall()}
db.close()
for t in sorted(seen - known - {'wander'}):
    findings.append(f"track {t} emits events but TRACKS has no label -> blank NAME on board, note/pause/run reject it")
# e059 freshness tripwire: badge says LIVE while data_through lags >1d.
try:
    d = json.load(open(os.path.join(p4, 'e059-crypto-valuations', 'output', 'multiples.json')))
    thrus = {p.get('data_through', '?') for p in d['protocols']}
    if len(thrus) > 1:
        findings.append(f"e059 mixed data_through {sorted(thrus)} — coins compared across different cutoffs")
except Exception as e:
    findings.append(f"e059 multiples.json unreadable: {e}")
out = {'ts': os.path.basename(shots), 'findings': findings}
json.dump(out, open(os.path.join(shots, 'findings.json'), 'w'), indent=1)
json.dump(out, open(os.path.join(e062, 'wander', 'latest.json'), 'w'), indent=1)
print(f"{len(findings)} findings")
for f in findings: print('-', f)
EOF

n=$(python3 -c "import json;print(len(json.load(open('$SHOTS/findings.json'))['findings']))")
# Beat + event in owner-first format. No ntfy: findings are not proof moves.
python3 "$E062/bin/ops.py" beat wander ok "Wander pass shot 7 apps at phone width, $n new findings | tech: shots $SHOTS, claim released" >>"$E062/server.log" 2>&1
python3 "$E062/bin/ops.py" emit wander wander "Wander pass: 7 phone shots, $n findings waiting in wander/latest.json | tech: $SHOTS" "wander:$(date +%F-%H%M)" >>"$E062/server.log" 2>&1
rm -f "$W/capture-claim.json"  # release only the capture sentinel; never touch legs' claim.json
ls "$SHOTS"
