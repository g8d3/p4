#!/usr/bin/env python3
"""e058 funding scanner web app — thin slice 1.
SQLite store (timestamped funding series) + FastAPI JSON + static table UI.
Run: python3 app.py  (port 8320)"""
import datetime, html, json, glob, os, sqlite3, time
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
    c.execute('CREATE TABLE IF NOT EXISTS paper_calls(call_date TEXT, logged_ts TEXT, coin TEXT, median_apy REAL, spread_bps REAL, long_v TEXT, short_v TEXT, persist TEXT, verdict TEXT, UNIQUE(call_date, coin))')
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

import subprocess as _sp
_VSTART = int(time.time())
try:
    _VRUN = _sp.run(['git', 'log', '-1', '--format=%h', '--', '.'], capture_output=True,
                    text=True, cwd=BASE).stdout.strip() or '?'
except Exception:
    _VRUN = '?'

@app.get('/api/version')
def version():
    try:
        latest = _sp.run(['git', 'log', '-1', '--format=%h', '--', '.'], capture_output=True,
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
body{font-family:system-ui;margin:8px;background:var(--bg);color:var(--fg);padding-bottom:76px}table{border-collapse:collapse;width:100%;font-size:14px}
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
.pos{color:#3ddc84}</style></head><body>
<h2>e058 funding scanner <small id=ts></small> <button onclick="document.documentElement.classList.toggle('dark');localStorage.e058t=document.documentElement.classList.contains('dark')?'d':'l'" style=float:right>dark/light</button></h2>
<script>if(localStorage.e058t==='d')document.documentElement.classList.add('dark');</script>
<div class=topcard id=top><div class=one id=top-one>%%TOPONE%%</div><div class=row id=top-row></div><div style="margin-top:6px;display:flex;gap:6px;align-items:center;flex-wrap:wrap"><button id=slipbtn onclick="copySlip()" style="padding:8px 12px;font-size:13px">copy paper slip</button> <small id=slipc style="font-size:12px;opacity:.7"></small></div><div style="font-size:12px;opacity:.7;margin-top:4px">steady = held every check — tap a coin to filter below. <button onclick="loadTop()" style="padding:2px 8px;font-size:12px">refresh</button></div><div id=pulse style="font-size:12px;opacity:.7;margin-top:4px">%%PULSE%%</div></div>
<details class=cfg id=fc><summary id=f-sum>Filter: all coins, top pay first (tap to narrow)</summary>
<div id=f style="margin-top:6px">
<label>APY <input id=a0 type=number value=0 style=width:70px>–<input id=a1 type=number value=100000 style=width:80px></label>
<label>OI rank <input id=o0 type=number value=0 style=width:55px>–<input id=o1 type=number value=9999 style=width:60px></label>
<label>min legs <input id=ml type=number value=2 style=width:45px></label>
<label>coin <input id=q type=text placeholder=JUP style=width:70px></label>
<label>sort <select id=s><option value=apy>APY</option><option value=oi>OI rank</option><option value=legs>legs</option></select></label>
<button onclick=load()>filter</button> <small id=c></small>
</div></details>
<details class=cfg id=r><summary id=r-sum>Daily digest: loading… (tap to change time)</summary>
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
<div class=twrap><table><thead><tr><th>sent</th><th>coin</th><th>med APY%</th><th>spread</th><th>long</th><th>short</th><th>persist</th><th>OI</th></tr></thead><tbody id=sb></tbody></table></div></details></div>
<div class=twrap><table><thead><tr><th>coin</th><th>APY%</th><th>spread bps</th><th>long</th><th>short</th><th>legs</th><th>OI</th></tr></thead>
<tbody id=b></tbody></table></div>
<div style="margin:4px 0;font-size:13px"><small id=morec style="opacity:.7"></small> <button id=moreb onclick="showAll()" style="display:none;padding:6px 12px;font-size:13px">show all</button></div>
<div class=thumbbar><button onclick="topGo(this)">★ top</button><button onclick="copySlip()">copy slip</button><button onclick="fltGo()">filter</button></div>
<div id=ver style="font-size:11px;opacity:.6;margin:56px 0 8px"></div>
<script>fetch('/api/version').then(r=>r.json()).then(v=>{if(v.ok)document.getElementById('ver').textContent='v'+v.running+(v.stale?' STALE—restart':'')+(v.dirty?' *':'');}).catch(()=>{});</script>
<script>function locTs(s){try{s=String(s||'').trim();if(!s||s==='unknown')return s||'\u2014';let d;if(/^\d+$/.test(s))d=new Date(+s*1000);else d=new Date(s.replace(' ','T')+(/Z|[+-]\d{2}:?\d{2}$/.test(s)?'':'Z'));if(isNaN(d))return String(s);const p=n=>(n<10?'0':'')+n;return p(d.getMonth()+1)+'/'+p(d.getDate())+' '+p(d.getHours())+':'+p(d.getMinutes());}catch(e){return String(s);}}
function locHour(h){try{const d=new Date();d.setUTCHours(+h,0,0,0);const p=n=>(n<10?'0':'')+n;return p(d.getHours())+':'+p(d.getMinutes());}catch(e){return '?';}}
let allRows=[], showN=100;
function rowHtml(r){return `<tr><td>${r.coin}</td><td class=pos>${r.apy}</td><td>${r.spread_bps}</td><td>${r.long} ${r.long_bps}</td><td>${r.short} ${r.short_bps}</td><td>${r.n_legs}</td><td>${r.oi_rank??'500+'}</td></tr>`;}
function showAll(){showN=allRows.length;document.getElementById('b').innerHTML=allRows.map(rowHtml).join('');const mc=document.getElementById('morec');if(mc)mc.textContent=`showing all ${allRows.length} coins`;const mb=document.getElementById('moreb');if(mb)mb.style.display='none';}
async function load(){showN=100;const g=id=>document.getElementById(id).value;
const d=await (await fetch(`/api/table?min_apy=${g('a0')}&max_apy=${g('a1')}&oi_min=${g('o0')}&oi_max=${g('o1')}&min_legs=${g('ml')}&q=${g('q')}&sort=${g('s')}`)).json();
document.getElementById('ts').textContent=locTs(d.ts||'')||'no data';
allRows=d.rows||[];const total=(d.count??allRows.length);
document.getElementById('c').textContent=`showing ${Math.min(showN,allRows.length)} of ${total}`;
const fs=document.getElementById('f-sum');if(fs){const qq=(g('q')||'').trim().toUpperCase();fs.textContent=`Filter: top ${Math.min(showN,allRows.length)} of ${total}${qq?' matching '+qq:''}, best pay first (tap to narrow)`;}
document.getElementById('b').innerHTML=allRows.slice(0,showN).map(rowHtml).join('');
const mc=document.getElementById('morec'),mb=document.getElementById('moreb');if(allRows.length>showN){if(mc)mc.textContent=`top 100 by pay — tap show all for ${total}`;if(mb)mb.style.display='';}else{if(mc)mc.textContent=allRows.length?`${allRows.length} coins`:'no coins match';if(mb)mb.style.display='none';}}
async function loadCfg(){try{const c=await (await fetch('/api/report-config')).json();
rh.value=c.report_hour_utc;rt.value=c.threshold_bps;rn.value=c.last_n;rtn.value=c.top_n;ru.value=c.urgent_mult;
const rs=document.getElementById('r-sum');if(rs)rs.textContent=`Daily digest ${c.report_hour_utc}:00 UTC (=${locHour(c.report_hour_utc)} your time), top ${c.top_n} over ${c.threshold_bps}bps (tap to change time)`;}catch(e){}}
async function saveCfg(){const b={report_hour_utc:+rh.value,threshold_bps:+rt.value,last_n:+rn.value,top_n:+rtn.value,urgent_mult:+ru.value};
try{const r=await (await fetch('/api/report-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)})).json();
rc.textContent=r.ok?'saved':'ERR: '+(r.error||'?');}catch(e){rc.textContent='ERR: unreachable';}}
async function loadSig(){try{const d=await (await fetch('/api/signals?limit=100')).json();
const ss=document.getElementById('sig-sum');if(ss)ss.textContent=`(${(d.rows||[]).length} alerts, newest first)`;
sb.innerHTML=(d.rows||[]).map(s=>`<tr><td>${locTs(s.sent_ts)}</td><td>${s.coin}</td><td class=pos>${s.median_apy}</td><td>${s.spread_bps}</td><td>${s.long_v}</td><td>${s.short_v}</td><td>${s.persist}</td><td>${s.oi_rank??''}</td></tr>`).join('');}catch(e){}}
let lastTop=[];
async function loadTop(){const one=document.getElementById('top-one'),row=document.getElementById('top-row');
try{const d=await (await fetch('/api/persistence?threshold_bps=20&last_n=4')).json();
const t=(d.rows||[]).slice(0,3);lastTop=t;
if(!t.length){one.textContent='Top persistent spreads: none holding right now';row.innerHTML='';return;}
let pc={};try{const b=await (await fetch('/api/backtest')).json();if(b&&b.ok&&b.per_coin)pc=b.per_coin;}catch(e){}
const held=c=>pc[c]?` (${pc[c].hit}/${pc[c].n} paid)`:' (new)';
one.textContent=`Top persistent spreads: ${t.map(r=>`${r.coin} ${r.median_apy}% ${r.verdict||r.persist}${held(r.coin)}`).join(' · ')}`;
row.innerHTML=t.map(r=>`<button class=pick onclick="pickCoin('${r.coin}')">${r.coin}<br><b class=pos>${r.median_apy}%</b> <small>${r.verdict||r.persist}${held(r.coin)} ${r.long||''}→${r.short||''}</small></button>`).join('');}catch(e){one.textContent='Top persistent spreads: offline';}}
function pickCoin(c){const fc=document.getElementById('fc');if(fc&&!fc.open)fc.open=true;document.getElementById('q').value=c;load();document.getElementById('b').scrollIntoView({block:'nearest'});}
function fltGo(){const fc=document.getElementById('fc');if(fc)fc.open=true;document.getElementById('fc').scrollIntoView();const q=document.getElementById('q');if(q)q.focus({preventScroll:true});}
async function copySlip(){const sc=document.getElementById('slipc');try{if(!lastTop.length)await loadTop();if(!lastTop.length){if(sc)sc.textContent='nothing steady right now';return;}const best=lastTop.find(r=>r.verdict==='STEADY')||lastTop[0];const s=best.paper||`PAPER e058 ${best.coin} ${best.median_apy}%`;await navigator.clipboard.writeText(s);if(sc)sc.textContent=`copied ${best.coin} — paste anywhere`;}catch(e){try{const best2=(lastTop.find(r=>r.verdict==='STEADY')||lastTop[0]||{});prompt('Copy paper slip:',best2.paper||'');if(sc)sc.textContent='copy it by hand';}catch(e2){if(sc)sc.textContent='copy blocked';}}}
function topGo(){document.getElementById('top').scrollIntoView();loadTop();}
load();loadCfg();loadSig();loadTop();</script></body></html>"""

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
                     'persist': f'{k}/{len(window)}',
                     'flips': flips, 'oi_rank': oir,
                     'verdict': verdict, 'paper': paper,
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
                c.execute('INSERT OR IGNORE INTO paper_calls VALUES (?,?,?,?,?,?,?,?,?)',
                          (today, lts, r.get('coin'), r.get('median_apy'), r.get('spread_bps'),
                           r.get('long'), r.get('short'), r.get('persist'), r.get('verdict')))
            except Exception: pass
        c.commit()
        logged = c.execute('SELECT COUNT(*) FROM paper_calls WHERE call_date=?', (today,)).fetchone()[0]
    snaps = [r[0] for r in c.execute('SELECT DISTINCT ts FROM funding ORDER BY ts')]
    days = [r[0] for r in c.execute('SELECT DISTINCT call_date FROM paper_calls ORDER BY call_date')]
    resolved_days, rh, rt = 0, 0, 0
    for day in days:
        pending = c.execute('SELECT coin, logged_ts FROM paper_calls WHERE call_date=? AND (call_date, coin) NOT IN (SELECT call_date, coin FROM paper_outcomes)', (day,)).fetchall()
        if not pending: continue
        done = 0
        for coin, lts in pending:
            base = _parse_ts(lts)
            if not base: continue
            cutoff = base + datetime.timedelta(hours=24)
            tgt = next((s for s in snaps if (_parse_ts(s) or cutoff) >= cutoff), None)
            if tgt is None: continue
            s24 = _spread_at(coin, tgt)
            if s24 is None: continue
            hit = 1 if s24 >= PAPER_THRESHOLD_BPS else 0
            try:
                c.execute('INSERT OR IGNORE INTO paper_outcomes VALUES (?,?,?,?,?)',
                          (day, coin, hit, s24, now.strftime('%Y-%m-%dT%H:%M:%SZ')))
                done += 1
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
    t3 = steady[:3]
    try:
        _b = json.load(open(os.path.join(BASE, 'backtest.json')))
        _pc = _b.get('per_coin', {}) if _b.get('ok') else {}
    except Exception:
        _pc = {}
    def _held(coin):
        st = _pc.get(coin)
        return f" ({st['hit']}/{st['n']} paid)" if st else ' (new)'
    if t3:
        top = 'Top persistent spreads: ' + ' · '.join(f"{r['coin']} {r['median_apy']}% {r.get('verdict') or r.get('persist')}{_held(r['coin'])}" for r in t3)
    else:
        top = 'Top persistent spreads: none holding right now'
    try:
        b = json.load(open(os.path.join(BASE, 'backtest.json')))
        bt = f"backtest {b.get('hit_rate_pct')}% held 24h ({b.get('n_hit')}/{b.get('n_signals')})" if b.get('ok') else 'backtest pending'
    except Exception:
        bt = 'backtest pending'
    try:
        pc = db()
        pr = pc.execute('SELECT COALESCE(SUM(hit),0), COUNT(*) FROM paper_outcomes').fetchone()
        pc.close()
        ph = f"paper {round(100.0*pr[0]/pr[1],1)}% ({pr[0]}/{pr[1]})" if pr[1] else 'paper logging'
    except Exception:
        ph = 'paper logging'
    pulse = (f"data {n//1000}k rows · last sample {age_m:.0f}m ago (every ~{cad}m) | "
             f"{bt} · {ph} | v{_VRUN}")
    return html.escape(top), html.escape(pulse)

@app.get('/', response_class=HTMLResponse)
def index():
    try:
        top, pulse = _server_card()
    except Exception:
        top, pulse = 'Top persistent spreads: unavailable', ''
    return HTMLResponse(INDEX.replace('%%TOPONE%%', top).replace('%%PULSE%%', pulse),
                        headers={'Cache-Control': 'no-store'})

if __name__ == '__main__':
    print(load_all())
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('E058_PORT', '8320')))
