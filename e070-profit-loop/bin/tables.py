#!/usr/bin/env python3
"""e070 tables: NATIVE table renderer + row/column definitions.

Stdlib only. Zero external table code — everything the desk shows is
defined and rendered here, inside this experiment.

SQL-table rule: every fact lives in a table with named atomic columns;
SQL verbs are UI gestures, never typed commands (header tap = ORDER BY,
column filter = WHERE/LIKE, min+max = WHERE BETWEEN, pager = LIMIT+OFFSET,
per-page = LIMIT). Tables render server-side (real <tr> rows in the HTML);
the inline JS only re-sorts/re-filters/re-pages the embedded rows, so
state persists (nothing is ever re-fetched or re-rendered from scratch).

Tables: gates opportunities ledger decisions sessions trends finds
resources funds.
"""
import html as _h
import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# USER_TZ: every human-facing time renders here (IANA name, stdlib only).
# Storage/logs stay UTC ISO-8601. Override with E070_TZ=Area/City.
USER_TZ = os.environ.get("E070_TZ", "America/Bogota")


def _tz():
    try:
        return ZoneInfo(USER_TZ)
    except Exception:  # noqa: BLE001 - unknown zone falls back to UTC
        return timezone.utc


def user_now():
    return datetime.now(timezone.utc).astimezone(_tz())


def user_date(iso):
    """Calendar day of a UTC instant in the user zone (YYYY-MM-DD)."""
    ep = _epoch(iso)
    if ep is None:
        return (iso or "?")[:10]
    return datetime.fromtimestamp(ep, timezone.utc).astimezone(_tz()).strftime("%Y-%m-%d")

TABLE_CSS = """
.twrap{overflow-x:auto;border:1px solid #e6e1d4;border-radius:10px}
@media(max-width:640px){.twrap table{font-size:13px}.twrap th,.twrap td{padding:6px 5px}}
.twrap table{width:100%;min-width:600px;border-collapse:collapse;font-size:14px;background:#fff}
.twrap th,.twrap td{border-bottom:1px solid #e6e1d4;border-right:1px solid #e6e1d4;padding:7px 6px;text-align:left;vertical-align:top}
.twrap th:last-child,.twrap td:last-child{border-right:none}
.twrap thead th{background:#f7f4ec;font-size:12px;color:#6f6a5c;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
.twrap th.srt{cursor:pointer;text-decoration:underline dotted}
.twrap tr.ff td{background:#faf8f2;padding:4px}
.twrap tr.ff input{width:100%;box-sizing:border-box;font-size:12px;padding:3px 5px;border:1px solid #e6e1d4;border-radius:6px}
.twrap tr.ff input.half{width:48%}
.twrap td.n{text-align:right;font-variant-numeric:tabular-nums}
.tctl{display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:13px;color:#6f6a5c;margin:6px 0}
.tctl select{font-size:13px;padding:2px 6px;border-radius:6px;border:1px solid #e6e1d4;background:#fff}
.tpgr{display:flex;gap:8px;align-items:center;font-size:14px;margin:8px 0 2px}
.tpgr button{font-size:14px;padding:4px 14px;border-radius:8px;border:1px solid #e6e1d4;background:#fff;cursor:pointer}
.tviews{display:flex;gap:6px;flex-wrap:wrap;font-size:13px;color:#6f6a5c;margin:6px 0;align-items:center}
.tviews button{font-size:13px;padding:3px 12px;border-radius:999px;border:1px solid #e6e1d4;background:#fff;cursor:pointer}
"""

