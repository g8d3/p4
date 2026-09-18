#!/usr/bin/env python3
"""e070 desk: read-only dashboard over the folder (the folder is truth).

Serves :8327 — verdict + pulse + funds + 7 SQL tables.
Read-only: never writes, never calls a model. Credits API cached 60s.
Stdlib only. Threaded so page + api never block each other.

SQL-table rule: every fact lives in a table; SQL verbs are UI gestures,
never typed commands (header tap = ORDER BY, column filter = WHERE/LIKE,
min+max = WHERE BETWEEN, pager = LIMIT+OFFSET, per-page = LIMIT,
chips = saved VIEW). Tables render server-side (real <tr> rows in the
HTML) via bin/tables.py — native to this experiment, zero external code.
ONE_TABLE: one entity = one table; focused cuts are VIEW chips, never
a second table.
"""
import calendar
import datetime
import json
import os
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(DIR, "bin"))

import tables  # noqa: E402

PORT = int(os.environ.get("E070_PORT", "8327"))
FLOOR = 0.80
CACHE = {"credits": None, "ts": 0}

SQL_LEGEND = ("tap header = ORDER BY · filter in column = WHERE / LIKE · "
              "min+max = WHERE BETWEEN · pager = LIMIT + OFFSET · "
              "per-page = LIMIT · chips = saved VIEW")


def transcript(short):
    """Serve a materialized leg transcript (owner-written files only)."""
    try:
        rows = tables.read_jsonl(os.path.join(DIR, "data", "sessions.jsonl"), 50)
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


def heartbeats():
    rows = tables.read_jsonl(os.path.join(DIR, "log", "heartbeat.jsonl"), 200)
    missing = not os.path.isfile(os.path.join(DIR, "log", "heartbeat.jsonl"))
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


def pulse_for(beats, mode, mode_row):
    now = time.time()
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
    cycle_age = None
    if "cycle" in beats:
        try:
            cycle_age = (now - calendar.timegm(time.strptime(beats["cycle"]["last"], "%Y-%m-%dT%H:%M:%SZ"))) / 60
        except (ValueError, KeyError):
            pass
    if cycle_age is not None and cycle_age <= 40 and mode == "RUN":
        return {"level": "RUNNING",
                "text": "Daemon alive (beat %.1fm ago) — iterating every ~30 min without anyone. Next run automatic."
                % cycle_age}
    if active_now and mode == "PAUSED":
        return {"level": "LIVE",
                "text": "%s active %.1fm ago DESPITE pilot pause — unsanctioned, investigate."
                % (latest_who, latest_age)}
    if mode == "PAUSED":
        return {"level": "PAUSED",
                "text": "Pilot resting since %s — nothing is spending. Next check %s "
                "(triggers re-checked then, or sooner if one fires). Resumes on: %s."
                % (tables.user_date(mode_row.get("ts", "")),
                   mode_row.get("review_on", "no date set — ask for one"),
                   mode_row.get("resume", "owner decision"))}
    if latest_age is None:
        return {"level": "UNKNOWN",
                "text": "No heartbeats ever recorded — nothing has run yet."}
    if latest_ev == "end":
        return {"level": "IDLE",
                "text": "%s finished %.1fm ago — parked between legs, not dead. "
                "A finished heartbeat can never read as LIVE." % (latest_who, latest_age)}
    if latest_age <= 10:
        return {"level": "LIVE",
                "text": "%s active %.1fm ago — a leg is running right now."
                % (latest_who, latest_age)}
    if latest_age <= 45:
        return {"level": "IDLE",
                "text": "Quiet for %.1fm (last: %s). Legs run ~30-45 min then pause "
                "for review — quiet is normal, not death." % (latest_age, latest_who)}
    return {"level": "STALLED",
            "text": "No heartbeat for %.1fm (limit 45m). The loop may be dead — "
            "watchdog WAKEUP applies." % latest_age}


def build_stamp():
    try:
        ts = os.path.getmtime(os.path.join(DIR, "bin", "desk.py"))
        return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%m-%d %H:%M")
    except (OSError, ValueError):
        return "?"


