#!/usr/bin/env python3
"""e062 fleet board — plans, changes, execution. Port 8322."""
import hashlib, json, os, secrets as _secrets, sqlite3, subprocess, time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get('E062_DB', os.path.join(BASE, 'ops.db'))
P4 = '/home/vuos/code/p4'
TRACKS = {'e058': 'funding scanner', 'e059': 'valuations', 'e060': 'social radar',
          'e061': 'game suite', 'e062': 'agent ops', 'e063': 'fleet ui v2', 'runner': 'dispatcher legs'}

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

AUTH_COOKIE = 'e062sess'
AUTH_DAYS = 90

def auth_tables(c):
    c.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, pw TEXT, role TEXT DEFAULT \'viewer\', created INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, uid INTEGER, created INTEGER, expires INTEGER)')

def _hash(pw, salt):
    return hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 200000).hex()

def current_user(req):
    try: tok = (req.cookies.get(AUTH_COOKIE) or '').strip()
    except Exception: tok = ''
    if not tok: return None
    c = sqlite3.connect(DB)
    auth_tables(c)
    r = c.execute('SELECT u.id, u.name, u.role, s.expires FROM sessions s JOIN users u ON u.id=s.uid WHERE s.token=?', (tok,)).fetchone()
    if not r:
        c.close(); return None
    if r[3] < int(time.time()):
        c.execute('DELETE FROM sessions WHERE token=?', (tok,)); c.commit()
        c.close(); return None
    c.close()
    return {'id': r[0], 'name': r[1], 'role': r[2]}

def need_login(req):
    u = current_user(req)
    return (None, u) if u else ({'ok': False, 'error': 'login required — top right'}, None)

def need_admin(req):
    u = current_user(req)
    if not u: return {'ok': False, 'error': 'login required — top right'}, None
    if u['role'] != 'admin': return {'ok': False, 'error': 'admin only — ask the owner to approve'}, None
    return None, u

def _login_cookie(name, role, uid):
    tok = _secrets.token_hex(24)
    now = int(time.time())
    c = sqlite3.connect(DB)
    auth_tables(c)
    c.execute('INSERT INTO sessions VALUES (?,?,?,?)', (tok, uid, now, now + AUTH_DAYS * 86400))
    c.commit(); c.close()
    r = JSONResponse({'ok': True, 'name': name, 'role': role})
    r.set_cookie(AUTH_COOKIE, tok, max_age=AUTH_DAYS * 86400, httponly=True, samesite='lax')
    return r

RUN_LOCK = '/tmp/e062-runner.lock'
RUNS_DIR = os.path.join(BASE, 'runs')
os.makedirs(RUNS_DIR, exist_ok=True)

def ensure_runs():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY AUTOINCREMENT, started_ts INTEGER, ended_ts INTEGER, scope TEXT, trigger TEXT, status TEXT DEFAULT 'running', summary TEXT DEFAULT '')")
    for col in ('tokens INTEGER', 'cost_usd REAL', 'start_tokens INTEGER', 'end_tokens INTEGER'):
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

def track_git_head(subdir):
    try:
        return subprocess.run(['git', 'log', '-1', '--format=%h', '--', subdir],
                                capture_output=True, text=True, cwd=P4).stdout.strip() or ''
    except Exception:
        return ''

def get_channels(c):
    try:
        c.execute('CREATE TABLE IF NOT EXISTS channels(track TEXT PRIMARY KEY, best_sha TEXT DEFAULT \'\', best_note TEXT DEFAULT \'\', best_ts INTEGER DEFAULT 0, next_sha TEXT DEFAULT \'\', next_note TEXT DEFAULT \'\', next_ts INTEGER DEFAULT 0)')
        rows = {t: {'best': b or '', 'best_note': bn or '', 'next': n or '', 'next_note': nn or ''}
                for t, b, bn, n, nn in c.execute('SELECT track, best_sha, best_note, next_sha, next_note FROM channels').fetchall()}
    except Exception:
        rows = {}
    return rows

