#!/usr/bin/env python3
"""Agents page v1: static table of agent legs from ledger + start/end log.
Reads ledger/credits.jsonl + log/llm-legs.log, writes agents.html. No server.
Usage: python3 bin/agents-page.py"""
import json, os, re
from datetime import datetime, timezone
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(p):
    try: return open(os.path.join(base, p), errors='ignore').read().splitlines()
    except OSError: return []
legs = {}
for line in load('log/llm-legs.log'):
    m = re.match(r'(\S+) LEG (\S+) (start|done.*|rc=.*)', line)
    if m: legs.setdefault(m.group(2), {})[m.group(3).split()[0][:4]] = m.group(1)
rows = []
for line in load('ledger/credits.jsonl'):
    try: e = json.loads(line)
    except ValueError: continue
    if e.get('kind') != 'llm': continue
    t = e.get('task', '?')
    st = legs.get(t, {})
    rows.append({'task': t, 'agent': e.get('model', '?'), 'start': st.get('star', '?'),
        'end': e.get('ts', '?'), 'tin': e.get('tokens_in'), 'tout': e.get('tokens_out'),
        'cost': e.get('cost_usd'), 'note': e.get('note', '')})
rows.sort(key=lambda r: r['end'], reverse=True)
def fmt(v): return '—' if v is None else (f"{v:,}" if isinstance(v, int) else f"${v:.4f}")
tr = '\n'.join(
    f"<tr><td>{r['agent']}</td><td>{r['task']}</td><td>{r['start']}</td><td>{r['end']}</td>"
    f"<td>{fmt(r['tin'])}</td><td>{fmt(r['tout'])}</td><td>{fmt(r['cost'])}</td><td>{r['note']}</td></tr>"
    for r in rows)
html = f"""<!doctype html><html><head><meta charset=utf-8><title>agents working</title>
<style>body{{font-family:system-ui;margin:2em}}table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:4px 8px;font-size:13px}}th{{background:#f0f0f0}}</style>
</head><body><h1>agents working ({len(rows)} legs)</h1>
<p>updated {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} · regen: <code>python3 bin/agents-page.py</code></p>
<table><tr><th>agent</th><th>task</th><th>started</th><th>finished</th><th>in</th><th>out</th><th>cost</th><th>what</th></tr>
{tr}</table></body></html>"""
open(os.path.join(base, 'agents.html'), 'w').write(html)
print(f"agents.html: {len(rows)} legs")
