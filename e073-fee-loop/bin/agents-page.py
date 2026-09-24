#!/usr/bin/env python3
"""Agents page v2: static shell + legs.json, page polls JSON every 5s and
upserts rows (no full reload). Regen writes both files; run after each leg
(llm-leg.sh hook) and each tick (tick.sh hook) so heartbeat stays fresh.
Usage: python3 bin/agents-page.py"""
import json, os, re, time
SESS_ROOT = os.path.expanduser('~/.pi/agent/sessions')
LIVE_MODEL = 'muse-spark-1.3-contributor'
UPAT = re.compile(r'"usage":\{"input":(\d+),"output":(\d+),[^}]*?"total":([0-9.e-]+)\}')
def session_path(tid):
    cutoff = time.time() - 3600
    try: roots = [os.path.join(SESS_ROOT, d) for d in os.listdir(SESS_ROOT)]
    except OSError: return None
    best = None
    for root in roots:
        for dp, _, fns in os.walk(root):
            for fn in fns:
                if not fn.endswith('.jsonl') or '.pi-web-activity' in fn: continue
                p = os.path.join(dp, fn)
                try:
                    if os.path.getmtime(p) < cutoff: continue
                    if tid in fn: return p
                    if tid in open(p, errors='ignore').read(4000): return p
                except OSError: continue
    return best
def live_usage(tid):
    p = session_path(tid)
    if not p: return None
    ti = to = 0; cost = 0.0
    try: raw = open(p, errors='ignore').read()
    except OSError: return None
    for a, b, c in UPAT.findall(raw):
        ti += int(a); to += int(b)
        try: cost += float(c)
        except ValueError: pass
    return (ti, to, round(cost, 6)) if ti else None
def session_view(tid):
    p = session_path(tid)
    if not p: return None
    msgs = []
    ti = to = 0; cost = 0.0
    try: lines = open(p, errors='ignore').read().splitlines()
    except OSError: return None
    for l in lines:
        m = re.search(r'"usage":\{"input":(\d+),"output":(\d+),[^}]*?"total":([0-9.e-]+)\}', l)
        if m:
            ti += int(m.group(1)); to += int(m.group(2))
            try: cost += float(m.group(3))
            except ValueError: pass
            continue
        try: e = json.loads(l)
        except ValueError: continue
        if e.get('type') != 'message': continue
        msg = e.get('message', {})
        role = msg.get('role')
        parts = msg.get('content')
        if not isinstance(parts, list): continue
        for part in parts:
            t = part.get('type')
            if t == 'text' and role in ('user', 'assistant'):
                txt = part.get('text', '')
                if txt.strip(): msgs.append({'who': 'agent' if role == 'assistant' else 'you', 'text': txt[:2000]})
            elif t == 'toolCall':
                args = json.dumps(part.get('arguments', {}))[:120]
                msgs.append({'who': 'tool', 'text': f"{part.get('name')}: {args}"})
    return {'updated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'totals': {'in': ti, 'out': to, 'cost': round(cost, 6)},
            'raw': log_of(tid),
            'messages': msgs[-120:]}
def rc_of(note):
    m = re.search(r'rc=(\d+)', note or '')
    return int(m.group(1)) if m else None
from datetime import datetime, timezone
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def desc(tid, fallback):
    import glob
    rep = os.path.join(base, 'runs', f'{tid}.md')
    title = ''
    if os.path.exists(rep):
        for l in open(rep, errors='ignore').read().splitlines():
            if l.startswith('# '): title = l[2:].strip()[:100]; break
    fs = sorted(glob.glob(os.path.join(base, 'runs', f'leg-*-{tid}.md')))
    files = ''
    if fs:
        try: lines = open(fs[-1], errors='ignore').read().splitlines()
        except OSError: lines = []
        done = [l.strip() for l in lines if l.strip().startswith('LEG_DONE')]
        if done:
            m = re.search(r'files=(\S+)', done[0])
            if m: files = m.group(1)[:80]
    if title and files: return f'{title} → {files}'
    return title or (f'files: {files}' if files else fallback)
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
import glob as _glob
def transcript_done(tid):
    pats = _glob.glob(os.path.join(base, 'runs', f'leg-*-{tid}.md'))
    pats += _glob.glob(os.path.join(base, 'runs', f'{tid}.md'))
    if tid.startswith('decide-'):
        pats += _glob.glob(os.path.join(base, 'runs', f'{tid}.md'))
    for p in pats:
        try:
            if 'LEG_DONE' in open(p, errors='ignore').read(): return True
        except OSError: pass
    return False
