#!/usr/bin/env python3
"""e063 fleet UI v2 — inbox-zero board over the e062 ops.db. Port 8325."""
import hashlib, json, os, secrets as _secrets, sqlite3, subprocess, time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse

BASE = os.path.dirname(os.path.abspath(__file__))
E062 = '/home/vuos/code/p4/e062-agent-ops'
DB = os.environ.get('E062_DB', os.path.join(E062, 'ops.db'))
P4 = '/home/vuos/code/p4'
TRACKS = {'e058': 'funding scanner', 'e059': 'valuations', 'e060': 'social radar',
          'e061': 'game suite', 'e062': 'agent ops', 'e063': 'fleet ui v2', 'runner': 'dispatcher legs'}
RUN_LOCK = '/tmp/e062-runner.lock'

app = FastAPI()

# ---- auth (same tables as e062, cookie shared so login works on both boards)
AUTH_COOKIE = 'e062sess'
AUTH_DAYS = 90

def _ensure_auth(c):
    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, pw TEXT, role TEXT DEFAULT 'viewer', created INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, uid INTEGER, created INTEGER, expires INTEGER)")

def _hash(pw, salt):
    return hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 200000).hex()

def current_user(req):
    try: tok = (req.cookies.get(AUTH_COOKIE) or '').strip()
    except Exception: tok = ''
    if not tok: return None
    c = sqlite3.connect(DB); _ensure_auth(c)
    r = c.execute('SELECT u.id, u.name, u.role, s.expires FROM sessions s JOIN users u ON u.id=s.uid WHERE s.token=?', (tok,)).fetchone()
    if not r: c.close(); return None
    if r[3] < int(time.time()):
        c.execute('DELETE FROM sessions WHERE token=?', (tok,)); c.commit()
        c.close(); return None
    c.close()
    return {'id': r[0], 'name': r[1], 'role': r[2]}

def _login_cookie(name, role, uid):
    tok = _secrets.token_hex(24)
    now = int(time.time())
    c = sqlite3.connect(DB); _ensure_auth(c)
    c.execute('INSERT INTO sessions VALUES (?,?,?,?)', (tok, uid, now, now + AUTH_DAYS * 86400))
    c.commit(); c.close()
    r = JSONResponse({'ok': True, 'name': name, 'role': role})
    r.set_cookie(AUTH_COOKIE, tok, max_age=AUTH_DAYS * 86400, httponly=True, samesite='lax')
    return r

def need_login(req):
    u = current_user(req)
    return (None, u) if u else ({'ok': False, 'error': 'login required — top right'}, None)

def need_admin(req):
    u = current_user(req)
    if not u: return {'ok': False, 'error': 'login required — top right'}, None
    if u['role'] != 'admin': return {'ok': False, 'error': 'admin only — ask the owner to approve'}, None
    return None, u

def get_prefs():
    c = sqlite3.connect(DB)
    try: rows = c.execute('SELECT key, value FROM prefs').fetchall()
    except Exception: rows = []
    c.close()
    d = {k: v for k, v in rows}
    out = {'report': 'simple', 'density': 'comfortable', 'font': 15}
    if d.get('report') in ('simple', 'both', 'tech'): out['report'] = d['report']
    if d.get('density') in ('compact', 'comfortable'): out['density'] = d['density']
    try: out['font'] = max(12, min(20, int(d.get('font', 15))))
    except Exception: pass
    return out

def runner_running():
    try:
        r = subprocess.run(['flock', '-n', RUN_LOCK, 'true'], capture_output=True, timeout=5)
        return r.returncode != 0
    except Exception:
        return False

