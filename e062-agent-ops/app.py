#!/usr/bin/env python3
"""e062 fleet board — plans, changes, execution. Port 8322."""
import os, sqlite3, subprocess, time
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
           'rowpad': 4, 'wrap': 1, 'density': 'comfortable', 'report': 'simple',
           'widgets': ''}
    for k in out:
        if k in d:
            if k in ('density', 'report', 'widgets'):
                out[k] = d[k]
            else:
                try: out[k] = int(d[k])
                except Exception: pass
    return out

def board_token():
    try: return open(os.path.expanduser('~/.config/e062/board_token')).read().strip()
    except Exception: return None

def need_token(req):
    tok = board_token()
    if not tok: return 'server token missing'
    got = (req.headers.get('x-token', '') or '').strip()
    if got != tok:
        try:
            ip = req.client.host if req.client else '?'
        except Exception:
            ip = '?'
        print(f"board auth fail from {ip}: got_len={len(got)} want_len={len(tok)}", flush=True)
        return ('bad token — press the token button (top-right) and re-enter '
                'the board token')
    return None

RUN_LOCK = '/tmp/e062-runner.lock'
RUNS_DIR = os.path.join(BASE, 'runs')
os.makedirs(RUNS_DIR, exist_ok=True)

def ensure_runs():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY AUTOINCREMENT, started_ts INTEGER, ended_ts INTEGER, scope TEXT, trigger TEXT, status TEXT DEFAULT 'running', summary TEXT DEFAULT '')")
    for col in ('tokens INTEGER', 'cost_usd REAL'):
        try: c.execute(f'ALTER TABLE runs ADD COLUMN {col}')
        except Exception: pass
    c.commit(); c.close()

ensure_runs()

def runner_running():
    # Lock-based (no pgrep self-match false positives): the lock is held
    # only while bin/runner.sh executes its leg body.
    try:
        r = subprocess.run(['flock', '-n', RUN_LOCK, 'true'],
                           capture_output=True, timeout=5)
        return r.returncode != 0
    except Exception:
        return False

