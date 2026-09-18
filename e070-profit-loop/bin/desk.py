#!/usr/bin/env python3
"""e070 desk: read-only dashboard over the folder (the folder is truth).

Serves :8327 — status, credits, per-agent freshness, ledger tail.
Read-only: never writes, never calls a model. Credits API cached 60s.
Stdlib only.
"""
import calendar
import json
import os
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(os.environ.get("E070_PORT", "8327"))
FLOOR = 0.80
CACHE = {"credits": None, "ts": 0}


def transcript(short):
    """Serve a materialized leg transcript (owner-written files only)."""
    try:
        rows, _ = read_jsonl(os.path.join(DIR, "data", "sessions.jsonl"), 50)
    except Exception:  # noqa: BLE001
        return {"ok": False, "error": "sessions registry unreadable"}
    if not any((r.get("sessionId") or "").startswith(short) for r in rows):
        return {"ok": False, "error": "unknown session " + short}
    p = os.path.join(DIR, "data", "transcripts", short + ".md")
    if not os.path.isfile(p):
        return {"ok": False,
                "error": "transcript not yet materialized — check back after the leg closes"}
    with open(p) as f:
        return {"ok": True, "text": f.read()[:6000]}


def read_jsonl(path, limit=50):
    try:
        with open(path) as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
    except FileNotFoundError:
        return [], True
    out = []
    for l in lines[-limit:]:
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out, False


def heartbeats():
    rows, missing = read_jsonl(os.path.join(DIR, "log", "heartbeat.jsonl"), 200)
    now = time.time()
    agents = {}
    for r in rows:
        who = r.get("who", "?")
        try:
            ts = calendar.timegm(time.strptime(r["ts"], "%Y-%m-%dT%H:%M:%SZ"))
        except (KeyError, ValueError):
            continue
        if who not in agents or ts >= agents[who][0]:
            agents[who] = (ts, r["ts"], r.get("event", "beat"))
    return {w: {"last": v[1], "age_min": round((now - v[0]) / 60, 1),
                "event": v[2]}
            for w, v in agents.items()}, missing


def credits():
    if time.time() - CACHE["ts"] < 60 and CACHE["credits"]:
        return CACHE["credits"]
    d = {"ok": False}
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/credits",
            headers={"Authorization": "Bearer " + os.environ.get("OPENROUTER_API_KEY", "")})
        with urllib.request.urlopen(req, timeout=10) as r:
            c = json.loads(r.read())["data"]
        d = {"ok": True, "total": c["total_credits"],
             "used": round(c["total_usage"], 4),
             "remaining": round(c["total_credits"] - c["total_usage"], 4)}
    except Exception as e:  # noqa: BLE001 - dashboard must render stale, not crash
        d = {"ok": False, "error": str(e)[:120]}
    CACHE.update(credits=d, ts=time.time())
    return d