def track_data(t):
    # DATA PULSE (copied pattern from e062): is it sampling, how fresh?
    # Never breaks the board: every reader guarded, unknown -> {}.
    try:
        if t == 'e058':
            c = sqlite3.connect(os.path.join(P4, 'e058-funding-scanner', 'data.db'))
            n, mx = c.execute('SELECT COUNT(*), MAX(ts) FROM funding').fetchone()
            c.close()
            return {'rows': n, 'last': mx or '', 'every': '15m'}
        if t == 'e059':
            dd = os.path.join(P4, 'e059-crypto-valuations', 'data')
            fs = [os.path.join(dd, f) for f in os.listdir(dd)]
            if not fs: return {}
            mt = max(os.path.getmtime(f) for f in fs)
            return {'files': len(fs), 'last': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mt)), 'every': '24h'}
        if t == 'e060':
            import json as _j
            r = _j.load(open(os.path.join(P4, 'e060-social-memecoin-radar', 'data', 'rotation.json')))
            calls = os.path.join(P4, 'e060-social-memecoin-radar', 'paper', 'calls.jsonl')
            n = sum(1 for _ in open(calls)) if os.path.isfile(calls) else 0
            return {'days': n, 'last': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(r.get('ts', 0))), 'every': '24h'}
        if t in ('e062', 'e063', 'runner'):
            c = sqlite3.connect(DB)
            n = c.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
            mx = c.execute('SELECT MAX(ended_ts) FROM runs').fetchone()[0] or 0
            c.close()
            return {'legs': n, 'last': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mx)) if mx else '', 'every': '30m'}
    except Exception:
        pass
    return {}

def _state():
    c = sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS focus(track TEXT PRIMARY KEY, text TEXT, ts INTEGER)')
    focus = {t: x for t, x in c.execute('SELECT track, text FROM focus').fetchall()}
    rungs = {t: (r, u, no) for t, r, u, no in c.execute('SELECT track, rung, url, note FROM rungs')}
    beats = {t: (ts, st, no) for t, ts, st, no in
             c.execute("SELECT track, datetime(ts,'unixepoch'), status, note FROM heartbeats")}
    events = [{'ts': ts, 'track': t, 'kind': k, 'summary': s} for ts, t, k, s in
              c.execute("SELECT datetime(ts,'unixepoch'), track, kind, summary FROM events ORDER BY ts DESC LIMIT 30")]
    props = [{'id': i, 'ts': ts, 'track': t, 'usd': u, 'action': a, 'reason': r, 'status': s}
             for i, ts, t, u, a, r, s in c.execute(
                 'SELECT id, datetime(ts,\'unixepoch\'), track, amount_usd, action, reason, status FROM proposals ORDER BY id DESC LIMIT 20')]
    try:
        trials = [{'name': n, 'renews': rd, 'usd': co, 'note': no} for n, rd, co, no in
                  c.execute("SELECT name, datetime(renews_ts,'unixepoch'), cost_usd, note FROM trials WHERE status='active' ORDER BY renews_ts")]
    except Exception: trials = []
    notes = [{'ts': ts, 'track': t, 'message': m} for ts, t, m in c.execute(
        "SELECT datetime(ts,'unixepoch'), track, message FROM notes WHERE done=0 ORDER BY ts DESC LIMIT 30")]
    try: paused = [r[0] for r in c.execute('SELECT track FROM paused').fetchall()]
    except Exception: paused = []
    try:
        sp = c.execute("SELECT COALESCE(SUM(usd),0) FROM ledger WHERE kind='spend'").fetchone()[0]
        ea = c.execute("SELECT COALESCE(SUM(usd),0) FROM ledger WHERE kind='earn'").fetchone()[0]
    except Exception: sp, ea = 0, 0
    try:
        runs = [{'id': i, 'started': st, 'ended': en, 'scope': sc, 'trigger': tr,
                 'status': s, 'summary': su, 'tokens': tok, 'cost_usd': co, 'session': se}
                for i, st, en, sc, tr, s, su, tok, co, se in c.execute(
                    "SELECT id, datetime(started_ts,'unixepoch'), " +
                    "CASE WHEN ended_ts IS NULL THEN NULL ELSE datetime(ended_ts,'unixepoch') END, " +
                    "scope, trigger, status, summary, tokens, cost_usd, session FROM runs ORDER BY id DESC LIMIT 20")]
    except Exception: runs = []
    try:
        cur = c.execute('SELECT id, datetime(started_ts,\'unixepoch\'), scope, trigger, status FROM runs ORDER BY id DESC LIMIT 1').fetchone()
    except Exception: cur = None
    c.close()
    tracks = []
    for t, label in TRACKS.items():
        rung, url, _note = rungs.get(t, (0, '', ''))
        b = beats.get(t)
        tracks.append({'track': t, 'label': label, 'rung': rung or 0, 'url': url or '',
                       'beat': ({'ts': b[0], 'status': b[1], 'note': b[2]} if b else None),
                       'focus': focus.get(t, ''), 'paused': t in paused,
                       'data': track_data(t)})
    try:
        directives = '\n'.join(open(os.path.join(E062, 'DIRECTIVES.md')).read().split('\n')[:25])
    except Exception: directives = ''
    try:
        ideas = [l for l in open(os.path.join(P4, 'IDEAS.md')).read().split('\n')[:30] if l.startswith('- ')]
    except Exception: ideas = []
    runner = {'running': runner_running()}
    if cur: runner.update({'run_id': cur[0], 'started': cur[1], 'scope': cur[2], 'trigger': cur[3], 'status': cur[4]})
    return {'tracks': tracks, 'events': events, 'proposals': props, 'trials': trials,
            'notes': notes, 'paused': paused, 'runs': runs,
            'runway': {'spent': sp, 'earned': ea, 'left': 300.0 - sp + ea},
            'directives': directives, 'ideas': ideas,
            'prefs': get_prefs(), 'runner': runner, 'now': int(time.time())}

