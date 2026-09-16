#!/usr/bin/env python3
"""e058 funding scanner web app — thin slice 1.
SQLite store (timestamped funding series) + FastAPI JSON + static table UI.
Run: python3 app.py  (port 8320)"""
import datetime, html, json, glob, os, sqlite3, time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get('E058_DB', os.path.join(BASE, 'data.db'))
CAP_GLOBS = [os.path.join(BASE, 'data', '*.json'),
             '/tmp/loris_cap_*.json', '/tmp/loris_funding.json', '/tmp/fund5.json']
DEX29 = ['zo','aster','bluefin','bullet','decibel','edgex','entropyio','extended',
 'grvt','hibachi','hotstuff','hyperliquid','kinetiq','lighter','nado','ondo',
 'pacifica','paradex','paragon','phoenix','qfex','reya','risex','tradexyz',
 'txflow','variational','vest','woofipro']

_CACHE: dict = {}
def _cached(key, ttl, fn, *args, **kwargs):
    """Tiny TTL memo: data refreshes every ~15min (cron), so short TTLs
    trade <=60s staleness for skipping repeated full-table scans."""
    now = time.time()
    e = _CACHE.get(key)
    if e is not None and e[0] > now:
        return e[1]
    v = fn(*args, **kwargs)
    _CACHE[key] = (now + ttl, v)
    return v

def db():
    c = sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS funding(ts TEXT, coin TEXT, venue TEXT, bps8 REAL)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_f ON funding(ts, coin)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_funding_ts_venue_coin ON funding(ts, venue, coin)')
    c.execute('CREATE TABLE IF NOT EXISTS symbols(ts TEXT, coin TEXT, oi_rank INTEGER, price_usd REAL, oi_usd REAL, exchange_count INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS signals(sent_ts TEXT, coin TEXT, median_apy REAL, spread_bps REAL, long_v TEXT, short_v TEXT, persist TEXT, oi_rank INTEGER, window TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS paper_calls(call_date TEXT, logged_ts TEXT, coin TEXT, median_apy REAL, spread_bps REAL, long_v TEXT, short_v TEXT, persist TEXT, verdict TEXT, flips INTEGER, oi_rank INTEGER, UNIQUE(call_date, coin))')
    try:
        _cols = [r[1] for r in c.execute('PRAGMA table_info(paper_calls)')]
        if 'flips' not in _cols: c.execute('ALTER TABLE paper_calls ADD COLUMN flips INTEGER')
        if 'oi_rank' not in _cols: c.execute('ALTER TABLE paper_calls ADD COLUMN oi_rank INTEGER')
    except Exception: pass
    c.execute('CREATE TABLE IF NOT EXISTS paper_outcomes(call_date TEXT, coin TEXT, hit INTEGER, spread_24h REAL, resolved_ts TEXT, UNIQUE(call_date, coin))')
    return c

REPORT_CFG = os.path.join(BASE, 'report_config.json')
REPORT_DEFAULTS = {'report_hour_utc': 8, 'threshold_bps': 50.0, 'last_n': 4, 'top_n': 10, 'urgent_mult': 3.0}

def load_config():
    cfg = dict(REPORT_DEFAULTS)
    try:
        user = json.load(open(REPORT_CFG))
        for k in cfg:
            if k in user:
                cfg[k] = user[k]
    except Exception:
        pass
    return cfg

def save_config(patch):
    cfg = load_config()
    errors = []
    bounds = {'report_hour_utc': (0, 23), 'threshold_bps': (1, 1000),
              'last_n': (2, 20), 'top_n': (1, 30), 'urgent_mult': (1, 10)}
    for k, (lo, hi) in bounds.items():
        if k in patch:
            try:
                v = float(patch[k])
                if k in ('report_hour_utc', 'last_n', 'top_n'): v = int(v)
            except (TypeError, ValueError):
                errors.append(f'{k} not a number'); continue
            if not (lo <= v <= hi):
                errors.append(f'{k} out of range [{lo},{hi}]'); continue
            cfg[k] = v
    if errors:
        return None, '; '.join(errors)
    json.dump(cfg, open(REPORT_CFG, 'w'), indent=1)
    return cfg, None

def log_signal_rows(window, rows):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    w = '|'.join(window or [])
    c = db()
    for r in rows:
        try:
            c.execute('INSERT INTO signals VALUES (?,?,?,?,?,?,?,?,?)',
                      (ts, r.get('coin'), r.get('median_apy'), r.get('spread_bps'),
                       r.get('long'), r.get('short'), r.get('persist'),
                       r.get('oi_rank') if isinstance(r.get('oi_rank'), int) else None, w))
        except Exception:
            pass
    c.commit(); c.close()
    return ts

def load_capture(path):
    d = json.load(open(path))
    ts = d.get('timestamp', 'unknown')
    fr = d.get('funding_rates', {})
    n = 0
    c = db()
    has = c.execute('SELECT 1 FROM funding WHERE ts=? LIMIT 1', (ts,)).fetchone()
    if not has:
        for venue, coins in fr.items():
            for coin, bps in coins.items():
                try: c.execute('INSERT INTO funding VALUES (?,?,?,?)', (ts, coin, venue, float(bps)))
                except Exception: pass
                n += 1
        oi = d.get('oi_rankings', {}) or {}
        syms = d.get('symbols', [])
        smeta = {s['symbol']: s for s in syms} if isinstance(syms, list) and syms and isinstance(syms[0], dict) else {}
        for coin, rank in (oi.items() if isinstance(oi, dict) else []):
            m = smeta.get(coin, {})
            try: c.execute('INSERT INTO symbols VALUES (?,?,?,?,?,?)',
                           (ts, coin, int(rank) if str(rank).isdigit() else None,
                            m.get('price_usd'), m.get('oi_usd'), m.get('exchange_count')))
            except Exception: pass
        c.commit()
    c.close()
    return ts, n

def load_all():
    out = []
    for g in CAP_GLOBS:
        for p in glob.glob(g):
            try: out.append((p,) + load_capture(p))
            except Exception as e: out.append((p, 'ERR', str(e)[:100]))
    return out

app = FastAPI()

import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(BASE), 'e068-tablelib'))
from tablelib.render import render_table as _tl_render
from tablelib.stats import auto_presets as _tl_presets, suggest as _tl_suggest

_TL_DIR = os.path.join(os.path.dirname(BASE), 'e068-tablelib', 'tablelib')

_TL_COINS_COLS = [
    {"key": "coin", "label": "coin", "cls": "", "kind": "text", "ph": "coin"},
    {"key": "apy", "label": "APY%", "cls": "", "kind": "num", "fmt": "{:.1f}", "ph": "\u2264 max"},
    {"key": "spread", "label": "spread bps", "cls": "", "kind": "num", "fmt": "{:.1f}"},
    {"key": "long", "label": "long", "cls": "", "kind": "text", "ph": "venue"},
    {"key": "long_bps", "label": "long bps", "cls": "", "kind": "num", "fmt": "{:.1f}"},
    {"key": "short", "label": "short", "cls": "", "kind": "text", "ph": "venue"},
    {"key": "short_bps", "label": "short bps", "cls": "", "kind": "num", "fmt": "{:.1f}"},
    {"key": "legs", "label": "legs", "cls": "", "kind": "num"},
    {"key": "oi", "label": "OI", "cls": "", "kind": "text"},
]
_TL_PAPER_COLS = [
    {"key": "coin", "label": "coin", "cls": "", "kind": "text", "ph": "coin"},
    {"key": "apy", "label": "entry APY%", "cls": "", "kind": "num", "fmt": "{:.1f}"},
    {"key": "long", "label": "long", "cls": "", "kind": "text", "ph": "venue"},
    {"key": "short", "label": "short", "cls": "", "kind": "text", "ph": "venue"},
    {"key": "spin", "label": "spread in", "cls": "", "kind": "num", "fmt": "{:.1f}"},
    {"key": "persist", "label": "held", "cls": "", "kind": "text"},
    {"key": "flips", "label": "flips", "cls": "", "kind": "num"},
    {"key": "oi", "label": "OI", "cls": "", "kind": "text"},
    {"key": "verdict", "label": "verdict", "cls": "", "kind": "text"},
    {"key": "entry", "label": "entry", "cls": "", "kind": "date"},
    {"key": "exit", "label": "exit", "cls": "", "kind": "date"},
    {"key": "grade_at", "label": "grades", "cls": "", "kind": "date"},
    {"key": "spout", "label": "spread out", "cls": "", "kind": "num", "fmt": "{:.1f}"},
    {"key": "delta", "label": "Δ spread", "cls": "", "kind": "num", "fmt": "{:+.1f}"},
    {"key": "result", "label": "result", "cls": "", "kind": "text"},
]
_TL_PWIN_COLS = [
    {"key": "day", "label": "day", "cls": "", "kind": "text"},
    {"key": "pending", "label": "pending", "cls": "", "kind": "num"},
    {"key": "first", "label": "logged first", "cls": "", "kind": "date"},
    {"key": "last", "label": "logged last", "cls": "", "kind": "date"},
    {"key": "grades", "label": "grades", "cls": "", "kind": "date"},
]
_TL_PERS_COLS = [
    {"key": "coin", "label": "coin", "cls": "", "kind": "text", "ph": "coin"},
    {"key": "streak", "label": "streak", "cls": "", "kind": "text"},
    {"key": "apy", "label": "med APY%", "cls": "", "kind": "num", "fmt": "{:.1f}"},
    {"key": "spin", "label": "spread now", "cls": "", "kind": "num", "fmt": "{:.1f}"},
    {"key": "curve", "label": "spread curve", "cls": "", "kind": "spark"},
    {"key": "minw", "label": "worst", "cls": "", "kind": "num", "fmt": "{:.1f}"},
    {"key": "verdict", "label": "verdict", "cls": "", "kind": "text"},
    {"key": "long", "label": "long", "cls": "", "kind": "text"},
    {"key": "short", "label": "short", "cls": "", "kind": "text"},
]
_TL_SIG_COLS = [
    {"key": "sent", "label": "sent", "cls": "", "kind": "text"},
    {"key": "coin", "label": "coin", "cls": "", "kind": "text", "ph": "coin"},
    {"key": "apy", "label": "med APY%", "cls": "", "kind": "num", "fmt": "{:.1f}"},
    {"key": "spread", "label": "spread", "cls": "", "kind": "num", "fmt": "{:.1f}"},
    {"key": "long", "label": "long", "cls": "", "kind": "text"},
    {"key": "short", "label": "short", "cls": "", "kind": "text"},
    {"key": "persist", "label": "persist", "cls": "", "kind": "text"},
    {"key": "oi", "label": "OI", "cls": "", "kind": "text"},
]


