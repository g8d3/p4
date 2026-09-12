#!/usr/bin/env python3
"""e062 fleet board — plans, changes, execution. Port 8322."""
import os, sqlite3
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get('E062_DB', os.path.join(BASE, 'ops.db'))
P4 = '/home/vuos/code/p4'
TRACKS = {'e058': 'funding scanner', 'e059': 'valuations', 'e060': 'social radar',
          'e061': 'game suite', 'e062': 'agent ops', 'runner': 'dispatcher legs'}

def get_prefs():
    import sqlite3
    c = sqlite3.connect(DB)
    try:
        rows = c.execute('SELECT key, value FROM prefs').fetchall()
    except Exception:
        rows = []
    c.close()
    d = {k: v for k, v in rows}
    out = {'font': 14, 'planw': 340, 'beatw': 220, 'urlw': 200, 'ctrlw': 220,
           'rowpad': 4, 'wrap': 1, 'density': 'comfortable'}
    for k in out:
        if k in d:
            try: out[k] = int(d[k])
            except Exception: out[k] = d[k] if k == 'density' else out[k]
    return out

def board_token():
    try: return open(os.path.expanduser('~/.config/e062/board_token')).read().strip()
    except Exception: return None

def need_token(req):
    tok = board_token()
    if not tok: return 'server token missing'
    if req.headers.get('x-token', '') != tok: return 'bad token'
    return None

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
    _notes_anchor = None
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
    c2 = sqlite3.connect(DB)
    paused = []
    try:
        paused = [r[0] for r in c2.execute('SELECT track FROM paused').fetchall()]
    except Exception: pass
    notes = [{'ts': ts, 'track': t, 'message': m} for ts, t, m in c2.execute(
        "SELECT datetime(ts,'unixepoch'), track, message FROM notes WHERE done=0 ORDER BY ts DESC LIMIT 20")]
    c2.close()
    directives = '\n'.join(read(os.path.join(BASE, 'DIRECTIVES.md'), 40))
    ideas = [l for l in read(os.path.join(P4, 'IDEAS.md'), 30) if l.startswith('- ')]
    return {'tracks': tracks, 'events': events, 'proposals': props,
            'trials': trials, 'directives': directives, 'ideas': ideas, 'runway': runway,
            'notes': notes, 'paused': paused}

@app.post('/api/pause')
async def api_pause(req: Request):
    d = await req.json()
    track = (d.get('track') or '').strip()
    if track not in TRACKS: return {'ok': False, 'error': 'bad track'}
    import sqlite3, time
    c = sqlite3.connect(DB)
    c.execute('INSERT OR REPLACE INTO paused VALUES (?,?,?)', (track, int(time.time()), 'board'))
    ts = int(time.time())
    c.execute('INSERT INTO events VALUES (?,?,?,?,?)',
              (ts, track, 'pause', 'paused from board', f'pause:{track}:{ts}'))
    c.commit(); c.close()
    return {'ok': True}

@app.post('/api/resume')
async def api_resume(req: Request):
    d = await req.json()
    track = (d.get('track') or '').strip()
    if track not in TRACKS: return {'ok': False, 'error': 'bad track'}
    import sqlite3, time
    c = sqlite3.connect(DB)
    c.execute('DELETE FROM paused WHERE track=?', (track,))
    ts = int(time.time())
    c.execute('INSERT INTO events VALUES (?,?,?,?,?)',
              (ts, track, 'resume', 'resumed from board', f'resume:{track}:{ts}'))
    c.commit(); c.close()
    return {'ok': True}

@app.post('/api/decide')
async def api_decide(req: Request):
    err = need_token(req)
    if err: return {'ok': False, 'error': err}
    d = await req.json()
    try: pid, verdict = int(d.get('id')), d.get('verdict')
    except Exception: return {'ok': False, 'error': 'need id + verdict'}
    if verdict not in ('approved', 'rejected'): return {'ok': False, 'error': 'verdict?'}
    import sqlite3, time
    c = sqlite3.connect(DB)
    c.execute('UPDATE proposals SET status=?, decided_ts=? WHERE id=?', (verdict, int(time.time()), pid))
    c.commit(); c.close()
    return {'ok': True}

@app.get('/api/prefs')
def api_prefs_get():
    return {'ok': True, 'prefs': get_prefs()}

@app.post('/api/prefs')
async def api_prefs_set(req: Request):
    d = await req.json()
    import sqlite3
    c = sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS prefs(key TEXT PRIMARY KEY, value TEXT)')
    limits = {'font': (10, 22), 'planw': (120, 800), 'beatw': (80, 600),
              'urlw': (80, 600), 'ctrlw': (120, 600), 'rowpad': (0, 14), 'wrap': (0, 1)}
    for k in list(limits) + ['density']:
        if k in d:
            v = str(d[k])[:20]
            if k == 'density':
                if v not in ('compact', 'comfortable'): continue
            else:
                try: v = str(max(limits[k][0], min(int(v), limits[k][1])))
                except Exception: continue
            c.execute('INSERT OR REPLACE INTO prefs VALUES (?,?)', (k, v))
    c.commit(); c.close()
    return {'ok': True}

@app.post('/api/note')
async def add_note(req: Request):
    d = await req.json()
    track, message = (d.get('track') or '').strip(), (d.get('message') or '').strip()[:500]
    if not track or not message or track not in TRACKS:
        return {'ok': False, 'error': 'need track + message'}
    import sqlite3, time
    c = sqlite3.connect(DB)
    c.execute('INSERT INTO notes VALUES (?,?,?,0)', (int(time.time()), track, message))
    c.commit(); c.close()
    return {'ok': True}