def state():
    ledger = tables.read_jsonl(os.path.join(DIR, "data", "ledger.jsonl"), 5000)
    ledger_missing = not os.path.isfile(os.path.join(DIR, "data", "ledger.jsonl"))
    decisions = tables.read_jsonl(os.path.join(DIR, "data", "decisions.jsonl"), 30)
    decisions = decisions[::-1]  # newest first
    mode = decisions[0].get("mode", "RUN") if decisions else "RUN"
    mode_row = decisions[0] if decisions else {}
    sessions = tables.read_jsonl(os.path.join(DIR, "data", "sessions.jsonl"), 30)
    go_usage_rows = tables.read_jsonl(os.path.join(DIR, "data", "go-baseline.json"), 5)
    go_usage = go_usage_rows[-1] if go_usage_rows else None
    metr = tables.read_jsonl(os.path.join(DIR, "data", "metrics.jsonl"), 5)
    beats, beats_missing = heartbeats()
    paper = sum(1 for e in ledger if e.get("kind") == "PAPER")
    confirmed = sum(1 for e in ledger if e.get("kind") == "CONFIRMED")
    cost = 0.0
    jev_n, jev_spend = 0, 0.0
    verdicts = {"ESCALATE": 0, "REVIEW": 0, "SKIP": 0}
    for e in ledger:
        try:
            cost += float(e.get("cost_usd", 0) or 0)
        except (TypeError, ValueError):
            pass
        lane = None
        for k in ("triage", "jev"):
            v = e.get(k)
            if isinstance(v, dict):
                lane = v
                try:
                    cost += float(v.get("cost_usd", 0) or 0)
                except (TypeError, ValueError):
                    pass
                break
        if lane is None:
            continue
        jev_n += 1
        if lane.get("verdict") in verdicts:
            verdicts[lane["verdict"]] += 1
        for src in (lane, e):
            try:
                c = float(src.get("cost_usd", 0) or 0)
            except (TypeError, ValueError):
                c = 0.0
            if c:
                jev_spend += c
                break
    cost = round(cost, 6)
    jev_spend = round(jev_spend, 6)
    llm_n = sum(1 for e in ledger
                if e.get("kind") == "COST" and e.get("who") == "builder")
    total_n = jev_n + llm_n
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
    pulse = pulse_for(beats, mode, mode_row)
    loop = ("STOPPED" if (stops and max(e.get("ts", "") for e in stops) >= (decisions[0].get("ts", "") if decisions and decisions[0].get("mode") == "RUN" else "")) else ("PAUSED" if mode == "PAUSED" else "PILOT"))
    if loop == "PILOT" and pulse["level"] in ("STALLED", "IDLE"):
        loop = "STALE" if pulse["level"] == "STALLED" else loop
    s = {
        "credits": credits(), "floor": FLOOR,
        "heartbeats": beats, "beats_missing": beats_missing,
        "ledger_missing": ledger_missing,
        "counts": {"paper": paper, "confirmed": confirmed, "spend_usd": cost,
                   "ledger_rows": len(ledger)},
        "economy": {"jev_decisions": jev_n, "llm_calls": llm_n,
                    "jev_spend_usd": jev_spend, "total_spend_usd": cost,
                    "utilization": round(jev_n / total_n, 2) if total_n else None,
                    "recent10": round(rj / recent_total, 2) if recent_total else None,
                    "verdicts": verdicts, "confirmed": confirmed,
                    "spend_per_confirmed": round(cost / confirmed, 6) if confirmed else None,
                    "go_legs": len(sessions),
                    "go_model": os.environ.get("OPENCODE_GO_MODEL", "unknown"),
                    "go_plan": "OpenCode Go $10/mo flat (unmetered by key)",
                    "go_usage": go_usage, "target": 0.9},
        "stops": stops[-5:],
        "events": ledger[-30:][::-1],
        "metrics": metr[-1] if metr else None,
        "pulse": pulse,
        "loop": loop,
        "build": build_stamp(),
        "stale_agents": stale_agents,
    }
    s["tables"] = {ns: len(fn()[0]) for ns, _, fn in tables.TABLES}
    return s


CARD_TITLES = {"stages": "Pipeline — is the loop progressing?",
               "opps": "Score+Act — opportunities (incl. needs-you 👀)",
               "ledger": "Money trail — ledger tail",
               "decisions": "Memory — decisions (pivots)",
               "trends": "Radar — trend briefs",
               "sight": "Radar — watcher finds",
               "sessions": "Workers & sessions",
               "res": "Resources — what the fleet spends"}


