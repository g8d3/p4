#!/usr/bin/env python3
"""e060 v1 — Dexscreener-only rotation radar (FREE tier, no keys, no secrets).

Owner decision 2026-09-12: cheapest way (free) -> Dexscreener-only.
No LunarCrush / X pipe. Social velocity deferred; rotation proxy =
boost attention $ x on-chain velocity (volume/txns) from Dexscreener.

Routes: / -> dashboard, /api/rotation -> JSON, /health -> ok.
Cache: data/rotation.json (5 min TTL), stale-badged when Dexscreener unreachable.
"""
import json, math, os, subprocess as _sp, threading, time, urllib.request
_BASE = os.path.dirname(os.path.abspath(__file__))
_VSTART = int(time.time())
try:
    _VRUN = _sp.run(['git', 'log', '-1', '--format=%h', '--', '.'], capture_output=True,
                    text=True, cwd=_BASE).stdout.strip() or '?'
except Exception:
    _VRUN = '?'
def _version():
    try:
        latest = _sp.run(['git', 'log', '-1', '--format=%h', '--', '.'], capture_output=True,
                         text=True, cwd=_BASE).stdout.strip() or '?'
        dirty = bool(_sp.run(['git', 'status', '--short', '--'] + ['e060-social-memecoin-radar/app.py', 'e060-social-memecoin-radar/bin/', 'e060-social-memecoin-radar/tests/'], capture_output=True,
                             text=True, cwd='/home/vuos/code/p4').stdout.strip())
    except Exception:
        latest, dirty = '?', False
    return {"ok": True, "track": "e060", "running": _VRUN,
            "latest": latest, "stale": _VRUN != latest,
            "dirty": dirty, "started_ts": _VSTART}
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("E060_PORT", "8323"))
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "rotation.json")
TTL = 300

BOOSTS_URL = "https://api.dexscreener.com/token-boosts/top/v1"
UA = {"User-Agent": "e060-radar/1.0 (+local)"}

def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def enrich(chain, addr):
    """Best-effort pair stats for one token. Returns dict or {}."""
    url = f"https://api.dexscreener.com/tokens/v1/{chain}/{addr}"
    try:
        pairs = fetch(url, timeout=8)
        if not pairs:
            return {}
        # pick highest-volume pair
        best = max(pairs, key=lambda p: (p.get("volume") or {}).get("h24", 0))
        return {
            "symbol": (best.get("baseToken") or {}).get("symbol", "?"),
            "name": (best.get("baseToken") or {}).get("name", ""),
            "priceUsd": best.get("priceUsd"),
            "vol_h24": (best.get("volume") or {}).get("h24", 0),
            "priceChange_h24": (best.get("priceChange") or {}).get("h24", 0),
            "txns_h24": sum(((best.get("txns") or {}).get("h24") or {}).values()) if isinstance((best.get("txns") or {}).get("h24"), dict) else 0,
            "dex": best.get("dexId", ""),
            "pairUrl": best.get("url", ""),
        }
    except Exception:
        return {}

def build():
    boosts = fetch(BOOSTS_URL, timeout=10)[:15]
    rows = []
    for b in boosts:
        chain, addr = b.get("chainId", "?"), b.get("tokenAddress", "")
        e = enrich(chain, addr) if addr else {}
        amt = b.get("totalAmount", 0) or 0
        vol = e.get("vol_h24", 0) or 0
        score = round(math.log10(amt + 1) * 10 + math.log10(vol + 1) * 5, 1)
        txns = e.get("txns_h24", 0) or 0
        chg = e.get("priceChange_h24") or 0
        # heat: rotation score + trade-speed (log txns) + 24h-move size (capped).
        # txns_h24 was collected but unused — now it powers the ranking.
        heat = round(score + 5 * math.log10(txns + 1) + min(abs(chg), 150) / 10, 1)
        rows.append({
            "symbol": e.get("symbol", "?"), "name": e.get("name", ""),
            "chain": chain, "token": addr,
            "boost_usd": amt, "vol_h24": vol,
            "priceChange_h24": e.get("priceChange_h24"),
            "txns_h24": txns,
            "rotation_score": score, "heat": heat,
            "dex": e.get("dex", ""), "pairUrl": e.get("pairUrl") or b.get("url", ""),
            "dsUrl": b.get("url", ""),
        })
    rows.sort(key=lambda r: r["rotation_score"], reverse=True)
    return {"ts": int(time.time()), "source": "dexscreener-free",
            "note": "heat = score + 5*log10(txns+1) + min(|chg24h|,150)/10; social velocity deferred (no X pipe)",
            "stale": False, "rows": rows}