def last_leg_tail(n=30):
    try:
        with open(os.path.join(BASE, 'runner.log')) as f:
            lines = f.read().split('\n')
        return '\n'.join([l for l in lines if l.strip()][-n:])
    except Exception:
        return ''

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
    c.close()
    c2 = sqlite3.connect(DB)
    paused = []
    try:
        paused = [r[0] for r in c2.execute('SELECT track FROM paused').fetchall()]
    except Exception: pass
    notes = [{'ts': ts, 'track': t, 'message': m} for ts, t, m in c2.execute(
        "SELECT datetime(ts,'unixepoch'), track, message FROM notes WHERE done=0 ORDER BY ts DESC LIMIT 20")]
    try: c2.execute('ALTER TABLE runs ADD COLUMN session TEXT')
    except Exception: pass
    try:
        runs = []
        for i, st, en, sc, tr, s, su, tok, co, se in c2.execute(
                "SELECT id, datetime(started_ts,'unixepoch'), " +
                "CASE WHEN ended_ts IS NULL THEN NULL ELSE datetime(ended_ts,'unixepoch') END, " +
                "scope, trigger, status, summary, tokens, cost_usd, session FROM runs ORDER BY id DESC LIMIT 10"):
            tok_s = None
            try:
                if tok and st:
                    t0 = time.mktime(time.strptime(st, '%Y-%m-%d %H:%M:%S'))
                    t1 = time.mktime(time.strptime(en, '%Y-%m-%d %H:%M:%S')) if en else time.time()
                    tok_s = round(tok / max(1, t1 - t0), 1)
            except Exception: pass
            runs.append({'id': i, 'started': st, 'ended': en, 'scope': sc,
                         'trigger': tr, 'status': s, 'summary': su,
                         'tokens': tok, 'tok_s': tok_s, 'cost_usd': co,
                         'session': se})
    except Exception: runs = []
    try:
        cur = c2.execute("SELECT id, datetime(started_ts,'unixepoch'), scope, trigger, status FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    except Exception: cur = None
    c2.close()
    runner_info = {'running': runner_running()}
    if cur:
        runner_info.update({'run_id': cur[0], 'started': cur[1], 'scope': cur[2],
                            'trigger': cur[3], 'status': cur[4]})
    directives = '\n'.join(read(os.path.join(BASE, 'DIRECTIVES.md'), 40))
    ideas = [l for l in read(os.path.join(P4, 'IDEAS.md'), 30) if l.startswith('- ')]
    return {'tracks': tracks, 'events': events, 'proposals': props,
            'trials': trials, 'directives': directives, 'ideas': ideas, 'runway': runway,
            'notes': notes, 'paused': paused, 'runs': runs, 'prefs': get_prefs(),
            'runner': runner_info, 'leg_tail': last_leg_tail()}

@app.get('/api/runstate')
def api_runstate():
    ensure_runs()
    c = sqlite3.connect(DB)
    try:
        last = c.execute(
            "SELECT id, started_ts, datetime(started_ts,'unixepoch'), scope, trigger, status, summary FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    except Exception: last = None
    c.close()
    live_sess = None
    if runner_running() and last and last[1]:
        # session file(s) touched since this leg started = this leg's sessions
        import glob as _g, json as _j
        live_sess = []
        root = os.path.expanduser('~/.pi/agent/sessions')
        for p in _g.glob(os.path.join(root, '*', '*.jsonl')):
            try:
                if int(os.path.getmtime(p)) < int(last[1]) - 60: continue
                o0 = _j.loads(open(p).readline())
                if isinstance(o0, dict) and o0.get('type') == 'session' and o0.get('id'):
                    sh = str(o0['id'])[:8]
                    if sh not in live_sess: live_sess.append(sh)
            except Exception: pass
            if len(live_sess) >= 4: break
    return {'ok': True, 'running': runner_running(),
            'live_session': (','.join(live_sess) if live_sess else None),
            'last': ({'id': last[0], 'started': last[2], 'scope': last[3],
                      'trigger': last[4], 'status': last[5], 'summary': last[6]} if last else None)}

@app.post('/api/run')
async def api_run(req: Request):
    # No token: tailnet-only board, and pause/resume/note are already open.
    # Worst case a stray tap costs one extra leg (cron runs 48/day anyway).
    # Money stays gated: /api/decide still requires the board token.
    try: d = await req.json()
    except Exception: return {'ok': False, 'error': 'bad json'}
    scope = (d.get('scope') or 'fleet').strip()
    if scope != 'fleet' and scope not in TRACKS:
        return {'ok': False, 'error': 'bad scope'}
    if runner_running():
        return {'ok': False, 'error': 'runner already running — wait for this leg to finish'}
    ensure_runs()
    c = sqlite3.connect(DB)
    cur = c.execute('INSERT INTO runs(started_ts, scope, trigger, status) VALUES (?,?,?,?)',
                    (int(time.time()), scope, 'board', 'queued'))
    rid = cur.lastrowid
    c.commit(); c.close()
    import os as _os
    env = dict(_os.environ, E062_TRIGGER='board', E062_FOCUS=scope, E062_RUN_ID=str(rid))
    try:
        subprocess.Popen(['nohup', os.path.join(BASE, 'bin', 'runner.sh')],
                         stdout=open(os.path.join(BASE, 'runner.log'), 'ab'),
                         stderr=subprocess.STDOUT, env=env,
                         start_new_session=True, cwd=BASE)
    except Exception as e:
        return {'ok': False, 'error': f'spawn failed: {e}'}
    return {'ok': True, 'run_id': rid}

@app.get('/api/leg/{rid}')
def api_leg(rid: int):
    # Full per-run leg output for the run cards (read-only, tailnet-only).
    p = os.path.join(RUNS_DIR, f'leg-{rid}.log')
    if not os.path.isfile(p):
        return {'ok': False, 'error': 'no full log for this run (predates capture)'}
    try:
        size = os.path.getsize(p)
        with open(p, 'rb') as f:
            if size > 200 * 1024:
                f.seek(size - 200 * 1024)
                tail = f.read().decode('utf-8', 'replace')
                return {'ok': True, 'truncated': True, 'log': '\u2026[tail]\n' + tail}
            return {'ok': True, 'truncated': False, 'log': f.read().decode('utf-8', 'replace')}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:100]}

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
    maxlen = {'widgets': 8000}
    for k in list(limits) + ['density', 'report', 'widgets']:
        if k in d:
            v = str(d[k])[:maxlen.get(k, 20)]
            if k == 'density':
                if v not in ('compact', 'comfortable'): continue
            elif k == 'report':
                if v not in ('simple', 'both', 'tech'): continue
            elif k == 'widgets':
                if v == '':
                    c.execute('INSERT OR REPLACE INTO prefs VALUES (?,?)', (k, ''))
                    continue
                try:
                    w = __import__('json').loads(v)
                    assert isinstance(w, list) and 1 <= len(w) <= 12
                    for x in w:
                        assert isinstance(x, dict) and 't' in x
                except Exception: continue
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
