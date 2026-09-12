#!/usr/bin/env python3
"""e062 fleet board — plans, changes, execution. Port 8322."""
import os, sqlite3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get('E062_DB', os.path.join(BASE, 'ops.db'))
P4 = '/home/vuos/code/p4'
TRACKS = {'e058': 'funding scanner', 'e059': 'valuations', 'e060': 'social radar',
          'e061': 'game suite', 'e062': 'agent ops', 'runner': 'dispatcher legs'}

app = FastAPI()

def read(p, n=60):
    try: return open(p).read().split('\n')[:n]
    except Exception: return []

@app.get('/api/board')
def board():
    c = sqlite3.connect(DB)
    rungs = {t: {'rung': r, 'ts': ts, 'url': u, 'note': no}
             for t, r, ts, u, no in c.execute(
                 "SELECT track, rung, datetime(ts,'unixepoch'), url, note FROM rungs")}
    beats = {t: {'ts': ts, 'status': st, 'note': no}
             for t, ts, st, no in c.execute(
                 "SELECT track, datetime(ts,'unixepoch'), status, note FROM heartbeats")}
    events = [{'ts': ts, 'track': t, 'kind': k, 'summary': s} for ts, t, k, s in
              c.execute("SELECT datetime(ts,'unixepoch'), track, kind, summary FROM events ORDER BY ts DESC LIMIT 25")]
    props = [{'id': i, 'ts': ts, 'track': t, 'usd': u, 'action': a, 'reason': r, 'status': s}
             for i, ts, t, u, a, r, s in c.execute(
                 "SELECT id, datetime(ts,'unixepoch'), track, amount_usd, action, reason, status FROM proposals ORDER BY id DESC LIMIT 20")]
    try:
        trials = [{'name': n, 'renews': rd, 'usd': co, 'note': no} for n, rd, co, no in
                  c.execute("SELECT name, datetime(renews_ts,'unixepoch'), cost_usd, note FROM trials WHERE status='active' ORDER BY renews_ts")]
    except Exception: trials = []
    c.close()
    tracks = []
    for t, label in TRACKS.items():
        d = os.path.join(P4, [d for d in os.listdir(P4) if d.startswith(t + '-')][:1][0]) if any(
            x.startswith(t + '-') for x in os.listdir(P4)) else None
        plan = ''
        if d:
            for f in ['AGENTS.md']:
                p = os.path.join(d, f)
                if os.path.exists(p):
                    plan = ' / '.join([l.strip('# ').strip() for l in read(p, 8) if l.strip()][:3])
        tracks.append({'track': t, 'label': label,
                       'rung': (rungs.get(t) or {}).get('rung', 0),
                       'url': (rungs.get(t) or {}).get('url', ''),
                       'beat': beats.get(t), 'plan': plan[:140]})
    try:
        sp = c.execute("SELECT COALESCE(SUM(usd),0) FROM ledger WHERE kind='spend'").fetchone()[0]
        ea = c.execute("SELECT COALESCE(SUM(usd),0) FROM ledger WHERE kind='earn'").fetchone()[0]
        runway = {'spent': sp, 'earned': ea, 'left': 300.0 - sp + ea}
    except Exception: runway = {'spent': 0, 'earned': 0, 'left': 300.0}
    directives = '\n'.join(read(os.path.join(BASE, 'DIRECTIVES.md'), 40))
    ideas = [l for l in read(os.path.join(P4, 'IDEAS.md'), 30) if l.startswith('- ')]
    return {'tracks': tracks, 'events': events, 'proposals': props,
            'trials': trials, 'directives': directives, 'ideas': ideas, 'runway': runway}

INDEX = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>fleet board</title>
<style>:root{--bg:#fff;--fg:#111;--bd:#ccc;--hd:#eee}html.dark{--bg:#111418;--fg:#e6e6e6;--bd:#333;--hd:#1e2228}
body{font-family:system-ui;margin:8px;background:var(--bg);color:var(--fg);font-size:14px}
table{border-collapse:collapse;width:100%}td,th{border:1px solid var(--bd);padding:4px 6px;text-align:left}
th{background:var(--hd)}input,button{background:var(--bg);color:var(--fg);border:1px solid var(--bd)}
h3{margin:14px 0 4px}.r1{color:#3ddc84}.r0{color:#e0a63d}.blk{color:#e05555}pre{white-space:pre-wrap;font-size:12px}</style></head><body>
<h2>fleet board <small id=ts></small><button onclick="document.documentElement.classList.toggle('dark');localStorage.ft=document.documentElement.classList.contains('dark')?'d':'l'" style=float:right>dark/light</button></h2>
<script>if(localStorage.ft==='d')document.documentElement.classList.add('dark');</script>
<h3>tracks (plan → rung → last beat)</h3><table><thead><tr><th>track</th><th>rung</th><th>plan</th><th>beat</th><th>url</th><th>steer (paste to agent)</th></tr></thead><tbody id=t></tbody></table>
<h3>proposals (money gates)</h3><tbody><table><thead><tr><th>#</th><th>track</th><th>$</th><th>action</th><th>status</th></tr></thead><tbody id=p></tbody></table>
<h3>events (how plans changed)</h3><pre id=e></pre>
<h3>treasury (wheel)</h3><pre id=w></pre>
<h3>trials</h3><pre id=tr></pre>
<h3>ideas inbox</h3><pre id=i></pre>
<script>async function load(){const d=await (await fetch('/api/board')).json();
document.getElementById('ts').textContent=new Date().toISOString().slice(11,16)+'Z';
document.getElementById('t').innerHTML=d.tracks.map(t=>`<tr><td><b>${t.track}</b> ${t.label}</td><td class=${t.rung>0?'r1':'r0'}>${t.rung}</td><td>${t.plan}</td><td class=${t.beat&&t.beat.status==='blocked'?'blk':''}>${t.beat?t.beat.ts+' '+t.beat.status+' '+t.beat.note:''}</td><td>${t.url?`<a href=${t.url}>${t.url}</a>`:''}</td><td style=font-size:12px>pause ${t.track} · priority: ${t.track} · approve #</td></tr>`).join('');
document.getElementById('p').innerHTML=d.proposals.map(p=>`<tr><td>${p.id}</td><td>${p.track}</td><td>${p.usd}</td><td>${p.action} — ${p.reason}</td><td>${p.status}</td></tr>`).join('')||'<tr><td colspan=5>none</td></tr>';
document.getElementById('e').textContent=d.events.map(e=>`${e.ts} [${e.track}/${e.kind}] ${e.summary}`).join('\\n')||'none';
document.getElementById('w').textContent=`spent $${d.runway.spent.toFixed(2)} earned $${d.runway.earned.toFixed(2)} left $${d.runway.left.toFixed(2)} of $300`;
document.getElementById('tr').textContent=d.trials.map(t=>`${t.name} renews ${t.renews} $${t.usd} ${t.note}`).join('\\n')||'none';
document.getElementById('i').textContent=d.ideas.join('\\n');}
load();setInterval(load,60000);</script></body></html>"""

@app.get('/', response_class=HTMLResponse)
def index(): return INDEX

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('E062_PORT', '8322')))