def _tl_coin_rows(rows):
    out = []
    for r in rows or []:
        oi = r.get('oi_rank')
        out.append({'coin': r.get('coin'), 'apy': r.get('apy'),
                    'spread': r.get('spread_bps'),
                    'long': r.get('long'), 'long_bps': r.get('long_bps'),
                    'short': r.get('short'), 'short_bps': r.get('short_bps'),
                    'legs': r.get('n_legs'),
                    'oi': oi if isinstance(oi, int) else '500+'})
    return out


def _tl_table(ns, rows, cols, sort_key, sort_dir=-1, click=None, derived=None, total=None, layout=None):
    try:
        return _tl_render(rows, cols, total=(total if total is not None else len(rows)), page=1, per=10,
                          sort_key=sort_key, sort_dir=sort_dir, ns=ns,
                          presets=_tl_presets(rows, cols),
                          suggestions=_tl_suggest(rows, cols, derived=derived),
                          derived=derived,
                          card_layout=layout,
                          row_click=click[0] if click else None,
                          row_click_key=click[1] if click else 'token')
    except Exception as e:
        return f'<div class=cav>table offline ({html.escape(str(e)[:80])})</div>'


@app.get('/tl/tablelib.js')
def _tl_js():
    return FileResponse(os.path.join(_TL_DIR, 'table.js'), media_type='application/javascript')


@app.get('/tl/tablelib.css')
def _tl_css():
    return FileResponse(os.path.join(_TL_DIR, 'table.css'), media_type='text/css')

import subprocess as _sp
_VSTART = int(time.time())
try:
    _VRUN = _sp.run(['git', 'log', '-1', '--format=%h', '--', 'app.py', 'bin/', 'tests/'], capture_output=True,
                    text=True, cwd=BASE).stdout.strip() or '?'
except Exception:
    _VRUN = '?'

@app.get('/api/version')
def version():
    try:
        latest = _sp.run(['git', 'log', '-1', '--format=%h', '--', 'app.py', 'bin/', 'tests/'], capture_output=True,
                         text=True, cwd=BASE).stdout.strip() or '?'
        dirty = bool(_sp.run(['git', 'status', '--short', '--'] + ['e058-funding-scanner/app.py', 'e058-funding-scanner/bin/', 'e058-funding-scanner/tests/'], capture_output=True,
                             text=True, cwd='/home/vuos/code/p4').stdout.strip())
    except Exception:
        latest, dirty = '?', False
    return {'ok': True, 'track': 'e058', 'running': _VRUN,
            'latest': latest, 'stale': _VRUN != latest,
            'dirty': dirty, 'started_ts': _VSTART}

@app.get('/api/status')
def status():
    c = db()
    snaps = c.execute('SELECT ts, COUNT(*) FROM funding GROUP BY ts ORDER BY ts').fetchall()
    coins = c.execute('SELECT COUNT(DISTINCT coin) FROM funding').fetchone()[0]
    c.close()
    return {'snapshots': [{'ts': t, 'rows': n} for t, n in snaps], 'coins': coins}

@app.post('/api/suggest')
async def suggest(req: Request):
    """AI hook (U5): same suggestion shape as tablelib heuristics.
    Heuristic engine today, model later — the GUI cannot tell them apart."""
    try:
        b = await req.json()
    except Exception:
        return JSONResponse({'suggestions': []})
    rows = b.get('rows') or []
    keys = b.get('cols') or []
    cols = [{'key': k, 'label': k, 'kind': 'num'} for k in keys]
    return JSONResponse({'suggestions': _tl_suggest(rows, cols, derived=(b.get('derived') or {}))})


@app.get('/api/table')
def table(min_apy: float = 0.0, max_apy: float = 1e9,
           oi_min: int = 0, oi_max: int = 9999,
           min_legs: int = 2, q: str = '',
           venues: str = '', dex_only: bool = True,
           sort: str = 'apy'):
    return _cached(('table', min_apy, max_apy, oi_min, oi_max, min_legs, q, venues, dex_only, sort),
                   60, _table_compute,
                   min_apy, max_apy, oi_min, oi_max, min_legs, q, venues, dex_only, sort)


def _table_compute(min_apy: float = 0.0, max_apy: float = 1e9,
           oi_min: int = 0, oi_max: int = 9999,
           min_legs: int = 2, q: str = '',
           venues: str = '', dex_only: bool = True,
           sort: str = 'apy'):
    c = db()
    ts = c.execute('SELECT MAX(ts) FROM funding').fetchone()[0]
    if not ts: return {'ts': None, 'rows': []}
    if venues:
        vlist = [v.strip() for v in venues.split(',') if v.strip()]
    else:
        vlist = DEX29 if dex_only else None
    q0 = 'SELECT coin, venue, bps8 FROM funding WHERE ts=?'
    args = [ts]
    if vlist:
        q0 += ' AND venue IN (%s)' % ','.join('?' * len(vlist))
        args += vlist
    legs = {}
    for coin, venue, bps in c.execute(q0, args):
        legs.setdefault(coin, []).append((venue, bps))
    oi = dict(c.execute('SELECT coin, oi_rank FROM symbols WHERE ts=?', (ts,)))
    c.close()
    ql = q.strip().upper()
    rows = []
    for coin, ll in legs.items():
        if len(ll) < min_legs: continue
        if ql and ql not in coin.upper(): continue
        oir = oi.get(coin)
        oir_n = oir if isinstance(oir, int) else 9999
        if not (oi_min <= oir_n <= oi_max): continue
        lo = min(ll, key=lambda x: x[1]); hi = max(ll, key=lambda x: x[1])
        apy = (hi[1] - lo[1]) / 100 * 3 * 365
        if not (min_apy <= apy <= max_apy): continue
        rows.append({'coin': coin, 'apy': round(apy, 1),
                     'long': lo[0], 'long_bps': round(lo[1], 2),
                     'short': hi[0], 'short_bps': round(hi[1], 2),
                     'spread_bps': round(hi[1] - lo[1], 2),
                     'n_legs': len(ll), 'oi_rank': oir})
    if sort == 'oi':
        rows.sort(key=lambda r: (r['oi_rank'] if isinstance(r['oi_rank'], int) else 9999))
    elif sort == 'legs':
        rows.sort(key=lambda r: r['n_legs'], reverse=True)
    else:
        rows.sort(key=lambda r: r['apy'], reverse=True)
    return {'ts': ts, 'dex_only': dex_only, 'count': len(rows), 'rows': rows[:500]}

