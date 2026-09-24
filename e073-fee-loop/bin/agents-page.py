#!/usr/bin/env python3
"""Agents page v2: static shell + legs.json, page polls JSON every 5s and
upserts rows (no full reload). Regen writes both files; run after each leg
(llm-leg.sh hook) and each tick (tick.sh hook) so heartbeat stays fresh.
Usage: python3 bin/agents-page.py"""
import json, os, re
from datetime import datetime, timezone
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(p):
    try: return open(os.path.join(base, p), errors='ignore').read().splitlines()
    except OSError: return []
starts, ends = {}, {}
for line in load('log/llm-legs.log'):
    m = re.match(r'(\S+) LEG (\S+) (start|done.*|rc=.*)', line)
    if not m: continue
    ts, tid, what = m.groups()
    if what == 'start': starts[tid] = ts
    else: ends[tid] = {'ts': ts, 'ok': what.startswith('done')}
spend = {}
for line in load('ledger/credits.jsonl'):
    try: e = json.loads(line)
    except ValueError: continue
    if e.get('kind') == 'llm' and e.get('task'): spend[e['task']] = e
rows = []
for tid in sorted(set(starts) | set(spend), reverse=True):
    s = spend.get(tid, {})
    en = ends.get(tid)
    rows.append({'task': tid, 'agent': s.get('model', '?'), 'start': starts.get(tid, '?'),
        'end': s.get('ts', '?'), 'tin': s.get('tokens_in'), 'tout': s.get('tokens_out'),
        'cost': s.get('cost_usd'), 'note': s.get('note', ''),
        'status': 'done' if en and en['ok'] else ('failed' if en else 'running')})
try: hb = open(os.path.join(base, 'log/heartbeat'), errors='ignore').read().strip()
except OSError: hb = '?'
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
json.dump({'generated_at': now, 'heartbeat': hb, 'legs': rows},
          open(os.path.join(base, 'legs.json'), 'w'))
def fmt(v): return '—' if v is None else (f"{v:,}" if isinstance(v, int) else f"${v:.4f}")
tr = '\n'.join(
    f"<tr id='r-{r['task']}'>" + "".join(f"<td>{c}</td>" for c in
    [r['agent'], r['task'], r['start'], r['end'], fmt(r['tin']), fmt(r['tout']),
     fmt(r['cost']), r['status'], r['note']]) + "</tr>" for r in rows)
html = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>agents working</title>
<style>body{{font-family:system-ui;margin:1em;font-size:16px}}.wrap{{overflow-x:auto;-webkit-overflow-scrolling:touch}}table{{border-collapse:collapse;min-width:640px}}td,th{{border:1px solid #ccc;padding:6px 8px;font-size:14px}}th{{background:#f0f0f0}}.running{{background:#fff3cd}}.failed{{background:#f8d7da}}.done{{background:#d4edda}}#hb{{margin:1em 0;font-weight:bold}}</style>
</head><body><h1>agents working</h1><div id=hb></div>
<div class=wrap><table id=t><thead><tr><th onclick="sort('agent')">agent</th><th onclick="sort('task')">task</th><th onclick="sort('start')">started</th><th onclick="sort('end')">finished</th><th onclick="sort('tin')">in</th><th onclick="sort('tout')">out</th><th onclick="sort('cost')">cost</th><th onclick="sort('status')">status</th><th>what</th></tr></thead>
<tbody id=tb>
{tr}</tbody></table></div>
<style>th{{cursor:pointer}}</style>
<script>
function T(x){{if(!x||x=='?')return '?';const d=new Date(x);return isNaN(d)?x:d.toLocaleString();}}
let last='',lastSig='',legs=[],sk='end',sd=-1;
function sort(k){{sd=(sk===k)?-sd:-1;sk=k;render();}}
function val(r,k){{const v=r[k];if(v==null)return sd>0?Infinity:-Infinity;return v;}}
function render(){{const tb=document.getElementById('tb');if(!tb)return;
const s=[...legs].sort((a,b)=>{{const x=val(a,sk),y=val(b,sk);return (x<y?-1:x>y?1:0)*sd;}});
tb.innerHTML=s.map(r=>'<tr class="'+r.status+'">'+[r.agent,r.task,T(r.start),T(r.end),r.tin??'—',r.tout??'—',r.cost??'—',r.status,r.note].map(x=>'<td>'+x+'</td>').join('')+'</tr>').join('');}}
async function up(){{try{{const r=await (await fetch('legs.json?'+Date.now())).text();
if(r===last)return;last=r;const d=JSON.parse(r);
const sig=JSON.stringify(d.legs);if(sig===lastSig)return;lastSig=sig;
document.getElementById('hb').textContent='loop heartbeat: '+T(d.heartbeat)+' · updated '+T(d.generated_at);
legs=d.legs;render();}}}}catch(e){{}}}}
up();setInterval(up,5000);</script></body></html>"""
open(os.path.join(base, 'agents.html'), 'w').write(html)
print(f"agents.html + legs.json: {len(rows)} legs, heartbeat {hb}")