@app.get('/api/state')
def api_state(req: Request):
    s = _state()
    u = current_user(req)
    s['me'] = ({'name': u['name'], 'role': u['role']} if u else None)
    return s

@app.get('/api/stream')
def api_stream(req: Request):
    # ponytail: no redis/pubsub — poll mtimes, push full state only on change.
    # me is snapshotted at connect (EventSource sends cookies on connect);
    # the client merges and never lets a push drop auth (the logout bug).
    u = current_user(req)
    me = ({'name': u['name'], 'role': u['role']} if u else None)
    def gen():
        last = ''
        yield 'retry: 3000\n\n'
        for _ in range(600):  # ~30min per connection, client reconnects
            try:
                sig = str(os.path.getmtime(DB)) + ':' + str(os.path.getsize(DB))
            except Exception:
                sig = ''
            if sig != last:
                last = sig
                s = _state(); s['me'] = me
                yield 'data: ' + json.dumps(s) + '\n\n'
            else:
                yield ': ping\n\n'
            time.sleep(3)
    return StreamingResponse(gen(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})

@app.post('/api/register')
async def api_register(req: Request):
    try: d = await req.json()
    except Exception: return {'ok': False, 'error': 'bad json'}
    name, pw = str(d.get('name') or '').strip()[:32], str(d.get('pw') or '')
    if len(name) < 2 or len(pw) < 6: return {'ok': False, 'error': 'name 2+ chars, password 6+ chars'}
    c = sqlite3.connect(DB); _ensure_auth(c)
    role = 'admin' if c.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0 else 'viewer'
    salt = _secrets.token_hex(8)
    try:
        cur = c.execute('INSERT INTO users(name, pw, role, created) VALUES (?,?,?,?)',
                        (name, _hash(pw, salt) + ':' + salt, role, int(time.time())))
        uid = cur.lastrowid; c.commit()
    except sqlite3.IntegrityError:
        c.close(); return {'ok': False, 'error': 'name taken — login instead'}
    c.close()
    return _login_cookie(name, role, uid)

@app.post('/api/login')
async def api_login(req: Request):
    try: d = await req.json()
    except Exception: return {'ok': False, 'error': 'bad json'}
    name, pw = str(d.get('name') or '').strip()[:32], str(d.get('pw') or '')
    c = sqlite3.connect(DB); _ensure_auth(c)
    r = c.execute('SELECT id, pw, role FROM users WHERE name=?', (name,)).fetchone()
    c.close()
    if not r: return {'ok': False, 'error': 'no such account — register first'}
    try: want, salt = r[1].split(':')
    except Exception: return {'ok': False, 'error': 'login broken — re-register'}
    if _hash(pw, salt) != want: return {'ok': False, 'error': 'wrong password'}
    return _login_cookie(name, r[2], r[0])