def _grade_eta(pend, due_ts):
    # one-line countdown chip text, e.g. '68 to grade (~14h)'. Never raises.
    try:
        s = int(due_ts - time.time())
        if s <= 0:
            return '%d grading now' % pend
        if s < 7200:
            return '%d to grade (~%dm)' % (pend, max(1, s // 60))
        if s < 172800:
            return '%d to grade (~%dh)' % (pend, s // 3600)
        return '%d to grade (~%dd)' % (pend, s // 86400)
    except Exception:
        return ''

def track_data(t):
    # Freshness badge: is this project building a time series, and is it fresh?
    # Never breaks the board: every reader is guarded, unknown -> {}.
    # grade = countdown chip: how many paper calls wait + when the next grades.
    try:
        if t == 'e058':
            import json as _j  # noqa: F401 (symmetry with siblings)
            c = sqlite3.connect(os.path.join(P4, 'e058-funding-scanner', 'data.db'))
            n, mx = c.execute('SELECT COUNT(*), MAX(ts) FROM funding').fetchone()
            try:
                rows = c.execute('SELECT p.logged_ts FROM paper_calls p LEFT JOIN paper_outcomes o ON o.call_date=p.call_date AND o.coin=p.coin WHERE o.coin IS NULL').fetchall()
            except Exception:
                rows = []
            c.close()
            out = {'rows': n, 'last': mx or '', 'every': '15m'}
            try:
                import datetime as _dt
                due = max(_dt.datetime.strptime(r[0], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=_dt.timezone.utc).timestamp() + 86400 for r in rows) if rows else 0
                if rows and due:
                    out['grade'] = _grade_eta(len(rows), due)
            except Exception:
                pass
            return out
        if t == 'e059':
            import json as _j
            dd = os.path.join(P4, 'e059-crypto-valuations', 'data')
            fs = [os.path.join(dd, f) for f in os.listdir(dd)]
            if not fs: return {}
            mt = max(os.path.getmtime(f) for f in fs)
            out = {'files': len(fs), 'last': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mt)), 'every': '24h'}
            try:
                pend, first_ts = 0, 0
                for line in open(os.path.join(dd, 'cheap_calls.jsonl')):
                    try:
                        o = _j.loads(line)
                    except Exception:
                        continue
                    if o.get('resolved') is None:
                        pend += 1
                        try:
                            import datetime as _dt
                            ts = _dt.datetime.strptime(o.get('date', ''), '%Y-%m-%d').replace(tzinfo=_dt.timezone.utc).timestamp()
                            first_ts = min(first_ts, ts) if first_ts else ts
                        except Exception:
                            pass
                if pend and first_ts:
                    out['grade'] = _grade_eta(pend, first_ts + 7 * 86400)
            except Exception:
                pass
            return out
        if t == 'e060':
            import json as _j
            r = _j.load(open(os.path.join(P4, 'e060-social-memecoin-radar', 'data', 'rotation.json')))
            calls = os.path.join(P4, 'e060-social-memecoin-radar', 'paper', 'calls.jsonl')
            n = sum(1 for _ in open(calls)) if os.path.isfile(calls) else 0
            out = {'days': n, 'last': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(r.get('ts', 0))), 'every': '24h'}
            try:
                sc = _j.load(open(os.path.join(P4, 'e060-social-memecoin-radar', 'paper', 'score.json')))
                pend = int(sc.get('pending', 0))
                if pend:
                    last_ts = 0
                    for line in open(calls):
                        try:
                            last_ts = max(last_ts, int(_j.loads(line).get('ts', 0)))
                        except Exception:
                            pass
                    if last_ts:
                        out['grade'] = _grade_eta(pend, last_ts + 86400)
            except Exception:
                pass
            return out
        if t in ('e062', 'e063', 'runner'):
            c = sqlite3.connect(DB)
            n = c.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
            mx = c.execute('SELECT MAX(ended_ts) FROM runs').fetchone()[0] or 0
            c.close()
            return {'legs': n, 'last': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mx)) if mx else '', 'every': '30m'}
    except Exception:
        pass
    return {}