def state():
    ledger, ledger_missing = read_jsonl(os.path.join(DIR, "data", "ledger.jsonl"), 100)
    decisions, _ = read_jsonl(os.path.join(DIR, "data", "decisions.jsonl"), 10)
    decisions = decisions[::-1]  # newest first
    mode = decisions[0].get("mode", "RUN") if decisions else "RUN"
    mode_row = decisions[0] if decisions else {}
    sessions, _ = read_jsonl(os.path.join(DIR, "data", "sessions.jsonl"), 30)
    sessions = sessions[::-1]  # newest first
    go_usage_rows, _ = read_jsonl(os.path.join(DIR, "data", "go-baseline.json"), 5)
    go_usage = go_usage_rows[-1] if go_usage_rows else None
    beats, beats_missing = heartbeats()
    paper = sum(1 for e in ledger if e.get("kind") == "PAPER")
    confirmed = sum(1 for e in ledger if e.get("kind") == "CONFIRMED")
    cost = 0.0
    for e in ledger:
        try:
            cost += float(e.get("cost_usd", 0) or 0)
        except (TypeError, ValueError):
            pass
        tr = e.get("triage", {})
        if isinstance(tr, dict):
            try:
                cost += float(tr.get("cost_usd", 0) or 0)
            except (TypeError, ValueError):
                pass
    cost = round(cost, 6)
    # Jev-first economy: Jev triage rows vs expensive builder (LLM) rows.
    jev_n = 0
    jev_spend = 0.0
    verdicts = {"ESCALATE": 0, "REVIEW": 0, "SKIP": 0}
    for e in ledger:
        t = e.get("triage")
        j = e.get("jev")
        lane = t if isinstance(t, dict) else (j if isinstance(j, dict) else None)
        if lane is None:
            continue
        jev_n += 1
        if lane.get("verdict") in verdicts:
            verdicts[lane["verdict"]] += 1
        for src in (lane, e):  # lane cost first, else row cost; never both
            try:
                c = float(src.get("cost_usd", 0) or 0)
            except (TypeError, ValueError):
                c = 0.0
            if c:
                jev_spend += c
                break
    jev_spend = round(jev_spend, 6)
    llm_n = sum(1 for e in ledger
                if e.get("kind") == "COST" and e.get("who") == "builder")
    total_n = jev_n + llm_n
    go_legs = len(sessions)  # scout/builder legs run on the Go plan (flat, unmetered)
    go_model = os.environ.get("OPENCODE_GO_MODEL", "unknown")
    tail10 = ledger[-10:]
    rj = sum(1 for e in tail10
             if isinstance(e.get("triage"), dict) or isinstance(e.get("jev"), dict))
    rl = sum(1 for e in tail10
             if e.get("kind") == "COST" and e.get("who") == "builder")
    recent_total = rj + rl
    stops = [e for e in ledger if e.get("kind") == "STOP"]
    now = time.time()
    stale_agents = [w for w, b in beats.items()
                    if (now - calendar.timegm(time.strptime(b["last"], "%Y-%m-%dT%H:%M:%SZ"))) > 45 * 60]
    latest_who, latest_age, latest_ev = None, None, "beat"
    for w, b in beats.items():
        try:
            age = (now - calendar.timegm(time.strptime(b["last"], "%Y-%m-%dT%H:%M:%SZ"))) / 60
        except (ValueError, KeyError):
            continue
        if latest_age is None or age < latest_age:
            latest_who, latest_age, latest_ev = w, age, b.get("event", "beat")
    active_now = (latest_age is not None and latest_ev != "end"
                  and latest_age <= 10)
    if active_now and mode == "PAUSED":
        pulse = {"level": "LIVE",
                 "text": "%s active %.1fm ago DESPITE pilot pause — unsanctioned, investigate."
                 % (latest_who, latest_age)}
    elif mode == "PAUSED":
        pulse = {"level": "PAUSED",
                 "text": "Pilot resting since %s — nothing is spending. Next check %s "
                 "(triggers re-checked then, or sooner if one fires). Resumes on: %s."
                 % (mode_row.get("ts", "?")[:10],
                    mode_row.get("review_on", "no date set — ask for one"),
                    mode_row.get("resume", "owner decision"))}
    elif latest_age is None:
        pulse = {"level": "UNKNOWN",
                 "text": "No heartbeats ever recorded — nothing has run yet."}
    elif latest_ev == "end":
        pulse = {"level": "IDLE",
                 "text": "%s finished %.1fm ago — parked between legs, not dead. "
                 "A finished heartbeat can never read as LIVE." % (latest_who, latest_age)}
    elif latest_age <= 10:
        pulse = {"level": "LIVE",
                 "text": "%s active %.1fm ago — a leg is running right now."
                 % (latest_who, latest_age)}
    elif latest_age <= 45:
        pulse = {"level": "IDLE",
                 "text": "Quiet for %.1fm (last: %s). Legs run ~30-45 min then pause "
                 "for review — quiet is normal, not death." % (latest_age, latest_who)}
    else:
        pulse = {"level": "STALLED",
                 "text": "No heartbeat for %.1fm (limit 45m). The loop may be dead — "
                 "watchdog WAKEUP applies." % latest_age}
    return {
        "credits": credits(), "floor": FLOOR,
        "heartbeats": beats, "beats_missing": beats_missing,
        "ledger_missing": ledger_missing,
        "counts": {"paper": paper, "confirmed": confirmed, "spend_usd": cost},
        "economy": {"jev_decisions": jev_n, "llm_calls": llm_n,
                      "jev_spend_usd": jev_spend, "total_spend_usd": cost,
                      "utilization": round(jev_n / total_n, 2) if total_n else None,
                      "recent10": round(rj / recent_total, 2) if recent_total else None,
                      "verdicts": verdicts, "confirmed": confirmed,
                      "spend_per_confirmed": round(cost / confirmed, 6) if confirmed else None,
                      "go_legs": go_legs, "go_model": go_model,
                      "go_plan": "OpenCode Go $10/mo flat (unmetered by key)",
                      "go_usage": go_usage,
                      "target": 0.9},
        "stops": stops[-5:],
        "decisions": decisions,
        "sessions": sessions,
        "pulse": pulse,
        "events": ledger[-30:][::-1],
        "loop": "STOPPED" if stops else ("PAUSED" if mode == "PAUSED" else ("STALE" if latest_age is None or latest_age > 45 else "PILOT")),
        "stale_agents": stale_agents,
    }