@app.post('/api/logout')
async def api_logout(req: Request):
    try: tok = (req.cookies.get(AUTH_COOKIE) or '').strip()
    except Exception: tok = ''
    if tok:
        c = sqlite3.connect(DB); _ensure_auth(c)
        c.execute('DELETE FROM sessions WHERE token=?', (tok,)); c.commit(); c.close()
    r = JSONResponse({'ok': True}); r.delete_cookie(AUTH_COOKIE); return r

@app.post('/api/note')
async def api_note(req: Request):
    err, _ = need_login(req)
    if err: return err
    d = await req.json()
    track, msg = (d.get('track') or '').strip(), (d.get('message') or '').strip()[:500]
    if track not in TRACKS or not msg: return {'ok': False, 'error': 'need track + message'}
    c = sqlite3.connect(DB)
    c.execute('INSERT INTO notes VALUES (?,?,?,0)', (int(time.time()), track, msg))
    c.commit(); c.close()
    return {'ok': True}

@app.post('/api/pause')
async def api_pause(req: Request):
    err, _ = need_login(req)
    if err: return err
    d = await req.json(); track = (d.get('track') or '').strip()
    if track not in TRACKS: return {'ok': False, 'error': 'bad track'}
    c = sqlite3.connect(DB); ts = int(time.time())
    c.execute('INSERT OR REPLACE INTO paused VALUES (?,?,?)', (track, ts, 'board-v2'))
    c.execute('INSERT INTO events VALUES (?,?,?,?,?)', (ts, track, 'pause', 'paused from board v2', f'pause:{track}:{ts}'))
    c.commit(); c.close(); return {'ok': True}

@app.post('/api/resume')
async def api_resume(req: Request):
    err, _ = need_login(req)
    if err: return err
    d = await req.json(); track = (d.get('track') or '').strip()
    if track not in TRACKS: return {'ok': False, 'error': 'bad track'}
    c = sqlite3.connect(DB); ts = int(time.time())
    c.execute('DELETE FROM paused WHERE track=?', (track,))
    c.execute('INSERT INTO events VALUES (?,?,?,?,?)', (ts, track, 'resume', 'resumed from board v2', f'resume:{track}:{ts}'))
    c.commit(); c.close(); return {'ok': True}

@app.post('/api/decide')
async def api_decide(req: Request):
    err, _ = need_admin(req)
    if err: return err
    d = await req.json()
    try: pid, verdict = int(d.get('id')), d.get('verdict')
    except Exception: return {'ok': False, 'error': 'need id + verdict'}
    if verdict not in ('approved', 'rejected'): return {'ok': False, 'error': 'verdict?'}
    c = sqlite3.connect(DB)
    c.execute('UPDATE proposals SET status=?, decided_ts=? WHERE id=?', (verdict, int(time.time()), pid))
    c.commit(); c.close(); return {'ok': True}

@app.post('/api/run')
async def api_run(req: Request):
    err, _ = need_login(req)
    if err: return err
    try: d = await req.json()
    except Exception: return {'ok': False, 'error': 'bad json'}
    scope = (d.get('scope') or 'fleet').strip()
    if scope != 'fleet' and scope not in TRACKS: return {'ok': False, 'error': 'bad scope'}
    if runner_running(): return {'ok': False, 'error': 'runner already running — wait for this leg to finish'}
    c = sqlite3.connect(DB)
    cur = c.execute('INSERT INTO runs(started_ts, scope, trigger, status) VALUES (?,?,?,?)',
                    (int(time.time()), scope, 'board-v2', 'queued'))
    rid = cur.lastrowid; c.commit(); c.close()
    env = dict(os.environ, E062_TRIGGER='board-v2', E062_FOCUS=scope, E062_RUN_ID=str(rid))
    try:
        subprocess.Popen(['nohup', os.path.join(E062, 'bin', 'runner.sh')],
                         stdout=open(os.path.join(E062, 'runner.log'), 'ab'),
                         stderr=subprocess.STDOUT, env=env, start_new_session=True, cwd=E062)
    except Exception as e:
        return {'ok': False, 'error': f'spawn failed: {e}'}
    return {'ok': True, 'run_id': rid}