def page():
    st = state()
    funds_rows, funds_cols = tables.funds_rows(st)
    funds_html = tables.render("funds", funds_rows, funds_cols, per=10)
    cards = []
    for ns, _, fn in tables.TABLES:
        rows, cols = fn()
        per = 10 if len(rows) > 10 else max(len(rows), 1)
        presets = tables.opportunities_presets() if ns == "opps" else None
        cards.append(
            '<div class=card id=c-%s><h2>%s (%d rows)</h2>'
            '<p class=sql>%s</p>%s</div>'
            % (ns, CARD_TITLES[ns], len(rows), SQL_LEGEND,
               tables.render(ns, rows, cols, per=per, presets=presets)))
    funds_card = ('<div class=card><h2>Money — funds &amp; KPIs (%d rows)</h2>'
                  '<p class=sql>%s</p>%s</div>'
                  % (len(funds_rows), SQL_LEGEND, funds_html))
    cards.insert(1, funds_card)
    c = st["credits"]
    credits_line = ("$%.4f left (floor $%.2f)" % (c["remaining"], st["floor"])
                    if c.get("ok") else "STALE CREDITS — %s" % (c.get("error") or "unreachable"))
    html = ("""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>e070 profit loop</title>
<style>
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;max-width:1000px;margin:0 auto;padding:12px;line-height:1.45;background:#f3f1ea;color:#201d16}
.card{background:#fff;border:1px solid #e6e1d4;border-radius:14px;padding:12px 14px;margin-bottom:12px}
.card h2{font-size:14px;color:#6f6a5c;margin:0 0 6px}
.verdict{font-size:16px;margin:2px 0 8px}
.mut{color:#6f6a5c;font-size:13px}
.sql{font-size:12px;color:#1d4ed8;background:#e5edfd;border-radius:8px;padding:6px 8px;margin:0 0 6px}
.pulse{font-size:15px;margin:2px 0 8px}
.foot{color:#6f6a5c;font-size:12px;text-align:center;margin:14px 0 6px}
""" + tables.TABLE_CSS + """</style></head><body>
<h1>e070 profit loop</h1>
<div id=verdict class=cav><p class=verdict>Turn ~$9.81 of OpenRouter credits into real cash. """
            """Track A WATCH at $0, Track B free proof-of-work only. PAPER never counts as profit.</p></div>
<div id=pulse class=cav><p class=pulse><b>@PLEVEL@</b> — @PTEXT@</p>
<p class=mut id=creditsline>credits @CREDITS@ · loop @LOOP@ · api/state live</p></div>
@CARDS@
<div class=foot>folder is truth · build @BUILD@ · ledger append-only · api/state + selfcheck dogfood · one entity one table · times @TZ@</div>
<script>""" + tables.CLIENT_JS + """
async function tick(){try{const r=await fetch("/api/state?_="+Date.now(),{cache:"no-store"});
const d=await r.json();const w=d.pulse||{};
document.querySelector("#pulse .pulse").innerHTML="<b>"+w.level+"</b> — "+w.text;
const c=d.credits||{};
document.getElementById("creditsline").textContent="credits "+(c.ok?("$"+c.remaining+" left (floor $"+d.floor+")"):("STALE — "+(c.error||"unreachable")))+" · loop "+d.loop+" · api/state live";
}catch(e){}}
document.addEventListener("DOMContentLoaded",function(){
document.querySelectorAll("[id^=tdata-]").forEach(function(el){try{tLoad(el.id.replace("tdata-",""))}catch(e){}});
setInterval(tick,30000)});
</script>
</body></html>""")
    html = html.replace("@PLEVEL@", st["pulse"]["level"]).replace("@PTEXT@", st["pulse"]["text"]).replace("@CREDITS@", credits_line).replace("@LOOP@", st["loop"]).replace("@CARDS@", "\n".join(cards)).replace("@TZ@", tables.USER_TZ).replace("@BUILD@", st["build"])
    return html


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = self.path.split("?", 1)[0]
        if route.startswith("/api/transcript/"):
            self._send(json.dumps(transcript(route.rsplit("/", 1)[-1])).encode(),
                       "application/json")
        elif route == "/api/state":
            self._send(json.dumps(state()).encode(), "application/json")
        else:
            self._send(page().encode(), "text/html; charset=utf-8")


if __name__ == "__main__":
    print("e070 desk on :%d" % PORT, flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