INDEX = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>fleet board</title>
<style>:root{--bg:#fff;--fg:#111;--bd:#ccc;--hd:#eee}html.dark{--bg:#111418;--fg:#e6e6e6;--bd:#333;--hd:#1e2228}
body{font-family:system-ui;margin:8px;background:var(--bg);color:var(--fg);font-size:14px}
table{border-collapse:collapse;width:100%}td,th{border:1px solid var(--bd);padding:4px 6px;text-align:left}
th{background:var(--hd)}input,button{background:var(--bg);color:var(--fg);border:1px solid var(--bd)}
h3{margin:14px 0 4px}.r1{color:#3ddc84}.r0{color:#e0a63d}.blk{color:#e05555}pre{white-space:pre-wrap;font-size:12px}</style></head><body>
<h2>fleet board <small id=ts></small><button onclick="document.documentElement.classList.toggle('dark');localStorage.ft=document.documentElement.classList.contains('dark')?'d':'l'" style=float:right>dark/light</button></h2>
<script>if(localStorage.ft==='d')document.documentElement.classList.add('dark');</script>
<h3>tracks (plan → rung → last beat)</h3><table><thead><tr><th>track</th><th>rung</th><th>plan</th><th>beat</th><th>url</th><th>note to project</th></tr></thead><tbody id=t></tbody></table>
<h3>proposals (money gates)</h3><tbody><table><thead><tr><th>#</th><th>track</th><th>$</th><th>action</th><th>status</th></tr></thead><tbody id=p></tbody></table>
<h3>events (how plans changed)</h3><pre id=e></pre>
<h3>treasury (wheel)</h3><pre id=w></pre>
<h3>owner → project notes</h3><pre id=no></pre>
<h3>trials</h3><pre id=tr></pre>
<h3>ideas inbox</h3><pre id=i></pre>
<script>async function load(){const d=await (await fetch('/api/board')).json();
document.getElementById('ts').textContent=new Date().toISOString().slice(11,16)+'Z';
document.getElementById('t').innerHTML=d.tracks.map(t=>`<tr><td><b>${t.track}</b> ${t.label}</td><td class=${t.rung>0?'r1':'r0'}>${t.rung}</td><td>${t.plan}</td><td class=${t.beat&&t.beat.status==='blocked'?'blk':''}>${t.beat?t.beat.ts+' '+t.beat.status+' '+t.beat.note:''}</td><td>${t.url?`<a href=${t.url}>${t.url}</a>`:''}</td><td style=font-size:12px><input id=n-${t.track} placeholder="what's missing…" style=width:120px><button onclick="sendNote('${t.track}',this)">send</button> <button onclick="togPause('${t.track}',this)">${(d.paused||[]).includes(t.track)?'resume':'pause'}</button></td></tr>`).join('');
document.getElementById('p').innerHTML=d.proposals.map(p=>`<tr><td>${p.id}</td><td>${p.track}</td><td>${p.usd}</td><td>${p.action} — ${p.reason}</td><td>${p.status}${p.status==='pending'?` <button onclick="decide(${p.id},'approved',this)">approve</button><button onclick="decide(${p.id},'rejected',this)">reject</button>`:''}</td></tr>`).join('')||'<tr><td colspan=5>none</td></tr>';
document.getElementById('e').textContent=d.events.map(e=>`${e.ts} [${e.track}/${e.kind}] ${e.summary}`).join('\\n')||'none';
document.getElementById('w').textContent=`spent $${d.runway.spent.toFixed(2)} earned $${d.runway.earned.toFixed(2)} left $${d.runway.left.toFixed(2)} of $300`;
document.getElementById('tr').textContent=d.trials.map(t=>`${t.name} renews ${t.renews} $${t.usd} ${t.note}`).join('\\n')||'none';
document.getElementById('i').textContent=d.ideas.join('\\n');
window._paused=d.paused||[];
document.getElementById('no').textContent=d.notes.map(n=>`${n.ts} [${n.track}] ${n.message}`).join('\\n')||'none';}
function tok(){let t=localStorage.bt;if(!t){t=prompt('board token — shown once in owner chat:');if(t)localStorage.bt=t;}return t||'';}
async function ctl(path,body,btn){const t=tok();if(!t)return;btn.textContent='…';
const r=await (await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Token':t},body:JSON.stringify(body)})).json();
if(r.ok){btn.textContent='done ✓';load();}else{btn.textContent='error';alert(r.error||'failed');}}
async function togPause(t,btn){const paused=(window._paused||[]).includes(t);await ctl(paused?'/api/resume':'/api/pause',{track:t},btn);}
async function decide(id,v,btn){await ctl('/api/decide',{id:id,verdict:v},btn);}
async function sendNote(t,btn){const v=document.getElementById('n-'+t).value.trim();if(!v)return;
const r=await (await fetch('/api/note',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({track:t,message:v})})).json();
if(r.ok){btn.textContent='sent ✓';document.getElementById('n-'+t).value='';setTimeout(()=>{btn.textContent='send';load();},800);}else{alert(r.error||'failed');}}
load();setInterval(load,60000);</script></body></html>"""

@app.get('/app.js')
def appjs():
    return FileResponse(os.path.join(BASE, 'static', 'app.js'), media_type='application/javascript',
                         headers={'Cache-Control': 'no-store'})

@app.get('/', response_class=HTMLResponse)
def index():
    return HTMLResponse(open(os.path.join(BASE, 'static', 'board.html')).read(),
                         headers={'Cache-Control': 'no-store'})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('E062_PORT', '8322')))
