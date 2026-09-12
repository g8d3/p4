#!/usr/bin/env python3
"""e058 funding scanner web app — thin slice 1.
SQLite store (timestamped funding series) + FastAPI JSON + static table UI.
Run: python3 app.py  (port 8320)"""
import datetime, json, glob, os, sqlite3, time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get('E058_DB', os.path.join(BASE, 'data.db'))
CAP_GLOBS = [os.path.join(BASE, 'data', '*.json'),
             '/tmp/loris_cap_*.json', '/tmp/loris_funding.json', '/tmp/fund5.json']
DEX29 = ['zo','aster','bluefin','bullet','decibel','edgex','entropyio','extended',
 'grvt','hibachi','hotstuff','hyperliquid','kinetiq','lighter','nado','ondo',
 'pacifica','paradex','paragon','phoenix','qfex','reya','risex','tradexyz',
 'txflow','variational','vest','woofipro']

def db():
    c = sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS funding(ts TEXT, coin TEXT, venue TEXT, bps8 REAL)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_f ON funding(ts, coin)')
    c.execute('CREATE TABLE IF NOT EXISTS symbols(ts TEXT, coin TEXT, oi_rank INTEGER, price_usd REAL, oi_usd REAL, exchange_count INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS signals(sent_ts TEXT, coin TEXT, median_apy REAL, spread_bps REAL, long_v TEXT, short_v TEXT, persist TEXT, oi_rank INTEGER, window TEXT)')
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
                if k == 'report_hour_utc': v = int(v)
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

@app.get('/api/status')
def status():
    c = db()
    snaps = c.execute('SELECT ts, COUNT(*) FROM funding GROUP BY ts ORDER BY ts').fetchall()
    coins = c.execute('SELECT COUNT(DISTINCT coin) FROM funding').fetchone()[0]
    c.close()
    return {'snapshots': [{'ts': t, 'rows': n} for t, n in snaps], 'coins': coins}