@app.get('/api/leg/{rid}')
def api_leg(rid: int):
    p = os.path.join(E062, 'runs', f'leg-{rid}.log')
    if not os.path.isfile(p): return {'ok': False, 'error': 'no full log for this run'}
    size = os.path.getsize(p)
    with open(p, 'rb') as f:
        if size > 200 * 1024:
            f.seek(size - 200 * 1024)
            return {'ok': True, 'truncated': True, 'log': '…[tail]\n' + f.read().decode('utf-8', 'replace')}
        return {'ok': True, 'truncated': False, 'log': f.read().decode('utf-8', 'replace')}

@app.post('/api/prefs')
async def api_prefs(req: Request):
    err, _ = need_login(req)
    if err: return err
    d = await req.json()
    c = sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS prefs(key TEXT PRIMARY KEY, value TEXT)')
    if d.get('report') in ('simple', 'both', 'tech'):
        c.execute('INSERT OR REPLACE INTO prefs VALUES (?,?)', ('report', d['report']))
    if d.get('density') in ('compact', 'comfortable'):
        c.execute('INSERT OR REPLACE INTO prefs VALUES (?,?)', ('density', d['density']))
    try:
        f = max(12, min(20, int(d.get('font'))))
        c.execute('INSERT OR REPLACE INTO prefs VALUES (?,?)', ('font', str(f)))
    except Exception: pass
    c.commit(); c.close(); return {'ok': True}

_STARTED = int(time.time())
try:
    _RUN_COMMIT = subprocess.run(['git', 'log', '-1', '--format=%h', '--', 'e063-fleet-ui'],
                                 capture_output=True, text=True, cwd=P4).stdout.strip() or '?'
except Exception:
    _RUN_COMMIT = '?'

def repo_state():
    try:
        head = subprocess.run(['git', 'log', '-1', '--format=%h', '--', 'e063-fleet-ui'],
                              capture_output=True, text=True, cwd=P4).stdout.strip() or '?'
        dirty = subprocess.run(['git', 'status', '--short', '--', 'e063-fleet-ui/app.py',
                                'e063-fleet-ui/static/app.js', 'e063-fleet-ui/static/index.html',
                                'e063-fleet-ui/static/style.css', 'e063-fleet-ui/tests/check.sh'],
                               capture_output=True, text=True, cwd=P4).stdout.strip()
        return head, bool(dirty)
    except Exception:
        return '?', False

@app.get('/api/version')
def api_version():
    latest, dirty = repo_state()
    return {'ok': True, 'track': 'e063', 'running': _RUN_COMMIT,
            'latest': latest, 'stale': _RUN_COMMIT != latest,
            'dirty': dirty, 'started_ts': _STARTED}

@app.get('/', response_class=HTMLResponse)
def index():
    return HTMLResponse(open(os.path.join(BASE, 'static', 'index.html')).read(),
                        headers={'Cache-Control': 'no-store'})

for _f in ('app.js', 'style.css'):
    @app.get('/' + _f)
    def _static(_f=_f):
        mt = 'application/javascript' if _f.endswith('.js') else 'text/css'
        return FileResponse(os.path.join(BASE, 'static', _f), media_type=mt,
                            headers={'Cache-Control': 'no-store'})

if __name__ == '__main__':
    import uvicorn
    _crt = os.path.expanduser('~/.config/e062/tail.crt')
    _key = os.path.expanduser('~/.config/e062/tail.key')
    _ssl = {'ssl_certfile': _crt, 'ssl_keyfile': _key} if (
        os.path.isfile(_crt) and os.path.isfile(_key)) else {}
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('E063_PORT', '8325')), **_ssl)