PAGE = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>e070 profit loop</title>
<style>body{background:#111;color:#ddd;font-family:system-ui;margin:0;padding:12px}
.card{background:#1c1c1c;border-radius:10px;padding:12px;margin-bottom:10px}
h1{font-size:18px;margin:0 0 8px}h2{font-size:14px;margin:0 0 6px;color:#aaa}
.big{font-size:26px}.ok{color:#6f6}.bad{color:#f66}.warn{color:#fc6}.mut{color:#888}
table{width:100%;border-collapse:collapse;font-size:13px}
td,th{border-bottom:1px solid #333;padding:4px;text-align:left}
.badge{display:inline-block;padding:1px 8px;border-radius:8px;font-size:12px;background:#333}
.dot{display:inline-block;width:11px;height:11px;border-radius:50%;animation:pl 2s infinite}@keyframes pl{50%{opacity:.3}}
button{background:#333;color:#ddd;border:1px solid #555;border-radius:8px;padding:2px 10px;font-size:13px}
pre{white-space:pre-wrap;font-size:12px;margin:4px 0}
</style></head><body>
<h1>e070 profit loop <span class=mut>read-only</span></h1>
<div class=mut style="margin-bottom:10px"><span id=clock>--:--:--</span> · <span id=upd>connecting…</span> · <span id=cd></span> <button id=rb>↻ refresh</button></div>
<div class=card><h2>pulse — is anyone working?</h2><div id=w>loading…</div></div>
<div class=card><h2>workers & sessions (newest first)</h2><table id=x></table></div>
<div class=card><h2>status</h2><div id=s>loading…</div></div>
<div class=card><h2>jev-first economy</h2><div id=j>loading…</div></div>
<div class=card><h2>decisions (pivots)</h2><div id=p>loading…</div></div>
<div class=card><h2>ledger tail</h2><table id=l></table></div>
<script>
const fmt=t=>{try{const d=new Date(t);return isNaN(d)?(t||''):d.toLocaleString([],{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false})}catch(e){return t}};
async function openT(id,i){const r=document.getElementById('t'+i);if(!r)return false;const c=r.querySelector('td');if(r.style.display!=='none'){r.style.display='none';return false}c.textContent='loading transcript…';try{const q=await fetch('/api/transcript/'+id);const j=await q.json();c.innerHTML='';const p=document.createElement('pre');p.textContent=j.ok?j.text:'('+j.error+')';c.appendChild(p)}catch(e){c.textContent='could not load transcript'}r.style.display='';return false}
let next=15;
async function refresh(manual){try{const r=await fetch('/api/state');const d=await r.json();
 const w=d.pulse;
 document.getElementById('w').innerHTML=`<span class=dot style="background:${w.level==='LIVE'?'#4c4':w.level==='STALLED'?'#f44':'#fc0'}"></span> <b>${w.level}</b> — <span>${w.text}</span>`;
 const c=d.credits;
 document.getElementById('s').innerHTML=
  (c.ok?`<span class=big>$${c.remaining}</span> left <span class=mut>(floor $${d.floor})</span>`
       :`<span class=bad>STALE CREDITS</span> <span class=mut>${c.error||''}</span>`)
  +` <span class=badge>${d.loop}</span><br><span class=mut>PAPER ${d.counts.paper} · CONFIRMED ${d.counts.confirmed} · spend $${d.counts.spend_usd}</span>`
  +(d.ledger_missing?'<br><span class=warn>NO LEDGER YET</span>':'');
 const j=d.economy;
 document.getElementById('j').innerHTML=
  j.utilization===null?'<span class=mut>No model calls yet — run bin/loop.sh to log the first Jev triage. Cheap gate first, expensive LLM only on escalation.</span>'
  :`<span class=big>${Math.round(j.utilization*100)}%</span> of metered decisions via Jev <span class=mut>(target ≥90%)</span><br><span class=mut>Jev ${j.jev_decisions} calls / $${j.jev_spend_usd} · metered LLM ${j.llm_calls} calls</span><br><span class=mut>agent legs on Go plan: ${j.go_legs} (${j.go_model}) — flat $10/mo, unmetered by key, abuse-monitored</span>`
  +(j.go_usage?'<br><span class=mut>Go limits: 5h '+j.go_usage.h5_pct+'% · wk '+j.go_usage.wk_pct+'% · mo '+j.go_usage.mo_pct+'% (manual seed '+(j.go_usage.ts||'')+', resets '+j.go_usage.h5_reset+'/'+j.go_usage.wk_reset+'/'+j.go_usage.mo_reset+')</span>':'')
  +(j.utilization<0.9?'<br><span class=warn>Below target: too many expensive calls — check why escalation is high before spending more.</span>':'')
  +`<br><span class=mut>last 10: ${j.recent10===null?'—':Math.round(j.recent10*100)+'% Jev'} · gate: ESC ${j.verdicts.ESCALATE} / REV ${j.verdicts.REVIEW} / SKIP ${j.verdicts.SKIP}</span>`
  +`<br><span class=mut>helping: ${j.confirmed?('$'+j.spend_per_confirmed+' spend per confirmed payout'):'no confirmed payouts yet — helping verdict pending first receipt'}</span>`;
 document.getElementById('p').innerHTML=(d.decisions||[]).length?d.decisions.map(x=>`<div style="margin-bottom:6px">• <b>${x.decision||''}</b> <span class=mut>(${fmt(x.ts)}, ${x.decider||''})</span><br><span class=mut>${x.evidence||''}</span></div>`).join(''):'<span class=mut>No decisions logged yet — the loop has not pivoted.</span>';
 document.getElementById('x').innerHTML='<tr><th>worker</th><th>status</th><th>last activity</th><th></th></tr>'+((d.sessions||[]).map((s,i)=>{const b=(d.heartbeats||{})[s.role]||{};const act=b.age_min!=null?b.age_min+'m ago'+(b.event?' ('+b.event+')':''):'—';return `<tr><td><b>${s.role||''}</b><br><span class=mut>${s.task||''}</span></td><td><span class=badge>${s.status||''}</span></td><td class=mut>${act}</td><td><a href="#" onclick="return openT('${(s.sessionId||'').slice(0,8)}',${i})">open</a></td></tr><tr id="t${i}" style="display:none"><td colspan=4 class=mut></td></tr>`}).join('')||'<tr><td colspan=4 class=mut>No worker sessions yet.</td></tr>');
 /* heartbeat freshness now lives inside the workers table above */
 document.getElementById('l').innerHTML='<tr><th>ts</th><th>who</th><th>kind</th><th>detail</th></tr>'+
  d.events.map(e=>{const t=e.triage||e.jev||null;const lane=t?'JEV':((e.kind==='COST'&&e.who==='builder')?'LLM':'—');const c=t?((t.cost_usd!=null?t.cost_usd:e.cost_usd)):e.cost_usd;const tag=`[${lane}${c!=null?` $${Number(c).toFixed(6)}`:''}]`;const det=t?`${e.task||t.id||''} → <b>${t.verdict||'scored'}</b>${t.verdict?` scam ${t.scam} payout ${t.payout} val ${t.value}`:` ${Object.entries(t).filter(([k,v])=>typeof v==='number').slice(0,3).map(([k,v])=>`${k} ${v}`).join(' ')}`}`:(e.note||e.task||'');return `<tr><td class=mut title="${e.ts||''} UTC">${fmt(e.ts)}</td><td>${e.who||''}</td><td>${e.kind||''}</td><td>${tag} ${det}</td></tr>`}).join('');
document.getElementById('upd').textContent='updated '+new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'})+(manual?' (manual)':'');next=15;}catch(e){document.getElementById('s').innerHTML='<span class=bad>OFFLINE</span> <span class=mut>desk unreachable — the server may be down; anything below is stale.</span>'}}
refresh(false);setInterval(()=>{const c=document.getElementById('clock');if(c)c.textContent=new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'});next--;const u=document.getElementById('cd');if(u)u.textContent='next refresh in '+next+'s';if(next<=0)refresh(false);},1000);document.getElementById('rb').onclick=()=>refresh(true);
</script></body></html>
"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/api/transcript/"):
            body = json.dumps(transcript(self.path.rsplit("/", 1)[-1])).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif self.path == "/api/state":
            body = json.dumps(state()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        else:
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("e070 desk on :%d" % PORT, flush=True)
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