@app.get('/api/table')
def table(min_apy: float = 0.0, max_apy: float = 1e9,
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
<title>e058 funding scanner</title>
<style>:root{--bg:#fff;--fg:#111;--bd:#ccc;--hd:#eee}html.dark{--bg:#111418;--fg:#e6e6e6;--bd:#333;--hd:#1e2228}
body{font-family:system-ui;margin:8px;background:var(--bg);color:var(--fg)}table{border-collapse:collapse;width:100%;font-size:14px}
td,th{border:1px solid var(--bd);padding:4px 6px;text-align:right}td:first-child,th:first-child{text-align:left}
th{position:sticky;top:0;background:var(--hd)}input,select,button{background:var(--bg);color:var(--fg);border:1px solid var(--bd)}
.pos{color:#3ddc84}</style></head><body>
<h2>e058 funding scanner <small id=ts></small> <button onclick="document.documentElement.classList.toggle('dark');localStorage.e058t=document.documentElement.classList.contains('dark')?'d':'l'" style=float:right>dark/light</button></h2>
<script>if(localStorage.e058t==='d')document.documentElement.classList.add('dark');</script>
<div id=f>
<label>APY <input id=a0 type=number value=0 style=width:70px>–<input id=a1 type=number value=100000 style=width:80px></label>
<label>OI rank <input id=o0 type=number value=0 style=width:55px>–<input id=o1 type=number value=9999 style=width:60px></label>
<label>min legs <input id=ml type=number value=2 style=width:45px></label>
<label>coin <input id=q type=text placeholder=JUP style=width:70px></label>
<label>sort <select id=s><option value=apy>APY</option><option value=oi>OI rank</option><option value=legs>legs</option></select></label>
<button onclick=load()>filter</button> <small id=c></small>
</div>
<div id=r style="margin:8px 0;border:1px solid var(--bd);padding:6px"><b>scheduled report</b> <small>(full digest only at hour UTC; outside it only urgent &ge;mult&times;threshold notifies)</small><br>
<label>hour UTC <input id=rh type=number min=0 max=23 style=width:50px></label>
<label>threshold bps <input id=rt type=number style=width:70px></label>
<label>last_n <input id=rn type=number style=width:50px></label>
<label>top_n <input id=rtn type=number style=width:50px></label>
<label>urgent&times; <input id=ru type=number step=0.5 style=width:50px></label>
<button onclick=saveCfg()>save</button> <small id=rc></small>
</div>
<div id=s style="margin:8px 0"><b>signal history</b> <small>(every sent alert, newest first — nothing lost)</small> <button onclick=loadSig()>refresh</button>
<table><thead><tr><th>sent (UTC)</th><th>coin</th><th>med APY%</th><th>spread</th><th>long</th><th>short</th><th>persist</th><th>OI</th></tr></thead><tbody id=sb></tbody></table></div>
<table><thead><tr><th>coin</th><th>APY%</th><th>spread bps</th><th>long</th><th>short</th><th>legs</th><th>OI</th></tr></thead>
<tbody id=b></tbody></table>
<script>async function load(){const g=id=>document.getElementById(id).value;
const d=await (await fetch(`/api/table?min_apy=${g('a0')}&max_apy=${g('a1')}&oi_min=${g('o0')}&oi_max=${g('o1')}&min_legs=${g('ml')}&q=${g('q')}&sort=${g('s')}`)).json();
document.getElementById('ts').textContent=d.ts||'no data';
document.getElementById('c').textContent=(d.count??d.rows.length)+' coins';
document.getElementById('b').innerHTML=d.rows.map(r=>
`<tr><td>${r.coin}</td><td class=pos>${r.apy}</td><td>${r.spread_bps}</td><td>${r.long} ${r.long_bps}</td><td>${r.short} ${r.short_bps}</td><td>${r.n_legs}</td><td>${r.oi_rank??'500+'}</td></tr>`).join('');}
async function loadCfg(){try{const c=await (await fetch('/api/report-config')).json();
rh.value=c.report_hour_utc;rt.value=c.threshold_bps;rn.value=c.last_n;rtn.value=c.top_n;ru.value=c.urgent_mult;}catch(e){}}
async function saveCfg(){const b={report_hour_utc:+rh.value,threshold_bps:+rt.value,last_n:+rn.value,top_n:+rtn.value,urgent_mult:+ru.value};
try{const r=await (await fetch('/api/report-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)})).json();
rc.textContent=r.ok?'saved':'ERR: '+(r.error||'?');}catch(e){rc.textContent='ERR: unreachable';}}
async function loadSig(){try{const d=await (await fetch('/api/signals?limit=100')).json();
sb.innerHTML=(d.rows||[]).map(s=>`<tr><td>${s.sent_ts}</td><td>${s.coin}</td><td class=pos>${s.median_apy}</td><td>${s.spread_bps}</td><td>${s.long_v}</td><td>${s.short_v}</td><td>${s.persist}</td><td>${s.oi_rank??''}</td></tr>`).join('');}catch(e){}}
load();loadCfg();loadSig();</script></body></html>"""

@app.get('/api/persistence')
def persistence(threshold_bps: float = 20.0, last_n: int = 4,
                min_legs: int = 2, dex_only: bool = True, venues: str = ''):
    """Spread persistence across snapshots (8h-bps).
    Survivor = spread >= threshold_bps in ALL of the last_n snapshots.
    Ranked by median window APY desc."""
    c = db()
    snaps = [r[0] for r in c.execute('SELECT DISTINCT ts FROM funding ORDER BY ts')]
    if not snaps: return {'snapshots': [], 'rows': []}
    if venues:
        vlist = [v.strip() for v in venues.split(',') if v.strip()]
    else:
        vlist = DEX29 if dex_only else None
    q0 = 'SELECT ts, coin, venue, bps8 FROM funding'
    args: list = []
    if vlist:
        q0 += ' WHERE venue IN (%s)' % ','.join('?' * len(vlist))
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
    window = snaps[-last_n:] if last_n > 0 else snaps
    rows = []
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
        if k < len(window): continue  # not a survivor
        apys = sorted(h['apy'] for h in wh)
        med = apys[len(apys) // 2]
        seq = [(h.get('long'), h.get('short')) for h in wh]
        flips = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
        last = wh[-1]
        rows.append({'coin': coin, 'median_apy': med,
                     'persist': f'{k}/{len(window)}',
                     'flips': flips, 'oi_rank': oi.get(coin),
                     'long': last['long'], 'short': last['short'],
                     'spread_bps': last['spread_bps'], 'apy': last['apy'],
                     'n_legs': last['n_legs'], 'history': wh})
    rows.sort(key=lambda r: r['median_apy'], reverse=True)
    return {'snapshots': window, 'threshold_bps': threshold_bps,
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

@app.get('/', response_class=HTMLResponse)
def index(): return INDEX

if __name__ == '__main__':
    print(load_all())
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('E058_PORT', '8320')))
