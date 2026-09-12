#!/usr/bin/env python3
"""e060 v1 — Dexscreener-only rotation radar (FREE tier, no keys, no secrets).

Owner decision 2026-09-12: cheapest way (free) -> Dexscreener-only.
No LunarCrush / X pipe. Social velocity deferred; rotation proxy =
boost attention $ x on-chain velocity (volume/txns) from Dexscreener.

Routes: / -> dashboard, /api/rotation -> JSON, /health -> ok.
Cache: data/rotation.json (5 min TTL), stale-badged when Dexscreener unreachable.
"""
import json, math, os, time, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

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
        rows.append({
            "symbol": e.get("symbol", "?"), "name": e.get("name", ""),
            "chain": chain, "token": addr,
            "boost_usd": amt, "vol_h24": vol,
            "priceChange_h24": e.get("priceChange_h24"),
            "txns_h24": e.get("txns_h24", 0),
            "rotation_score": score,
            "dex": e.get("dex", ""), "pairUrl": e.get("pairUrl") or b.get("url", ""),
            "dsUrl": b.get("url", ""),
        })
    rows.sort(key=lambda r: r["rotation_score"], reverse=True)
    return {"ts": int(time.time()), "source": "dexscreener-free",
            "note": "rotation proxy = boost$ x volume; social velocity deferred (no X pipe)",
            "stale": False, "rows": rows}

def get_data():
    try:
        if os.path.exists(CACHE) and time.time() - os.path.getmtime(CACHE) < TTL:
            with open(CACHE) as f:
                return json.load(f)
    except Exception:
        pass
    try:
        data = build()
    except Exception as ex:
        if os.path.exists(CACHE):
            try:
                with open(CACHE) as f:
                    d = json.load(f)
                d["stale"] = True
                d["stale_reason"] = f"dexscreener unreachable: {ex}"
                return d
            except Exception:
                pass
        return {"ts": int(time.time()), "source": "dexscreener-free",
                "stale": True, "stale_reason": str(ex), "rows": []}
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass
    return data

PAGE = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>e060 rotation radar (free)</title><style>body{font-family:system-ui,sans-serif;max-width:900px;margin:2em auto;padding:0 1em}html.dark body{background:#111418;color:#e6e6e6}html.dark td,html.dark th{border-color:#444}html.dark a{color:#8ab4ff}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:4px 8px;font-size:13px;text-align:right}td:nth-child(1),th:nth-child(1),td:nth-child(2),th:nth-child(2){text-align:left}.badge{background:#dfd;padding:2px 8px;border-radius:8px}.stale{background:#fdd}</style></head>
<body><h1>e060 rotation radar <span class=badge>DEXSCREENER FREE</span> <button onclick="document.documentElement.classList.toggle('dark');localStorage.e60=document.documentElement.classList.contains('dark')?'d':'l'" style=float:right>dark/light</button></h1>
<script>if(localStorage.e60==='d')document.documentElement.classList.add('dark')</script>
<p>Owner decision: cheapest (free). No paid social pipe. Rotation proxy = boost attention x volume. <a href=/api/rotation>JSON</a> <a href=/health>health</a></p>
<div id=s>loading…</div><table id=t></table>
<script>fetch('/api/rotation').then(r=>r.json()).then(d=>{document.getElementById('s').innerHTML=(d.stale?'<span class="badge stale">STALE</span> ':'<span class=badge>LIVE</span> ')+new Date(d.ts*1000).toLocaleString()+' — '+d.rows.length+' tokens';
let h='<tr><th>token</th><th>chain</th><th>score</th><th>boost$</th><th>vol24h</th><th>chg24h%</th><th>link</th></tr>';
for(const r of d.rows){h+=`<tr><td>${r.symbol}</td><td>${r.chain}</td><td>${r.rotation_score}</td><td>${r.boost_usd}</td><td>${Math.round(r.vol_h24)}</td><td>${r.priceChange_h24??'—'}</td><td><a href="${r.dsUrl}">ds</a></td></tr>`}
document.getElementById('t').innerHTML=h})</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"ok": True, "track": "e060"}).encode()
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
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