@app.get('/api/board')
def board(req: Request):
    c = sqlite3.connect(DB)
    try:
        c.execute('CREATE TABLE IF NOT EXISTS focus(track TEXT PRIMARY KEY, text TEXT, ts INTEGER)')
        focus = {t: x for t, x in c.execute('SELECT track, text FROM focus').fetchall()}
    except Exception:
        focus = {}
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
    chans = get_channels(c)
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
        ch = chans.get(t) or {}
        if not ch.get('best') and d:
            head = track_git_head(os.path.basename(d))
            if head:
                ch = {'best': head, 'best_note': 'auto-seed', 'next': head, 'next_note': 'auto-seed'}
                try:
                    c.execute('INSERT OR REPLACE INTO channels VALUES (?,?,?,?,?,?,?)', (t, head, 'auto-seed', int(time.time()), head, 'auto-seed', int(time.time())))
                    c.commit()
                except Exception:
                    pass
        tracks.append({'track': t, 'label': label,
                       'rung': (rungs.get(t) or {}).get('rung', 0),
                       'rung_note': (rungs.get(t) or {}).get('note', ''),
                       'rung_ts': (rungs.get(t) or {}).get('ts', ''),
                       'url': (rungs.get(t) or {}).get('url', ''),
                       'beat': beats.get(t), 'plan': plan[:140],
                       'focus': focus.get(t, ''),
                       'best': ch.get('best', ''), 'best_note': ch.get('best_note', ''),
                       'next': ch.get('next', ''), 'next_note': ch.get('next_note', ''),
                       'data': track_data(t)})
    try:
        sp = c.execute("SELECT COALESCE(SUM(usd),0) FROM ledger WHERE kind='spend'").fetchone()[0]
        ea = c.execute("SELECT COALESCE(SUM(usd),0) FROM ledger WHERE kind='earn'").fetchone()[0]
        try: w = json.load(open(os.path.join(BASE, 'wallets_cache.json')))
        except Exception: w = None
        funds = (w.get('total_usd') if isinstance(w, dict) else None)
        runway = {'spent': sp, 'earned': ea, 'funds': funds,
                  'left': (funds - sp + ea) if funds is not None else None}
        try:
            c.execute('CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY)')
            u = c.execute("SELECT COUNT(*), COALESCE(SUM(tokens),0), COALESCE(SUM(cost_usd),0), COALESCE(SUM(end_tokens-start_tokens),0) FROM runs WHERE status='done'").fetchone()
            ud = c.execute("SELECT COALESCE(SUM(tokens),0), COALESCE(SUM(cost_usd),0) FROM runs WHERE status='done' AND ended_ts > strftime('%s','now','-1 day')").fetchone()
            usage = {'legs': u[0], 'tokens': u[1], 'cost_usd': round(u[2], 4), 'growth': u[3], 'day_tokens': ud[0], 'day_cost': round(ud[1], 4)}
        except Exception: usage = None
    except Exception: runway = {'spent': 0, 'earned': 0, 'funds': None, 'left': None}; usage = None
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
    try: c2.execute('ALTER TABLE runs ADD COLUMN start_tokens INTEGER')
    except Exception: pass
    try: c2.execute('ALTER TABLE runs ADD COLUMN end_tokens INTEGER')
    except Exception: pass
    try:
        runs = []
        for i, st, en, sc, tr, s, su, tok, co, se, stt, ent in c2.execute(
                "SELECT id, datetime(started_ts,'unixepoch'), " +
                "CASE WHEN ended_ts IS NULL THEN NULL ELSE datetime(ended_ts,'unixepoch') END, " +
                "scope, trigger, status, summary, tokens, cost_usd, session, start_tokens, end_tokens FROM runs ORDER BY id DESC LIMIT 10"):
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
                         'session': se, 'start_tokens': stt, 'end_tokens': ent})
    except Exception: runs = []
    try:
        cur = c2.execute("SELECT id, datetime(started_ts,'unixepoch'), scope, trigger, status FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    except Exception: cur = None
    c2.close()
    runner_info = {'running': runner_running()}
    try: quota = json.load(open(os.path.join(BASE, 'quota.json')))
    except Exception: quota = None
    if cur:
        runner_info.update({'run_id': cur[0], 'started': cur[1], 'scope': cur[2],
                            'trigger': cur[3], 'status': cur[4]})
    directives = '\n'.join(read(os.path.join(BASE, 'DIRECTIVES.md'), 40))
    ideas = [l for l in read(os.path.join(P4, 'IDEAS.md'), 30) if l.startswith('- ')]
    return {'tracks': tracks, 'events': events, 'proposals': props,
            'trials': trials, 'directives': directives, 'ideas': ideas, 'runway': runway, 'usage': usage,
            'notes': notes, 'paused': paused, 'runs': runs, 'prefs': get_prefs(),
            'runner': runner_info, 'leg_tail': last_leg_tail(), 'quota': quota,
            'me': ({'name': u['name'], 'role': u['role']} if (u := current_user(req)) else None)}

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

@app.post('/api/register')
async def api_register(req: Request):
    try: d = await req.json()
    except Exception: return {'ok': False, 'error': 'bad json'}
    name = str(d.get('name') or '').strip()[:32]
    pw = str(d.get('pw') or '')
    if len(name) < 2 or len(pw) < 6:
        return {'ok': False, 'error': 'name 2+ chars, password 6+ chars'}
    c = sqlite3.connect(DB)
    auth_tables(c)
    role = 'admin' if c.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0 else 'viewer'
    salt = _secrets.token_hex(8)
    try:
        cur = c.execute('INSERT INTO users(name, pw, role, created) VALUES (?,?,?,?)',
                        (name, _hash(pw, salt) + ':' + salt, role, int(time.time())))
        uid = cur.lastrowid
        c.commit()
    except sqlite3.IntegrityError:
        c.close(); return {'ok': False, 'error': 'name taken — login instead'}
    c.close()
    return _login_cookie(name, role, uid)

@app.post('/api/login')
async def api_login(req: Request):
    try: d = await req.json()
    except Exception: return {'ok': False, 'error': 'bad json'}
    name = str(d.get('name') or '').strip()[:32]
    pw = str(d.get('pw') or '')
    c = sqlite3.connect(DB)
    auth_tables(c)
    r = c.execute('SELECT id, pw, role FROM users WHERE name=?', (name,)).fetchone()
    c.close()
    if not r: return {'ok': False, 'error': 'no such account — register first'}
    try: want, salt = r[1].split(':')
    except Exception: return {'ok': False, 'error': 'login broken — re-register'}
    if _hash(pw, salt) != want: return {'ok': False, 'error': 'wrong password'}
    return _login_cookie(name, r[2], r[0])

def _rp(req):
    # rp id + origin from the Host header (tailnet name on phone, loopback dev)
    host = (req.headers.get('host') or '').split(':')[0].strip() or 'localhost'
    scheme = (req.headers.get('x-forwarded-proto') or req.url.scheme or 'https').split(',')[0].strip()
    if 'localhost' in host or host in ('127.0.0.1', '[::1]'):
        scheme = 'https'
    return host, scheme + '://' + (req.headers.get('host') or host)

@app.post('/api/webauthn/register/options')
async def api_wa_reg_opt(req: Request):
    err, me = need_login(req)
    if err: return err
    import webauthn as _wa
    rp_id, origin = _rp(req)
    return {'ok': True, 'options': _wa.register_options(DB, me['id'], me['name'], rp_id, origin)}

@app.post('/api/webauthn/register/verify')
async def api_wa_reg_verify(req: Request):
    err, me = need_login(req)
    if err: return err
    try: d = await req.json()
    except Exception: return {'ok': False, 'error': 'bad json'}
    import webauthn as _wa
    cred, verr = _wa.register_verify(DB, me['id'], d)
    if verr: return {'ok': False, 'error': verr}
    return {'ok': True, 'registered': True}

@app.post('/api/webauthn/login/options')
async def api_wa_login_opt(req: Request):
    try: d = await req.json()
    except Exception: return {'ok': False, 'error': 'bad json'}
    name = str(d.get('name') or '').strip()[:32]
    if not name: return {'ok': False, 'error': 'name first'}
    c = sqlite3.connect(DB)
    r = c.execute('SELECT id FROM users WHERE name=?', (name,)).fetchone()
    c.close()
    if not r: return {'ok': False, 'error': 'no such account — register first'}
    import webauthn as _wa
    rp_id, origin = _rp(req)
    opts, oerr = _wa.login_options(DB, r[0], rp_id, origin)
    if oerr: return {'ok': False, 'error': oerr}
    return {'ok': True, 'options': opts}

@app.post('/api/webauthn/login/verify')
async def api_wa_login_verify(req: Request):
    try: d = await req.json()
    except Exception: return {'ok': False, 'error': 'bad json'}
    import webauthn as _wa
    u, verr = _wa.login_verify(DB, d)
    if verr: return {'ok': False, 'error': verr}
    return _login_cookie(u['name'], u['role'], u['uid'])

@app.post('/api/logout')
async def api_logout(req: Request):
    try: tok = (req.cookies.get(AUTH_COOKIE) or '').strip()
    except Exception: tok = ''
    if tok:
        c = sqlite3.connect(DB)
        auth_tables(c)
        c.execute('DELETE FROM sessions WHERE token=?', (tok,))
        c.commit(); c.close()
    r = JSONResponse({'ok': True})
    r.delete_cookie(AUTH_COOKIE)
    return r

@app.get('/api/me')
def api_me(req: Request):
    u = current_user(req)
    return {'ok': True, 'me': ({'name': u['name'], 'role': u['role']} if u else None)}

@app.post('/api/promote')
async def api_promote(req: Request):
    err, me = need_admin(req)
    if err: return err
    try: d = await req.json()
    except Exception: return {'ok': False, 'error': 'bad json'}
    name = str(d.get('name') or '').strip()[:32]
    c = sqlite3.connect(DB)
    auth_tables(c)
    cur = c.execute("UPDATE users SET role='admin' WHERE name=?", (name,))
    c.commit(); c.close()
    if not cur.rowcount: return {'ok': False, 'error': 'no such account'}
    return {'ok': True}

@app.post('/api/run')
async def api_run(req: Request):
    # No token: tailnet-only board, and pause/resume/note are already open.
    # Worst case a stray tap costs one extra leg (cron runs 48/day anyway).
    err, _me = need_login(req)
    if err: return err
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
    err, _me = need_login(req)
    if err: return err
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
    err, _me = need_login(req)
    if err: return err
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
    err, _me = need_admin(req)
    if err: return err
    d = await req.json()
    try: pid, verdict = int(d.get('id')), d.get('verdict')
    except Exception: return {'ok': False, 'error': 'need id + verdict'}
    if verdict not in ('approved', 'rejected'): return {'ok': False, 'error': 'verdict?'}
    import sqlite3, time
    c = sqlite3.connect(DB)
    c.execute('UPDATE proposals SET status=?, decided_ts=? WHERE id=?', (verdict, int(time.time()), pid))
    c.commit(); c.close()
    return {'ok': True}

@app.post('/api/channel/mark')
async def api_channel_mark(req: Request):
    err, _me = need_login(req)
    if err: return err
    try: d = await req.json()
    except Exception: return {'ok': False, 'error': 'bad json'}
    track, slot = (d.get('track') or '').strip(), (d.get('slot') or '').strip()
    sha = (d.get('sha') or '').strip()[:40]
    note = str(d.get('note') or '')[:140]
    if track not in TRACKS or slot not in ('best', 'next') or not sha:
        return {'ok': False, 'error': 'need track + slot=best|next + sha'}
    import sqlite3, time
    c = sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS channels(track TEXT PRIMARY KEY, best_sha TEXT DEFAULT \'\', best_note TEXT DEFAULT \'\', best_ts INTEGER DEFAULT 0, next_sha TEXT DEFAULT \'\', next_note TEXT DEFAULT \'\', next_ts INTEGER DEFAULT 0)')
    c.execute('INSERT OR IGNORE INTO channels(track) VALUES (?)', (track,))
    col = 'best_sha, best_note, best_ts' if slot == 'best' else 'next_sha, next_note, next_ts'
    c.execute(f'UPDATE channels SET {col.split(chr(44))[0]}=?, {col.split(chr(44))[1]}=?, {col.split(chr(44))[2]}=? WHERE track=?', (sha, note, int(time.time()), track))
    ts = int(time.time())
    c.execute('INSERT INTO events VALUES (?,?,?,?,?)', (ts, track, 'channel', f'{track} {slot} now {sha}: {note or "marked"} | tech: channel {slot}={sha}', f'{track}:channel:{slot}:{sha}'))
    c.commit(); c.close()
    return {'ok': True}

@app.post('/api/channel/promote')
async def api_channel_promote(req: Request):
    err, _me = need_admin(req)
    if err: return err
    try: d = await req.json()
    except Exception: return {'ok': False, 'error': 'bad json'}
    track = (d.get('track') or '').strip()
    if track not in TRACKS: return {'ok': False, 'error': 'bad track'}
    import sqlite3, time
    c = sqlite3.connect(DB)
    r = c.execute('SELECT next_sha, next_note FROM channels WHERE track=?', (track,)).fetchone()
    if not r or not r[0]:
        c.close(); return {'ok': False, 'error': 'NEXT empty — nothing to promote'}
    c.execute('UPDATE channels SET best_sha=?, best_note=?, best_ts=? WHERE track=?', (r[0], r[1], int(time.time()), track))
    ts = int(time.time())
    c.execute('INSERT OR REPLACE INTO events VALUES (?,?,?,?,?)', (ts, track, 'promote-channel', f'{track} BEST now {r[0]} (was NEXT) | tech: promote-channel {r[0]}', f'{track}:promote-channel:{r[0]}'))
    c.commit(); c.close()
    return {'ok': True, 'best': r[0]}

_STARTED = int(time.time())
# Served code only (UX §8 + e058/e060 precedent): doc/data commits
# (ATTENTION.md, DIRECTIVES.md, STRATEGIES.md) must never fake STALE.
CODE_PATHS = ['e062-agent-ops/app.py', 'e062-agent-ops/webauthn.py',
              'e062-agent-ops/static/']
try:
    _RUN_COMMIT = subprocess.run(['git', 'log', '-1', '--format=%h', '--'] + CODE_PATHS,
                                 capture_output=True, text=True, cwd=P4).stdout.strip() or '?'
except Exception:
    _RUN_COMMIT = '?'

def repo_state(sub=None):
    # latest commit TOUCHING SERVED CODE + its dirtiness (repo-wide HEAD is
    # meaningless here: other tracks move it every leg; docs move it hourly)
    try:
        head = subprocess.run(['git', 'log', '-1', '--format=%h', '--'] + CODE_PATHS,
                              capture_output=True, text=True, cwd=P4).stdout.strip() or '?'
        dirty = subprocess.run(['git', 'status', '--short', '--'] + ['e062-agent-ops/app.py', 'e062-agent-ops/bin/ops.py', 'e062-agent-ops/bin/runner.sh', 'e062-agent-ops/static/app.js', 'e062-agent-ops/static/board.html', 'e062-agent-ops/tests/e2e.sh'],
                               capture_output=True, text=True, cwd=P4).stdout.strip()
        return head, bool(dirty)
    except Exception:
        return '?', False

@app.get('/api/tax/export')
def api_tax_export(year: int = 2026):
    import csv, datetime, io
    c = sqlite3.connect(DB)
    try:
        rows = c.execute(
            "SELECT ts, track, kind, usd, tx_hash, note FROM ledger "
            "WHERE strftime('%Y', ts, 'unixepoch')=? ORDER BY ts", (str(year),)).fetchall()
    except Exception:
        rows = []
    c.close()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['ts', 'iso8601', 'track', 'kind', 'amount_usd', 'tx_hash', 'notes'])
    for ts, tr, k, u, h, n in rows:
        try:
            iso = datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).isoformat()
        except Exception:
            iso = ''
        w.writerow([ts, iso, tr, k, u, h or '', n or ''])
    return Response(content=buf.getvalue(), media_type='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="tax-{year}.csv"'})

@app.get('/api/version')
def api_version():
    latest, dirty = repo_state('e062-agent-ops')
    return {'ok': True, 'track': 'e062', 'running': _RUN_COMMIT,
            'latest': latest, 'stale': _RUN_COMMIT != latest,
            'dirty': dirty, 'started_ts': _STARTED}

@app.get('/api/prefs')
def api_prefs_get():
    return {'ok': True, 'prefs': get_prefs()}

@app.post('/api/prefs')
async def api_prefs_set(req: Request):
    err, _me = need_login(req)
    if err: return err
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
                    assert isinstance(w, list) and 0 <= len(w) <= 12
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
    err, _me = need_login(req)
    if err: return err
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
    _crt = os.path.expanduser('~/.config/e062/tail.crt')
    _key = os.path.expanduser('~/.config/e062/tail.key')
    _ssl = {'ssl_certfile': _crt, 'ssl_keyfile': _key} if (
        os.path.isfile(_crt) and os.path.isfile(_key)) else {}
    # https on :8322 (valid tailnet cert -> Secure Context -> passkeys work
    # from the phone; localhost over https too, cert name only matches the
    # tailnet hostname so local clients skip verification)
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('E062_PORT', '8322')), **_ssl)