INDEX = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>e058 funding scanner</title><link rel=stylesheet href="/tl/tablelib.css">
<style>:root{--bg:#fff;--fg:#111;--bd:#ccc;--hd:#eee}html.dark{--bg:#111418;--fg:#e6e6e6;--bd:#333;--hd:#1e2228}
body{font-family:system-ui;margin:8px;background:var(--bg);color:var(--fg);padding-bottom:124px}table{border-collapse:collapse;width:100%;font-size:14px}
td,th{border:1px solid var(--bd);padding:4px 6px;text-align:right}td:first-child,th:first-child{text-align:left}
th{position:sticky;top:0;background:var(--hd);z-index:2}input,select,button{background:var(--bg);color:var(--fg);border:1px solid var(--bd);border-radius:6px;padding:4px 8px}
button{cursor:pointer}button:disabled{opacity:.4}
.twrap{max-height:52vh;overflow-y:auto;overflow-x:auto;border:1px solid var(--bd);border-radius:8px;margin:6px 0}
.twrap table{margin:0;border:0}
.topcard{border:1px solid var(--bd);border-radius:10px;padding:8px;margin:8px 0;background:var(--bg)}
.topcard .one{font-size:14px}
.topcard .row{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.topcard .pick{flex:1;min-width:90px;text-align:left;padding:8px;font-size:13px}
.thumbbar{position:fixed;left:8px;right:8px;bottom:8px;z-index:5;background:var(--bg);border:1px solid var(--bd);border-radius:12px;padding:8px;display:flex;gap:8px}
.thumbbar button{flex:1;padding:12px 8px;font-size:15px}
details.cfg{border:1px solid var(--bd);border-radius:8px;padding:6px;margin:8px 0;font-size:13px}
details.cfg summary{cursor:pointer}
.pos{color:#3ddc84}.secttl{font-size:13px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;opacity:.9;margin:10px 0 4px;padding:6px 10px;background:rgba(127,127,127,.14);border-radius:8px}</style></head><body>
<h2>e058 funding scanner <small id=ts></small></h2>
<script>if(localStorage.e058t==='d')document.documentElement.classList.add('dark');</script>
<div class=topcard id=top><div class=one id=top-one>%%TOPONE%%</div><div class=row id=top-row>%%TOPROW%%</div><details style="font-size:12px;opacity:.7;margin-top:4px"><summary>What the labels mean (tap to expand)</summary><table><tbody><tr><td>steady \u2713</td><td>held every check with solid backing</td></tr><tr><td>new</td><td>first day, holding so far</td></tr><tr><td>watch</td><td>thin backing \u2014 tap a coin for detail</td></tr></tbody></table></details><div style="margin-top:4px"><button onclick="loadTop()" style="padding:2px 8px;font-size:12px">refresh</button></div><div id=pulse style="font-size:12px;opacity:.7;margin-top:4px">%%PULSE%%</div></div>
<details class=cfg id=fc><summary id=f-sum>Filter: all coins, top pay first (tap to narrow)</summary>
<div id=f style="margin-top:6px">
<label>APY <input id=a0 type=number value=0 style=width:70px>–<input id=a1 type=number value=100000 style=width:80px></label>
<label>OI rank <input id=o0 type=number value=0 style=width:55px>–<input id=o1 type=number value=9999 style=width:60px></label>
<label>min legs <input id=ml type=number value=2 style=width:45px></label>
<label>coin <input id=q type=text placeholder=JUP style=width:70px></label>
<label>sort <select id=s><option value=apy>APY</option><option value=oi>OI rank</option><option value=legs>legs</option></select></label>
<button onclick=load()>filter</button> <small id=c></small>
</div></details>
<details class=cfg id=r><summary id=r-sum>%%DIGEST%%</summary>
<div style="margin-top:6px">
<label>digest time (UTC hour) <input id=rh type=number min=0 max=23 style=width:50px></label>
<label>coins in digest <input id=rtn type=number style=width:50px></label>
<button onclick=saveCfg()>save</button> <small id=rc></small>
<details style="margin-top:6px"><summary>Pay filters (advanced — usually leave alone)</summary>
<div style="margin-top:6px">
<label>min pay (bps) <input id=rt type=number style=width:70px></label>
<label>steady checks <input id=rn type=number style=width:50px></label>
<label>urgent if bigger &times; <input id=ru type=number step=0.5 style=width:50px></label>
</div></details>
</div></details>
<div id=s style="margin:8px 0"><details><summary><b>signal history</b> <small id=sig-sum>(every sent alert, newest first)</small></summary> <button onclick=loadSig() style="padding:2px 8px;font-size:12px">refresh</button>
%%SIGNALS%%<div style="margin:4px 0;font-size:12px;opacity:.7">alerts by hour (UTC):</div>%%SIGHOURS%%</details></div>
<div id=pb style="margin:8px 0"><details><summary><b>paper ballot</b> <small id=pb-sum>(tap to expand)</small></summary><div style="margin:4px 0;font-size:12px;opacity:.7">Funnel: each row feeds the next — snapshot → holders → alerts + paper → graded.</div>%%FUNNEL%%%%PSUMMARY%%<div style="margin:4px 0;font-size:12px;opacity:.7">Pending calls grouped by day — each grades ~24h after its first log.</div>%%PWIN%% <button onclick=loadPaper() style="padding:2px 8px;font-size:12px">refresh</button>
%%PAPER%%</details></div>
<div class=secttl>coins <small id=coins-sum style="text-transform:none;letter-spacing:0;opacity:.7"></small></div>
<div id=coinDetail style="margin:4px 0;font-size:13px"></div>
%%COINS%%
<div style="margin:4px 0;font-size:13px"><small id=morec style="opacity:.7"></small></div>
<div class=secttl>persistence <small id=pers-sum style="text-transform:none;letter-spacing:0;opacity:.7">%%PERSSUM%%</small></div>
<div style="margin:4px 0;font-size:13px">min pay <input id=pt type=number value=20 style=width:60px>bps · checks <input id=pn type=number value=4 style=width:45px> · min streak <input id=pk type=number value=4 style=width:45px> <button onclick=loadPers() style="padding:2px 8px">show</button></div>
<div style="margin:4px 0;font-size:13px">market survival (checks held: coins): <small id=surv>%%SURV%%</small></div>
%%PERS%%
<div class=thumbbar><button onclick="topGo(this)">★ top</button><button id=tbslip onclick="copySlip(this)">copy slip</button><button onclick="fltGo()">filter</button><button onclick="clearQ()">✕ clear</button><button onclick="themeGo()">◐ theme</button></div>
<div id=ver style="font-size:11px;opacity:.6;margin:56px 0 8px">%%VER%%</div>
<script src="/tl/tablelib.js"></script>
<script>fetch('/api/version').then(r=>r.json()).then(v=>{if(v.ok&&(v.stale||v.dirty))document.getElementById('ver').textContent='v'+v.running+(v.stale?' STALE\u2014restart':'')+(v.dirty?' *':'');}).catch(()=>{});</script>
<script>function locTs(s){try{s=String(s||'').trim();if(!s||s==='unknown')return s||'\u2014';let d;if(/^\d+$/.test(s))d=new Date(+s*1000);else d=new Date(s.replace(' ','T')+(/Z|[+-]\d{2}:?\d{2}$/.test(s)?'':'Z'));if(isNaN(d))return String(s);const p=n=>(n<10?'0':'')+n;return p(d.getMonth()+1)+'/'+p(d.getDate())+' '+p(d.getHours())+':'+p(d.getMinutes());}catch(e){return String(s);}}
function locHour(h){try{const d=new Date();d.setUTCHours(+h,0,0,0);const p=n=>(n<10?'0':'')+n;return p(d.getHours())+':'+p(d.getMinutes());}catch(e){return '?';}}
let allRows=[], backPC={}, lastAge='';
function sampleAge(ts){try{const ms=Date.now()-new Date(String(ts||'')).getTime();if(!(ms>=0))return '';return ms<36e5?` · sample ${Math.max(1,Math.round(ms/6e4))}m ago`:` · sample ${(ms/36e6).toFixed(1)}h ago`;}catch(e){return '';}}
function coinLibRow(r){return {coin:r.coin,apy:r.apy,spread:r.spread_bps,long:r.long,long_bps:r.long_bps,short:r.short,short_bps:r.short_bps,legs:r.n_legs,oi:(typeof r.oi_rank==='number'?r.oi_rank:'500+')};}
async function load(){const g=id=>document.getElementById(id).value;
try{const b=await (await fetch('/api/backtest')).json();if(b&&b.ok&&b.per_coin)backPC=b.per_coin;}catch(e){}
const d=await (await fetch(`/api/table?min_apy=${g('a0')}&max_apy=${g('a1')}&oi_min=${g('o0')}&oi_max=${g('o1')}&min_legs=${g('ml')}&q=${g('q')}&sort=${g('s')}`)).json();
document.getElementById('ts').textContent=locTs(d.ts||'')||'no data';
lastAge=sampleAge(d.ts);
allRows=d.rows||[];const total=(d.count??allRows.length);
document.getElementById('c').textContent=`${allRows.length} loaded of ${total}`;
const cs=document.getElementById('coins-sum');if(cs)cs.textContent=`${total} by pay${lastAge} — pager below`;
const fs=document.getElementById('f-sum');if(fs){const qq=(g('q')||'').trim().toUpperCase();fs.textContent=`Filter: ${total}${qq?' matching '+qq:''}, best pay first (tap to narrow)`;}
if(window.tlRender&&window.tlState){const st=tlState('coins');st.all=allRows.map(coinLibRow);tlRender('coins');}
const mc=document.getElementById('morec'),mb=document.getElementById('moreb');if(mc)mc.textContent=allRows.length?`${total} coins — tap headers to sort, filter inside columns`:'no coins match';if(mb)mb.style.display='none';}
function persRow(r){return {coin:r.coin,streak:(r.streak+'/'+(r.history||[]).length),apy:r.median_apy,spin:r.spread_bps,curve:r.spreads,minw:r.min_spread,verdict:r.verdict,long:r.long,short:r.short};}
async function loadPers(){const g=id=>document.getElementById(id).value;
try{const d=await (await fetch(`/api/persistence?threshold_bps=${g('pt')}&last_n=${g('pn')}&min_streak=${g('pk')}`)).json();
const rows=d.rows||[];const total=(d.count??rows.length);
const ps=document.getElementById('pers-sum');if(ps)ps.textContent=`${total} holding ≥${d.threshold_bps}bps · window ${g('pn')} checks, streak ≥${g('pk')}`;
const sv=document.getElementById('surv');if(sv)sv.textContent=(d.survival||[]).map(s=>`${s.streak}: ${s.n}`).join(' · ');
if(window.tlRender&&window.tlState){const st=tlState('pers');st.all=rows.map(persRow);tlRender('pers');}}catch(e){}}
async function loadCfg(){try{const c=await (await fetch('/api/report-config')).json();
rh.value=c.report_hour_utc;rt.value=c.threshold_bps;rn.value=c.last_n;rtn.value=c.top_n;ru.value=c.urgent_mult;
const rs=document.getElementById('r-sum');if(rs)rs.textContent=`Daily digest ${c.report_hour_utc}:00 UTC (=${locHour(c.report_hour_utc)} your time), top ${c.top_n} over ${c.threshold_bps}bps (tap to change time)`;}catch(e){}}
async function saveCfg(){const b={report_hour_utc:+rh.value,threshold_bps:+rt.value,last_n:+rn.value,top_n:+rtn.value,urgent_mult:+ru.value};
try{const r=await (await fetch('/api/report-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)})).json();
rc.textContent=r.ok?'saved':'ERR: '+(r.error||'?');}catch(e){rc.textContent='ERR: unreachable';}}
async function loadSig(){try{const d=await (await fetch('/api/signals?limit=100')).json();
const ss=document.getElementById('sig-sum');if(ss)ss.textContent=`(${(d.rows||[]).length} alerts, newest first)`;
if(window.tlRender&&window.tlState){const st=tlState('sig');st.all=[];for(const s of (d.rows||[])){st.all.push({sent:locTs(s.sent_ts),coin:s.coin,apy:s.median_apy,spread:s.spread_bps,long:s.long_v,short:s.short_v,persist:s.persist,oi:(typeof s.oi_rank==='number'?s.oi_rank:'')});}tlRender('sig');}}catch(e){}}
async function loadPaper(){try{const d=await (await fetch('/api/paper/calls')).json();
const ss=document.getElementById('pb-sum');if(ss)ss.textContent=d.ok?'(tap to expand)':'(offline)';
const set=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v;};
if(d.ok){set('ps-pred',String((d.calls||[]).length));set('ps-graded',`${d.paper_resolved??0} (${d.paper_hit_rate_pct??'—'}%)`);set('ps-wait',`${d.waiting??0} · ${d.grade_status||''}`);set('ps-rule',d.rule||'');set('ps-cushion',d.cushion||'');
if(window.tlRender&&window.tlState){const st=tlState('pwin');st.all=Object.keys(d.by_date||{}).sort().map(day=>{const w=d.by_date[day];let g='?';try{const s0=String(w.logged_first||'');let t=Date.parse(s0);if(isNaN(t))t=Date.parse(s0.replace(' ','T')+'Z');if(!isNaN(t))g=new Date(t+864e5).toISOString();}catch(e){}return {day:day,pending:w.pending,first:w.logged_first,last:w.logged_last,grades:g};});tlRender('pwin');}}
window._paperRows=(d.calls||[]);if(window.tlRender&&window.tlState){const st=tlState('paper');st.all=(d.calls||[]).map(c=>{const dl=(c.spread_24h!=null&&c.spread_bps!=null)?Math.round((c.spread_24h-c.spread_bps)*10)/10:null;return {coin:c.coin,apy:c.median_apy,long:c.long_v,short:c.short_v,spin:c.spread_bps,persist:c.persist,flips:c.flips,oi:(typeof c.oi_rank==='number'?c.oi_rank:'500+'),verdict:c.verdict,entry:c.logged_ts,exit:c.exit_ts,grade_at:c.grade_at,spout:c.spread_24h,delta:dl,result:(c.hit===1?'hit':(c.hit===0?'miss':'…'))};});tlRender('paper');}}catch(e){}}
let lastTop=[];
function shortV(r,hasH){const v=r.verdict||r.persist;if(v==='FLIPPY')return 'flippy';if(v==='STEADY')return hasH?'steady \u2713':'new';if(v==='WATCH')return 'watch';return v||'';}
function plainV(r,hasH){const v=r.verdict||r.persist;if(v==='FLIPPY')return `flippy \u2014 edge moves between ${r.long||'?'} and ${r.short||'?'}`;if(v==='STEADY'&&!hasH)return 'new \u2014 holding so far';return v==='STEADY'?'steady \u2713':v==='WATCH'?'watch \u2014 thin backing':(v||'');}
async function loadTop(){const one=document.getElementById('top-one'),row=document.getElementById('top-row');
try{const d=await (await fetch('/api/persistence?threshold_bps=20&last_n=4')).json();
let pc={};try{const b=await (await fetch('/api/backtest')).json();if(b&&b.ok&&b.per_coin)pc=b.per_coin;}catch(e){}
const _good=c=>{const s=pc[c];return !!(s&&+s.n>=5&&s.n>0&&(s.hit/s.n)>=0.5);};
const _tier=r=>[(_good(r.coin)?0:(r.verdict==='STEADY'?1:(r.verdict==='WATCH'?2:(r.verdict==='FLIPPY'?3:2)))),-(+r.median_apy||0)];
const _s=(a,b)=>{const x=_tier(a),y=_tier(b);return (x[0]-y[0])||(x[1]-y[1]);};
const t=(d.rows||[]).slice().sort(_s).slice(0,3);lastTop=t;
if(!t.length){one.textContent='Top pays now: none holding right now';row.innerHTML='';return;}
const held=c=>pc[c]?` (${pc[c].hit}/${pc[c].n} paid)`:'';
const _pv=t.filter(r=>_good(r.coin)),_nw=t.length-_pv.length;one.textContent='Top pays now: '+(_pv.length?_pv.map(r=>`${r.coin} ${r.median_apy}% ${shortV(r,true)}`).join(' \u00b7 '):'no proven pay yet \u2014 new coins holding below')+(_nw?` \u00b7 +${_nw} new high pay${_nw>1?'s':''} below (unproven)`: '')+' \u00b7 tap a coin for why';
row.innerHTML=t.map(r=>`<button class=pick onclick="pickCoin('${r.coin}')">${r.coin}<br><b class=pos>${r.median_apy}%</b> <small>${plainV(r,!!pc[r.coin])}${held(r.coin)} ${r.long||''}→${r.short||''}</small></button>`).join('');}catch(e){one.textContent='Top pays now: offline';}}
function pickCoin(c){const r=(allRows||[]).find(x=>x.coin===c);const el=document.getElementById('coinDetail');if(!r){const pr=(window._paperRows||[]).find(x=>x.coin===c);if(el)el.innerHTML=pr?`<b>${c}</b> paper ${pr.median_apy}% APY · ${pr.verdict||''} · held ${pr.persist||'?'} · route ${pr.long_v||'?'}→${pr.short_v||'?'} · in ${pr.spread_bps??'?'}bps → out ${pr.spread_24h??'?'}bps · ${pr.hit===1?'HIT':pr.hit===0?'MISS':'pending'}`:'';return;}const pc=backPC[c];if(el)el.innerHTML=`<b>${c}</b> <span class=pos>${r.apy}% APY</span> · spread ${r.spread_bps}bps · long ${r.long} ${r.long_bps} / short ${r.short} ${r.short_bps} · legs ${r.n_legs} · OI ${r.oi_rank??'500+'} · paid ${pc?pc.hit+'/'+pc.n:'no history yet'} <button onclick="qFilter('${c}')" style="padding:2px 8px">filter to ${c}</button> <button onclick="clearCoin()" style="padding:2px 8px">✕</button>`;if(el)el.scrollIntoView({block:'nearest'});}
function qFilter(c){const fc=document.getElementById('fc');if(fc&&!fc.open)fc.open=true;document.getElementById('q').value=c;load();}
function clearCoin(){const el=document.getElementById('coinDetail');if(el)el.innerHTML='';clearQ();}
function fltGo(){const fc=document.getElementById('fc');if(fc)fc.open=true;document.getElementById('fc').scrollIntoView();const q=document.getElementById('q');if(q)q.focus({preventScroll:true});}
function clearQ(){document.getElementById('q').value='';load();document.getElementById('top').scrollIntoView();}
async function copySlip(btn){const sc=document.getElementById('slipc');const tb=btn||document.getElementById('tbslip');const flash=t=>{if(tb){tb.textContent=t;}};try{if(!lastTop.length)await loadTop();if(!lastTop.length){flash('nothing steady');if(sc)sc.textContent='nothing steady right now';return;}const best=lastTop.find(r=>r.verdict==='STEADY')||lastTop[0];const s=best.paper||`PAPER e058 ${best.coin} ${best.median_apy}%`;await navigator.clipboard.writeText(s);flash(`copied ${best.coin} ✓`);setTimeout(()=>flash('copy slip'),2500);if(sc)sc.textContent=`copied ${best.coin} — paste anywhere`;}catch(e){try{const best2=(lastTop.find(r=>r.verdict==='STEADY')||lastTop[0]||{});prompt('Copy paper slip:',best2.paper||'');flash('copy it by hand');if(sc)sc.textContent='copy it by hand';}catch(e2){flash('copy blocked');if(sc)sc.textContent='copy blocked';}}}
function topGo(){document.getElementById('top').scrollIntoView();loadTop();}
function themeGo(){document.documentElement.classList.toggle('dark');localStorage.e058t=document.documentElement.classList.contains('dark')?'d':'l';}
load();loadCfg();loadSig();loadPaper();loadTop();</script></body></html>"""

@app.get('/api/persistence')
def persistence(threshold_bps: float = 20.0, last_n: int = 4,
                min_legs: int = 2, dex_only: bool = True, venues: str = '',
                min_streak: int = None):
    """Spread persistence across snapshots (8h-bps).
    Streak k = trailing snapshots with spread >= threshold_bps.
    Returns rows with k >= min_streak (default: all last_n), ranked by
    median window APY, plus the market survival curve (coins holding
    k=1..N) so persistence reads as a decay, not a yes/no."""
    if min_streak is None: min_streak = last_n
    return _cached(('persistence', threshold_bps, last_n, min_legs, dex_only, venues, min_streak),
                   120, _persistence_compute,
                   threshold_bps, last_n, min_legs, dex_only, venues, min_streak)


def _persistence_compute(threshold_bps: float = 20.0, last_n: int = 4,
                         min_legs: int = 2, dex_only: bool = True, venues: str = '',
                         min_streak: int = 4):
    c = db()
    snaps = [r[0] for r in c.execute('SELECT DISTINCT ts FROM funding ORDER BY ts')]
    if not snaps: return {'snapshots': [], 'rows': []}
    window = snaps[-last_n:] if last_n > 0 else snaps
    if venues:
        vlist = [v.strip() for v in venues.split(',') if v.strip()]
    else:
        vlist = DEX29 if dex_only else None
    # Window-scoped scan: persistence only ever looks at the last_n
    # snapshots, so never read the full history (was: 3.2M rows/scan).
    q0 = 'SELECT ts, coin, venue, bps8 FROM funding WHERE ts IN (%s)' % ','.join('?' * len(window))
    args: list = list(window)
    if vlist:
        q0 += ' AND venue IN (%s)' % ','.join('?' * len(vlist))
        args += vlist
    per = {}  # (ts, coin) -> [(venue, bps)]
    for ts, coin, venue, bps in c.execute(q0, args):
        try: b = float(bps)
        except (TypeError, ValueError): continue
        per.setdefault((ts, coin), []).append((venue, b))
    oi = {}
    try:
        oi = dict(c.execute('SELECT coin, oi_rank FROM symbols WHERE ts=?', (snaps[-1],)))
    except Exception: pass
    c.close()
    rows = []
    surv: dict = {}
    for coin in {k[1] for k in per}:
        hist = []
        for ts in snaps:
            ll = per.get((ts, coin), [])
            if len(ll) < min_legs:
                hist.append({'ts': ts, 'spread_bps': None})
                continue
            lo = min(ll, key=lambda x: x[1]); hi = max(ll, key=lambda x: x[1])
            s = hi[1] - lo[1]
            hist.append({'ts': ts, 'spread_bps': round(s, 2),
                         'apy': round(s / 100 * 3 * 365, 1),
                         'long': lo[0], 'short': hi[0], 'n_legs': len(ll)})
        wh = hist[-len(window):]
        k = 0
        for h in reversed(wh):
            if h['spread_bps'] is not None and h['spread_bps'] >= threshold_bps: k += 1
            else: break
        for i in range(1, k + 1):
            surv[i] = surv.get(i, 0) + 1
        if k < min_streak: continue  # below the asked streak
        have = [h for h in wh if h.get('spread_bps') is not None]
        if not have: continue
        apys = sorted(h['apy'] for h in have if 'apy' in h)
        med = apys[len(apys) // 2] if apys else 0
        seq = [(h.get('long'), h.get('short')) for h in have]
        flips = sum(1 for a, b in zip(seq, seq[1:]) if a != b and None not in a + b)
        last = have[-1]
        oir = oi.get(coin)
        if flips > 0:
            verdict = 'FLIPPY'
        elif isinstance(oir, int) and oir <= 400:
            verdict = 'STEADY'
        else:
            verdict = 'WATCH'
        paper = (f"PAPER e058 {coin} LONG {last['long']} / SHORT {last['short']} "
                 f"med {med}% last {last['apy']}% ({k}/{len(window)} checks, "
                 f"spread {last['spread_bps']}bps) kill if spread<{threshold_bps:g}bps")
        rows.append({'coin': coin, 'median_apy': med,
                     'persist': f'{k}/{len(window)}', 'streak': k,
                     'min_spread': round(min(h['spread_bps'] for h in have), 2),
                     'spreads': [h.get('spread_bps') for h in wh],
                     'flips': flips, 'oi_rank': oir,
                     'verdict': verdict, 'paper': paper,
                     'long': last.get('long'), 'short': last.get('short'),
                     'spread_bps': last.get('spread_bps'), 'apy': last.get('apy', med),
                     'n_legs': last.get('n_legs'), 'history': wh})
    rows.sort(key=lambda r: r['median_apy'], reverse=True)
    return {'snapshots': window, 'threshold_bps': threshold_bps, 'last_n': len(window),
            'min_streak': min_streak,
            'survival': [{'streak': i, 'n': surv.get(i, 0)} for i in range(1, len(window) + 1)],
            'count': len(rows), 'rows': rows[:200]}

@app.get('/api/report-config')
def report_config():
    return load_config()

@app.post('/api/report-config')
async def report_config_save(req: Request):
    try:
        patch = await req.json()
    except Exception:
        return JSONResponse({'ok': False, 'error': 'invalid JSON'}, status_code=400)
    cfg, err = save_config(patch if isinstance(patch, dict) else {})
    if err:
        return JSONResponse({'ok': False, 'error': err}, status_code=400)
    return {'ok': True, 'config': cfg}

@app.get('/api/signals')
def signal_history(limit: int = 100):
    limit = max(1, min(limit, 500))
    c = db()
    rows = c.execute('SELECT sent_ts, coin, median_apy, spread_bps, long_v, short_v, persist, oi_rank FROM signals ORDER BY rowid DESC LIMIT ?', (limit,)).fetchall()
    c.close()
    return {'count': len(rows), 'rows': [
        {'sent_ts': t, 'coin': co, 'median_apy': ma, 'spread_bps': sp,
         'long_v': lo, 'short_v': sh, 'persist': pe, 'oi_rank': oi}
        for t, co, ma, sp, lo, sh, pe, oi in rows]}

@app.post('/api/signals/log')
async def signal_log(req: Request):
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({'ok': False, 'error': 'invalid JSON'}, status_code=400)
    rows = body.get('rows', []) if isinstance(body, dict) else []
    window = body.get('window', []) if isinstance(body, dict) else []
    if not isinstance(rows, list) or not rows:
        return JSONResponse({'ok': False, 'error': 'empty rows'}, status_code=400)
    ts = log_signal_rows(window, rows)
    return {'ok': True, 'sent_ts': ts, 'logged': len(rows)}

@app.get('/api/backtest')
def backtest():
    """Cached backtest score: do persistent-spread signals still pay 24h later?
    Computed by bin/backtest.py from saved funding data (T0, no network)."""
    try:
        d = json.load(open(os.path.join(BASE, 'backtest.json')))
        return d
    except Exception:
        return {'ok': False, 'error': 'no backtest yet — run bin/backtest.py'}

PAPER_THRESHOLD_BPS = 20.0

def _parse_ts(s):
    try: return datetime.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    except Exception: return None

def _spread_at(coin, ts, vlist=None, min_legs=2):
    """Spread (max-min bps across venues) for one coin at one snapshot. None if < min_legs."""
    c = db()
    try:
        v = vlist or DEX29
        rows = c.execute('SELECT bps8 FROM funding WHERE ts=? AND coin=? AND venue IN (%s)' % ','.join('?' * len(v)), [ts, coin] + v).fetchall()
    finally:
        c.close()
    legs = []
    for (b,) in rows:
        try: legs.append(float(b))
        except (TypeError, ValueError): pass
    if len(legs) < min_legs: return None
    return round(max(legs) - min(legs), 2)

def _paper_run(log_today=True):
    """Log today's steady set once per UTC day; resolve past days 24h later. Returns summary dict."""
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.strftime('%Y-%m-%d')
    steady = persistence(threshold_bps=PAPER_THRESHOLD_BPS, last_n=4).get('rows', [])
    c = db()
    logged = 0
    if log_today:
        lts = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        for r in steady:
            try:
                c.execute('INSERT OR IGNORE INTO paper_calls VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                          (today, lts, r.get('coin'), r.get('median_apy'), r.get('spread_bps'),
                           r.get('long'), r.get('short'), r.get('persist'), r.get('verdict'),
                           r.get('flips'), r.get('oi_rank') if isinstance(r.get('oi_rank'), int) else None))
            except Exception: pass
        c.commit()
        logged = c.execute('SELECT COUNT(*) FROM paper_calls WHERE call_date=?', (today,)).fetchone()[0]
    snaps = [r[0] for r in c.execute('SELECT DISTINCT ts FROM funding ORDER BY ts')]
    days = [r[0] for r in c.execute('SELECT DISTINCT call_date FROM paper_calls ORDER BY call_date')]
    snap_dt = [(s, _parse_ts(s)) for s in snaps]
    resolved_days, rh, rt = 0, 0, 0
    for day in days:
        pending = c.execute('SELECT coin, logged_ts FROM paper_calls WHERE call_date=? AND (call_date, coin) NOT IN (SELECT call_date, coin FROM paper_outcomes)', (day,)).fetchall()
        if pending:
            # Group pending calls by target snapshot: one query per
            # snapshot instead of one connection per coin (was: 73x).
            by_tgt = {}
            for coin, lts in pending:
                base = _parse_ts(lts)
                if not base: continue
                cutoff = base + datetime.timedelta(hours=24)
                tgt = next((s for s, dt in snap_dt if (dt or cutoff) >= cutoff), None)
                if tgt is None: continue
                by_tgt.setdefault(tgt, []).append(coin)
            for tgt, coins in by_tgt.items():
                q = 'SELECT coin, bps8 FROM funding WHERE ts=? AND coin IN (%s) AND venue IN (%s)' % (
                    ','.join('?' * len(coins)), ','.join('?' * len(DEX29)))
                legs = {}
                for co, b in c.execute(q, [tgt] + coins + DEX29):
                    try: legs.setdefault(co, []).append(float(b))
                    except (TypeError, ValueError): pass
                for co in coins:
                    ll = legs.get(co, [])
                    if len(ll) < 2: continue
                    s24 = round(max(ll) - min(ll), 2)
                    hit = 1 if s24 >= PAPER_THRESHOLD_BPS else 0
                    try:
                        c.execute('INSERT OR IGNORE INTO paper_outcomes VALUES (?,?,?,?,?)',
                                  (day, co, hit, s24, now.strftime('%Y-%m-%dT%H:%M:%SZ')))
                    except Exception: pass
            c.commit()
        dh, dt = c.execute('SELECT COALESCE(SUM(hit),0), COUNT(*) FROM paper_outcomes WHERE call_date=?', (day,)).fetchone()
        if dt and dt == c.execute('SELECT COUNT(*) FROM paper_calls WHERE call_date=?', (day,)).fetchone()[0]:
            resolved_days += 1
        rh += dh or 0; rt += dt or 0
    c.close()
    hr = round(100.0 * rh / rt, 1) if rt else None
    return {'ok': True, 'today': today, 'today_logged': logged,
            'today_coins': [r.get('coin') for r in steady[:5]],
            'resolved_days': resolved_days, 'paper_hit_rate_pct': hr,
            'paper_n_hit': rh, 'paper_n': rt}

@app.get('/api/paper/calls')
def ballot():
    """Paper ballot list: every logged call + outcome status (ISSUES #8).
    One endpoint serves the ballot table + countdown; newest first."""
    return _cached(('ballot',), 60, _ballot_compute)


def _ballot_compute():
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        _paper_run(log_today=False)
        try:
            _vvv = json.load(open(os.path.join(BASE, 'data', 'volume.json')))
            _vols_b = _vvv.get('vols', {}) or {}
            _floor_b = float(_vvv.get('floor_usd', 1000000))
        except Exception:
            _vols_b, _floor_b = {}, 1000000.0
        c = db()
        rows = c.execute('SELECT call_date, logged_ts, coin, median_apy, spread_bps, long_v, short_v, verdict, persist, flips, oi_rank FROM paper_calls ORDER BY logged_ts DESC, coin LIMIT 300').fetchall()
        outs = {(d, co): (h, s, rt_) for d, co, h, s, rt_ in c.execute('SELECT call_date, coin, hit, spread_24h, resolved_ts FROM paper_outcomes')}
        c.close()
        calls, waits, win = [], [], {}
        for day, lts, coin, apy, sp, lo, sh, ve, pe, fl, oi in rows:
            base = _parse_ts(lts)
            ago = (now - base).total_seconds() / 3600 if base else None
            ago_h = round(ago, 1) if ago is not None and ago >= 0 else None
            o = outs.get((day, coin))
            if o is None:
                wait = max(0.0, 24 - ago) if ago is not None else 24.0
                waits.append(wait)
                w = win.setdefault(day, {'n': 0, 'first': lts, 'last': lts})
                w['n'] += 1
                w['first'] = min(w['first'], lts)
                w['last'] = max(w['last'], lts)
                if ago_h is not None:
                    st = f"called {ago_h:.0f}h ago · grades in {wait:.0f}h"
                else:
                    st = f"grades in {wait:.0f}h"
                hit, s24, wait_h = None, None, round(wait, 1)
                rts = None
                try: grd = (base + datetime.timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ') if base else None
                except Exception: grd = None
            else:
                hit, s24, rts = o
                grd = rts
                st = ('hit' if hit else 'miss') + (f" · called {ago_h:.0f}h ago" if ago_h is not None else '')
                wait_h = 0.0
            calls.append({'call_date': day, 'logged_ts': lts, 'coin': coin,
                          'median_apy': apy, 'spread_bps': sp, 'long_v': lo,
                          'short_v': sh, 'verdict': ve, 'status': st,
                          'persist': pe, 'flips': fl, 'oi_rank': oi,
                          'called_ago_h': ago_h, 'grades_in_h': wait_h,
                          'vol_usd': round(_vols_b.get(str(coin).upper(), 0) or 0),
                          'sized': bool((_vols_b.get(str(coin).upper(), 0) or 0) >= _floor_b),
                          'hit': hit, 'spread_24h': s24, 'exit_ts': rts, 'grade_at': grd})
        # Rolling grade windows, one per pending day (UX law: every number
        # carries its time window) — e.g. 81×09-13→grade 09-14 05:04–22:04.
        def _hh(s):
            try: return str(s)[11:16]
            except Exception: return '?'
        wins = []
        for day in sorted(win):
            w = win[day]
            b0 = _parse_ts(w['first'])
            gday = (b0 + datetime.timedelta(hours=24)).strftime('%m-%d') if b0 else '?'
            wins.append(f"{w['n']}×{day[5:]}→grade {gday} {_hh(w['first'])}–{_hh(w['last'])} UTC")
        by_date = {day: {'pending': win[day]['n'], 'logged_first': win[day]['first'],
                         'logged_last': win[day]['last']} for day in sorted(win)}
        cd = ('grading now' if min(waits) < 1 else f"first grade ~{min(waits):.0f}h") if waits else 'all graded'
        if wins:
            cd += ' · ' + ' · '.join(wins)
        # run #110 (owner friction, phone): summary line stays ONE plain line
        # ("grading now · 87 waiting"); per-day windows live behind the tap.
        _pend = len(waits)
        _base = ('grading now' if min(waits) < 1 else f"first grade ~{min(waits):.0f}h") if waits else 'all graded'
        cds = _base + (f" · {_pend} waiting" if waits else '')
        rule = 'hit = spread still \u226520bps at first snapshot \u226524h after logging'
        # run #101: paper-cushion line — misses-to-bar as a number, not a warning.
        # Owner reads the collapsed summary and knows if the paper edge is alive.
        rh = sum(1 for h, s, _ in outs.values() if h == 1)
        rt = len(outs)
        pend = len(waits)
        import math as _m
        if rt:
            need = _m.ceil(0.30 * (rt + pend)) - rh
            cushion = f"needs {need} of next {pend} to hold 30%" if need > 0 else f"above 30% bar by {-need}"
            hr = round(100.0 * rh / rt, 1)
        else:
            cushion, hr = 'no grades yet', None
        return {'ok': True, 'rule': rule, 'countdown': cd, 'countdown_short': cds, 'count': len(calls), 'calls': calls, 'by_date': by_date,
                'waiting': _pend, 'grade_status': _base,
                'cushion': cushion, 'paper_hits': rh, 'paper_resolved': rt, 'paper_hit_rate_pct': hr}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}

@app.get('/api/paper')
def paper():
    """Paper-trade loop: auto-log today's steady calls, resolve past days 24h later."""
    try:
        return _paper_run(log_today=True)
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}

def _server_card():
    """Server-rendered one-line verdict + data-pulse for the topcard (no JS needed)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    c = db()
    n = c.execute('SELECT COUNT(*) FROM funding').fetchone()[0]
    snaps = [r[0] for r in c.execute('SELECT DISTINCT ts FROM funding ORDER BY ts')] or ['unknown']
    c.close()
    last = snaps[-1]
    base = _parse_ts(last)
    age_m = (now - base).total_seconds() / 60 if base else 9999
    gaps = []
    for a, b in zip(snaps[-6:-1], snaps[-5:]):
        pa, pb = _parse_ts(a), _parse_ts(b)
        if pa and pb: gaps.append((pb - pa).total_seconds() / 60)
    cad = round(sorted(gaps)[len(gaps) // 2]) if gaps else 15
    try:
        steady = persistence(threshold_bps=PAPER_THRESHOLD_BPS, last_n=4).get('rows', [])
    except Exception:
        steady = []
    try:
        _b = json.load(open(os.path.join(BASE, 'backtest.json')))
        _pc = _b.get('per_coin', {}) if _b.get('ok') else {}
    except Exception:
        _pc = {}
    # Lead with what the owner can act on: proven pays first, never the
    # lure number (fleet-wide lure-lead fix, cf e060 run #64). A proven
    # payer (24h record, N>=5, hit-rate>=50%) leads whatever its current
    # verdict; unproven "new" coins never lead, even when STEADY.
    def _good(coin):
        st = _pc.get(coin)
        try:
            return bool(st) and int(st.get('n', 0)) >= 5 and float(st.get('hit', 0)) / float(st.get('n', 1)) >= 0.5
        except (TypeError, ValueError, ZeroDivisionError):
            return False
    def _tier(r):
        if _good(r.get('coin')):
            t = 0  # proven pay — holdable edge first
        elif r.get('verdict') == 'STEADY':
            t = 1  # new: holding so far, no 24h record yet
        else:
            t = {'WATCH': 2, 'FLIPPY': 3}.get(r.get('verdict'), 2)
        try:
            pay = -float(r.get('median_apy') or 0)
        except (TypeError, ValueError):
            pay = 0
        return (t, pay)
    t3 = sorted(steady, key=_tier)[:3]
    def _held(coin):
        st = _pc.get(coin)
        return f" ({st['hit']}/{st['n']} paid)" if st else ''
    _PLAIN = {'STEADY': 'steady', 'WATCH': 'watch'}
    def _verdict(r):
        if r.get('verdict') == 'FLIPPY':
            return 'flippy'
        if r.get('verdict') == 'STEADY' and r.get('coin') not in _pc:
            return 'new'
        return _PLAIN.get(r.get('verdict'), r.get('verdict') or r.get('persist'))
    if t3:
        _proven = [f"{r['coin']} {r['median_apy']}% {_verdict(r)}" for r in t3 if _good(r['coin'])]
        _newn = sum(1 for r in t3 if not _good(r['coin']))
        # One-line lure guard (run #67): biggest numbers are usually unproven
        # "new" coins — lead with proven pays only, collapse new to a count
        # so the owner taps holdable edge first (buttons below still list all).
        top = 'Top pays now: ' + (' \u00b7 '.join(_proven) if _proven else 'no proven pay yet \u2014 new coins holding below')
        if _newn:
            top += f" \u00b7 +{_newn} new high pay{'s' if _newn > 1 else ''} below (unproven)"
        top += " \u00b7 tap a coin for why"
    else:
        top = 'Top pays now: none holding right now'
    try:
        b = json.load(open(os.path.join(BASE, 'backtest.json')))
        _wl = str(b.get('window_last', ''))[:16].replace('T', ' ')
        _wf = str(b.get('window_first', ''))[:16].replace('T', ' ')
        _wrange = f"{_wf[5:]}Z \u2192 {_wl[5:]}Z" if _wl and _wf else ((_wl[5:] + 'Z') if _wl else '?')
        if b.get('ok'):
            _brows = [('replay 24h', f"{b.get('hit_rate_pct')}% ({b.get('n_hit')}/{b.get('n_signals')})", 'history replay: past signals still paying 24h later'),
                      ('replay window', _wrange, 'signals evaluated in this range')]
        else:
            _brows = [('replay 24h', 'pending', 'no replay computed yet')]
    except Exception:
        _brows = [('replay 24h', 'pending', 'no replay computed yet')]
    try:
        pc = db()
        pr = pc.execute('SELECT COALESCE(SUM(hit),0), COUNT(*) FROM paper_outcomes').fetchone()
        if pr[1]:
            _prows_p = [('paper 24h', f"{round(100.0*pr[0]/pr[1],1)}% ({pr[0]}/{pr[1]})", 'live calls graded so far')]
        else:
            today = now.strftime('%Y-%m-%d')
            tc = pc.execute('SELECT COUNT(*) FROM paper_calls WHERE call_date=?', (today,)).fetchone()[0]
            try:
                _old = pc.execute('SELECT MIN(logged_ts) FROM paper_calls LEFT JOIN paper_outcomes USING (call_date, coin) WHERE paper_outcomes.coin IS NULL').fetchone()[0]
            except Exception:
                _old = None
            _cd = ''
            _ob = _parse_ts(_old) if _old else None
            if _ob:
                _h = 24 - (now - _ob).total_seconds() / 3600
                if _h > 0:
                    _cd = ", grading now" if _h < 1 else f", first grade ~{_h:.0f}h"
            _prows_p = [('paper 24h', f"{tc} logged today, grades after 24h{_cd}" if tc else 'logging', 'live calls graded so far')]
        pc.close()
    except Exception:
        _prows_p = [('paper 24h', 'logging', 'live calls graded so far')]
    _hr = f"{n/1e6:.1f}M" if n >= 1_000_000 else f"{n//1000}k"
    try:
        _rn = _rh = _tn = _th = 0
        for _st in _pc.values():
            _n = int(_st.get('n', 0) or 0)
            _h = int(_st.get('hit', 0) or 0)
            if _n >= 5:
                _rn += _n
                _rh += _h
            else:
                _tn += _n
                _th += _h
        _gate_rows = ([('proven (n\u22655)', f"{round(100.0*_rh/max(1,_rn),1)}% ({_rh}/{_rn})", 'well-sampled coins: the tradable edge'),
                        ('thin (n<5)', f"{round(100.0*_th/max(1,_tn),1)}% ({_th}/{_tn})", 'too few samples: noise, not trusted')]
                 if (_rn + _tn) > 0 else [])
    except Exception:
        _gate_rows = []
    # run #167: size filter — free Binance quoteVolume joined into the
    # paper grade (bin/volume.py, $0). Thin-volume steady pays are
    # suspected mirages; the owner reads sized-vs-thin in one glance.
    try:
        _vv = json.load(open(os.path.join(BASE, 'data', 'volume.json')))
        _vols = _vv.get('vols', {}) or {}
        _floor = float(_vv.get('floor_usd', 1000000))
        _vts = _vv.get('ts', '?')
        _pcc = db()
        _outs = _pcc.execute(
            'SELECT coin, hit FROM paper_outcomes').fetchall()
        _pcc.close()
        _sn = _sh = _tn2 = _th2 = 0
        for _co, _hh in _outs:
            if (_vols.get(str(_co).upper(), 0) or 0) >= _floor:
                _sn += 1
                _sh += int(_hh or 0)
            else:
                _tn2 += 1
                _th2 += int(_hh or 0)
        _size_rows = ([('sized (\u2265$1M vol)',
                         f"{round(100.0*_sh/max(1,_sn),1)}% ({_sh}/{_sn})",
                         f"big-market calls, vol {_vts[5:10]}"),
                        ('thin-vol (<$1M)',
                         f"{round(100.0*_th2/max(1,_tn2),1)}% ({_th2}/{_tn2})",
                         'small-market: likely mirage, not trusted')]
                 if (_sn + _tn2) > 0 else [])
    except Exception:
        _size_rows = []
    _prows = ([('rows', _hr, 'funding readings stored'),
               ('sample', f"{age_m:.0f}m ago", 'time since last snapshot'),
               ('cadence', f"~{cad}m", 'median gap between snapshots')]
              + _brows + _prows_p + _gate_rows + _size_rows + [('version', _VRUN, 'code running now')])
    pulse = ('<table id="ppulse"><tbody>' + ''.join(
        f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td><td>{html.escape(str(m))}</td></tr>"
        for k, v, m in _prows) + '</tbody></table>')
    if t3:
        _row = ''.join(
            f"<button class=pick onclick=\"pickCoin('{html.escape(r['coin'])}')\">"
            f"{html.escape(r['coin'])}<br><b class=pos>{html.escape(str(r['median_apy']))}%</b> "
            f"<small>{html.escape(_verdict(r))}{html.escape(_held(r['coin']))}</small></button>"
            for r in t3)
    else:
        _row = ''
    # First-paint digest line from saved config (was "loading…" until JS
    # fetched /api/report-config — owner saw a dead line on every cold open).
    # JS loadCfg() still refines it with local-time after load.
    try:
        _cfg = json.load(open(REPORT_CFG))
        try:
            _thr = '%g' % float(_cfg.get('threshold_bps', 50))
        except (TypeError, ValueError):
            _thr = str(_cfg.get('threshold_bps', 50))
        _dg = (f"Daily digest {_cfg.get('report_hour_utc', 8)}:00 UTC, "
               f"top {_cfg.get('top_n', 10)} over {_thr}bps "
               f"(tap to change time)")
    except Exception:
        _dg = 'Daily digest (tap to change time)'
    return html.escape(top), pulse, _row, html.escape(_dg)

def _plain_ver(msg):
    import re as _re
    m = _re.sub(r'^run\s*#?\d+\s*:\s*\w+\s*', '', msg or '')
    m = _re.sub(r'\([^)]*\)', '', m).strip(' \u2014-')
    m = _re.sub(r'\s{2,}', ' ', m).strip()
    return m[:90]

@app.get('/', response_class=HTMLResponse)
def index():
    return _cached(('index',), 45, _index_compute)


def _index_compute():
    try:
        top, pulse, row, digest = _server_card()
    except Exception:
        top, pulse, row, digest = 'Top persistent spreads: unavailable', '', '', 'Daily digest (tap to change time)'
    try:
        _vmsg = _sp.run(['git', 'log', '-1', '--format=%s', '--', 'app.py', 'bin/', 'tests/'], capture_output=True,
                         text=True, cwd=BASE).stdout.strip() or ''
    except Exception:
        _vmsg = ''
    verline = 'v' + _VRUN + ((' \u2014 ' + _plain_ver(_vmsg)) if _plain_ver(_vmsg) else '')
    try:
        _t = table()
        coins_html = _tl_table('coins', _tl_coin_rows(_t.get('rows')), _TL_COINS_COLS, 'apy', -1, ('pickCoin', 'coin'), derived={'apy': 'spread', 'spread': ['long_bps', 'short_bps']}, total=_t.get('count'), layout=[['coin', 'apy'], ['spread'], ['long', 'short'], ['long_bps', 'short_bps'], ['legs', 'oi']])
    except Exception:
        coins_html = '<div class=cav>coins: offline</div>'
    try:
        _b = ballot()
        _paper_rows = []
        for c in (_b.get('calls') or []):
            _s24, _sp = c.get('spread_24h'), c.get('spread_bps')
            _dl = (round(_s24 - _sp, 1) if isinstance(_s24, (int, float)) and isinstance(_sp, (int, float)) else None)
            _paper_rows.append({'coin': c.get('coin'), 'apy': c.get('median_apy'),
                         'long': c.get('long_v'), 'short': c.get('short_v'),
                         'spin': _sp, 'persist': c.get('persist'), 'flips': c.get('flips'),
                         'oi': (c.get('oi_rank') if isinstance(c.get('oi_rank'), int) else '500+'),
                         'verdict': c.get('verdict'), 'entry': c.get('logged_ts'),
                         'exit': c.get('exit_ts'), 'grade_at': c.get('grade_at'), 'spout': _s24, 'delta': _dl,
                         'result': ('hit' if c.get('hit') == 1 else
                                    'miss' if c.get('hit') == 0 else '\u2026')})
        paper_html = _tl_table('paper', _paper_rows, _TL_PAPER_COLS, 'apy', -1, ('pickCoin', 'coin'), derived={'apy': 'spin', 'delta': ['spin', 'spout']}, layout=[['coin', 'apy'], ['long', 'short'], ['spin', 'spout'], ['delta', 'result'], ['persist', 'flips'], ['oi', 'verdict'], ['entry', 'exit'], ['grade_at']])
        _hr = _b.get('paper_hit_rate_pct')
        _graded = f"{_b.get('paper_resolved', 0)} ({_hr}% hit)" if _hr is not None else f"{_b.get('paper_resolved', 0)} graded"
        psum_html = (f'<table id="psummary"><tbody>'
            f"<tr><td>calls logged</td><td id='ps-pred'>{_b.get('count', 0)}</td><td>every paper prediction ever recorded</td></tr>"
            f"<tr><td>graded</td><td id='ps-graded'>{_graded}</td><td>old enough to check 24h later; % still paying</td></tr>"
            f"<tr><td>waiting</td><td id='ps-wait'>{_b.get('waiting', 0)} \u00b7 {html.escape(str(_b.get('grade_status', '')))}</td><td>logged &lt;24h ago; grade pending</td></tr>"
            f"<tr><td>hit rule</td><td id='ps-rule'>{html.escape(str(_b.get('rule', '')))}</td><td>how a call scores; exit is the first snapshot \u226524h after logging</td></tr>"
            f"<tr><td>cushion vs 30%</td><td id='ps-cushion'>{html.escape(str(_b.get('cushion', '')))}</td><td>bar: paper must hold \u226530% hits; hits still needed from pending</td></tr>"
            '</tbody></table>')
        _pwin_rows = []
        for _day in sorted(_b.get('by_date') or {}):
            _w = _b['by_date'][_day]
            _b0 = _parse_ts(_w.get('logged_first'))
            _g = ((_b0 + datetime.timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')
                  if _b0 else '?')
            _pwin_rows.append({'day': _day, 'pending': _w.get('pending'),
                               'first': _w.get('logged_first'), 'last': _w.get('logged_last'),
                               'grades': _g})
        pwin_html = _tl_table('pwin', _pwin_rows, _TL_PWIN_COLS, 'day', 1)
        _fc = db()
        _mts = _fc.execute('SELECT MAX(ts) FROM funding').fetchone()[0]
        _snapn = _fc.execute('SELECT COUNT(*) FROM funding WHERE ts=?', (_mts,)).fetchone()[0] if _mts else 0
        _sign = _fc.execute('SELECT COUNT(*), MAX(sent_ts) FROM signals').fetchone()
        _fc.close()
        _hp = persistence()
        funnel_html = (f'<table id="pfunnel"><tbody>'
            f"<tr><td>snapshot rows</td><td>{_snapn:,}</td><td>readings in the latest capture (venues × coins)</td></tr>"
            f"<tr><td>holding 4/4 \u226520bps</td><td>{_hp.get('count', 0)}</td><td>coins whose spread survived 4 straight checks</td></tr>"
            f"<tr><td>signals sent</td><td>{_sign[0] or 0} total</td><td>Telegram alerts: digest \u226550bps top-10 + urgent \u2265150bps; list shows last 100</td></tr>"
            f"<tr><td>paper logged</td><td>{_b.get('count', 0)}</td><td>steady-set calls in the 24h experiment</td></tr>"
            f"<tr><td>graded</td><td>{_graded}</td><td>with 24h outcome; the tradable verdict</td></tr>"
            '</tbody></table>')
    except Exception:
        paper_html = '<div class=cav>ballot: offline</div>'
        psum_html = '<div class=cav>summary: offline</div>'
        pwin_html = ''
        funnel_html = ''
    try:
        _p = persistence()
        _pwl = len(_p.get('snapshots') or [])
        _pers_rows = [{'coin': r.get('coin'), 'streak': f"{r.get('streak')}/{_pwl}",
                        'apy': r.get('median_apy'), 'spin': r.get('spread_bps'),
                        'curve': r.get('spreads'), 'minw': r.get('min_spread'),
                        'verdict': r.get('verdict'), 'long': r.get('long'), 'short': r.get('short')}
                       for r in (_p.get('rows') or [])]
        pers_html = _tl_table('pers', _pers_rows, _TL_PERS_COLS, 'apy', -1)
        pers_sum = f"{_p.get('count', 0)} holding \u2265{_p.get('threshold_bps')}bps"
        surv_html = ' \u00b7 '.join(f"{s.get('streak')}: {s.get('n')}" for s in (_p.get('survival') or []))
    except Exception:
        pers_html = '<div class=cav>persistence: offline</div>'
        pers_sum, surv_html = '', ''
    try:
        _s = signal_history()
        _sig_rows = [{'sent': r.get('sent_ts'), 'coin': r.get('coin'), 'apy': r.get('median_apy'),
                       'spread': r.get('spread_bps'), 'long': r.get('long_v'), 'short': r.get('short_v'),
                       'persist': r.get('persist'),
                       'oi': (r.get('oi_rank') if isinstance(r.get('oi_rank'), int) else '')}
                      for r in (_s.get('rows') or [])]
        sig_html = _tl_table('sig', _sig_rows, _TL_SIG_COLS, 'sent', -1, derived={'apy': 'spread'})
        _sh = db()
        _shrows = _sh.execute("SELECT substr(sent_ts,12,2) h, COUNT(*) FROM signals GROUP BY h ORDER BY h").fetchall()
        _sh.close()
        sighours_html = ('<table id="sighours"><tbody>' + ''.join(
            f"<tr><td>{h}h</td><td>{n}</td></tr>" for h, n in _shrows) + '</tbody></table>') if _shrows else ''
    except Exception:
        sig_html = '<div class=cav>signals: offline</div>'
        sighours_html = ''
    return HTMLResponse(INDEX.replace('%%TOPONE%%', top).replace('%%PULSE%%', pulse).replace('%%TOPROW%%', row).replace('%%DIGEST%%', digest).replace('%%VER%%', html.escape(verline)).replace('%%COINS%%', coins_html).replace('%%PERS%%', pers_html).replace('%%PERSSUM%%', pers_sum).replace('%%SURV%%', surv_html).replace('%%PAPER%%', paper_html).replace('%%FUNNEL%%', funnel_html).replace('%%PSUMMARY%%', psum_html).replace('%%PWIN%%', pwin_html).replace('%%SIGNALS%%', sig_html).replace('%%SIGHOURS%%', sighours_html),
                        headers={'Cache-Control': 'no-store'})

if __name__ == '__main__':
    print(load_all())
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('E058_PORT', '8320')))