CLIENT_JS = """
const TBL={};
function tEsc(s){return String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function tSave(ns){try{const T=TBL[ns];localStorage.setItem("e070-"+ns,JSON.stringify({sortKey:T.sortKey,sortDir:T.sortDir,filters:T.filters,page:T.page,per:T.per}));}catch(e){}}
function tLoad(ns){
  let sv={};try{sv=JSON.parse(localStorage.getItem("e070-"+ns)||"{}");}catch(e){}
  const data=JSON.parse(document.getElementById("tdata-"+ns).textContent);
  TBL[ns]={cols:data.cols,rows:data.rows,views:data.views||[],sortKey:sv.sortKey||null,sortDir:sv.sortDir||1,filters:sv.filters||{},page:sv.page||1,per:sv.per||data.per};
  const sel=document.getElementById("tper-"+ns);if(sel)sel.value=String(TBL[ns].per);
  for(const c of data.cols){const f=TBL[ns].filters[c.key];if(f==null)continue;
    if(typeof f==="object"){const a=document.getElementById("tf-"+ns+"-"+c.key+"-lo"),b=document.getElementById("tf-"+ns+"-"+c.key+"-hi");if(a)a.value=f.lo||"";if(b)b.value=f.hi||"";}
    else{const i=document.getElementById("tf-"+ns+"-"+c.key);if(i)i.value=f;}}
  tRender(ns);
}
function tSort(ns,key){const T=TBL[ns];if(T.sortKey===key)T.sortDir*=-1;else{T.sortKey=key;T.sortDir=1;}T.page=1;tSave(ns);tRender(ns);}
function tFilter(ns,key,val){const T=TBL[ns];T.filters[key]=val;T.page=1;tSave(ns);tRender(ns);}
function tFilterR(ns,key,val,edge){const T=TBL[ns];const f=T.filters[key];const o=(f&&typeof f==="object")?{lo:f.lo||"",hi:f.hi||""}:{lo:"",hi:""};o[edge]=val;T.filters[key]=(o.lo===""&&o.hi==="")?null:o;T.page=1;tSave(ns);tRender(ns);}
function tPage(ns,d){const T=TBL[ns];T.page+=d;tSave(ns);tRender(ns);}
function tPer(ns,val){const T=TBL[ns];T.per=(val==="all")?"all":Math.max(1,parseInt(val||"10",10));T.page=1;tSave(ns);tRender(ns);}
function tView(ns,i){const T=TBL[ns];const v=(T.views||[])[i]||{filters:{},sortKey:null,sortDir:1};T.filters=JSON.parse(JSON.stringify(v.filters||{}));T.sortKey=v.sortKey||null;T.sortDir=v.sortDir||1;T.page=1;tSave(ns);tRender(ns);}
function tRender(ns){
  const T=TBL[ns];let rows=T.rows.slice();
  rows=rows.filter(r=>{for(const c of T.cols){const f=T.filters[c.key];
    if(f==null||f===""||(!Array.isArray(f)&&typeof f==="object"&&!f.lo&&!f.hi))continue;
    const cell=r[c.key]||{d:"",s:null};
    if(c.kind==="num"){const v=parseFloat(cell.s);
      if(f.lo!==""&&!(v>=parseFloat(f.lo)))return false;
      if(f.hi!==""&&!(v<=parseFloat(f.hi)))return false;}
    else if(c.kind==="date"){const v=cell.s;
      if(f.lo){const lo=Date.parse(f.lo);if(!(v!=null&&v*1000>=lo))return false;}
      if(f.hi){const hi=Date.parse(f.hi);if(!(v!=null&&v*1000<=hi))return false;}}
    else{const vals=Array.isArray(f)?f:[f];const hay=String(cell.d).toLowerCase();
      if(!vals.some(v=>hay.indexOf(String(v).toLowerCase())>=0))return false;}}
    return true;});
  if(T.sortKey){const col=T.cols.find(c=>c.key===T.sortKey);
    rows.sort((a,b)=>{const x=(a[T.sortKey]||{}).s,y=(b[T.sortKey]||{}).s;
      if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;
      const r=(col&&col.kind==="text")?String(x).localeCompare(String(y)):(x<y?-1:x>y?1:0);
      return r*T.sortDir;});}
  const total=T.rows.length,shown=rows.length;
  const per=(T.per==="all")?Math.max(shown,1):T.per;
  const pages=Math.max(1,Math.ceil(shown/per));
  if(T.page>pages)T.page=pages;if(T.page<1)T.page=1;
  const slice=rows.slice((T.page-1)*per,T.page*per);
  document.querySelector("#tbl-"+ns+" tbody").innerHTML=slice.map(r=>"<tr>"+T.cols.map(c=>{
    const cell=r[c.key]||{d:"—",s:null};const cls=c.kind==="num"?"n":"";
    const ti=cell.t?(' title="'+tEsc(cell.t)+'"'):"";
    return '<td data-l="'+tEsc(c.label)+'" class="'+cls+'"'+ti+">"+tEsc(cell.d)+"</td>";}).join("")+"</tr>").join("");
  document.getElementById("tcnt-"+ns).textContent="Page "+T.page+"/"+pages+" · "+shown+" of "+total+" rows";
  document.getElementById("tpg-"+ns).textContent=T.page+"/"+pages;
  for(const c of T.cols){const el=document.getElementById("tarr-"+ns+"-"+c.key);
    if(el)el.textContent=(T.sortKey===c.key)?(T.sortDir===1?" ▲":" ▼"):"";}
}
"""