spend = {}
for line in load('ledger/credits.jsonl'):
    try: e = json.loads(line)
    except ValueError: continue
    if e.get('kind') == 'llm' and e.get('task'): spend[e['task']] = e
rows = []
for tid in sorted(set(starts) | set(spend), reverse=True):
    s = spend.get(tid, {})
    en = ends.get(tid)
    done = bool(en and en['ok']) or (spend.get(tid) and transcript_done(tid))
    rows.append({'task': tid, 'agent': s.get('model', '?'), 'start': starts.get(tid, '?'),
        'end': s.get('ts', '?'), 'tin': s.get('tokens_in'), 'tout': s.get('tokens_out'),
        'cost': s.get('cost_usd'), 'note': s.get('note', ''),
        'status': 'done' if done else ('failed' if en else 'running')})
RC_MEAN = {0: 'success', 124: 'timeout (20min cap)'}
def rc_txt(rc):
    if rc is None: return 'running'
    return RC_MEAN.get(rc, 'failed')
def log_of(tid):
    import glob
    for pat in (f'leg-*-{tid}.md', f'{tid}.md'):
        fs = sorted(glob.glob(os.path.join(base, 'runs', pat)))
        if fs: return 'runs/' + os.path.basename(fs[-1])
    return None
for r in rows:
    r['note'] = desc(r['task'], r['note'] or 'pre-metering leg — see runs/')
    r['rc'] = rc_txt(rc_of(spend.get(r['task'], {}).get('note', '')))
    r['log'] = log_of(r['task'])
    if r['status'] == 'running' and r['tin'] is None:
        lv = live_usage(r['task'])
        if lv: r['tin'], r['tout'], r['cost'] = lv
        if r['agent'] == '?': r['agent'] = LIVE_MODEL
    if r['status'] == 'running':
        sv = session_view(r['task'])
        if sv:
            os.makedirs(os.path.join(base, 'sessions'), exist_ok=True)
            json.dump(sv, open(os.path.join(base, 'sessions', r['task'] + '.json'), 'w'))
            r['log'] = 'session.html?task=' + r['task']
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
js = """<script>
function T(x){if(!x||x=='?')return '?';const d=new Date(x);return isNaN(d)?x:d.toLocaleString();}
let last='',lastSig='',legs=[],sk=localStorage.getItem('sk')||'end',sd=parseInt(localStorage.getItem('sd')||'-1');
function sort(k){sd=(sk===k)?-sd:-1;sk=k;localStorage.setItem('sk',sk);localStorage.setItem('sd',sd);render();}
function val(r,k){const v=r[k];if(v==null)return sd>0?Infinity:-Infinity;return v;}
const KEYS=['agent','task','start','end','tin','tout','cost','status','rc',null,null];
function render(){const tb=document.getElementById('tb');if(!tb)return;
const s=[...legs].sort((a,b)=>{const x=val(a,sk),y=val(b,sk);return (x<y?-1:x>y?1:0)*sd;});
tb.innerHTML=s.map(r=>'<tr class="'+r.status+'">'+[r.agent,r.task,T(r.start),T(r.end),r.tin??'—',r.tout??'—',r.cost??'—',r.status,r.rc??'—',r.note,'<a href="'+(r.log||'#')+'">open</a>'].map(x=>'<td>'+x+'</td>').join('')+'</tr>').join('');
document.querySelectorAll('#t th').forEach((th,i)=>{const base=th.textContent.replace(/[ ▲▼]/g,'');th.textContent=base+((KEYS[i]&&KEYS[i]===sk)?(sd>0?' ▲':' ▼'):'');});}
async function up(){try{const r=await (await fetch('legs.json?'+Date.now())).text();
if(r===last)return;last=r;const d=JSON.parse(r);
const sig=JSON.stringify(d.legs);if(sig===lastSig)return;lastSig=sig;
document.getElementById('hb').textContent='loop heartbeat: '+T(d.heartbeat)+' · updated '+T(d.generated_at);
legs=d.legs;render();}catch(e){}}
up();setInterval(up,3000);</script>"""
html = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>agents working</title>
<style>body{{font-family:system-ui;margin:1em;font-size:16px}}.wrap{{overflow-x:auto;-webkit-overflow-scrolling:touch}}table{{border-collapse:collapse}}#t{{min-width:640px}}td,th{{border:1px solid #ccc;padding:6px 8px;font-size:14px}}th{{background:#f0f0f0}}.running{{background:#fff3cd}}.failed{{background:#f8d7da}}.done{{background:#d4edda}}#hb{{margin:1em 0;font-weight:bold}}</style>
</head><body><h1>agents working</h1><div id=hb></div>
<div id=cad>checks state every ~3s · page refreshes every 3s · new agent within 5min of idle</div>
<div class=wrap><table id=t><thead><tr><th onclick="sort('agent')">agent</th><th onclick="sort('task')">task</th><th onclick="sort('start')">started</th><th onclick="sort('end')">finished</th><th onclick="sort('tin')">in</th><th onclick="sort('tout')">out</th><th onclick="sort('cost')">cost</th><th onclick="sort('status')">status</th><th onclick="sort('rc')">return code</th><th>what</th><th>log</th></tr></thead>
<tbody id=tb>
{tr}</tbody></table></div>
<style>th{{cursor:pointer}}</style>
{js}</body></html>"""
open(os.path.join(base, 'agents.html'), 'w').write(html)
open(os.path.join(base, 'log.html'), 'w').write(r"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>leg log</title>
<style>body{font-family:system-ui;margin:1em;font-size:15px}pre{white-space:pre-wrap;word-break:break-word;font-size:13px}a{font-size:16px}</style>
</head><body><a href=agents.html>← back</a><div id=rep></div><h2>transcript</h2><pre id=b>loading…</pre>
<script>function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;');}
async function up(){try{const f=new URLSearchParams(location.search).get('file');if(!f)return;
let task=(f.match(/leg-\d+T\d+Z-(.+)\.md/)||[])[1]||(f.match(/(decide-\S+)\.md/)||[])[1]||'';
let rep='';
if(task){try{rep=await (await fetch('runs/'+task+'.md?'+Date.now())).text();}catch(e){}}
if(rep&&!rep.startsWith('<')){const R=document.getElementById('rep');
R.innerHTML=rep.split('\n').map(l=>{const s=l.trim();
if(s.startsWith('### '))return '<h3>'+esc(s.slice(4))+'</h3>';
if(s.startsWith('## '))return '<h2>'+esc(s.slice(3))+'</h2>';
if(s.startsWith('# '))return '<h1>'+esc(s.slice(2))+'</h1>';
if(!s)return '<br>';return esc(l)+'<br>';}).join('');}
const t=await (await fetch(f+'?'+Date.now())).text();
const clean=t.split('\n').filter(l=>{const s=l.trim();return s&&!s.startsWith('[')&&!s.startsWith('Warning')&&!s.includes('sync-opencode')&&!s.includes('zz-groq');});
document.getElementById('b').innerHTML=clean.map(l=>{const s=l.trim();
if(s.startsWith('LEG_DONE'))return '<b style="color:green">'+esc(l)+'</b>';
if(/fail|error|rc=[1-9]/i.test(s))return '<b style="color:red">'+esc(l)+'</b>';
return esc(l);}).join('\n')||'(no readable output yet — leg starting)';}catch(e){}}
up();setInterval(up,3000);</script></body></html>""")
open(os.path.join(base, 'session.html'), 'w').write(r"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>agent live</title>
<style>body{font-family:system-ui;margin:1em;font-size:15px}#meta{position:sticky;top:0;background:#111;color:#fff;padding:8px;border-radius:8px;font-size:14px}#c{margin-top:1em}.you{background:#e7f3ff;border-radius:8px;padding:8px;margin:6px 0}.agent{background:#f0f0f0;border-radius:8px;padding:8px;margin:6px 0;white-space:pre-wrap;word-break:break-word}.tool{color:#666;font-size:13px;margin:4px 0;white-space:pre-wrap;word-break:break-word}a{font-size:16px}</style>
</head><body><a href=agents.html>← back</a> <a id=raw href=#>raw log</a><div id=meta>…</div><div id=c></div>
<script>function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;');}
let last='';
async function up(){try{const t=new URLSearchParams(location.search).get('task');if(!t)return;
const r=await (await fetch('sessions/'+t+'.json?'+Date.now())).text();
if(r===last)return;last=r;const d=JSON.parse(r);
document.getElementById('raw').href=d.raw?('log.html?file='+d.raw):'#';
document.getElementById('meta').textContent='in '+d.totals.in.toLocaleString()+' · out '+d.totals.out.toLocaleString()+' · $'+d.totals.cost+' · '+d.updated;
const c=document.getElementById('c');const stick=(innerHeight+scrollY>document.body.scrollHeight-200);
c.innerHTML=d.messages.map(m=>'<div class="'+m.who+'">'+esc(m.text)+'</div>').join('');
if(stick)scrollTo(0,document.body.scrollHeight);}catch(e){}}
up();setInterval(up,3000);</script></body></html>""")
print(f"agents.html + legs.json: {len(rows)} legs, heartbeat {hb}")
