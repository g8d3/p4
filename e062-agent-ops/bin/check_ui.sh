#!/usr/bin/env bash
# UI guard: run after ANY app.py HTML/JS edit, before telling the owner.
# Catches: syntax breaks + top-level `d.` references (the repeat offender:
# statements outside load() referencing fetched data abort the whole block).
set -uo pipefail
PORT="${1:-8322}"
curl -s --max-time 10 "http://127.0.0.1:$PORT/" -o /tmp/check_ui.html
python3 - "$PORT" << 'EOF'
import re, sys
h = open('/tmp/check_ui.html').read()
scripts = re.findall(r'<script>(.*?)</script>', h, re.S)
open('/tmp/check_ui.js', 'w').write(max(scripts, key=len))
print('script blocks:', len(scripts))
EOF
node --check /tmp/check_ui.js || exit 1
echo "JS syntax OK"
echo "--- top-level d. refs (must be empty) ---"
python3 - << 'EOF'
import re
s = open('/tmp/check_ui.js').read()
# crude: lines starting at col 0 referencing d. outside function bodies
depth = 0
bad = []
for i, line in enumerate(s.split('\n'), 1):
    stripped = line.strip()
    if re.match(r'^(async )?function |^const .*=\s*\(.*\)\s*=>', stripped):
        depth += 1  # approx: function opens (single-line bodies ignored, good enough as tripwire)
    if stripped.startswith('}') and depth > 0:
        depth -= 1
    if depth == 0 and re.search(r'\bd\.', stripped) and not stripped.startswith('//'):
        bad.append((i, stripped[:80]))
print(bad if bad else 'none — OK')
EOF