def read_jsonl(path, limit=5000):
    try:
        with open(path) as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
    except FileNotFoundError:
        return []
    out = []
    for l in lines[-limit:]:
        try:
            o = json.loads(l)
            if isinstance(o, dict):
                out.append(o)
        except ValueError:
            pass
    return out


def _num(v):
    try:
        f = float(v)
        return f if f == f and abs(f) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _epoch(v):
    if v in (None, ""):
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return int(d.timestamp())
    except (ValueError, OverflowError):
        return None


def _short(ep):
    """User-zone display 'MM/DD HH:MM UTC-5' (offset per timestamp, DST-safe)."""
    try:
        d = datetime.fromtimestamp(int(ep), timezone.utc).astimezone(_tz())
        off = d.utcoffset()
        hrs = int(off.total_seconds() // 3600) if off is not None else 0
        zone = d.strftime("%Z")
        if not zone or zone.startswith(("+", "-")):
            zone = "UTC%+d" % hrs
        return "%02d/%02d %02d:%02d %s" % (d.month, d.day, d.hour, d.minute, zone)
    except (TypeError, ValueError, OverflowError, OSError):
        return "—"


VRANK = {"WATCH": 0, "REVIEW": 1, "SKIP": 2, "SEEN": 3}

# Curated human-gate rows. `vein` joins candidates.jsonl for evidence links;
# everything else is literal copy the owner wrote (short, one fact per cell).
TAKES = [
    {"vein": "one-trader-jev-pilot", "opportunity": "Free alerts to 1 trader",
     "you_do": "Message 1 trader you know: free alerts for a week?",
     "agent_does": "Produces the alerts.", "take": "do"},
    {"vein": "turso-perorg-tip", "opportunity": "Cash tips on merged Turso PRs",
     "you_do": "Nothing. Only at claim: 1 Stripe click with GitHub login.",
     "agent_does": "Re-checks merged PRs for a new tip.", "take": "watch"},
    {"vein": "localbiz-bot-pilot", "opportunity": "Booking bots for local shops",
     "you_do": "Free Fiverr signup (~30 min, your ID) — or message 1 owner.",
     "agent_does": "Builds demo bot + gig text.", "take": "do"},
    {"vein": "wider-oss-hunt", "opportunity": "Paid issues beyond Turso",
     "you_do": "Say go: one recon leg (~$0.0001).",
     "agent_does": "Scouts live paid issues across repos.", "take": "watch"},
    {"vein": "template-pack-notion", "opportunity": "Sell our own Notion pack",
     "you_do": "Nothing now. Gumroad signup only if a pack exists.",
     "agent_does": "Builds the pack.", "take": "forget"},
]


def gates_table():
    """RETIRED (ONE_TABLE violation 1+2): gates was the same grain as
    opportunities ('one opportunity') plus action columns. The columns moved
    into opportunities_table; the focused cut is a VIEW chip ('needs-you'),
    not a table. Kept as a function so old imports fail loudly, not silently."""
    raise RuntimeError("gates_table retired: use opportunities_table + 'needs-you' view")


def opportunities_table():
    opps = {}

    def up(key, name, verdict, payout, ev, url, ts,
           take="—", you_do="—", agent_does="—"):
        o = opps.get(key)
        if o is None:
            opps[key] = {"name": (name or key)[:80],
                         "verdict": verdict or "SEEN", "payout": payout,
                         "ev": ev, "url": url or "", "seen": 1,
                         "first": ts or "", "last": ts or "",
                         "take": take, "you_do": you_do,
                         "agent_does": agent_does}
            return
        o["seen"] += 1
        if ts:
            if not o["first"] or ts < o["first"]:
                o["first"] = ts
            if ts >= o["last"]:
                o["last"] = ts
        if VRANK.get(verdict or "SEEN", 2) < VRANK.get(o["verdict"], 3):
            o["verdict"] = verdict
            if name:
                o["name"] = name[:80]
        if not o["url"] and url:
            o["url"] = url
        for k, v in (("payout", payout), ("ev", ev)):
            if isinstance(v, (int, float)) and (o[k] is None or v > o[k]):
                o[k] = v

    for w in read_jsonl(os.path.join(DIR, "data", "watch.jsonl"), 2000):
        up(w.get("url") or w.get("title") or "?", w.get("title"),
           "SEEN", None, None, w.get("url"), w.get("ts"))
    by_vein = {}
    for r in read_jsonl(os.path.join(DIR, "data", "candidates.jsonl"), 5000):
        if isinstance(r, dict) and r.get("vein"):
            by_vein[r["vein"]] = r
    take_by_vein = {t["vein"]: t for t in TAKES}
    for c in by_vein.values():
        sc = c.get("scores") if isinstance(c.get("scores"), dict) else {}
        t = take_by_vein.get(c.get("vein"), {})
        up(c.get("evidence_url") or c.get("vein"), c.get("vein"),
           c.get("verdict"), sc.get("payout_likely"),
           sc.get("expected_value_14d"), c.get("evidence_url"), None,
           take=t.get("take", "—"), you_do=t.get("you_do", "—"),
           agent_does=t.get("agent_does", "—"))
    # Curated gates with no data row yet are still opportunities (ONE_TABLE:
    # seed the row, don't build a second table for it).
    names = {o["name"] for o in opps.values()}
    for t in TAKES:
        if t["vein"] not in names:
            up(t["vein"], t["vein"],
               "WATCH" if t["take"] == "watch" else "SEEN",
               None, None, "", None, take=t["take"],
               you_do=t["you_do"], agent_does=t["agent_does"])
    rows = sorted(opps.values(),
                  key=lambda o: (VRANK.get(o["verdict"], 3), o["name"]))
    cols = [
        {"key": "name", "label": "opportunity", "kind": "text",
         "ph": "filter…"},
        {"key": "verdict", "label": "signal", "kind": "text", "ph": "WATCH?"},
        {"key": "take", "label": "take", "kind": "text", "ph": "do?"},
        {"key": "payout", "label": "payout", "kind": "num", "fmt": "{:.2f}"},
        {"key": "ev", "label": "ev 14d", "kind": "num", "fmt": "{:.2f}"},
        {"key": "seen", "label": "seen", "kind": "num", "fmt": "{:.0f}"},
        {"key": "you_do", "label": "you do", "kind": "text",
         "ph": "filter…"},
        {"key": "agent_does", "label": "agent does", "kind": "text",
         "ph": "filter…"},
        {"key": "last", "label": "last seen", "kind": "date"},
        {"key": "url", "label": "link", "kind": "text", "ph": "url"},
    ]
    return rows, cols


def opportunities_presets():
    """VIEW chips over the ONE opportunities table (ONE_TABLE: views never
    duplicate rows — the old gates table is this first chip)."""
    return [
        {"name": "👀 needs-you", "sortKey": "take", "sortDir": 1,
         "filters": {"take": ["do", "watch", "forget"]}},
        {"name": "WATCH only", "sortKey": "payout", "sortDir": -1,
         "filters": {"verdict": ["watch"]}},
    ]


def ledger_table():
    rows = []
    for e in read_jsonl(os.path.join(DIR, "data", "ledger.jsonl"), 5000):
        lane = None
        for k in ("triage", "jev"):
            v = e.get(k)
            if isinstance(v, dict):
                lane = v
                break
        if lane is not None:
            item = str(e.get("task") or lane.get("id") or "")[:100]
            verdict = lane.get("verdict") or "scored"
            cost = _num(lane.get("cost_usd")) or _num(e.get("cost_usd"))
            line = "JEV"
        elif e.get("kind") == "COST" and e.get("who") == "builder":
            item = str(e.get("note") or e.get("task") or "")[:100]
            verdict = "—"
            cost = _num(e.get("cost_usd"))
            line = "LLM"
        else:
            item = str(e.get("note") or e.get("task") or "")[:100]
            verdict = "—"
            cost = _num(e.get("cost_usd"))
            line = "—"
        rows.append({"ts": e.get("ts", ""), "who": e.get("who", ""),
                     "kind": e.get("kind", ""), "track": e.get("track", ""),
                     "item": item, "verdict": verdict, "lane": line,
                     "cost_usd": cost if cost is not None else 0.0})
    rows.sort(key=lambda r: r["ts"])
    cols = [
        {"key": "ts", "label": "time", "kind": "date"},
        {"key": "who", "label": "who", "kind": "text", "ph": "who"},
        {"key": "kind", "label": "kind", "kind": "text", "ph": "PAPER?"},
        {"key": "track", "label": "track", "kind": "text", "ph": "A/B"},
        {"key": "item", "label": "item", "kind": "text", "ph": "filter…"},
        {"key": "verdict", "label": "verdict", "kind": "text",
         "ph": "verdict"},
        {"key": "lane", "label": "lane", "kind": "text", "ph": "JEV/LLM"},
        {"key": "cost_usd", "label": "cost $", "kind": "num",
         "fmt": "{:.6f}"},
    ]
    return rows, cols


def decisions_table():
    rows = [{"ts": d.get("ts", ""), "decider": d.get("decider", ""),
             "mode": d.get("mode", ""), "decision": d.get("decision", ""),
             "resume": d.get("resume", ""), "review_on": d.get("review_on", "")}
            for d in read_jsonl(os.path.join(DIR, "data", "decisions.jsonl"))]
    rows.sort(key=lambda r: r["ts"], reverse=True)
    cols = [
        {"key": "ts", "label": "date", "kind": "date"},
        {"key": "decider", "label": "by", "kind": "text", "ph": "who"},
        {"key": "mode", "label": "mode", "kind": "text", "ph": "RUN?"},
        {"key": "decision", "label": "decision", "kind": "text",
         "ph": "filter…"},
        {"key": "resume", "label": "resumes when", "kind": "text",
         "ph": "filter…"},
        {"key": "review_on", "label": "review", "kind": "date"},
    ]
    return rows, cols


def sessions_table():
    rows = [{"role": s.get("role", ""), "task": s.get("task", ""),
             "status": s.get("status", ""),
             "started": s.get("started_ts") or "",
             "ended": s.get("ended_ts") or "",
             "session": (s.get("sessionId") or "")[:8]}
            for s in read_jsonl(os.path.join(DIR, "data", "sessions.jsonl"))]
    rows.reverse()  # newest first
    cols = [
        {"key": "role", "label": "worker", "kind": "text", "ph": "role"},
        {"key": "task", "label": "task", "kind": "text", "ph": "filter…"},
        {"key": "status", "label": "status", "kind": "text", "ph": "LIVE?"},
        {"key": "started", "label": "started", "kind": "date"},
        {"key": "ended", "label": "ended", "kind": "date"},
        {"key": "session", "label": "session", "kind": "text", "ph": "id"},
    ]
    return rows, cols


def trends_table():
    rows = [{"ts": t.get("ts", ""), "query": t.get("query", ""),
             "brief": (t.get("brief") or "")[:220],
             "urls_n": len(t.get("urls") or [])}
            for t in read_jsonl(os.path.join(DIR, "data", "trends.jsonl"))]
    rows.sort(key=lambda r: r["ts"], reverse=True)
    cols = [
        {"key": "ts", "label": "date", "kind": "date"},
        {"key": "query", "label": "radar query", "kind": "text",
         "ph": "filter…"},
        {"key": "brief", "label": "brief", "kind": "text", "ph": "filter…"},
        {"key": "urls_n", "label": "urls", "kind": "num", "fmt": "{:.0f}"},
    ]
    return rows, cols


def watch_table():
    rows = [{"ts": w.get("ts", ""), "query": w.get("query", ""),
             "title": w.get("title", ""), "score": _num(w.get("score_hint")),
             "url": w.get("url", "")}
            for w in read_jsonl(os.path.join(DIR, "data", "watch.jsonl"), 2000)]
    rows.sort(key=lambda r: r["ts"], reverse=True)
    cols = [
        {"key": "ts", "label": "seen", "kind": "date"},
        {"key": "query", "label": "query", "kind": "text", "ph": "filter…"},
        {"key": "title", "label": "find", "kind": "text", "ph": "filter…"},
        {"key": "score", "label": "score", "kind": "num", "fmt": "{:.3f}"},
        {"key": "url", "label": "link", "kind": "text", "ph": "url"},
    ]
    return rows, cols


def resources_table():
    try:
        with open(os.path.join(DIR, "data", "resources.json")) as f:
            data = json.load(f)
    except (FileNotFoundError, ValueError):
        data = []
    rows = [r for r in data if isinstance(r, dict)]
    cols = [
        {"key": "name", "label": "resource", "kind": "text", "ph": "filter…"},
        {"key": "use", "label": "used for", "kind": "text", "ph": "filter…"},
        {"key": "plan", "label": "plan", "kind": "text", "ph": "filter…"},
        {"key": "live", "label": "live status", "kind": "text",
         "ph": "filter…"},
        {"key": "fallback", "label": "if it runs out", "kind": "text",
         "ph": "filter…"},
        {"key": "agent", "label": "agent", "kind": "text", "ph": "who"},
    ]
    return rows, cols


def funds_rows(state):
    """Numbers-as-rows: every KPI the old Status/Jev cards showed as text."""
    c = state.get("credits", {}) or {}
    n = state.get("counts", {}) or {}
    j = state.get("economy", {}) or {}
    m = state.get("metrics") or {}
    rows = [
        {"metric": "credits left $", "value": _num(c.get("remaining")),
         "note": "floor $%.2f" % state.get("floor", 0.8)},
        {"metric": "credits used $", "value": _num(c.get("used")),
         "note": "of $%s prepaid" % c.get("total", "?")},
        {"metric": "ledger spend $", "value": _num(n.get("spend_usd")),
         "note": "%s PAPER / %s CONFIRMED" % (n.get("paper"), n.get("confirmed"))},
        {"metric": "Jev share", "value": _num(j.get("utilization")),
         "note": "target >= 0.90; last10 %s" % j.get("recent10")},
        {"metric": "finds 7d", "value": _num(m.get("finds_7d")),
         "note": "cost/find $%s" % m.get("cost_per_find_7d")},
        {"metric": "revenue $", "value": _num(m.get("revenue_usd")),
         "note": "%s confirmed payouts" % m.get("confirmed_payouts")},
    ]
    cols = [
        {"key": "metric", "label": "metric", "kind": "text", "ph": "metric"},
        {"key": "value", "label": "value", "kind": "num", "fmt": "{:.4f}"},
        {"key": "note", "label": "note", "kind": "text", "ph": "note"},
    ]
    return rows, cols


def _age_min(ts):
    ep = _epoch(ts)
    if ep is None:
        return None
    try:
        return (datetime.now(timezone.utc).timestamp() - ep) / 60
    except (TypeError, ValueError, OverflowError):
        return None


def _fresh(ts):
    """LIVE <=60min, IDLE <=24h, STALE beyond, — when unknown."""
    a = _age_min(ts)
    if a is None:
        return "—"
    if a <= 60:
        return "LIVE"
    if a <= 1440:
        return "IDLE"
    return "STALE"


def stages_table():
    """ONE row per pipeline stage: is the loop progressing, and where?
    Grain 'one stage' — a new entity, not a copy of another table."""
    watch = read_jsonl(os.path.join(DIR, "data", "watch.jsonl"), 5000)
    trends = read_jsonl(os.path.join(DIR, "data", "trends.jsonl"), 5000)
    ledger = read_jsonl(os.path.join(DIR, "data", "ledger.jsonl"), 5000)
    decisions = read_jsonl(os.path.join(DIR, "data", "decisions.jsonl"), 100)
    opps, _ = opportunities_table()
    wlast = max([w.get("ts", "") for w in watch] or [""])
    tlast = max([t.get("ts", "") for t in trends] or [""])
    llast = max([e.get("ts", "") for e in ledger] or [""])
    dlast = max([d.get("ts", "") for d in decisions] or [""])
    nwatch = sum(1 for o in opps if o.get("verdict") == "WATCH")
    ngates = sum(1 for o in opps if o.get("take") in ("do", "watch", "forget"))
    spend = 0.0
    for e in ledger:
        spend += _num(e.get("cost_usd")) or 0.0
        lane = e.get("triage") if isinstance(e.get("triage"), dict) else e.get("jev")
        if isinstance(lane, dict):
            spend += _num(lane.get("cost_usd")) or 0.0
    revenue = sum(_num(e.get("amount_usd")) or 0.0 for e in ledger
                  if e.get("kind") == "CONFIRMED")
    rows = [
        {"stage": "RADAR", "step": "watcher finds",
         "items_open": None, "items_total": len(watch),
         "revenue_usd": None, "spend_usd": None,
         "next": "scan every 30m (daemon)",
         "last": wlast, "state": _fresh(wlast)},
        {"stage": "RADAR", "step": "trend briefs",
         "items_open": None, "items_total": len(trends),
         "revenue_usd": None, "spend_usd": None,
         "next": "demand radar every 30m (daemon)",
         "last": tlast, "state": _fresh(tlast)},
        {"stage": "SCORE", "step": "opportunities triaged",
         "items_open": nwatch, "items_total": len(opps),
         "revenue_usd": None, "spend_usd": None,
         "next": "triage new finds on arrival",
         "last": wlast, "state": "LIVE" if nwatch else "IDLE"},
        {"stage": "ACT", "step": "human gates open",
         "items_open": ngates, "items_total": len(opps),
         "revenue_usd": None, "spend_usd": None,
         "next": "advance free lane; humans only at claim",
         "last": "", "state": "LIVE" if ngates else "—"},
        {"stage": "MONEY", "step": "revenue vs spend",
         "items_open": None, "items_total": len(ledger),
         "revenue_usd": round(revenue, 2), "spend_usd": round(spend, 6),
         "next": "receipts only; paper never counts",
         "last": llast, "state": "LIVE" if revenue else "IDLE"},
        {"stage": "MEMORY", "step": "decisions logged",
         "items_open": None, "items_total": len(decisions),
         "revenue_usd": None, "spend_usd": None,
         "next": "log every pivot as data",
         "last": dlast, "state": _fresh(dlast)},
    ]
    cols = [
        {"key": "stage", "label": "stage", "kind": "text", "ph": "stage"},
        {"key": "step", "label": "step", "kind": "text", "ph": "step"},
        {"key": "items_open", "label": "open", "kind": "num",
         "fmt": "{:.0f}"},
        {"key": "items_total", "label": "total", "kind": "num",
         "fmt": "{:.0f}"},
        {"key": "revenue_usd", "label": "revenue $", "kind": "num",
         "fmt": "{:.2f}"},
        {"key": "spend_usd", "label": "spend $", "kind": "num",
         "fmt": "{:.6f}"},
        {"key": "next", "label": "next (agent)", "kind": "text",
         "ph": "filter…"},
        {"key": "last", "label": "last activity", "kind": "date"},
        {"key": "state", "label": "state", "kind": "text",
         "ph": "STALE?"},
    ]
    return rows, cols


TABLES = [("stages", "Pipeline — is the loop progressing?", stages_table),
          ("opps", "Score+Act — opportunities (incl. needs-you)", opportunities_table),
          ("ledger", "Ledger", ledger_table),
          ("decisions", "Decisions", decisions_table),
          ("sessions", "Workers & sessions", sessions_table),
          ("trends", "Trend radar", trends_table),
          ("sight", "Watcher finds", watch_table),
          ("res", "Resources", resources_table)]


def _cell(c, v):
    """(display, sort, title) triple for one value."""
    kind = c.get("kind", "text")
    if v is None or v == "":
        return ("—", None, None)
    if kind == "num":
        f = _num(v)
        if f is None:
            return (str(v), str(v), None)
        fmt = c.get("fmt")
        if fmt:
            try:
                return (fmt.format(f), f, None)
            except Exception:  # noqa: BLE001 - fall back to plain
                pass
        return ("%g" % f, f, None)
    if kind == "date":
        ep = _epoch(v)
        if ep is None:
            return (str(v), str(v), None)
        # Tooltip carries the exact UTC instant (auditable across zones).
        utc = datetime.fromtimestamp(ep, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return (_short(ep), ep, utc)
    return (str(v), str(v).lower(), None)


def _filter_input(ns, c):
    key, kind = c["key"], c.get("kind", "text")
    if kind == "num":
        return (f'<input class=half id="tf-{ns}-{key}-lo" placeholder="≥min" '
                f'oninput="tFilterR(\'{ns}\',\'{key}\',this.value,\'lo\')"> '
                f'<input class=half id="tf-{ns}-{key}-hi" placeholder="≤max" '
                f'oninput="tFilterR(\'{ns}\',\'{key}\',this.value,\'hi\')">')
    if kind == "date":
        return (f'<input class=half type="datetime-local" '
                f'id="tf-{ns}-{key}-lo" title="from (UTC)" '
                f'oninput="tFilterR(\'{ns}\',\'{key}\',this.value,\'lo\')"> '
                f'<input class=half type="datetime-local" '
                f'id="tf-{ns}-{key}-hi" title="to (UTC)" '
                f'oninput="tFilterR(\'{ns}\',\'{key}\',this.value,\'hi\')">')
    return (f'<input id="tf-{ns}-{key}" placeholder="{_h.escape(c.get("ph", "filter…"))}" '
            f'oninput="tFilter(\'{ns}\',\'{key}\',this.value)"> ')


def render(ns, rows, cols, per=10, presets=None):
    """One SQL table: counter + pager + sortable/filterable SSR thead + rows.
    presets = [{name, filters, sortKey, sortDir}] — VIEW chips (filter state
    over the same rows, never a second table)."""
    per = per if per in (10, 25, 50) else 10
    presets = presets or []
    data_rows = []
    for r in rows:
        data_rows.append({c["key"]: {"d": d, "s": s, **({"t": t} if t else {})}
                          for c in cols for (d, s, t) in [_cell(c, r.get(c["key"]))]})
    ths = "".join(
        f'<th class="srt" onclick="tSort(\'{ns}\',\'{c["key"]}\')">'
        f'{_h.escape(c["label"])}<span id="tarr-{ns}-{c["key"]}"></span></th>'
        for c in cols)
    frs = "".join(f"<td>{_filter_input(ns, c)}</td>" for c in cols)
    body = []
    for r in rows[:per]:
        tds = []
        for c in cols:
            d, s, t = _cell(c, r.get(c["key"]))
            cls = "n" if c.get("kind") == "num" else ""
            ti = f' title="{_h.escape(t)}"' if t else ""
            tds.append(f'<td data-l="{_h.escape(c["label"])}" class="{cls}"{ti}>'
                       f'{_h.escape(d)}</td>')
        body.append("<tr>" + "".join(tds) + "</tr>")
    pages = max(1, (len(rows) + per - 1) // per)
    opts = "".join(
        f'<option value="{v}">{"all" if v == "all" else v}</option>'
        for v in (10, 25, 50, "all"))
    meta = [{"key": c["key"], "label": c["label"],
             "kind": c.get("kind", "text")} for c in cols]
    views = [{"name": v["name"], "filters": v.get("filters", {}),
              "sortKey": v.get("sortKey"), "sortDir": v.get("sortDir", 1)}
             for v in presets]
    chips = "".join(
        f'<button onclick="tView(\'{ns}\',{i})">{_h.escape(v["name"])}</button>'
        for i, v in enumerate(presets))
    chips = (f'<div class=tviews>view: {chips}'
             f'<button onclick="tView(\'{ns}\',-1)">all</button></div>' if presets else "")
    return (
        chips +
        f'<div class=tctl><span id="tcnt-{ns}">Page 1/{pages} · {len(rows)} of {len(rows)} rows</span>'
        f'<label>per page <select id="tper-{ns}" onchange="tPer(\'{ns}\',this.value)">{opts}</select></label></div>'
        f'<div class=twrap><table id="tbl-{ns}"><thead><tr>{ths}</tr>'
        f'<tr class=ff>{frs}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
        f'<div class=tpgr><button onclick="tPage(\'{ns}\',-1)">‹ prev</button>'
        f'<span id="tpg-{ns}">1/{pages}</span>'
        f'<button onclick="tPage(\'{ns}\',1)">next ›</button></div>'
        f'<script type="application/json" id="tdata-{ns}">'
        f'{json.dumps({"cols": meta, "rows": data_rows, "per": per, "views": views})}</script>')