_REFRESH_LOCK = threading.Lock()
_REFRESHING = False


def maybe_refresh():
    """Serve cache instantly; rebuild in background so the page never hangs."""
    global _REFRESHING
    try:
        if os.path.exists(CACHE) and time.time() - os.path.getmtime(CACHE) < TTL:
            return
    except Exception:
        pass
    with _REFRESH_LOCK:
        if _REFRESHING:
            return
        _REFRESHING = True

    def _run():
        global _REFRESHING
        try:
            data = build()
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            with open(CACHE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass
        finally:
            with _REFRESH_LOCK:
                _REFRESHING = False
    threading.Thread(target=_run, daemon=True).start()


def get_data():
    maybe_refresh()
    try:
        with open(CACHE) as f:
            d = json.load(f)
        # backfill heat for caches written before heat existed (instant, no fetch)
        for r in d.get("rows", []):
            if "heat" not in r:
                tx = r.get("txns_h24", 0) or 0
                ch = r.get("priceChange_h24") or 0
                r["heat"] = round((r.get("rotation_score", 0) or 0) + 5 * math.log10(tx + 1) + min(abs(ch), 150) / 10, 1)
        try:
            age = time.time() - os.path.getmtime(CACHE)
        except Exception:
            age = 0
        if age >= 3 * TTL:
            d["stale"] = True
            d["stale_reason"] = "cache older than 3x TTL, background refresh pending"
        return d
    except Exception as ex:
        return {"ts": int(time.time()), "source": "dexscreener-free",
                "stale": True, "stale_reason": str(ex), "rows": []}

PAGE = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>e060 rotation radar (free)</title><style>body{font-family:system-ui,sans-serif;max-width:900px;margin:1em auto 0;padding:0 1em}html.dark body{background:#111418;color:#e6e6e6}html.dark td,html.dark th{border-color:#444}html.dark a{color:#8ab4ff}table{border-collapse:collapse;width:100%;margin:0;min-width:640px}td,th{border:1px solid #ccc;padding:4px 8px;font-size:13px;text-align:right}td:nth-child(1),th:nth-child(1){text-align:left;position:sticky;left:0;background:#fff;z-index:1}html.dark td:nth-child(1),html.dark th:nth-child(1){background:#111418}.badge{background:#dfd;padding:2px 8px;border-radius:8px}.stale{background:#fdd}details{margin:.4em 0;color:#555;font-size:13px}html.dark details{color:#aaa}summary{cursor:pointer}.twrap{max-height:62vh;overflow:auto;border:1px solid #ccc;border-radius:8px}.twrap thead th{position:sticky;top:0;background:#f4f4f4;z-index:1}html.dark .twrap{border-color:#444}html.dark .twrap thead th{background:#1c2127}.twrap thead th:nth-child(1){z-index:2}html.dark .twrap thead th:nth-child(1){background:#1c2127}.twrap thead th:nth-child(1){background:#f4f4f4}.thumbbar{position:sticky;bottom:0;display:flex;gap:8px;padding:10px 0 calc(12px + env(safe-area-inset-bottom));background:#fff}html.dark .thumbbar{background:#111418}.thumbbar button{flex:1;padding:14px 4px;font-size:16px;border-radius:12px;border:1px solid #ccc;background:#f4f4f4}html.dark .thumbbar button{background:#1c2127;color:#e6e6e6;border-color:#444}.thumbbar button.on{background:#222;color:#fff;border-color:#222}html.dark .thumbbar button.on{background:#e6e6e6;color:#111;border-color:#e6e6e6}small{color:#888;font-size:11px}</style></head>
<body><h1>e060 rotation radar <span class=badge>FREE</span></h1>
<div id=s>loading…</div>
<details><summary>Boost attention × volume + speed — one tap below sorts it.</summary>
<p>Cheapest plan (free, no paid pipe). <b>heat</b> = score + trade-speed + 24h-move size. Per-row <b>trades</b> opens that pair's Dexscreener trades tab (top traders, free, no key). <a href=/api/rotation>JSON</a> <a href=/health>health</a> <small id=ver></small></p></details>
<div class=twrap><table id=t></table></div>
<nav class=thumbbar><button data-k=score class=on>★ Score</button><button data-k=movers>🚀 Movers</button><button data-k=vol>💰 Volume</button><button id=dark>🌙 Dark</button></nav>
<script>if(localStorage.e60==='d')document.documentElement.classList.add('dark')
let ROWS=[],CUR='score';const KEYS={score:(a,b)=>b.rotation_score-a.rotation_score,movers:(a,b)=>Math.abs(b.priceChange_h24||0)-Math.abs(a.priceChange_h24||0),vol:(a,b)=>b.vol_h24-a.vol_h24};
const fmt=n=>n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?(n/1e3).toFixed(1)+'K':Math.round(n)+'';
function render(){const rows=[...ROWS].sort(KEYS[CUR]);let h='<thead><tr><th>token</th><th>heat</th><th>score</th><th>chg24h%</th><th>vol24h</th><th>boost$</th><th>link</th><th>traders</th></tr></thead><tbody>';
for(const r of rows){h+=`<tr><td>${r.symbol} <small>${r.chain}</small></td><td><b>${r.heat??'—'}</b></td><td>${r.rotation_score}</td><td>${r.priceChange_h24??'—'}</td><td>${fmt(r.vol_h24)}</td><td>${r.boost_usd}</td><td><a href="${r.dsUrl}">ds</a></td><td>${r.pairUrl?`<a href="${r.pairUrl}">trades</a>`:'—'}</td></tr>`}
document.getElementById('t').innerHTML=h+'</tbody>'}
fetch('/api/version').then(r=>r.json()).then(v=>{if(v.ok)document.getElementById('ver').textContent='v'+v.running+(v.stale?' STALE—restart':'')+(v.dirty?' *':'')}).catch(()=>{});
fetch('/api/rotation').then(r=>r.json()).then(d=>{ROWS=d.rows;document.getElementById('s').innerHTML=(d.stale?'<span class="badge stale">STALE</span> ':'<span class=badge>LIVE</span> ')+new Date(d.ts*1000).toLocaleString()+' — '+d.rows.length+' tokens';render()});
document.querySelectorAll('.thumbbar [data-k]').forEach(b=>b.onclick=()=>{CUR=b.dataset.k;document.querySelectorAll('.thumbbar [data-k]').forEach(x=>x.classList.toggle('on',x===b));render()});
document.getElementById('dark').onclick=()=>{document.documentElement.classList.toggle('dark');localStorage.e60=document.documentElement.classList.contains('dark')?'d':'l'};</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"ok": True, "track": "e060"}).encode()
            return self.send(body, "application/json")
        if self.path == "/api/version":
            body = json.dumps(_version()).encode()
            return self.send(body, "application/json")
        if self.path == "/api/rotation":
            body = json.dumps(get_data()).encode()
            return self.send(body, "application/json")
        body = PAGE.encode("utf-8")
        return self.send(body, "text/html; charset=utf-8")
    def send(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
