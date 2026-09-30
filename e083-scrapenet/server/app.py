#!/usr/bin/env python3
"""ScrapeNet collector — stdlib only. Serves public/ + /api/*.

Config: ALL machine values come from needs.json (port, bind, payout,
commission, storage paths). No hardcoded IPs/ports/URLs.
"""
import fnmatch
import hashlib
import io
import json
import os
import re
import secrets
import threading
import time
import datetime
import urllib.parse
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEEDS = os.path.join(DIR, "needs.json")
PUB = os.path.join(DIR, "public")


def cfg():
    try:
        with open(NEEDS) as f:
            return json.load(f)
    except Exception:
        return {}


def p(name, default):
    c = cfg()
    rel = c.get(name, default)
    return os.path.join(DIR, rel) if not os.path.isabs(rel) else rel


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)


def load_lines(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def append_line(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(obj) + "\n")


# ---- auth (self-serve signup, token-gated writes) ----
# Writes (/api/ingest, /api/recipes POST|PUT|DELETE, /api/publish) require the
# per-node token issued ONCE by POST /api/signup. Tokens are stored as
# sha256 hashes in data/auth.json (mode 0600) and never appear in any other
# response. Reads stay public.
# Migration: node_ids that already had records/ledger rows before auth
# launched are sealed into auth.json "legacy_nodes" and may still write
# without a token (sunset: owner can delete the list to force signup).

def auth_path():
    return p("auth_path", "data/auth.json")


def auth_db():
    db = load_json(auth_path(), None)
    if not isinstance(db, dict) or "nodes" not in db:
        nodes = {}
        legacy = set()
        for r in load_lines(p("records_path", "data/records.jsonl")):
            if r.get("node_id"):
                legacy.add(r["node_id"])
        for e in load_lines(p("ledger_path", "data/ledger.jsonl")):
            if e.get("node_id"):
                legacy.add(e["node_id"])
        db = {"nodes": nodes, "legacy_nodes": sorted(legacy)}
        save_auth(db)
    return db


def save_auth(db):
    path = auth_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(db, f, indent=1)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def token_hash(tok):
    return hashlib.sha256(tok.encode()).hexdigest()


# ---- owner panel + secrets (CALM 2026-09-29) ----
# The Owner drawer on `/` is gated by a master token that lives in
# needs.json (`owner_token`, auto-generated on first boot, never served).
# Secrets pasted in the panel (X bearer, Stripe keys) are NEVER written to
# needs.json — they live in data/secrets.json (mode 0600). needs.json
# keeps only non-secret config: the panel edits it through
# POST /api/owner/config, never the reverse. Every GET masks secrets to
# booleans (`*_set`); write-only fields never echo values back.

SECRET_KEYS = ("x_bearer_token", "stripe_secret", "stripe_webhook_secret")


def secrets_path():
    return p("secrets_path", "data/secrets.json")


def load_secrets():
    s = load_json(secrets_path(), {})
    return s if isinstance(s, dict) else {}


def save_secrets(s):
    path = secrets_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(s, f, indent=1)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def secret(name):
    """One secret value: 0600 file first, legacy needs.json value migrates in."""
    s = load_secrets()
    v = s.get(name, "")
    v = v.strip() if isinstance(v, str) else ""
    if v:
        return v
    c = cfg()
    legacy = c.get(name, "")
    legacy = legacy.strip() if isinstance(legacy, str) else ""
    if legacy and name in SECRET_KEYS:
        s[name] = legacy
        save_secrets(s)
        try:
            c[name] = ""
            with open(NEEDS, "w") as f:
                json.dump(c, f, indent=1)
        except Exception:
            pass
        audit("secret_migrated", key=name)
        return legacy
    return ""


def owner_token():
    """Master token from needs.json (generated once, never served)."""
    c = cfg()
    tok = c.get("owner_token", "")
    tok = tok.strip() if isinstance(tok, str) else ""
    if not tok:
        tok = secrets.token_hex(16)
        c["owner_token"] = tok
        try:
            with open(NEEDS, "w") as f:
                json.dump(c, f, indent=1)
        except Exception:
            pass
    return tok


def check_owner_auth(body, headers, query=None):
    """Master-token gate for /api/owner/*. Accepts Authorization: Bearer,
    JSON `owner_token`, or query `owner_token`. Never echoes the token."""
    body = body if isinstance(body, dict) else {}
    query = query or {}
    cands = []
    auth = (headers.get("Authorization") or headers.get("authorization") or "")
    if auth.lower().startswith("bearer "):
        cands.append(auth[7:].strip())
    for k in ("owner_token", "token"):
        v = body.get(k, "")
        if isinstance(v, str) and v.strip():
            cands.append(v.strip())
    for k in ("owner_token", "token"):
        for v in (query.get(k, []) or []):
            if isinstance(v, str) and v.strip():
                cands.append(v.strip())
    try:
        master = owner_token()
    except Exception:
        return False
    return any(secrets.compare_digest(t, master) for t in cands if t)


def decisions_path():
    return p("decisions_path", "data/decisions.jsonl")


def payout_decision_for(*keys):
    """Latest owner payout decision matching any of the keys (node/code)."""
    want = {k for k in keys if k}
    best = None
    for d in load_lines(decisions_path()):
        if (isinstance(d, dict) and d.get("kind") == "payout"
                and d.get("referrer") in want):
            best = d
    return best


def intent_decision_for(index):
    for d in load_lines(decisions_path()):
        if (isinstance(d, dict) and d.get("kind") == "intent"
                and d.get("ref") == index):
            return d
    return None


def bearer_token(headers, body):
    auth = (headers.get("Authorization") or headers.get("authorization") or "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    for k in ("token", "auth_token"):
        v = body.get(k, "") if isinstance(body, dict) else ""
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def check_write_auth(body, headers, query=None):
    """Gate for all write endpoints. Returns (node_id, None) on success or
    (None, (code, payload)) on failure. Credentials may come from the JSON
    body, the Authorization header, or (DELETE/PUT) query params."""
    body = body if isinstance(body, dict) else {}
    query = query or {}
    node_id = body.get("node_id", "")
    if not node_id:
        vals = query.get("node_id", [""])
        node_id = vals[0] if vals else ""
    node_id = node_id.strip() if isinstance(node_id, str) else ""
    tok = bearer_token(headers, body)
    if not tok and query:
        vals = query.get("token", []) + query.get("auth_token", [])
        tok = next((v.strip() for v in vals if isinstance(v, str) and v.strip()), "")
    if not node_id:
        return None, (401, {"error": "node_id required — get one via POST /api/signup {\"name\": \"...\"}"})
    if len(node_id) > 64:
        return None, (401, {"error": "node_id too long (max 64 chars)"})
    db = auth_db()
    acct = db.get("nodes", {}).get(node_id)
    if acct and tok and secrets.compare_digest(token_hash(tok), acct.get("token_sha256", "")):
        return node_id, None
    if not tok and node_id in db.get("legacy_nodes", []):
        return node_id, None  # grandfathered pre-auth node (see sunset note above)
    if acct and not tok:
        return None, (401, {"error": "token required for '" + node_id + "' — pass your signup token as Authorization: Bearer <token> or JSON field 'token'"})
    return None, (401, {"error": "invalid node_id/token — signup via POST /api/signup {\"name\": \"...\"}"})


def new_referral_code(db):
    used = {a.get("referral_code") for a in db.get("nodes", {}).values()}
    for _ in range(50):
        code = secrets.token_hex(3).upper()
        if code not in used:
            return code
    return secrets.token_hex(4).upper()


# ---- domain ----

def recipes():
    return load_json(p("recipes_path", "data/recipes.json"), [])


def save_recipes(items):
    save_json(p("recipes_path", "data/recipes.json"), items)


def records(limit=None, dataset=None, node_id=None, include_test=False):
    """Ingested rows, newest first. Test/agent rows are EXCLUDED by
    default (?include_test=1 audits them with test:true visible)."""
    hide = set() if include_test else test_node_ids()
    mark = test_node_ids() if include_test else hide
    rows = load_lines(p("records_path", "data/records.jsonl"))
    if dataset:
        rows = [r for r in rows if r.get("dataset") == dataset]
    if node_id:
        rows = [r for r in rows if r.get("node_id") == node_id]
    rows = list(reversed(rows))
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        is_t = bool(r.get("test")) or r.get("node_id") in mark
        if r.get("node_id") in hide or (not include_test and bool(r.get("test"))):
            continue
        out.append({**r, "test": is_t})
    if limit:
        out = out[:limit]
    return out


def published(include_test=False):
    """Published datasets. Snapshots published by test nodes are EXCLUDED
    by default (?include_test=1 audits them with test:true visible)."""
    pub = load_json(p("published_path", "data/published.json"), {})
    if include_test or not isinstance(pub, dict):
        if isinstance(pub, dict):
            for ds, meta in pub.items():
                if isinstance(meta, dict):
                    meta["test"] = str(meta.get("published_by", "")) in test_node_ids()
        return pub
    test_ids = test_node_ids()
    return {ds: meta for ds, meta in pub.items()
            if str((meta or {}).get("published_by", "")) not in test_ids}


def ledger():
    return load_lines(p("ledger_path", "data/ledger.jsonl"))


def node_wallet(node_id):
    for e in reversed(ledger()):
        if e.get("node_id") == node_id and e.get("wallet"):
            return e["wallet"]
    return ""


DS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def audit(event, **fields):
    """Append-only audit trail for ingests/publishes/recipe changes."""
    try:
        f = dict(fields)
        f.update({"at": now_iso(), "event": event})
        append_line(p("audit_path", "data/audit.jsonl"), f)
    except Exception:
        pass


# ---- telemetry (UX funnel, same schema as e082 so funnels match) ----
# Client snippet POSTs /api/events {v:1, session, ts, page, event, detail?,
# ms?}. No IPs are ever stored — only a random client-generated session id.
# GET /api/funnel aggregates {views, downloads, signups, publishes,
# stuck_sessions[]} for the dashboard "Stuck users" card.
EV_EXACT = ("page_view", "download", "signup", "first_proof_seen",
            "js_error", "idle_45s", "publish", "generate", "proof")


def events_path():
    return p("events_path", "data/events.jsonl")


def valid_event(name):
    if not isinstance(name, str) or not (1 <= len(name) <= 80):
        return False
    if name in EV_EXACT:
        return True
    if name.startswith("click:") and len(name) > 6 and \
            re.fullmatch(r"[A-Za-z0-9_:.-]+", name):
        return True
    return False


def valid_session(s):
    return isinstance(s, str) and \
        re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", s or "") is not None


def valid_agent(a):
    """Driven-browser self-identification (AGENT CONVENTION 2026-09-29).
    Browsers driven by agents must send ?agent=<name> (saved to localStorage
    by the snippet, forwarded as the `agent` field on every event).
    The name is stored on the event row (auditable) and forces
    synthetic:true — hidden from human counts by default, revealed by
    ?bots=1."""
    return (isinstance(a, str) and 1 <= len(a) <= 64 and
            re.fullmatch(r"[A-Za-z0-9_.\-]+", a) is not None)


def is_bot_session(sess):
    """Synthetic-session test (same schema as e082): our own check.sh
    polls (check-*) and QA probes (*-probe) are bots, not humans."""
    if not isinstance(sess, str):
        return False
    s = sess.strip()
    return (s.startswith("check-") or s.startswith("probe-")
            or s.endswith("-probe") or s in ("healthcheck", "health-check"))


BOT_UA_HINTS = ("curl", "wget", "python-urllib", "python-requests",
                "urllib/", "go-http", "httpie", "node-fetch", "axios",
                "loop.sh", "daemon", "probe", "healthcheck", "uptime",
                "pingdom", "nagios", "check.sh", "headless")


def is_bot_ua(ua):
    """Loop/daemon/CI user-agents are synthetic. Never stored — only the
    boolean flag lands in the log (no IPs, no UAs)."""
    low = str(ua or "").lower()
    if not low:
        return False
    if "mozilla" in low and "chrome" in low or "firefox" in low or "safari" in low:
        return False  # real browsers are human
    return any(h in low for h in BOT_UA_HINTS)


def funnel_thresholds():
    """Verdict rules live in needs.json — never hardcoded."""
    c = cfg()

    def num(key, default):
        try:
            return float(c.get(key, default))
        except (TypeError, ValueError):
            return default
    return {"min_visits": int(num("funnel_min_visits", 5)),
            "download_alarm_ratio": num("funnel_download_alarm_ratio", 0.05),
            "bot_noise_ratio": num("funnel_bot_noise_ratio", 0.5),
            "action_healthy_ratio": num("funnel_proof_healthy_ratio", 0.3)}


def funnel_verdict(views, downloads, actions, bot_stuck, human_stuck):
    """One computed verdict line — same levels as e082 (rules, not vibes).
    Metric mapping for ScrapeNet: installs->downloads, proofs->signups+
    publishes actions that keep pace with visits."""
    t = funnel_thresholds()
    total = bot_stuck + human_stuck
    if total > 0 and bot_stuck / total > t["bot_noise_ratio"]:
        return {"level": "NOISE",
                "line": (f"NOISE: {bot_stuck}/{total} stuck are bots — hiding them, "
                           f"{human_stuck} human need help")}
    if views >= t["min_visits"] and downloads == 0:
        return {"level": "FAILING",
                "line": (f"FAILING: 0 downloads after {views} visits — "
                           "nobody installs the extension")}
    if views >= t["min_visits"] and downloads / max(1, views) < t["download_alarm_ratio"]:
        return {"level": "FAILING",
                "line": (f"FAILING: {downloads} downloads after {views} visits "
                           "— install path leaks")}
    if views >= t["min_visits"] and actions / max(1, views) >= t["action_healthy_ratio"]:
        return {"level": "HEALTHY",
                "line": (f"HEALTHY: signups/publishes keep pace with visits "
                           f"({actions} actions / {views} visits)")}
    if views < t["min_visits"]:
        return {"level": "QUIET",
                "line": (f"QUIET: only {views} visits — not enough signal yet")}
    return {"level": "WATCH",
            "line": (f"WATCH: {views} visits, {downloads} downloads, "
                       f"{actions} actions — middling, watch one more day")}


# ---- test/prod separation (ATTRIBUTION 2026-09-29) ----
# Agent/test traffic must never pump the public money story. Nodes flagged
# test:true (signup with agent:<name>, or node_id/name matching
# needs.json test_node_patterns) are EXCLUDED from /api/earnings,
# /api/leaderboard and /api/published by default (?include_test=1 audits
# them) and are purgeable via POST /api/nodes/purge-test (test rows only).

def test_patterns():
    """Name patterns that mark a node as test. From needs.json — never
    hardcoded. fnmatch syntax (check-bot-*, *-proof*, ...)."""
    c = cfg()
    pats = c.get("test_node_patterns", [])
    return [p for p in pats if isinstance(p, str) and p]


def _matches_test(s):
    s = str(s or "")
    return any(fnmatch.fnmatchcase(s, p) for p in test_patterns())


def test_node_ids():
    """Every node id currently considered test: flagged accounts +
    pattern-matching node_ids/names + pattern-matching legacy (pre-auth)
    ids. Prod nodes (real users) never match — purge only touches these."""
    db = auth_db()
    accts = db.get("nodes", {}) if isinstance(db, dict) else {}
    out = set()
    for nid, a in accts.items():
        if not isinstance(a, dict):
            continue
        if a.get("test") is True or _matches_test(nid) or _matches_test(a.get("name", "")):
            out.add(nid)
    for n in (db.get("legacy_nodes", []) or []):
        if isinstance(n, str) and _matches_test(n):
            out.add(n)
    return out


def load_events():
    return load_lines(events_path())


def short_sid(s):
    s = str(s)
    return (s[:12] + "\u2026") if len(s) > 12 else s


def clean_detail(d):
    d = str(d or "")[:120]
    if d.strip().lower() in ("none", "null", "undefined", "-", "n/a"):
        return ""
    return d


def funnel(include_bots=False, include_test=False):
    """UX funnel from client events + server-truth publishes (audit log).
    Synthetic sessions (own polls/probes: check-*, *-probe, CI UAs, AND
    agent-tagged driven browsers per the AGENT CONVENTION) are EXCLUDED by
    default (?bots=1 reveals them). Publishes from test nodes are excluded
    from the public count by default (?include_test=1 audits them)."""
    test_ids = set() if include_test else test_node_ids()
    by_session = {}
    for e in load_events():
        s = e.get("session", "")
        ev = e.get("event", "")
        if not valid_session(s):
            continue
        ag = e.get("agent", "") if isinstance(e.get("agent", ""), str) else ""
        bot = bool(e.get("synthetic")) or is_bot_session(s) or ag != ""
        info = by_session.setdefault(s, {"events": set(), "bot": False,
                                         "agent": "", "last": None})
        info["events"].add(ev)
        info["last"] = e
        if ag:
            info["agent"] = ag
        if bot:
            info["bot"] = True
    shown = {s: i for s, i in by_session.items()
             if include_bots or not i["bot"]}
    bots = {s: i for s, i in by_session.items() if i["bot"]}
    sessions_views = {s for s, i in shown.items() if "page_view" in i["events"]}
    downloads = sum(1 for i in shown.values() if "download" in i["events"])
    signups = sum(1 for i in shown.values() if "signup" in i["events"])

    def is_active(i):
        if i["events"] & {"download", "signup"}:
            return True
        return any(isinstance(x, str) and x.startswith("click:")
                   for x in i["events"])

    def is_stuck(s, i):
        if "idle_45s" in i["events"]:
            return True
        return "page_view" in i["events"] and not is_active(i)
    bot_stuck, human_rows = 0, []
    for s in sorted(by_session):
        info = by_session[s]
        if not is_stuck(s, info):
            continue
        if info["bot"]:
            bot_stuck += 1
            if not include_bots:
                continue
        last = info["last"] or {}
        human_rows.append({"session": s, "short": short_sid(s),
                           "synthetic": bool(info["bot"]),
                           "agent": info.get("agent", ""),
                           "last_event": last.get("event"),
                           "last_detail": clean_detail(last.get("detail")),
                           "last_at": last.get("at")})
    # Dashboard card stays bounded; the explicit audit surface (?bots=1)
    # reveals every synthetic row (honest-counters must not evict audit rows).
    human_stuck = sum(1 for r in human_rows if not r["synthetic"])
    if not include_bots:
        human_rows = human_rows[:50]
    agents_hidden = 0 if include_bots else sum(
        1 for i in by_session.values() if i["bot"] and i.get("agent"))
    publishes = sum(1 for a in load_lines(p("audit_path", "data/audit.jsonl"))
                    if a.get("event") == "publish" and
                    (include_test or a.get("published_by", "") not in test_ids))
    test_publishes_hidden = 0 if include_test else sum(
        1 for a in load_lines(p("audit_path", "data/audit.jsonl"))
        if a.get("event") == "publish" and a.get("published_by", "") in test_ids)
    verdict = funnel_verdict(len(sessions_views), downloads,
                             signups + publishes, bot_stuck, human_stuck)
    return {
        "views": len(sessions_views),
        "downloads": downloads,
        "signups": signups,
        "publishes": publishes,
        "stuck_sessions": human_rows,
        "bots_hidden": 0 if include_bots else bot_stuck,
        "bots_total": len(bots),
        "agents_hidden": agents_hidden,
        "test_publishes_hidden": test_publishes_hidden,
        "sessions_total": len(sessions_views),
        "sessions_total_raw": len(by_session),
        "verdict": verdict,
    }


def clean_str(v, max_len):
    if not isinstance(v, str):
        return None, "must be a string"
    v = v.strip()
    if len(v) > max_len:
        return None, f"too long (max {max_len} chars)"
    return v, None


def purge_test_nodes():
    """Delete ONLY test nodes and their rows. Backs up every touched file
    first (data/*.bak-<ts>). Returns counts. Prod nodes are never matched
    (see test_node_ids) — but the caller must still pass the explicit
    test_only flag, refused otherwise."""
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    doomed = test_node_ids()
    counts = {"nodes": 0, "records": 0, "ledger": 0, "published": 0}
    arec = p("records_path", "data/records.jsonl")
    aled = p("ledger_path", "data/ledger.jsonl")
    apub = p("published_path", "data/published.json")
    apubdir = p("published_dir", "data/published")
    # accounts
    db = auth_db()
    accts = db.get("nodes", {}) if isinstance(db, dict) else {}
    gone = sorted(n for n in accts if n in doomed)
    if gone:
        save_json(auth_path() + f".bak-{ts}", db)
        for n in gone:
            del accts[n]
        save_auth(db)
        counts["nodes"] = len(gone)
    # records + ledger rows
    for path, key in ((arec, "records"), (aled, "ledger")):
        rows = load_lines(path)
        keep = [r for r in rows if r.get("node_id") not in doomed]
        if len(keep) != len(rows):
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path + f".bak-{ts}", "w") as f:
                    for r in rows:
                        f.write(json.dumps(r) + "\n")
            except Exception:
                pass
            with open(path, "w") as f:
                for r in keep:
                    f.write(json.dumps(r) + "\n")
            counts[key] = len(rows) - len(keep)
    # published snapshots owned by test nodes
    pub = load_json(apub, {})
    if isinstance(pub, dict):
        drop = sorted(ds for ds, m in pub.items()
                      if str((m or {}).get("published_by", "")) in doomed)
        if drop:
            save_json(apub + f".bak-{ts}", pub)
            for ds in drop:
                del pub[ds]
                try:
                    fp = os.path.join(apubdir, ds + ".json")
                    if os.path.exists(fp):
                        os.remove(fp)
                except Exception:
                    pass
            save_json(apub, pub)
            counts["published"] = len(drop)
    audit("purge_test", purged_nodes=counts["nodes"],
          purged_records=counts["records"], purged_ledger=counts["ledger"],
          purged_published=counts["published"])
    return {"ok": True, "purged_test_nodes": sorted(doomed), **counts}


def parse_limit(raw, default, ceiling=500):
    if raw is None or raw == "":
        return default, None
    try:
        lim = int(raw)
    except (TypeError, ValueError):
        return None, "limit must be an integer"
    if lim < 1 or lim > ceiling:
        return None, f"limit must be 1..{ceiling}"
    return lim, None


# Recipe fns run client-side via `new Function` (extension + dashboard), so a
# malicious fn stored on the collector executes in every user's browser. The
# server itself NEVER executes recipe JS (no eval/exec/Function anywhere
# server-side) — it only statically analyzes fns on write and in /api/recipes/test.
FN_FORBIDDEN = [
    "fetch(", "xmlhttprequest", "websocket", "document.", "document[",
    "window.", "localstorage", "sessionstorage", "chrome.", "browser.",
    "eval(", "new function", "import(", "require(", "cookie", "sendbeacon",
    "navigator.", "location.", "<script", ".innerhtml", "for(;;)", "while(true",
]


def analyze_fn(fn_str):
    """Static-only recipe safety check. Never executes the code."""
    errors, warnings = [], []
    if not isinstance(fn_str, str) or not fn_str.strip():
        return {"ok": False, "errors": ["fn must be a non-empty JS function string"],
                "warnings": warnings,
                "note": "Static analysis only. The server never executes recipe JS."}
    if len(fn_str) > 32768:
        errors.append("fn too large (max 32768 chars)")
    low = fn_str.lower()
    for pat in FN_FORBIDDEN:
        if pat in low:
            errors.append(
                f"fn uses forbidden capability {pat!r} \u2014 recipe transforms must be "
                "pure data mapping (no network/DOM/storage access)")
    for a, b in (("{", "}"), ("(", ")"), ("[", "]")):
        if fn_str.count(a) != fn_str.count(b):
            errors.append(f"unbalanced {a}{b} \u2014 fn likely has a syntax error")
    if "transform" not in fn_str:
        warnings.append("fn does not mention 'transform' \u2014 expected function transform(raw, ctx)")
    if "return" not in low:
        warnings.append("fn has no 'return' \u2014 it must return an array of records")
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "note": "Static analysis only. The server never executes recipe JS."}


# ---- declarative transform ops (SAFE server-side subset; no JS execution) ----
# Op set (also documented in AGENTS.md + dashboard recipe help + extension):
#   {"op":"css-select","selector":"...","fields":{out:{"sel":..,"attr":..}},"limit":50}
#       Parse raw.html with a stdlib HTML tree, match a small CSS subset
#       (tag, .class, #id, [attr]/[attr="v"]/[^=]/[*=], :nth-child(N),
#       descendant + comma lists), one row per match. attr "text" or an
#       attribute name ("html" is refused — raw markup never ships back).
#   {"op":"json-path","path":"cards[*].price"}  dotted path, [*]/[N] over raw.
#   {"op":"regex","field":"text","pattern":"..","group":1,"out":"price"}
#       Per-row extraction from a string field into a new field.
#   {"op":"map","fields":{old:new},"drop":[..],"const":{k:v}}  rename/drop/add.
#   {"op":"filter","field":"price","exists":true}  keep rows where the field
#       exists | equals X | contains "sub" | gt/lt number.
# Recipes carry {"run_where":"client"|"server"|"both"} (default "client"):
# client = content script runs recipe.fn locally (private); server = raw +
# recipe goes to POST /api/transform which runs ONLY these ops; both = run
# both and merge-dedupe. Anything outside this op set is rejected by
# validate_ops() — the server never evals recipe JS.
OP_NAMES = ("css-select", "json-path", "regex", "map", "filter")
OP_KEYS = {
    "css-select": {"op", "selector", "fields", "limit", "input"},
    "json-path": {"op", "path"},
    "regex": {"op", "field", "in", "pattern", "group", "out"},
    "map": {"op", "fields", "drop", "const"},
    "filter": {"op", "field", "exists", "equals", "contains", "gt", "lt"},
}
def validate_ops(ops):
    """Allow-list validator for the declarative op set. Returns [errors]."""
    if not isinstance(ops, list) or not ops or len(ops) > 20:
        return ["ops must be a non-empty list (max 20 ops)"]
    errs = []
    for i, op in enumerate(ops):
        tag = f"ops[{i}]"
        if not isinstance(op, dict):
            errs.append(f"{tag} must be an object")
            continue
        name = op.get("op")
        if name not in OP_KEYS:
            errs.append(f"{tag}.op must be one of {sorted(OP_NAMES)} (got {name!r})")
            continue
        extra = set(op) - OP_KEYS[name]
        if extra:
            errs.append(f"{tag} unknown keys: {sorted(extra)} — allowed: {sorted(OP_KEYS[name])}")
        if name == "css-select":
            sel = op.get("selector", "")
            if not isinstance(sel, str) or not sel.strip() or len(sel) > 500:
                errs.append(f"{tag}.selector must be a non-empty CSS selector (max 500 chars)")
            elif _parse_selector(sel) is None:
                errs.append(f"{tag}.selector uses unsupported syntax — tag/.class/#id/[attr]/:nth-child/descendant/comma only")
            fl = op.get("fields", {})
            if not isinstance(fl, dict) or len(fl) > 30 or \
                    any(not isinstance(k, str) or len(k) > 64 for k in fl):
                errs.append(f"{tag}.fields must be an object of <=30 output names (each max 64 chars)")
            else:
                for k, spec in fl.items():
                    spec = spec if isinstance(spec, dict) else {"sel": str(spec)}
                    if spec.get("sel") is not None and \
                            (not isinstance(spec["sel"], str) or len(spec["sel"]) > 500 or
                             _parse_selector(spec["sel"]) is None):
                        errs.append(f"{tag}.fields.{k}.sel: bad selector")
                    if spec.get("attr") is not None and \
                            (not isinstance(spec["attr"], str) or len(spec["attr"]) > 64):
                        errs.append(f"{tag}.fields.{k}.attr: bad attribute name")
            lim = op.get("limit", 50)
            if not isinstance(lim, int) or isinstance(lim, bool) or not 1 <= lim <= 200:
                errs.append(f"{tag}.limit must be an integer 1..200")
        elif name == "json-path":
            pth = op.get("path", "")
            if not isinstance(pth, str) or not pth.strip() or len(pth) > 500:
                errs.append(f"{tag}.path must be a non-empty dotted path (max 500 chars)")
            elif not re.fullmatch(r"[A-Za-z0-9_]+(\[(\*|\d+)\])?(\.[A-Za-z0-9_]+(\[(\*|\d+)\])?)*", pth):
                errs.append(f"{tag}.path syntax: dotted names with optional [*]/[N] (got {pth!r})")
        elif name == "regex":
            pat = op.get("pattern", "")
            if not isinstance(pat, str) or not pat or len(pat) > 500:
                errs.append(f"{tag}.pattern must be a non-empty regex (max 500 chars)")
            else:
                try:
                    re.compile(pat)
                except re.error as e:
                    errs.append(f"{tag}.pattern does not compile: {e}")
            for kk in ("field", "in", "out"):
                if op.get(kk) is not None and (not isinstance(op[kk], str) or len(op[kk]) > 64):
                    errs.append(f"{tag}.{kk} must be a field name (max 64 chars)")
            grp = op.get("group", 0)
            if not isinstance(grp, int) or isinstance(grp, bool) or not 0 <= grp <= 10:
                errs.append(f"{tag}.group must be an integer 0..10")
        elif name == "map":
            if not any(k in op for k in ("fields", "drop", "const")):
                errs.append(f"{tag}: map needs at least one of fields/drop/const")
            fl = op.get("fields", {})
            if "fields" in op and (not isinstance(fl, dict) or len(fl) > 30 or
                    any(not isinstance(k, str) or len(k) > 64 or not isinstance(v, str) or len(v) > 64
                        for k, v in fl.items())):
                errs.append(f"{tag}.fields must map <=30 names to names (each max 64 chars)")
            dr = op.get("drop", [])
            if "drop" in op and (not isinstance(dr, list) or len(dr) > 30 or
                    any(not isinstance(x, str) or len(x) > 64 for x in dr)):
                errs.append(f"{tag}.drop must be a list of <=30 field names")
            co = op.get("const", {})
            if "const" in op and (not isinstance(co, dict) or len(co) > 30 or
                    any(not isinstance(k, str) or len(k) > 64 or len(json.dumps(v)) > 500
                        for k, v in co.items())):
                errs.append(f"{tag}.const must be an object of <=30 small values")
        elif name == "filter":
            if not isinstance(op.get("field"), str) or not op["field"] or len(op["field"]) > 64:
                errs.append(f"{tag}.field must be a field name (max 64 chars)")
            conds = [k for k in ("exists", "equals", "contains", "gt", "lt") if k in op]
            if len(conds) != 1:
                errs.append(f"{tag}: filter needs exactly one condition (exists/equals/contains/gt/lt)")
            if "contains" in op and not isinstance(op["contains"], str):
                errs.append(f"{tag}.contains must be a string")
            for kk in ("gt", "lt"):
                if kk in op and not isinstance(op[kk], (int, float)):
                    errs.append(f"{tag}.{kk} must be a number")
    return errs


from html.parser import HTMLParser as _HTMLParser


class _El:
    __slots__ = ("tag", "attrs", "kids", "text", "parent")

    def __init__(self, tag="", attrs=None, parent=None):
        self.tag = (tag or "").lower()
        self.attrs = attrs or {}
        self.kids = []
        self.text = ""
        self.parent = parent


_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
          "link", "meta", "param", "source", "track", "wbr"}


class _Tree(_HTMLParser):
    """Minimal stdlib HTML tree for css-select + suggest analysis."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _El("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        el = _El(tag, {k.lower(): (v if v is not None else "") for k, v in attrs},
                 self.stack[-1])
        self.stack[-1].kids.append(el)
        if tag.lower() not in _VOID:
            self.stack.append(el)

    def handle_startendtag(self, tag, attrs):
        el = _El(tag, {k.lower(): (v if v is not None else "") for k, v in attrs},
                 self.stack[-1])
        self.stack[-1].kids.append(el)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if data.strip():
            self.stack[-1].text += data


def _text_of(el):
    parts = [el.text]
    for k in el.kids:
        parts.append(_text_of(k))
    return " ".join(p for p in parts if p).strip()


def _parse_simple(tok):
    """Parse one simple selector. None = unsupported syntax."""
    nth = None
    m = re.search(r":nth-child\((\d+)\)$", tok or "")
    if m:
        nth = int(m.group(1))
        tok = tok[:m.start()]
        if not 1 <= nth <= 1000:
            return None
    if not tok or ":" in tok or " " in tok or "," in tok:
        return None
    tag, id_, classes, attrs = None, None, [], []
    m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*|\*)", tok)
    i = 0
    if m:
        tag = m.group(1).lower()
        i = m.end()
    while i < len(tok):
        c = tok[i]
        if c == "#":
            m = re.match(r"#([A-Za-z0-9_-]+)", tok[i:])
            if not m or id_ is not None:
                return None
            id_ = m.group(1)
            i += m.end()
        elif c == ".":
            m = re.match(r"\.([A-Za-z0-9_-]+)", tok[i:])
            if not m:
                return None
            classes.append(m.group(1))
            i += m.end()
        elif c == "[":
            j = tok.find("]", i)
            if j < 0:
                return None
            inner = tok[i + 1:j]
            m = re.fullmatch(r"([A-Za-z0-9_-]+)(\^=|\*=|=)?\"([^\"]*)\"|" \
                             r"([A-Za-z0-9_-]+)(\^=|\*=|=)?'([^']*)'|" \
                             r"([A-Za-z0-9_-]+)((\^=|\*=|=)([^\"'\\]]+))?", inner)
            if not m:
                return None
            name = (m.group(1) or m.group(4) or m.group(7) or "").lower()
            aop = m.group(2) or m.group(5) or m.group(9) or ""
            val = m.group(3) if m.group(3) is not None else (m.group(6) if m.group(6) is not None else (m.group(10) or ""))
            if not name:
                return None
            attrs.append((name, aop, val))
            i = j + 1
        else:
            return None
    if tag is None and id_ is None and not classes and not attrs and nth is None:
        return None
    return {"tag": tag, "id": id_, "classes": classes, "attrs": attrs, "nth": nth}


def _parse_selector(sel):
    """Parse a selector into comma-groups of simple-selector chains."""
    try:
        groups = []
        for grp in sel.split(","):
            chain = [_parse_simple(t) for t in grp.strip().split()]
            if not chain or any(s is None for s in chain):
                return None
            groups.append(chain)
        return groups or None
    except Exception:
        return None


def _match_simple(el, s):
    if s["tag"] and s["tag"] != "*" and el.tag != s["tag"]:
        return False
    if s["id"] is not None and el.attrs.get("id", "") != s["id"]:
        return False
    if s["classes"]:
        have = set(el.attrs.get("class", "").split())
        if any(c not in have for c in s["classes"]):
            return False
    for name, aop, val in s["attrs"]:
        have = el.attrs.get(name)
        if have is None:
            return False
        if aop == "" :
            continue
        if aop == "=" and have != val:
            return False
        if aop == "^=" and not have.startswith(val):
            return False
        if aop == "*=" and val not in have:
            return False
    if s["nth"] is not None:
        if el.parent is None:
            return False
        sibs = [k for k in el.parent.kids if k.tag]
        pos = next((n + 1 for n, k in enumerate(sibs) if k is el), -1)
        if pos != s["nth"]:
            return False
    return True


def _desc(el):
    for k in el.kids:
        yield k
        yield from _desc(k)


def _select(root, selector):
    groups = _parse_selector(selector)
    if groups is None:
        return []
    out, seen = [], set()
    for chain in groups:
        cur = [root]
        for s in chain:
            nxt = []
            for el in cur:
                nxt.extend([d for d in _desc(el) if _match_simple(d, s)])
            cur = nxt
        for el in cur:
            if id(el) not in seen:
                seen.add(id(el))
                out.append(el)
    return out


def _seed_rows(raw):
    if isinstance(raw, dict):
        for k in ("rows", "items", "cards"):
            if isinstance(raw.get(k), list):
                return [r for r in raw[k] if isinstance(r, dict)][:200]
        return [raw]
    if isinstance(raw, list):
        return [r if isinstance(r, dict) else {"value": r} for r in raw[:200]]
    return [{"value": raw}]


def _op_css_select(op, raw):
    html = ""
    if isinstance(raw, dict):
        html = raw.get("html", "") or ""
    if not isinstance(html, str) or not html.strip():
        return []
    tree = _Tree()
    try:
        tree.feed(html[:200000])
        tree.close()
    except Exception:
        return []
    fields = op.get("fields") or {}
    limit = max(1, min(int(op.get("limit", 50)), 200))
    rows = []
    for el in _select(tree.root, op["selector"])[:limit]:
        if not fields:
            t = _text_of(el).strip()
            if t:
                rows.append({"text": t[:2000]})
            continue
        row = {}
        for out, spec in fields.items():
            spec = spec if isinstance(spec, dict) else {"sel": str(spec)}
            target = el
            if spec.get("sel"):
                subs = _select(el, spec["sel"])
                if not subs:
                    continue
                target = subs[0]
            attr = (spec.get("attr") or "text").lower()
            if attr == "text":
                row[out] = _text_of(target).strip()[:2000]
            elif attr == "html":
                continue  # raw markup never ships back
            else:
                row[out] = str(target.attrs.get(attr, ""))[:2000]
        if row:
            rows.append(row)
    return rows


def _op_json_path(op, raw):
    cur = raw
    try:
        for seg in op["path"].split("."):
            m = re.fullmatch(r"([^\[]*)(?:\[(\*|\d+)\])?", seg)
            if not m:
                return []
            name, idx = m.group(1), m.group(2)
            if name:
                cur = cur.get(name) if isinstance(cur, dict) else None
            if idx is not None and cur is not None:
                if not isinstance(cur, list):
                    return []
                cur = list(cur) if idx == "*" else ([cur[int(idx)]] if 0 <= int(idx) < len(cur) else [])
                if idx == "*":
                    pass
            if cur is None:
                return []
        items = cur if isinstance(cur, list) else [cur]
        return [(r if isinstance(r, dict) else {"value": r}) for r in items[:200]]
    except Exception:
        return []


def _op_regex(op, rows, raw):
    try:
        pat = re.compile(op["pattern"])
    except re.error:
        return []
    field = op.get("field") or op.get("in") or "text"
    group = int(op.get("group", 0))
    out = op.get("out") or field
    if not rows and isinstance(raw, dict) and isinstance(raw.get(field), str):
        rows = [{field: raw[field]}]
    out_rows = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        src = r.get(field, "")
        src = src if isinstance(src, str) else str(src)
        m = pat.search(src)
        if not m:
            continue
        try:
            val = m.group(group)
        except IndexError:
            continue
        nr = dict(r)
        nr[out] = val
        out_rows.append(nr)
    return out_rows


def _op_map(op, rows):
    ren = op.get("fields") or {}
    drop = set(op.get("drop") or [])
    const = op.get("const") or {}
    out_rows = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        nr = {}
        for k, v in r.items():
            if k in drop:
                continue
            nr[ren.get(k, k)] = v
        for k, v in const.items():
            nr[k] = v
        out_rows.append(nr)
    return out_rows


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _op_filter(op, rows):
    f = op["field"]
    out_rows = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        v = r.get(f)
        keep = False
        if "exists" in op:
            keep = (v not in (None, "", [], {})) == bool(op["exists"])
        elif "equals" in op:
            keep = v == op["equals"]
        elif "contains" in op:
            keep = isinstance(v, str) and op["contains"] in v
        elif "gt" in op:
            n = _num(v)
            keep = n is not None and n > op["gt"]
        elif "lt" in op:
            n = _num(v)
            keep = n is not None and n < op["lt"]
        if keep:
            out_rows.append(r)
    return out_rows


def execute_ops(ops, raw):
    """Run a validated op list. Pure data mapping — no code execution."""
    rows = None
    for op in ops:
        name = op.get("op")
        if name == "css-select":
            rows = _op_css_select(op, raw)
        elif name == "json-path":
            rows = _op_json_path(op, raw)
        elif name == "regex":
            rows = _op_regex(op, rows if rows is not None else _seed_rows(raw), raw)
        elif name == "map":
            rows = _op_map(op, rows if rows is not None else _seed_rows(raw))
        elif name == "filter":
            rows = _op_filter(op, rows if rows is not None else _seed_rows(raw))
    return (rows or [])[:200]


def suggest_mapping(url, html):
    """Rule-based extraction proposal for a stripped DOM snapshot.
    Never stores or echoes the html — returns counts + a proposed op list."""
    html = (html or "")[:100000]
    host = ""
    try:
        host = (urllib.parse.urlparse(url or "").hostname or "site").lower()
    except Exception:
        host = "site"
    base = re.sub(r"[^a-z0-9]+", "-", host).strip("-")[:24] or "site"
    # JSON-LD blocks
    ld_types, ld_fields = [], []
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                         html, re.I | re.S):
        try:
            j = json.loads(m.group(1))
        except Exception:
            continue
        objs = j if isinstance(j, list) else [j]
        if isinstance(j, dict) and isinstance(j.get("@graph"), list):
            objs = j["@graph"]
        for o in objs:
            if not isinstance(o, dict):
                continue
            t = o.get("@type", "")
            if isinstance(t, list):
                t = ",".join(str(x) for x in t)
            if t and str(t) not in ld_types:
                ld_types.append(str(t)[:64])
            for k, v in o.items():
                if k.startswith("@"):
                    continue
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        if isinstance(v2, (str, int, float)) and len(ld_fields) < 30 \
                                and f"{k}.{k2}" not in ld_fields:
                            ld_fields.append(f"{k}.{k2}"[:64])
                elif isinstance(v, (str, int, float)) and len(ld_fields) < 30 \
                        and k not in ld_fields:
                    ld_fields.append(k[:64])
            if len(ld_types) > 10:
                break
    # tables
    tables = []
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", html, re.I | re.S):
        body = m.group(1)
        # Skip nested tables inside this one (layout wrappers): only count
        # direct rows. A layout table (uneven rows) is not a data table.
        inner_stripped = re.sub(r"<table[^>]*>.*?</table>", "", body, flags=re.I | re.S)
        cell_counts = [len(re.findall(r"<t[hd][ >]", rm.group(1), re.I))
                       for rm in re.finditer(r"<tr[^>]*>(.*?)</tr>", inner_stripped, re.I | re.S)][:6]
        nrows = len(re.findall(r"<tr[ >]", inner_stripped, re.I))
        if nrows >= 3 and cell_counts and len(set(cell_counts)) == 1 and cell_counts[0] >= 2:
            tables.append({"rows": nrows, "cols": cell_counts[0]})
    # repeated classed structures
    repeats = []
    prices = len(re.findall(r"[$\u20ac\u00a3\u00a5]\s?\d[\d.,]*", html))
    dates = len(re.findall(r"\d{4}-\d{2}-\d{2}|\b\d{1,2}\s+[A-Z][a-z]+\s+\d{4}", html))
    try:
        tree = _Tree()
        tree.feed(html[:200000])
        tree.close()
        groups = {}
        for el in _desc(tree.root):
            cls = (el.attrs.get("class", "") or "").split()
            if not cls or el.tag in ("script", "style", "option"):
                continue
            key = (el.tag, cls[0][:40])
            g = groups.setdefault(key, {"n": 0, "txt": 0, "samples": []})
            t = _text_of(el).strip()
            if not t or len(t) > 2000:
                continue
            g["n"] += 1
            g["txt"] += len(t)
            if len(g["samples"]) < 3:
                g["samples"].append(t[:200])
        for (tag, cls), g in groups.items():
            if g["n"] >= 3 and g["txt"] / max(1, g["n"]) > 5:
                repeats.append({"tag": tag, "class": cls, "count": g["n"],
                                "avg_len": round(g["txt"] / g["n"]), "samples": g["samples"]})
        repeats.sort(key=lambda r: (-r["count"], -r["avg_len"]))
        repeats = repeats[:5]
    except Exception:
        repeats = []
    blob = " ".join(ld_types).lower()
    if any(k in blob for k in ("product", "offer", "aggregate")):
        kind = "product"
    elif any(k in blob for k in ("article", "news", "blog", "posting")):
        kind = "article"
    elif any(k in blob for k in ("job",)):
        kind = "job"
    elif tables:
        kind = "table"
    elif repeats:
        kind = "list"
    else:
        kind = "generic"
    dataset = f"{base}-{kind}s"[:64]
    fields, ops, reasons = [], [], []
    conf = 0.3
    if ld_types:
        fields = ld_fields[:20] or ["name", "url"]
        type_field = "@type" if any("@type" in f for f in ld_fields) else None
        ops = [{"op": "json-path", "path": "jsonld[*]"}]
        if type_field:
            ops.append({"op": "filter", "field": type_field, "exists": True})
        ops.append({"op": "map", "const": {"source": host}})
        conf = 0.9
        reasons.append(f"JSON-LD types: {', '.join(ld_types[:5])}")
    elif tables:
        t = tables[0]
        fields = [f"col{i + 1}" for i in range(min(t["cols"], 8))]
        ops = [{"op": "css-select", "selector": "table tr",
                "fields": {f"col{i + 1}": {"sel": f"td:nth-child({i + 1}), th:nth-child({i + 1})"}
                             for i in range(min(t["cols"], 8))}, "limit": 100}]
        conf = 0.7
        reasons.append(f"table with ~{t['rows']} rows x {t['cols']} cols")
    elif repeats:
        r = repeats[0]
        sel = f"{r['tag']}.{r['class']}"
        fields = ["title", "url", "text"]
        fmap = {"title": {"sel": "a, h2, h3, h1", "attr": "text"},
                "url": {"sel": "a", "attr": "href"},
                "text": {"attr": "text"}}
        if prices:
            fields.append("price")
            ops_extra = [{"op": "regex", "field": "text",
                          "pattern": "[$\u20ac\u00a3\u00a5]\\s?\\d[\\d.,]*",
                          "group": 0, "out": "price"}]
        else:
            ops_extra = []
        ops = [{"op": "css-select", "selector": sel, "fields": fmap, "limit": 100}] + ops_extra
        ops.append({"op": "filter", "field": "title", "exists": True})
        conf = 0.6
        reasons.append(f"repeated <{r['tag']}.{r['class']}> x{r['count']} (avg {r['avg_len']} chars)")
    else:
        reasons.append("no JSON-LD, tables, or repeated structures found")
    if prices:
        reasons.append(f"{prices} price-like strings")
    if dates:
        reasons.append(f"{dates} date-like strings")
    return {"dataset": dataset, "kind": kind,
            "fields": fields[:20], "proposed_ops": ops,
            "confidence": conf, "reason": "; ".join(reasons) or "empty page",
            "scanned": {"html_bytes": len(html), "jsonld_types": ld_types[:10],
                          "tables": len(tables), "repeat_groups": len(repeats),
                          "prices": prices, "dates": dates},
            "note": "Approve to create a server-side recipe (where=server). "
                      "Snapshot was client-stripped (no inputs/passwords) and is never stored."}


_RATE = {}
_RATE_LOCK = threading.Lock()


def rate_hit(node_id):
    c = cfg()
    try:
        per_min = int(c.get("ingest_rate_per_minute", 30))
    except (TypeError, ValueError):
        per_min = 30
    if per_min <= 0:
        return False
    window = 60.0
    t = time.time()
    with _RATE_LOCK:
        hits = [x for x in _RATE.get(node_id, []) if t - x < window]
        if len(hits) >= per_min:
            _RATE[node_id] = hits
            return True
        hits.append(t)
        _RATE[node_id] = hits
        return False


def record_hash(dataset, node_id, rec):
    canon = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{dataset}\x00{node_id}\x00{canon}".encode()).hexdigest()


def recent_hashes(dataset=None):
    c = cfg()
    try:
        scan_last = int(c.get("dedupe_scan_last", 5000))
    except (TypeError, ValueError):
        scan_last = 5000
    seen = set()
    path = p("records_path", "data/records.jsonl")
    if not os.path.exists(path):
        return seen
    with open(path) as f:
        lines = f.read().splitlines()[-scan_last:]
    for line in lines:
        try:
            r = json.loads(line)
        except Exception:
            continue
        rec = r.get("record")
        if isinstance(rec, dict) and (dataset is None or r.get("dataset") == dataset):
            seen.add(record_hash(r.get("dataset", ""), r.get("node_id", ""), rec))
    return seen


def compute_earnings(counts, token, rate, comm, cap_recs, cap_net):
    """Pure payout math (unit-tested in test/commission_test.py)."""
    nodes = []
    for nid in sorted(counts):
        billable = min(counts[nid], cap_recs)
        gross = round(billable * rate, 4)
        fee = round(gross * comm / 100.0, 4)
        net = round(gross - fee, 4)
        capped = counts[nid] > cap_recs
        if cap_net is not None and net > cap_net:
            net = cap_net
            capped = True
        nodes.append({
            "node_id": nid,
            "records": counts[nid],
            "billable_records": billable,
            "capped": capped,
            "gross": gross,
            "commission": fee,
            "net": net,
            "token": token,
        })
    total_billable = sum(min(v, cap_recs) for v in counts.values())
    total_gross = round(total_billable * rate, 4)
    return nodes, {
        "records": sum(counts.values()),
        "billable_records": total_billable,
        "gross": total_gross,
        "commission": round(total_gross * comm / 100.0, 4),
        "net": round(total_gross * (1 - comm / 100.0), 4),
    }


def earnings(include_test=False):
    """Payout math per node. Test nodes (agent/test traffic) are EXCLUDED
    by default (?include_test=1 audits them with test:true visible) so
    test bookings never pump the public money story."""
    test_ids = set() if include_test else test_node_ids()
    all_test = test_node_ids() if include_test else set()
    c = cfg()
    token = c.get("payout_token_symbol", "SCRAPE")
    rate = float(c.get("payout_per_record", 0.01))
    comm = float(c.get("commission_pct", 10))
    try:
        cap_recs = int(c.get("max_records_per_node_earnings", 1000))
    except (TypeError, ValueError):
        cap_recs = 1000
    try:
        cap_net = c.get("max_payout_net_per_node", None)
        cap_net = float(cap_net) if cap_net not in (None, "") else None
    except (TypeError, ValueError):
        cap_net = None
    counts = {}
    for r in load_lines(p("records_path", "data/records.jsonl")):
        n = r.get("node_id", "unknown")
        if n in test_ids:
            continue
        counts[n] = counts.get(n, 0) + 1
    test_records_hidden = 0 if include_test else sum(
        1 for r in load_lines(p("records_path", "data/records.jsonl"))
        if r.get("node_id", "unknown") in test_ids)
    nodes, totals = compute_earnings(counts, token, rate, comm, cap_recs, cap_net)
    for n in nodes:
        n["wallet"] = node_wallet(n["node_id"])
        n["test"] = n["node_id"] in all_test
    # Referral split: referral_pct % of each referred node's platform
    # commission is redirected to the referrer (bonus on top for them, the
    # referred node keeps its full net). Documented in needs.json.
    try:
        ref_pct = float(c.get("referral_pct", 0) or 0)
    except (TypeError, ValueError):
        ref_pct = 0.0
    db = auth_db()
    accts = db.get("nodes", {}) if isinstance(db, dict) else {}
    bonus_by = {}
    for n in nodes:
        acct = accts.get(n["node_id"], {})
        rb = acct.get("referred_by")
        n["referred_by"] = rb
        n["referral_earnings"] = 0.0
        if rb and ref_pct > 0:
            share = round(n["commission"] * ref_pct / 100.0, 4)
            n["referral_share_to_referrer"] = share
            bonus_by[rb] = round(bonus_by.get(rb, 0.0) + share, 4)
    for n in nodes:
        if n["node_id"] in bonus_by:
            n["referral_earnings"] = bonus_by[n["node_id"]]
    totals["referral_paid"] = round(sum(bonus_by.values()), 4)
    totals["platform_commission"] = round(totals["commission"] - totals["referral_paid"], 4)
    return {
        "token": token,
        "payout_per_record": rate,
        "commission_pct": comm,
        "referral_pct": ref_pct,
        "referral_rule": c.get("referral_rule", ""),
        "max_records_per_node_earnings": cap_recs,
        "max_payout_net_per_node": cap_net,
        "test_hidden": 0 if include_test else len(test_ids),
        "test_records_hidden": test_records_hidden,
        "nodes": nodes,
        "totals": totals,
    }


IDEA_RULES = [
    ("price", "Price-drop alerts API",
     "Sell a webhook/API that pings subscribers when a tracked product falls below target. Charge per tracked SKU per month.",
     "price history + subscriber webhooks; needs daily refresh per SKU"),
    ("job", "Niche job board + alerts",
     "Publish a curated board for one role/stack from the listings dataset; charge employers for featured posts and candidates for instant alerts.",
     "deduped listings + email/discord alerts; needs fresh crawl daily"),
    ("crypto", "Spread / momentum signal feed",
     "Sell a tick feed + spread/momentum signals computed from the price dataset; charge per API key per month.",
     "clean tick series + signal endpoint; needs minute-level freshness"),
    ("title", "Lead list for outreach",
     "Package hiring companies (or sellers) as a lead list with contact enrichment; charge per 1k verified rows.",
     "dedupe by company+title, verify URLs; needs weekly refresh"),
    ("symbol", "Historical OHLC dataset download",
     "Sell versioned CSV/JSON dumps of the tick dataset for backtests; charge per download or subscription.",
     "aggregated candles + checksums; needs stable schema"),
]


def suggest_ideas(fields, dataset=""):
    fl = [str(f).lower() for f in fields]
    blob = " ".join(fl) + " " + str(dataset).lower()
    scored = []
    for key, title, how, needs in IDEA_RULES:
        score = 2 if key in blob else 0
        scored.append((score, {"title": title, "how": how, "needs": needs,
                               "matched_on": key if score else "general"}))
    scored.sort(key=lambda x: -x[0])
    top = [s[1] for s in scored[:3]]
    if not any(s["matched_on"] != "general" for s in top):
        top[0] = {"title": "Metered public API for this dataset",
                  "how": "Publish the dataset, rate-limit free tier, charge per 1k calls above quota.",
                  "needs": "published endpoint + key tracking",
                  "matched_on": "general"}
    return top


def dataset_fields(dataset, include_test=False):
    tids = set() if include_test else test_node_ids()
    rows = [r for r in load_lines(p("records_path", "data/records.jsonl"))
            if (not dataset or r.get("dataset") == dataset)
            and r.get("node_id") not in tids]
    fields = []
    for r in rows[:50]:
        rec = r.get("record", {})
        if isinstance(rec, dict):
            for k in rec:
                if k not in fields:
                    fields.append(k)
    return fields, len(rows)


def refine(sample, recipe_fn=""):
    """Rule-based transform improver: dedupe, schema inference, quality score,
    selector-fix suggestions. LLM slot: if needs.json llm_model_endpoint is set,
    response includes llm_available=true and the prompt to send (server never
    invents LLM output itself)."""
    c = cfg()
    seen = set()
    unique = []
    dupes = 0
    for r in sample:
        key = json.dumps(r, sort_keys=True)
        if key in seen:
            dupes += 1
        else:
            seen.add(key)
            unique.append(r)
    types = {}
    non_empty = {}
    total = max(1, len(unique))
    for r in unique:
        if not isinstance(r, dict):
            continue
        for k, v in r.items():
            t = type(v).__name__
            types.setdefault(k, {}).setdefault(t, 0)
            types[k][t] += 1
            if v not in (None, "", [], {}):
                non_empty[k] = non_empty.get(k, 0) + 1
    schema = {k: max(v.items(), key=lambda x: x[1])[0] for k, v in types.items()}
    quality = {k: round(non_empty.get(k, 0) / total, 2) for k in types}
    overall = round(sum(quality.values()) / max(1, len(quality)), 2) if quality else 0.0
    suggestions = []
    for k, q in quality.items():
        if q < 0.7:
            suggestions.append(
                f"Field '{k}' is empty in {int((1 - q) * 100)}% of rows — "
                f"selector likely wrong. Check alternate keys/aliases for '{k}' "
                f"(e.g. title<->name, amount<->price) or add a fallback in the recipe fn.")
    if dupes:
        suggestions.append(
            f"{dupes} exact-duplicate rows dropped — add a dupe key "
            f"(url+name, symbol+at) before ingest.")
    if not suggestions:
        suggestions.append("Schema looks clean — no selector fixes suggested.")
    llm_ep = (c.get("llm_model_endpoint") or "").strip()
    out = {
        "input_rows": len(sample),
        "dupes_removed": dupes,
        "unique_rows": len(unique),
        "schema": schema,
        "field_quality": quality,
        "quality_score": overall,
        "suggestions": suggestions,
        "clean_sample": unique[:10],
        "llm_available": bool(llm_ep),
        "llm_model": c.get("llm_model", ""),
    }
    if llm_ep:
        out["llm_prompt"] = (
            f"Rewrite this transform recipe fn to fix empty fields {quality}. "
            f"Recipe fn:\n{recipe_fn}\nSample rows:\n"
            + json.dumps(unique[:5], indent=1))
        out["llm_endpoint"] = llm_ep
    else:
        out["llm_note"] = c.get("llm_note", "Set llm_model_endpoint in needs.json to plug an LLM here.")
    return out


WHERE_MODES = ("client", "server", "both")


def normalize_where(v):
    """Per-recipe transform location. CLIENT runs in the user's browser
    (raw page never leaves); SERVER sends raw to the collector for AI
    refine (smarter, less private); BOTH tries client first."""
    v = (v or "client") if isinstance(v, str) else "client"
    v = v.strip().lower()
    return v if v in WHERE_MODES else None


GEN_FN_TMPL = {
 "price": ("function transform(raw, ctx) {\n  const out = [];\n"
  "  const cards = raw.cards || (raw.items || []);\n"
  "  for (const c of cards) {\n"
  "    const name = (c.name || c.title || '').toString().trim();\n"
  "    const price = parseFloat(String(c.price ?? c.amount ?? '').replace(/[^0-9.]/g, ''));\n"
  "    if (!name || !isFinite(price)) continue;\n"
  "    out.push({ name, price, currency: c.currency || 'USD', url: c.url || ctx.url || '' });\n"
  "  }\n  return out;\n}"),
 "job": ("function transform(raw, ctx) {\n  const out = [];\n"
  "  const cards = raw.cards || (raw.items || raw.jobs || []);\n"
  "  for (const c of cards) {\n"
  "    const title = (c.title || c.name || '').toString().trim();\n"
  "    if (!title) continue;\n"
  "    out.push({ title, company: (c.company || '').toString().trim(), "
  "location: (c.location || 'remote').toString().trim(), url: c.url || ctx.url || '' });\n"
  "  }\n  return out;\n}"),
 "crypto": ("function transform(raw, ctx) {\n  const out = [];\n"
  "  const cards = raw.cards || (raw.items || raw.tickers || []);\n"
  "  for (const c of cards) {\n"
  "    const symbol = (c.symbol || c.pair || '').toString().toUpperCase().trim();\n"
  "    const price = parseFloat(String(c.price ?? c.last ?? ''));\n"
  "    if (!symbol || !isFinite(price)) continue;\n"
  "    out.push({ symbol, price, at: c.at || ctx.at || new Date().toISOString() });\n"
  "  }\n  return out;\n}"),
 "generic": ("function transform(raw, ctx) {\n  const out = [];\n"
  "  const cards = raw.cards || (raw.items || []);\n"
  "  for (const c of cards) {\n"
  "    const title = (c.title || c.name || '').toString().trim();\n"
  "    if (!title) continue;\n"
  "    out.push({ title, url: c.url || ctx.url || '' });\n"
  "  }\n  return out;\n}"),
}

GEN_META = {
 "price": ("product-prices", ["name", "price", "currency", "url"],
             "Product price", "shop|store|product"),
 "job": ("job-listings", ["title", "company", "location", "url"],
           "Job listing", "jobs|career|hiring"),
 "crypto": ("crypto-prices", ["symbol", "price", "at"],
              "Crypto price", "coin|crypto|exchange"),
 "generic": ("default", ["title", "url"], "Generic cards", "card|item|list"),
}


def propose_recipe(html, url_hint="", name_hint="", dataset_hint=""):
    """Rule-based recipe proposal from a pasted HTML sample or a fetched
    URL body. Never executes anything - pure string signals. LLM slot: if
    needs.json llm_model_endpoint is set, the response also carries
    llm_available=true + a ready prompt (same pattern as /api/refine)."""
    blob = html if isinstance(html, str) else ""
    low = blob.lower()
    prices = len(re.findall(r"[$\u20ac\u00a3]\s?\d", blob))
    cards = len(re.findall(r"class\s*=\s*[\"'][^\"']*(product|card|item)[^\"']*", low))
    ld_product = "product" in low and "application/ld+json" in low
    job_kw = sum(low.count(k) for k in ("job", "career", "hiring", "apply now"))
    crypto_kw = sum(low.count(k) for k in ("ticker", "symbol", "usdt", "exchange", "order book"))
    if crypto_kw >= 2 and crypto_kw >= job_kw and prices <= crypto_kw:
        kind = "crypto"
        why = ("found %d crypto/ticker signals" % crypto_kw +
               (" + %d price tags" % prices if prices else "") +
               " -> crypto-price recipe")
    elif job_kw >= 2 and job_kw > prices:
        kind = "job"
        why = "found %d job/career signals -> job-listing recipe" % job_kw
    elif prices > 0 or cards > 0 or ld_product:
        kind = "price"
        why = ("found %d price tags + %d product/card/item blocks" % (prices, cards) +
               (" + JSON-LD Product" if ld_product else "") +
               " -> product-price recipe")
    else:
        kind = "generic"
        why = ("no price/job/crypto signals - generic title+url recipe; "
               "paste a page with product cards or prices for a sharper proposal")
    ds_default, schema, label, match = GEN_META[kind]
    host = ""
    try:
        host = urllib.parse.urlparse(url_hint).hostname or ""
    except Exception:
        host = ""
    if host:
        match = re.sub(r"[^a-z0-9|]+", "", host.replace(".", "|").lower())[:60] or match
    dataset = (dataset_hint or "").strip() or ds_default
    if not DS_RE.fullmatch(dataset):
        dataset = ds_default
    base = re.sub(r"[^a-z0-9]+", "-", (name_hint or label).lower()).strip("-")[:24] or kind
    rid = "%s-%s" % (base, secrets.token_hex(2))
    c = cfg()
    llm_ep = (c.get("llm_model_endpoint") or "").strip()
    out = {
        "ok": True,
        "kind": kind,
        "explanation": why,
        "recipe": {
            "id": rid,
            "name": (name_hint or label).strip()[:120],
            "dataset": dataset,
            "match": match[:120],
            "description": "AI-prefill (%s) from pasted sample: %s" % (kind, why),
            "schema": schema,
            "fn": GEN_FN_TMPL[kind],
            "where": "client",
        },
        "signals": {"price_tags": prices, "card_blocks": cards,
                      "jsonld_product": ld_product, "job_kw": job_kw,
                      "crypto_kw": crypto_kw},
        "llm_available": bool(llm_ep),
        "llm_model": c.get("llm_model", ""),
    }
    if llm_ep:
        out["llm_prompt"] = (
            "Write a ScrapeNet recipe fn `function transform(raw, ctx)` "
            "returning [%s] rows. Detected: %s. "
            "Sample HTML (truncated):\n%s" % (", ".join(schema), why, blob[:4000]))
        out["llm_endpoint"] = llm_ep
    else:
        out["llm_note"] = c.get("llm_note", "")
    return out


def fetch_url_sample(url):
    """Fetch a page body for /api/generate (stdlib urllib, 10s, 200KB
    cap, http/https only). Returns (html, error)."""
    try:
        u = urllib.parse.urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname:
            return "", "url must be http(s) with a host"
    except Exception:
        return "", "url must be http(s) with a host"
    try:
        import urllib.request as _rq
        req = _rq.Request(url, headers={"User-Agent": "ScrapeNet-generate/1.0"})
        with _rq.urlopen(req, timeout=10) as r:
            raw = r.read(200_000)
        return raw.decode("utf-8", "replace"), ""
    except Exception as e:
        return "", "fetch failed: %s" % str(e)[:200]


def last_capture(include_test=False):
    """Newest ingested row (prefer one carrying its raw capture) plus the
    recipe fn that produced it - the PROOF behind 'Show last capture'.
    Test/agent rows are skipped by default (?include_test=1 audits them)."""
    tids = set() if include_test else test_node_ids()
    rows = [r for r in load_lines(p("records_path", "data/records.jsonl"))
            if r.get("node_id") not in tids]
    if not rows:
        return None
    pick = None
    for r in reversed(rows[-2000:]):
        if isinstance(r.get("raw"), (dict, list)):
            pick = r
            break
    if pick is None:
        pick = rows[-1]
    fn = ""
    rid = pick.get("recipe_id", "")
    if rid:
        for rec in recipes():
            if rec.get("id") == rid:
                fn = rec.get("fn", "")
                break
    return {"at": pick.get("at", ""), "dataset": pick.get("dataset", ""),
            "node_id": pick.get("node_id", ""),
            "recipe_id": rid,
            "has_raw": isinstance(pick.get("raw"), (dict, list)),
            "raw": pick.get("raw"),
            "record": pick.get("record", {}),
            "recipe_fn": fn}


def last_payout(include_test=False):
    """Payout math for the node behind the newest HONEST record - the PROOF
    behind 'Show last payout math': records x rate - commission = payout.
    (?include_test=1 audits the newest row whatever its flag.)"""
    tids = set() if include_test else test_node_ids()
    rows = [r for r in load_lines(p("records_path", "data/records.jsonl"))
            if r.get("node_id") not in tids]
    if not rows:
        return None
    nid = rows[-1].get("node_id", "unknown")
    e = earnings(include_test=True)
    entry = next((n for n in e["nodes"] if n["node_id"] == nid), None)
    if entry is None:
        return None
    eq = ("%s records x %s %s - %s%% commission "
          "(%s %s) = %s %s" % (entry["billable_records"], e["payout_per_record"],
          e["token"], e["commission_pct"], entry["commission"],
          e["token"], entry["net"], e["token"]))
    return {"node_id": nid, "records": entry["records"],
            "billable_records": entry["billable_records"],
            "rate": e["payout_per_record"], "token": e["token"],
            "gross": entry["gross"], "commission_pct": e["commission_pct"],
            "commission": entry["commission"], "net": entry["net"],
            "referral_earnings": entry.get("referral_earnings", 0.0),
            "equation": eq}


def leaderboard(include_test=False):
    """Referral leaderboard: referrers ranked by records their invitees
    contributed. Public (growth loop surface for dashboard + LAUNCH kit).
    Test referrers/invitees are EXCLUDED by default (?include_test=1
    audits them with test:true visible)."""
    c = cfg()
    try:
        ref_pct = float(c.get("referral_pct", 0) or 0)
    except (TypeError, ValueError):
        ref_pct = 0.0
    db = auth_db()
    accts = db.get("nodes", {}) if isinstance(db, dict) else {}
    test_ids = set() if include_test else test_node_ids()
    counts = {}
    for r in load_lines(p("records_path", "data/records.jsonl")):
        n = r.get("node_id", "unknown")
        if n in test_ids:
            continue
        counts[n] = counts.get(n, 0) + 1
    e = earnings(include_test=include_test)
    bonus = {}
    for n in e["nodes"]:
        rb = n.get("referred_by")
        share = n.get("referral_share_to_referrer", 0.0) or 0.0
        if rb and share > 0:
            bonus[rb] = round(bonus.get(rb, 0.0) + share, 4)
    leaders = []
    for nid, a in sorted(accts.items()):
        if nid in test_ids:
            continue
        invited = [m for m, b in accts.items()
                   if b.get("referred_by") == nid and m not in test_ids]
        if not invited and bonus.get(nid, 0.0) <= 0:
            continue
        recs = sum(counts.get(m, 0) for m in invited)
        credit = bonus.get(nid, 0.0)
        try:
            thr = float(cfg().get("referral_payout_threshold", 5) or 0)
        except (TypeError, ValueError):
            thr = 5.0
        dec = payout_decision_for(nid, a.get("referral_code", ""))
        if dec and dec.get("approve"):
            pstatus = "paid"
        elif dec and not dec.get("approve"):
            pstatus = "rejected"
        elif credit >= thr:
            pstatus = "awaiting_manual_review"
        else:
            pstatus = "accruing"
        leaders.append({
            "node_id": nid,
            "name": a.get("name", ""),
            "test": bool(a.get("test")) or _matches_test(nid),
            "referral_code": a.get("referral_code", ""),
            "referred_signups": len(invited),
            "referred_records": recs,
            "referral_earnings": credit,
            "referral_credit": credit,
            "payout_status": pstatus,
            "token": e["token"],
        })
    leaders.sort(key=lambda x: (-x["referred_records"], -x["referred_signups"]))
    try:
        payout_thr = float(c.get("referral_payout_threshold", 5) or 0)
    except (TypeError, ValueError):
        payout_thr = 5.0
    return {
        "referral_pct": ref_pct,
        "referral_rule": c.get("referral_rule", ""),
        "commission_pct": float(c.get("commission_pct", 10)),
        "payout": {"threshold": payout_thr, "token": e["token"],
                   "note": c.get("referral_payout_note", "")},
        "test_hidden": 0 if include_test else len(test_ids),
        "leaders": leaders,
        "totals": {
            "referrers": len(leaders),
            "referred_signups": sum(1 for nid, a in accts.items()
                                      if a.get("referred_by") is not None
                                      and nid not in test_ids),
            "referred_records": sum(l["referred_records"] for l in leaders),
            "referral_paid": e["totals"].get("referral_paid", 0.0),
        },
    }


# ---- loop backlog gaps (e082 hands write here; stdlib only) ----
# The e082 keep-going loop observes this collector every tick. When
# publishes stall it files a gap row here (evidence, not vibes); when the
# funnel verdict is FAILING the row carries priority:high. Rows are public
# reads; writes need a node token or the owner key (same gate as growth
# approvals). Test rows (test:true) hide from the public list by default
# (?include_test=1 audits them) and are the only rows a node token may
# delete (owner may delete any row) — proof ticks clean up after themselves.
LOOP_SOURCE = "e082-loop"
GAP_PRIORITIES = ("normal", "high")


def gaps_path():
    return p("gaps_path", "data/gaps.jsonl")


def list_gaps(include_test=False):
    rows = [r for r in load_lines(gaps_path()) if isinstance(r, dict)]
    if not include_test:
        rows = [r for r in rows if not r.get("test")]
    return rows


def file_gap(item, evidence, priority="normal", by="", test=False):
    """Append one gap row. Returns the row (with id). Pure validation +
    append — no network, no side effects."""
    errs = []
    if not isinstance(item, str) or not item.strip() or len(item) > 200:
        errs.append("item required (string 1..200 chars)")
    if not isinstance(evidence, str) or not evidence.strip() or len(evidence) > 2000:
        errs.append("evidence required (string 1..2000 chars)")
    if priority not in GAP_PRIORITIES:
        errs.append("priority must be normal|high")
    if errs:
        return None, "; ".join(errs)
    gid = ("gap-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")
             + secrets.token_hex(2))
    row = {"id": gid, "at": now_iso(), "source": LOOP_SOURCE,
           "item": item.strip()[:200], "evidence": evidence.strip()[:2000],
           "priority": priority, "by": str(by or "")[:64],
           "test": bool(test)}
    append_line(gaps_path(), row)
    audit("gap_filed", id=gid, priority=priority, by=str(by or "")[:64])
    return row, None


def delete_gap(gid, by="", owner=False):
    """Remove one gap row. Owner may remove any row; a node token may
    only remove test rows (proof-tick cleanup). Returns (ok, error)."""
    rows = [r for r in load_lines(gaps_path()) if isinstance(r, dict)]
    hit = next((r for r in rows if r.get("id") == gid), None)
    if hit is None:
        return False, "gap not found"
    if not owner and not hit.get("test"):
        return False, "only test gaps may be deleted with a node token (owner may delete any)"
    keep = [r for r in rows if r.get("id") != gid]
    try:
        with open(gaps_path(), "w") as f:
            for r in keep:
                f.write(json.dumps(r) + "\n")
    except Exception as e:
        return False, f"could not rewrite gaps store: {type(e).__name__}"
    audit("gap_deleted", id=gid, by=str(by or "")[:64])
    return True, None


# ---- growth loop (autonomous poster; stdlib only) ----
# CONTENT ENGINE: GET /api/growth/queue returns the next 7 days of posts,
# auto-generated from LIVE app data (records, earnings, leaderboard,
# published). Rule-based templates over real numbers — every post cites a
# real fact with a link (dataset/share URL + ?ref=growth so conversions
# attribute to the loop). Queue regenerates daily; POST /api/growth/approve
# {id} (token-authed) or the growth_auto_approve flag in needs.json.
# POSTER: needs.json growth_channel + keys. Backends: `dryrun` (default:
# logs exactly what WOULD post to data/outbox.jsonl) and `x_api` (stdlib
# urllib POST to X API v2 with the OAuth2 bearer from needs.json,
# idempotent via outbox dedupe). SCHEDULER: bin/growth.sh one|daemon ticks
# growth_tick() daily (regenerate -> post due item -> log data/growth.jsonl).
GROWTH_DAYS = 7
GROWTH_REF = "growth"


def growth_paths():
    c = cfg()
    q = c.get("growth_queue_path", "data/growth.json")
    o = c.get("outbox_path", "data/outbox.jsonl")
    g = c.get("growth_log_path", "data/growth.jsonl")
    qp = os.path.join(DIR, q) if not os.path.isabs(q) else q
    op = os.path.join(DIR, o) if not os.path.isabs(o) else o
    gp = os.path.join(DIR, g) if not os.path.isabs(g) else g
    return qp, op, gp


def growth_settings():
    """Poster config, all from needs.json — never hardcoded."""
    c = cfg()
    channel = str(c.get("growth_channel", "dryrun") or "dryrun").strip().lower()
    if channel not in ("dryrun", "x_api"):
        channel = "dryrun"
    try:
        interval = int(c.get("growth_interval_sec", 86400))
    except (TypeError, ValueError):
        interval = 86400
    return {
        "channel": channel,
        "auto_approve": bool(c.get("growth_auto_approve", True)),
        "x_bearer_token_set": bool(secret("x_bearer_token")),
        "interval_sec": max(60, interval),
        "base_url": (c.get("public_url", "") or "").strip().rstrip("/"),
    }


def _num_list(vals):
    out = []
    for v in vals:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            pass
    return out


def growth_facts():
    """Snapshot of LIVE numbers the templates cite. HONEST by default:
    test/agent rows are excluded (a real zero beats a fake 14), so every
    cited number is a genuinely true fact about the world. Templates may
    only cite `real_datasets` (prod rows carrying source+fetched_at)."""
    c = cfg()
    base = (c.get("public_url", "") or "").strip().rstrip("/")
    test_ids = test_node_ids()
    rows = [r for r in load_lines(p("records_path", "data/records.jsonl"))
            if r.get("node_id") not in test_ids]
    per_ds, nodes = {}, set()
    for r in rows:
        ds = r.get("dataset", "unknown")
        per_ds[ds] = per_ds.get(ds, 0) + 1
        if r.get("node_id"):
            nodes.add(r["node_id"])
    # Real datasets: prod rows whose records carry source+fetched_at
    # (the loop collector's verifiable facts — re-pullable by anyone).
    real = {}
    for r in rows:
        rec = r.get("record", {})
        if isinstance(rec, dict) and rec.get("source") and rec.get("fetched_at"):
            ds = r.get("dataset", "unknown")
            d = real.setdefault(ds, {"count": 0, "sources": set(),
                                      "latest_at": "", "rows": []})
            d["count"] += 1
            d["sources"].add(str(rec["source"]))
            if str(rec["fetched_at"]) > d["latest_at"]:
                d["latest_at"] = str(rec["fetched_at"])
            d["rows"].append(rec)
    real_datasets = {ds: {"count": d["count"],
                           "sources": sorted(d["sources"]),
                           "latest_at": d["latest_at"],
                           "rows": d["rows"][-10:]}
                      for ds, d in real.items()}
    e = earnings()
    lb = leaderboard()
    pub = published()
    spread = None
    prices = _num_list([
        r.get("record", {}).get("price") for r in rows
        if r.get("dataset") == "product-prices"
        and isinstance(r.get("record"), dict)])
    if len(prices) >= 2:
        spread = {"lo": min(prices), "hi": max(prices),
                  "n": len(prices),
                  "spread": round(max(prices) - min(prices), 2)}
    top_ds = max(per_ds.items(), key=lambda x: x[1]) if per_ds else ("crypto-spot", 0)
    leaders = lb.get("leaders", [])
    all_rows = load_lines(p("records_path", "data/records.jsonl"))
    return {
        "base": base,
        "records_total": len(rows),
        "test_records_hidden": len(all_rows) - len(rows),
        "test_nodes_hidden": len(test_ids),
        "datasets": sorted(per_ds.items(), key=lambda x: -x[1]),
        "nodes_total": len(nodes),
        "real_datasets": real_datasets,
        "published": {ds: {"count": m.get("count", 0), "at": m.get("at", "")}
                        for ds, m in pub.items()},
        "payout_token": e.get("token", "SCRAPE"),
        "payout_per_record": e.get("payout_per_record", 0.01),
        "paid_net": (e.get("totals") or {}).get("net", 0.0),
        "earn_nodes": len(e.get("nodes", [])),
        "top_dataset": {"id": top_ds[0], "count": top_ds[1]},
        "spread": spread,
        "top_referrer": leaders[0] if leaders else None,
        "referred_signups": (lb.get("totals") or {}).get("referred_signups", 0),
    }


def _fit(text, link, limit=280):
    """Keep posts X-shaped: text + link under `limit` chars."""
    text, link = (text or "").strip(), (link or "").strip()
    if len(text) + 1 + len(link) <= limit:
        return text + " " + link
    cut = limit - len(link) - 2  # space + ellipsis
    return text[:max(0, cut)].rstrip() + "… " + link


def build_growth_queue(today=None):
    """Pure builder: dated posts from VERIFIED facts only. No I/O but reads.
    DRY-RUN HONESTY: every template cites a real dataset (prod rows with
    source+fetched_at, re-pullable by anyone). A template with no real data
    is REMOVED, not faked — the queue shrinks to what is true (possibly
    empty). Old test-traffic templates (product-prices size, fake spread,
    referral theater, breadth counts pumped by bots) are gone."""
    f = growth_facts()
    base = f["base"]
    day0 = today or datetime.date.today().isoformat()
    d0 = datetime.date.fromisoformat(day0)
    real = f.get("real_datasets", {}) or {}

    def link(ds):
        return (f"{base}/dataset/{ds}?ref={GROWTH_REF}" if base
                else f"/dataset/{ds}?ref={GROWTH_REF}")
    home_link = f"{base}/?ref={GROWTH_REF}" if base else f"/?ref={GROWTH_REF}"
    cands = []
    cx = real.get("crypto-spot")
    if cx:
        btc = [r for r in cx["rows"]
               if r.get("symbol") == "BTC" and r.get("price_usd")]
        if btc:
            last = btc[-1]
            src = last.get("source", "?")
            cands.append(("btc-spot",
                f"BTC ${float(last['price_usd']):,.2f} right now ({src}, fetched {str(last.get('fetched_at', ''))[:16]}Z) — our crypto-spot dataset tracks it live as a free public API:",
                link("crypto-spot"),
                f"crypto-spot BTC=${last['price_usd']} via {src}"))
        if len(btc) >= 2:
            a, b = float(btc[0]["price_usd"]), float(btc[-1]["price_usd"])
            mv = round(b - a, 2)
            cands.append(("btc-move",
                f"BTC moved ${a:,.2f} → ${b:,.2f} ({mv:+,.2f}) across our last {len(btc)} crypto-spot observations. Real ticks, free JSON — watch it live:",
                link("crypto-spot"),
                f"crypto-spot BTC move {mv:+} over {len(btc)} obs"))
    fx = real.get("usd-fx")
    if fx:
        eur = [r for r in fx["rows"] if r.get("pair") == "USD/EUR" and r.get("rate")]
        if eur:
            last = eur[-1]
            src = last.get("source", "?")
            cands.append(("fx-rate",
                f"USD/EUR {float(last['rate']):.4f} ({src}, upstream {str(last.get('upstream_at', ''))[:16]}) — our usd-fx dataset republishes it as a free public API:",
                link("usd-fx"),
                f"usd-fx USD/EUR={last['rate']} via {src}"))
    for ds in ("crypto-spot", "usd-fx"):
        d = real.get(ds)
        if d and f["published"].get(ds):
            m = f["published"][ds]
            cands.append((f"pub-{ds}",
                f"Fresh API: {ds} — {m.get('count')} verified rows ({', '.join(d['sources'])}) published {str(m.get('at', ''))[:10]}, free JSON. Re-pull the source yourself, numbers match:",
                link(ds), f"published {ds}={m.get('count')} verified rows"))
    if cx or fx:
        latest = max([d["latest_at"] for d in real.values() if d.get("latest_at")],
                       default="")
        cands.append(("freshness",
            f"Last verified fetch {str(latest)[:16]}Z across {len(real)} live datasets ({sum(d['count'] for d in real.values())} rows). Every row carries source + fetched-at — verify any of them:",
            link(sorted(real)[0]),
            f"freshness {latest} {len(real)} live datasets"))
        cands.append(("cta",
            f"These {sum(d['count'] for d in real.values())} rows are collected by a loop, no humans involved. Install the extension, publish YOUR dataset, earn per record:",
            home_link, f"cta over {len(real)} real datasets"))
    s = growth_settings()
    posts = []
    for i, (tpl, text, link, fact) in enumerate(cands[:GROWTH_DAYS]):
        day = (d0 + datetime.timedelta(days=i)).isoformat()
        posts.append({
            "id": f"g-{day}-{tpl}",
            "scheduled_for": day,
            "template": tpl,
            "text": _fit(text, link),
            "link": link,
            "fact": fact,
            "approved": bool(s["auto_approve"]),
            "rejected": False,
            "posted": False,
            "posted_at": None,
        })
    return {"generated_at": day0, "channel": s["channel"],
            "auto_approve": s["auto_approve"], "posts": posts}


def get_growth_queue():
    """Daily-regenerating queue. Carries approved/posted flags forward for
    surviving ids; anything already in the outbox stays posted.
    Loop drafts (source:loop, filed via POST /api/growth/draft) ride
    ALONGSIDE the 7 template posts and survive regeneration until they
    are posted, rejected, or deleted — the builder never invents them
    and never drops them silently."""
    qp, op, _ = growth_paths()
    fresh = build_growth_queue()
    posted_ids = set()
    if os.path.exists(op):
        for r in load_lines(op):
            if isinstance(r, dict) and r.get("id") and r.get("status") in (
                    "dryrun-queued", "posted"):
                posted_ids.add(r["id"])
    old = load_json(qp, None)
    carry = {}
    loop_kept = []
    if isinstance(old, dict) and isinstance(old.get("posts"), list):
        for post in old["posts"]:
            if isinstance(post, dict) and post.get("id"):
                carry[post["id"]] = (bool(post.get("approved")),
                                    bool(post.get("posted")),
                                    bool(post.get("rejected")))
                if post.get("source") == "loop" and not post.get("posted"):
                    # Owner-parked (rejected) loop drafts stay visible;
                    # pending ones stay actionable. Posted ones are history.
                    if post["id"] in posted_ids:
                        post["posted"] = True
                    loop_kept.append(post)
    if isinstance(old, dict) and old.get("generated_at") == fresh["generated_at"]:
        # Same day: facts may have moved — refresh text/link/fact but keep
        # owner state (approvals, rejections, posted flags).
        for post in fresh["posts"]:
            if post["id"] in carry:
                ap, pp, rej = carry[post["id"]]
                post["approved"] = (ap or post["approved"]) and not rej
                post["rejected"] = rej
                post["posted"] = pp
                if pp and not post["posted_at"]:
                    post["posted_at"] = old.get("generated_at")
            if post["id"] in posted_ids:
                post["posted"] = True
        fresh_posts = fresh["posts"]
    else:
        for post in fresh["posts"]:
            if post["id"] in carry and carry[post["id"]][1]:
                post["posted"] = True
                post["posted_at"] = old.get("generated_at")
            if post["id"] in posted_ids:
                post["posted"] = True
        fresh_posts = fresh["posts"]
    fresh["posts"] = fresh_posts
    fresh_ids = {pp.get("id") for pp in fresh_posts if isinstance(pp, dict)}
    for lp in loop_kept:
        if lp.get("id") not in fresh_ids:
            fresh_posts.append(lp)
    save_json(qp, fresh)
    return fresh


def queue_loop_draft(text, link="", fact="", by=""):
    """Draft ONE growth post from the e082 loop. Always unapproved — the
    scheduler only posts approved rows, so human/auto-approve rules decide
    (POST /api/growth/approve). At most one pending loop draft is kept:
    a second draft while one waits returns the waiting one (no queue spam
    from a 60s daemon). Returns (post, error)."""
    if not isinstance(text, str) or not text.strip() or len(text) > 280:
        return None, "text required (string 1..280 chars, X-shaped)"
    for k, v in (("link", link), ("fact", fact)):
        if v is not None and (not isinstance(v, str) or len(v) > 500):
            return None, f"{k} must be a string (max 500 chars)"
    qp, _, _ = growth_paths()
    q = get_growth_queue()
    posts = q.get("posts", [])
    waiting = next((pp for pp in posts
                    if isinstance(pp, dict) and pp.get("source") == "loop"
                    and not pp.get("posted") and not pp.get("rejected")), None)
    if waiting is not None:
        return waiting, None
    day0 = datetime.date.today().isoformat()
    pid = f"loop-{day0}-{secrets.token_hex(2)}"
    post = {"id": pid, "scheduled_for": day0, "template": "loop-note",
            "text": text.strip()[:280], "link": (link or "").strip()[:500],
            "fact": (fact or "").strip()[:500], "source": "loop",
            "by": str(by or "")[:64], "approved": False, "rejected": False,
            "posted": False, "posted_at": None}
    posts.append(post)
    q["posts"] = posts
    save_json(qp, q)
    audit("growth_loop_draft", id=pid, by=str(by or "")[:64])
    return post, None


def delete_loop_draft(pid, by=""):
    """Remove one UNPOSTED loop draft (proof-tick cleanup). Posted rows
    are history and refuse (park them via reject instead)."""
    qp, _, _ = growth_paths()
    q = get_growth_queue()
    posts = q.get("posts", [])
    hit = next((pp for pp in posts if isinstance(pp, dict) and pp.get("id") == pid), None)
    if hit is None:
        return False, "queued post not found"
    if hit.get("posted"):
        return False, "already posted — history, park via reject instead"
    q["posts"] = [pp for pp in posts if pp.get("id") != pid]
    save_json(qp, q)
    audit("growth_loop_draft_deleted", id=pid, by=str(by or "")[:64])
    return True, None


def outbox_ids():
    _, op, _ = growth_paths()
    ids = set()
    for r in load_lines(op):
        if isinstance(r, dict) and r.get("id"):
            ids.add(r["id"])
    return ids


def post_growth_item(post):
    """Poster with provider interface. dryrun logs what WOULD post;
    x_api POSTs via stdlib urllib when the bearer key is present.
    Idempotent via outbox dedupe. Never invents credentials, never posts
    without a configured backend."""
    qp, op, _ = growth_paths()
    s = growth_settings()
    pid = post.get("id", "")
    if pid in outbox_ids():
        return {"ok": True, "id": pid, "backend": "dedupe",
                "status": "already-in-outbox", "posted": False}
    text = post.get("text", "")
    if s["channel"] == "x_api":
        tok = secret("x_bearer_token")
        if not tok:
            return {"ok": False, "id": pid, "backend": "x_api",
                    "status": "misconfigured",
                    "error": ("growth_channel=x_api but no X bearer is stored "
                              "(Owner panel → paste key) — nothing was posted.")}
        try:
            import urllib.request as _rq
            body = json.dumps({"text": text}).encode()
            req = _rq.Request("https://api.x.com/2/tweets", data=body,
                              headers={"Authorization": "Bearer " + tok,
                                       "Content-Type": "application/json"},
                              method="POST")
            with _rq.urlopen(req, timeout=15) as r:
                resp = json.loads(r.read(100000).decode("utf-8", "replace"))
            entry = {"at": now_iso(), "id": pid, "backend": "x_api",
                     "status": "posted", "text": text,
                     "x_id": str(resp.get("data", {}).get("id", ""))}
            append_line(op, entry)
            return {"ok": True, "id": pid, "backend": "x_api",
                    "status": "posted", "posted": True, "x": resp}
        except Exception as e:
            return {"ok": False, "id": pid, "backend": "x_api",
                    "status": "post-failed", "posted": False,
                    "error": str(e)[:300]}
    # dryrun (default): prove the full loop with zero accounts.
    append_line(op, {"at": now_iso(), "id": pid, "backend": "dryrun",
                     "status": "dryrun-queued", "text": text,
                     "link": post.get("link", ""),
                     "would_post_to": "X API v2 (set growth_channel=x_api + x_bearer_token to go live)"})
    return {"ok": True, "id": pid, "backend": "dryrun",
            "status": "dryrun-queued", "posted": True}


def growth_tick(today=None):
    """Scheduler tick: regenerate queue -> post the due item -> log result
    to data/growth.jsonl. Due = earliest scheduled_for <= today that is
    approved and not posted. Returns the tick record."""
    qp, _, gp = growth_paths()
    q = get_growth_queue()
    day0 = today or datetime.date.today().isoformat()
    due = [p for p in q["posts"]
           if p.get("scheduled_for", "") <= day0
           and p.get("approved") and not p.get("rejected")
           and not p.get("posted")]
    due.sort(key=lambda p: p.get("scheduled_for", ""))
    if not due:
        rec = {"at": now_iso(), "day": day0, "status": "nothing-due",
               "backend": growth_settings()["channel"],
               "queued": len(q["posts"]),
               "posted_count": sum(1 for p in q["posts"] if p.get("posted"))}
        append_line(gp, rec)
        return rec
    post = due[0]
    res = post_growth_item(post)
    if res.get("posted"):
        post["posted"] = True
        post["posted_at"] = now_iso()
        post["post_result"] = {k: res.get(k) for k in ("backend", "status")}
        save_json(qp, q)
    rec = {"at": now_iso(), "day": day0, "id": post["id"],
           "scheduled_for": post.get("scheduled_for"), **res,
           "queued": len(q["posts"])}
    append_line(gp, rec)
    return rec


def growth_stats(include_test=False):
    """The only number that matters: posts -> visits -> signups -> paid.
    HONEST by default: test/agent signups and visits are excluded (a real
    zero beats a fake 14); ?include_test=1 audits them. Growth-attributed
    visits = telemetry events citing the growth ref (dataset pages carry
    ?ref=growth and beacon it); signups = accounts with referred_by=growth;
    paid = ledger net (paywall flag included so the card is honest about
    real money vs test tokens)."""
    test_ids = set() if include_test else test_node_ids()
    q = get_growth_queue()
    _, op, gp = growth_paths()
    outbox = load_lines(op)
    ticks = load_lines(gp)
    growth_visits = 0
    for e in load_events():
        blob = f"{e.get('event', '')} {e.get('detail', '')}".lower()
        if GROWTH_REF in blob and not e.get("synthetic") \
                and not e.get("agent") \
                and not is_bot_session(str(e.get("session", ""))):
            growth_visits += 1
    db = auth_db()
    accts = db.get("nodes", {}) if isinstance(db, dict) else {}
    growth_signups = sum(1 for nid, a in accts.items()
                         if isinstance(a, dict)
                         and a.get("referred_by") == GROWTH_REF
                         and nid not in test_ids)
    e = earnings()
    totals = e.get("totals", {}) or {}
    c = cfg()
    posts = q.get("posts", [])
    nxt = next((p for p in sorted(posts, key=lambda x: x.get("scheduled_for", ""))
                if not p.get("posted")), None)
    last = outbox[-1] if outbox else None
    return {
        "posts_total": len(posts),
        "posts_posted": sum(1 for p in posts if p.get("posted")),
        "posts_approved": sum(1 for p in posts if p.get("approved")),
        "loop_drafts": sum(1 for p in posts if p.get("source") == "loop"),
        "loop_pending": sum(1 for p in posts if p.get("source") == "loop"
                           and not p.get("posted") and not p.get("rejected")),
        "last_post": ({k: last.get(k) for k in
                         ("at", "id", "backend", "status", "text")}
                        if isinstance(last, dict) else None),
        "ticks": len(ticks),
        "growth_visits": growth_visits,
        "growth_signups": growth_signups,
        "paid_net": totals.get("net", 0.0),
        "paid_token": e.get("token", "SCRAPE"),
        "paywall_live": bool((c.get("paywall_endpoint", "") or "").strip()),
        "channel": growth_settings()["channel"],
        "auto_approve": growth_settings()["auto_approve"],
        "next_run": (nxt or {}).get("scheduled_for"),
        "next_post_id": (nxt or {}).get("id"),
        "interval_sec": growth_settings()["interval_sec"],
        "generated_at": q.get("generated_at"),
    }


def brief():
    """Public hero data: ONE headline number (the alive one), the plain-
    language away-line, and the counts the single next-action button needs.
    No secrets, no tokens — safe for strangers."""
    c = cfg()
    day = utc_day()
    tok = c.get("payout_token_symbol", "SCRAPE")
    try:
        rate = float(c.get("payout_per_record", 0.01) or 0)
    except (TypeError, ValueError):
        rate = 0.01
    db = auth_db()
    accts = db.get("nodes", {}) if isinstance(db, dict) else {}
    signups_today = sum(1 for nid, a in accts.items()
                        if isinstance(a, dict)
                        and str(a.get("created", ""))[:10] == day
                        and nid not in test_node_ids()
                        and not _matches_test(a.get("name", "")))
    tids = test_node_ids()
    rows = [r for r in load_lines(p("records_path", "data/records.jsonl"))
            if r.get("node_id") not in tids]
    rec_today = sum(1 for r in rows if str(r.get("at", ""))[:10] == day)
    earned_today = round(rec_today * rate, 4)
    _, op, _ = growth_paths()
    outbox = load_lines(op)
    posts_out = sum(1 for o in outbox
                    if isinstance(o, dict)
                    and o.get("status") in ("posted", "dryrun-queued"))
    visits = sum(1 for e in load_events()
                 if e.get("event") == "page_view" and not e.get("synthetic")
                 and not e.get("agent"))
    e = earnings()
    paid = (e.get("totals", {}) or {}).get("referral_paid", 0.0)
    if earned_today > 0:
        headline = {"kind": "earned", "value": earned_today,
                    "unit": tok, "label": "earned today"}
    elif signups_today > 0:
        headline = {"kind": "signups", "value": signups_today,
                    "unit": "people", "label": "joined today"}
    else:
        headline = {"kind": "rows", "value": len(rows),
                    "unit": "rows", "label": "live on the hub"}
    post_word = "post" if posts_out == 1 else "posts"
    person_word = "person" if visits == 1 else "people"
    return {
        "headline": headline,
        "away_line": (f"While you were away: {posts_out} {post_word} "
                        f"went out, {visits} {person_word} visited, "
                        f"{paid} {tok} paid."),
        "signups_today": signups_today,
        "records_today": rec_today,
        "earned_today": earned_today,
        "posts_out": posts_out,
        "visits": visits,
        "paid": paid,
        "token": tok,
    }


def owner_status():
    """Masked owner dashboard: booleans and counts only — secret VALUES
    never leave the server (write-only fields on the page)."""
    c = cfg()
    s = growth_settings()
    q = get_growth_queue()
    posts = q.get("posts", [])
    _, op, _ = growth_paths()
    outbox = [o for o in load_lines(op) if isinstance(o, dict)][-10:]
    intents = [r for r in load_lines(intents_path())]
    pending_intents = []
    for i, r in enumerate(intents):
        if not isinstance(r, dict) or intent_decision_for(i):
            continue
        pending_intents.append({"index": i, "at": r.get("at", ""),
                                "node_id": r.get("node_id", ""),
                                "tier": r.get("tier", ""),
                                "provider": r.get("provider", ""),
                                "price_usd": r.get("price_usd")})
    lb = leaderboard()
    pending_payouts = [{"node_id": l["node_id"], "name": l["name"],
                        "code": l["referral_code"],
                        "credit": l["referral_credit"],
                        "status": l["payout_status"],
                        "token": l["token"]}
                       for l in lb.get("leaders", [])
                       if l.get("referral_credit", 0) > 0]
    t = tiers_cfg()
    return {
        "ok": True,
        "channel": s["channel"],
        "auto_approve": s["auto_approve"],
        "bearer_set": bool(secret("x_bearer_token")),
        "stripe_set": bool(secret("stripe_secret")),
        "stripe_webhook_set": bool(secret("stripe_webhook_secret")),
        "tiers": {
            "free": {"api_calls_per_day": quota_limit("free"),
                       "datasets": int(t.get("free", {}).get("datasets", 1))},
            "pro": {"price_usd": t.get("pro", {}).get("price_usd", 9),
                      "api_calls_per_day": quota_limit("pro"),
                      "datasets": int(t.get("pro", {}).get("datasets", 50)),
                      "note": t.get("pro", {}).get("note", "")},
        },
        "queue": {
            "total": len(posts),
            "posted": sum(1 for x in posts if x.get("posted")),
            "pending": [{"id": x["id"],
                           "scheduled_for": x.get("scheduled_for", ""),
                           "text": x.get("text", ""),
                           "template": x.get("template", "")}
                          for x in posts
                          if not x.get("approved") and not x.get("rejected")
                          and not x.get("posted")],
            "rejected": sum(1 for x in posts if x.get("rejected")),
        },
        "outbox": [{"at": o.get("at", ""), "id": o.get("id", ""),
                      "backend": o.get("backend", ""),
                      "status": o.get("status", ""),
                      "text": str(o.get("text", ""))[:200]} for o in outbox],
        "intents_pending": pending_intents,
        "payouts_pending": pending_payouts,
        "payout_threshold": lb.get("payout", {}).get("threshold", 5.0),
    }


# ---- paywall + metered API (PAYWALL 2026-09-29) ----
# Tiers live in needs.json ("tiers"). Free quota is enforced per token on
# GET /api/public/* + GET /api/records via UTC day buckets in
# data/usage.json. Token requests count against the node's bucket;
# anonymous browser reads share the "anon" bucket; bot/CI user-agents
# (curl, urllib, probes) are EXEMPT so monitors never trip the paywall
# (documented bypass: curl without a token reads free — see report).
# Upgrade = provider interface: "manual" (default: contact-to-activate +
# intent logged to data/intents.jsonl, human flips the tier) or "stripe"
# (live the moment needs.json stripe_secret is set: real Checkout Session
# via stdlib urllib, webhook flips the tier after signature check).
# Money movement stays human-approved: the webhook only flips the tier
# flag; referral payouts still need manual review (leaderboard "payout").

_UQ_LOCK = threading.Lock()


def tiers_cfg():
    c = cfg()
    t = c.get("tiers")
    if not isinstance(t, dict) or "free" not in t:
        return {"free": {"api_calls_per_day": 100, "datasets": 1,
                           "price_usd": 0},
                "pro": {"api_calls_per_day": 10000, "datasets": 50,
                          "price_usd": 9}}
    return t


def tier_of(name):
    t = tiers_cfg()
    n = (name or "free").lower() if isinstance(name, str) else "free"
    return n if n in t else "free"


def node_tier(node_id):
    db = auth_db()
    a = db.get("nodes", {}).get(node_id, {}) if isinstance(db, dict) else {}
    return tier_of(a.get("tier") if isinstance(a, dict) else None)


def set_node_tier(node_id, tier):
    db = auth_db()
    a = db.get("nodes", {}).get(node_id) if isinstance(db, dict) else None
    if not isinstance(a, dict):
        return False
    a["tier"] = tier_of(tier)
    save_auth(db)
    return True


def usage_path():
    return p("usage_path", "data/usage.json")


def intents_path():
    return p("intents_path", "data/intents.jsonl")


def utc_day():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def resets_at_iso():
    nxt = datetime.datetime.now(datetime.timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    return nxt.isoformat(timespec="seconds")


def load_usage():
    u = load_json(usage_path(), {})
    if not isinstance(u, dict):
        u = {}
    if u.get("day") != utc_day():
        u = {"day": utc_day(), "buckets": {}}
    if not isinstance(u.get("buckets"), dict):
        u["buckets"] = {}
    return u


def save_usage(u):
    try:
        save_json(usage_path(), u)
    except Exception:
        pass


def quota_limit(tier):
    try:
        return int(tiers_cfg()[tier_of(tier)].get("api_calls_per_day", 100))
    except (TypeError, ValueError):
        return 100


def quota_status(key, tier):
    u = load_usage()
    used = int(u.get("buckets", {}).get(key, 0) or 0)
    lim = quota_limit(tier)
    return {"used": used, "limit": lim, "left": max(0, lim - used),
            "resets_at": resets_at_iso()}


def quota_hit(key, tier):
    with _UQ_LOCK:
        u = load_usage()
        b = u.setdefault("buckets", {})
        b[key] = int(b.get(key, 0) or 0) + 1
        save_usage(u)
    return quota_status(key, tier)


def token_owner(tok):
    if not tok:
        return ""
    h = token_hash(tok)
    db = auth_db()
    for nid, a in (db.get("nodes", {}) or {}).items():
        if isinstance(a, dict) and a.get("token_sha256") == h:
            return nid
    return ""


def caller_identity(headers, query):
    tok = ""
    auth = (headers.get("Authorization") or headers.get("authorization") or "")
    if auth.lower().startswith("bearer "):
        tok = auth[7:].strip()
    if not tok and query:
        vals = query.get("token", []) + query.get("auth_token", [])
        tok = next((v.strip() for v in vals
                    if isinstance(v, str) and v.strip()), "")
    if tok:
        nid = token_owner(tok)
        if nid:
            return "node:" + nid, node_tier(nid)
    return "anon", "free"


def quota_headers(key, tier, qs):
    return {"X-Quota-Tier": tier, "X-Quota-Used": str(qs["used"]),
            "X-Quota-Left": str(qs["left"]),
            "X-Quota-Resets-At": qs["resets_at"]}


def paywall_body(used, lim, resets_at, tier):
    t = tiers_cfg()
    pro = t.get("pro", {}) if isinstance(t.get("pro"), dict) else {}
    free = t.get("free", {}) if isinstance(t.get("free"), dict) else {}
    return {
        "error": (f"quota exhausted: {used}/{lim} API calls used today on "
                    f"the {tier} tier \u2014 resets {resets_at}"),
        "tier": tier, "quota_used": used, "quota_limit": lim,
        "resets_at": resets_at,
        "free": {"api_calls_per_day": quota_limit("free"),
                 "datasets": free.get("datasets", 1)},
        "pro": {"price_usd": pro.get("price_usd", 9),
                "api_calls_per_day": pro.get("api_calls_per_day", 10000),
                "datasets": pro.get("datasets", 50),
                "note": pro.get("note", "")},
        "upgrade": {
            "checkout": ("POST /api/checkout {\"node_id\": ..., "
                         "\"token\": ..., \"tier\": \"pro\"}"),
            "hint": (f"Free gives {quota_limit('free')} calls/day + "
                       f"{free.get('datasets', 1)} dataset(s). Pro "
                       f"(${pro.get('price_usd', 9)}/mo) gives "
                       f"{pro.get('api_calls_per_day', 10000)} calls/day + "
                       f"{pro.get('datasets', 50)} datasets.")},
    }


def meter_allow(headers, query):
    """Quota gate for metered reads. Returns (key, tier, quota, blocked):
    blocked is None when allowed (the hit is already counted). Token
    requests always count (even from curl, so usage is honest); anonymous
    bot/CI traffic is fully exempt so monitors never trip the paywall."""
    ua = headers.get("User-Agent", "") or ""
    key, tier = caller_identity(headers, query or {})
    qs = quota_status(key, tier)
    if qs["used"] >= qs["limit"] and not is_bot_ua(ua):
        return key, tier, qs, paywall_body(qs["used"], qs["limit"],
                                           qs["resets_at"], tier)
    if key == "anon" and is_bot_ua(ua):
        return key, tier, qs, None
    return key, tier, quota_hit(key, tier), None


def checkout_provider():
    if secret("stripe_secret"):
        return "stripe"
    return "manual"


def manual_checkout(node_id, tier):
    """Default backend: contact-to-activate. Never a dead end — the buyer
    gets a working contact link and the intent lands in intents.jsonl + audit
    for a human to approve (tier flip is manual, within 24h)."""
    c = cfg()
    t = tiers_cfg()
    intent = {"at": now_iso(), "node_id": node_id, "tier": tier,
              "provider": "manual",
              "price_usd": t[tier].get("price_usd", 9)}
    append_line(intents_path(), intent)
    audit("checkout_intent", node_id=node_id, tier=tier, provider="manual")
    base = (c.get("support_url") or "").strip()
    text = urllib.parse.quote(
        f"ScrapeNet Pro activation for node {node_id} (tier {tier})")
    url = (base + ("?text=" if "?" not in base else "&text=") + text
           if base else "")
    return {
        "status": "pending_manual", "provider": "manual", "tier": tier,
        "price_usd": t[tier].get("price_usd", 9),
        "checkout_url": url,
        "contact": c.get("support_contact", ""),
        "message": ("Contact to activate: open the link and send the "
                      "pre-filled request. A human approves within 24h and "
                      "flips your tier to pro \u2014 nothing is charged "
                      "automatically."),
        "intent_logged": True,
    }


def stripe_checkout_session(node_id, tier):
    """Real Stripe Checkout Session via stdlib urllib (no SDK). Raises on
    transport/API errors — the caller turns that into a 502."""
    import urllib.request as _rq
    c = cfg()
    t = tiers_cfg()
    if tier not in t or tier == "free":
        raise ValueError("unknown paid tier: %r" % (tier,))
    sk = secret("stripe_secret")
    if not sk:
        raise ValueError("stripe not configured (no secret stored — Owner panel)")
    amount = int(float(t[tier].get("price_usd", 9)) * 100)
    base = (c.get("public_url") or "").strip().rstrip("/")
    fields = {
        "mode": "subscription",
        "success_url": base + "/dataset/product-prices?paid=1",
        "cancel_url": base + "/?cancelled=1",
        "client_reference_id": node_id,
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][unit_amount]": str(amount),
        "line_items[0][price_data][recurring][interval]": "month",
        "line_items[0][price_data][product_data][name]": (
            "ScrapeNet %s" % tier.capitalize()),
    }
    data = urllib.parse.urlencode(fields).encode()
    req = _rq.Request("https://api.stripe.com/v1/checkout/sessions",
                      data=data,
                      headers={"Authorization": "Bearer " + sk,
                               "Content-Type":
                               "application/x-www-form-urlencoded"})
    with _rq.urlopen(req, timeout=20) as r:
        sess = json.loads(r.read().decode("utf-8", "replace"))
    if not isinstance(sess, dict) or not sess.get("url"):
        raise ValueError("stripe error: %s" % json.dumps(sess)[:300])
    return sess


def verify_stripe_sig(raw, header, secret):
    """Stripe-Signature check (t=..,v1=.. HMAC-SHA256). stdlib hmac."""
    import hmac as _hm
    if not secret or not header or not raw:
        return False
    try:
        parts = dict(kv.split("=", 1) for kv in header.split(",")
                     if "=" in kv)
        mac = _hm.new(secret.encode(),
                      parts.get("t", "").encode() + b"." + raw,
                      hashlib.sha256).hexdigest()
        return bool(parts.get("v1")) and secrets.compare_digest(
            mac, parts["v1"])
    except Exception:
        return False


def esc_html(s):
    return str(s if s is not None else "").replace("&", "&amp;"
        ).replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_dataset_page(ds, ref="", include_test=False):
    """Shareable human page for one dataset (the UGC engine): stats, sample
    rows, copy-API-link + subscribe buttons, referral attribution via ?ref=.
    HONEST by default: test/agent rows are hidden (real zero beats fake 14);
    ?include_test=1 audits them. Rows carrying source+fetched_at render a
    REAL-DATA provenance banner (origin + latest fetch) so every cited fact
    is re-pullable by anyone."""
    c = cfg()
    pub = published(include_test=include_test).get(ds)
    tids = set() if include_test else test_node_ids()
    rows = [r for r in load_lines(p("records_path", "data/records.jsonl"))
            if r.get("dataset") == ds and r.get("node_id") not in tids]
    if not pub and not rows:
        if include_test:
            return None
        # Honest zero, not a 404 lie: test/agent rows may exist under
        # ?include_test=1 — fall through to the empty page with the door open.
        any_rows = [r for r in load_lines(
            p("records_path", "data/records.jsonl"))
            if r.get("dataset") == ds]
        if not any_rows:
            return None
    fields = []
    for r in rows[:50]:
        rec = r.get("record", {})
        if isinstance(rec, dict):
            for k in rec:
                if k not in fields:
                    fields.append(k)
    nodes = sorted({r.get("node_id", "?") for r in rows})
    sample = rows[-10:]
    count = pub["count"] if pub else len(rows)
    at = pub["at"] if pub else (rows[-1].get("at", "") if rows else "")
    ref = (ref or "").strip().upper()[:16]
    ref_note = (f"<p class='ref'>You arrived via referral code <b>{esc_html(ref)}</b> — "
                f"use it at signup and your inviter earns a cut of your records. "
                f"<a href='/?ref={esc_html(ref)}'>Join ScrapeNet</a></p>" if ref else
                "")
    if sample:
        cols = fields[:6]
        trs = []
        for r in reversed(sample):
            rec = r.get("record", {}) if isinstance(r.get("record"), dict) else {}
            trs.append("<tr>" + "".join(
                f"<td>{esc_html(rec.get(k, ''))}</td>" for k in cols) + "</tr>")
        table = (f"<table><tr>{''.join(f'<th>{esc_html(k)}</th>' for k in cols)}</tr>"
                 + "".join(trs) + "</table>")
    else:
        table = "<p class='mut'>No rows yet.</p>"
    api_path = f"/api/public/{esc_html(ds)}"
    t = tiers_cfg()
    free = t.get("free", {}) if isinstance(t.get("free"), dict) else {}
    pro = t.get("pro", {}) if isinstance(t.get("pro"), dict) else {}
    pub_banner = (f"<p>Published {esc_html(at)} · {esc_html(count)} records · "
                    f"<a href='{api_path}'>raw JSON API</a></p>" if pub else
                  "<p class='mut'>Not published yet — showing live preview of contributed rows.</p>")
    # REAL-DATA provenance: origins + latest fetch over honest rows.
    prov_sources, prov_latest = set(), ""
    for r in rows:
        rec = r.get("record", {})
        if isinstance(rec, dict) and rec.get("source") and rec.get("fetched_at"):
            prov_sources.add(str(rec["source"]))
            if str(rec["fetched_at"]) > prov_latest:
                prov_latest = str(rec["fetched_at"])
    if prov_sources:
        prov_banner = (f"<p class='ref'>REAL DATA · source(s): "
                       f"{esc_html(', '.join(sorted(prov_sources)))} · latest fetch "
                       f"{esc_html(prov_latest)} — re-pull the source yourself, numbers match.</p>")
    elif not include_test:
        prov_banner = ("<p class='mut'>Counts exclude test/agent traffic "
                       "(<a href='?include_test=1'>audit with ?include_test=1</a>).</p>")
    else:
        prov_banner = "<p class='mut'>Audit view: test/agent rows included.</p>"
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{esc_html(ds)} — ScrapeNet dataset</title>"
            "<style>body{font-family:system-ui,sans-serif;max-width:860px;margin:0 auto;"
            "padding:16px;background:#0d1117;color:#e6edf3;font-size:15px}"
            ".card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;margin:12px 0}"
            ".mut{color:#8b949e;font-size:13px}.ref{background:#1c2b1c;border:1px solid #3fb950;"
            "border-radius:10px;padding:10px}"
            "table{width:100%;border-collapse:collapse;font-size:13px}td,th{text-align:left;"
            "padding:6px;border-top:1px solid #30363d;word-break:break-word}"
            "button{background:#58a6ff;border:1px solid #58a6ff;color:#001;font-weight:700;"
            "border-radius:8px;padding:9px 14px;margin:4px 6px 4px 0;cursor:pointer;font-size:14px}"
            "input{font-size:14px;border-radius:8px;border:1px solid #30363d;background:#0d1117;"
            "color:#e6edf3;padding:8px;width:100%;margin:4px 0}"
            "a{color:#58a6ff}code{background:#0d1117;padding:2px 6px;border-radius:6px}</style></head><body>"
            f"<p class='mut'><a href='/'>ScrapeNet</a> · public dataset</p><h1>{esc_html(ds)}</h1>"
            f"{ref_note}<div class='card'>{pub_banner}{prov_banner}"
            f"<p class='mut'>{esc_html(len(rows))} contributed rows · "
            f"{esc_html(len(nodes))} nodes · fields: {esc_html(', '.join(fields[:12]))}</p>"
            f"<p><code id='api'>" + api_path + "</code></p>"
            "<p><button onclick=\"navigator.clipboard.writeText(location.origin+"
            "document.getElementById('api').textContent);this.textContent='Copied!';\">"
            "Copy API link</button> "
            "<button onclick=\"navigator.clipboard.writeText('curl '+location.origin+"
            "document.getElementById('api').textContent);this.textContent='Copied curl!';\">"
            "Subscribe: copy curl</button></p>"
            "<p class='mut'>Subscribe = poll the API URL (free, public). Paste the curl in a terminal; re-run to get fresh rows.</p></div>"
            "<div class='card'><h2>Sample rows</h2>" + table + "</div>"
            "<div class='card'><h2>Publish your own data, earn per record</h2>"
            "<p class='mut'>1) Install the extension 2) scrape a site 3) publish — your dataset gets a page like this one.</p>"
            f"<p><a href='/download/extension.zip'><button>Install extension</button></a> "
            f"<a href='/?ref={esc_html(ref)}'><button>Sign up" + (" (ref " + esc_html(ref) + ")" if ref else "") + "</button></a></p></div>"
            "<script>(function(){try{var m=new URLSearchParams(location.search).get('ref');"
            "if(!m)return;var s='g'+Math.random().toString(16).slice(2,10);"
            "fetch('/api/events',{method:'POST',headers:{'Content-Type':'application/json'},"
            "body:JSON.stringify({v:1,session:s,ts:Date.now(),page:location.pathname,"
            "event:'click:ref-'+m.toUpperCase().slice(0,16),detail:m.toUpperCase().slice(0,16)})"
            "}).catch(function(){});}catch(e){}})();</script>"
            f"<div class='card'><h2>API plan \u2014 Free {esc_html(free.get('api_calls_per_day', 100))}/day \u00b7 Go Pro ${esc_html(pro.get('price_usd', 9))}/mo</h2>"
            f"<p class='mut'>Free: {esc_html(free.get('api_calls_per_day', 100))} API calls/day + {esc_html(free.get('datasets', 1))} dataset. "
            f"Pro (${esc_html(pro.get('price_usd', 9))}/mo): {esc_html(pro.get('api_calls_per_day', 10000))} calls/day + {esc_html(pro.get('datasets', 50))} datasets. {esc_html(pro.get('note', ''))}</p>"
            "<div id='quota' class='mut'>Sign up on the dashboard to see your live quota here (your token unlocks it).</div>"
            f"<p><button id='bGoPro'>Go Pro ${esc_html(pro.get('price_usd', 9))}/mo</button> <span class='mut' id='coMsg'></span></p></div>"
            "<script>(function(){var n=localStorage.getItem('sn_node')||'',t=localStorage.getItem('sn_token')||'';"
            "function q(id){return document.getElementById(id);}"
            "if(n&&t){fetch('/api/me?node_id='+encodeURIComponent(n)+'&token='+encodeURIComponent(t)).then(function(r){return r.json();}).then(function(m){"
            "if(m&&!m.error){q('quota').textContent=m.quota_used+'/'+m.quota_limit+' calls used \u2014 '+m.quota_left+' left today ('+m.tier+', resets '+m.resets_at+').';}}).catch(function(){});}"
            "var b=q('bGoPro');if(b){b.onclick=function(){if(!n||!t){q('coMsg').textContent='Sign up on the dashboard first \u2014 your token unlocks checkout.';return;}"
            "fetch('/api/checkout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({node_id:n,token:t,tier:'pro'})}).then(function(r){return r.json();}).then(function(j){"
            "if(j.checkout_url){q('coMsg').innerHTML='';var a=document.createElement('a');a.href=j.checkout_url;a.target='_blank';a.rel='noopener';a.textContent=(j.status==='stripe'?'Pay with Stripe':'Activate ('+j.status+')');q('coMsg').appendChild(a);q('coMsg').appendChild(document.createTextNode(' \u2014 '+(j.message||j.note||'')));}"
            "else{q('coMsg').textContent='error: '+JSON.stringify(j);}}).catch(function(e){q('coMsg').textContent='error: '+e;});};}})();</script>"
            "</body></html>")


# ---- BUSINESS SPAWNER (one-button business, stdlib composition) ----
# POST /api/businesses/spawn {niche | idea_id} runs the full composition
# server-side, reusing the primitives that already exist:
#   dataset scaffold (ingest seed rows as the caller) -> recipe (propose_recipe,
#   the same builder behind POST /api/generate) -> publish (same tier-cap
#   + snapshot logic as POST /api/publish) -> default tier (free quota via
#   the shared metering engine + pro upsell from tiers_cfg) -> 7 niche growth
#   posts (same _fit/link/?ref= scheme as the growth engine) -> owner referral
#   code (the caller's own code from auth_db).
# Guards: strict token auth (legacy carve-out does NOT apply — a business
# needs a real account), niche <=120 chars, duplicate normalized niche ->
# 409, spawn_max_per_hour per owner -> 429.
# GET /api/businesses lists with LIVE per-business stats (records counted
# from records.jsonl, calls from the business_calls counter bumped on every
# served GET /api/public/<dataset>, signups/revenue from live auth/earnings).
# GET /api/businesses/suggest derives 3 spawnable niches from live data gaps.
# DELETE /api/businesses/<id> (owner only): unpublish + snapshot delete,
# recipe delete, owner seed-row delete, posts dequeued (they live on the
# business record), calls counter dropped. Nothing stubbed.

def _biz_paths():
    return (p("businesses_path", "data/businesses.json"),
            p("business_spawns_path", "data/business_spawns.jsonl"),
            p("business_calls_path", "data/business_calls.json"))


def load_businesses():
    bp, _, _ = _biz_paths()
    d = load_json(bp, {})
    return d if isinstance(d, dict) else {}


def save_businesses(d):
    bp, _, _ = _biz_paths()
    save_json(bp, d)


def load_business_calls():
    _, _, cp = _biz_paths()
    d = load_json(cp, {})
    return d if isinstance(d, dict) else {}


def save_business_calls(d):
    _, _, cp = _biz_paths()
    save_json(cp, d)


def bump_business_calls(dataset):
    """Count one served public read against the owning business (if any)."""
    try:
        for bid, b in load_businesses().items():
            if isinstance(b, dict) and b.get("dataset_id") == dataset:
                calls = load_business_calls()
                calls[bid] = int(calls.get(bid, 0) or 0) + 1
                save_business_calls(calls)
                return
    except Exception:
        pass


def slugify_niche(niche):
    s = re.sub(r"[^a-z0-9]+", "-", (niche or "").lower()).strip("-")
    return (s[:48] or "niche")


def norm_niche(niche):
    return re.sub(r"\s+", " ", (niche or "").strip().lower())


def spawn_rate_left(owner):
    """Successful spawns by owner in the last 3600s vs needs.json cap."""
    c = cfg()
    try:
        cap = int(c.get("spawn_max_per_hour", 3))
    except (TypeError, ValueError):
        cap = 3
    _, sp, _ = _biz_paths()
    cutoff = time.time() - 3600
    n = 0
    for r in load_lines(sp):
        try:
            if r.get("owner") == owner and r.get("ts", 0) >= cutoff:
                n += 1
        except Exception:
            pass
    return max(0, cap - n), cap


def resolve_idea(idea_id, dataset_hint=""):
    """idea_id formats: '<dataset>:<index>' (index into /api/ideas for that
    dataset) or an idea title (case-insensitive substring match across the
    busiest datasets). Returns (niche, dataset, idea) or (None, err)."""
    raw = (idea_id or "").strip()
    if not raw:
        return None, "idea_id required (format '<dataset>:<index>' or an idea title)"
    if ":" in raw:
        ds, _, idx = raw.rpartition(":")
        ds, idx = ds.strip(), idx.strip()
        try:
            i = int(idx)
        except (TypeError, ValueError):
            return None, "idea index must be an integer (got %r)" % idx[:32]
        if not ds or not DS_RE.fullmatch(ds):
            return None, "bad dataset in idea_id (use '<dataset>:<index>')"
        fields, _ = dataset_fields(ds)
        ideas = suggest_ideas(fields, ds)
        if not 0 <= i < len(ideas):
            return None, "idea index out of range (0..%d for %s)" % (len(ideas) - 1, ds)
        idea = ideas[i]
        return idea["title"][:120], ds, idea
    # title lookup across the busiest datasets + global fallback
    rows = load_lines(p("records_path", "data/records.jsonl"))
    per = {}
    for r in rows:
        per[r.get("dataset", "")] = per.get(r.get("dataset", ""), 0) + 1
    cands = [d for d, _ in sorted(per.items(), key=lambda x: -x[1])[:5]] or [dataset_hint or "product-prices"]
    low = raw.lower()
    for ds in cands:
        fields, _ = dataset_fields(ds)
        for idea in suggest_ideas(fields, ds):
            if low in idea["title"].lower() or idea["title"].lower() in low:
                return idea["title"][:120], ds, idea
    return None, "no idea matches %r (try '<dataset>:<index>' from POST /api/ideas)" % raw[:64]


def _seed_val(field, niche, slug, i):
    f = (field or "").lower()
    if f in ("price", "amount", "cost", "last"):
        return round(9.99 + i * 5.5, 2)
    if f == "currency":
        return "USD"
    if f in ("url", "link"):
        return "https://example.com/%s/%d" % (slug, i)
    if f in ("symbol", "pair"):
        return "EXAMPLE/USD"
    if f in ("at", "date", "created"):
        return now_iso()
    if f == "company":
        return "Example Co %d" % i
    if f == "location":
        return "remote"
    if f == "source":
        return "spawner"
    if f in ("title", "name"):
        return "%s sample %d" % (niche, i)
    return "%s %d" % (field, i)


def build_biz_posts(bid, niche, name, ds, refcode, base):
    """7 niche growth posts reusing the growth engine's _fit/link/?ref=
    scheme. Stored on the business record (dequeuing = deleting them)."""
    link = ("%s/dataset/%s?ref=%s" % (base, ds, refcode) if base
            else "/dataset/%s?ref=%s" % (ds, refcode))
    home = ("%s/?ref=%s" % (base, refcode) if base else "/?ref=%s" % refcode)
    cands = [
        ("launch", "New API: %s — live %s data as free JSON, spawned in one click on ScrapeNet:" % (name, niche), link, "launch %s" % ds),
        ("how", "How it works: extension scrapes, recipe transforms, published API. This niche (%s) took one button:" % niche, link, "one-button %s" % ds),
        ("data", "%s opens with 3 seeded rows across its schema — every new scrape earns per record. First rows live here:" % name, link, "3 seed rows"),
        ("referral", "Every dataset page is a landing page: share it with YOUR ?ref= code and earn 20%% of the platform commission. This one pays its owner:" % (), link, "referral loop"),
        ("api", "Developers: free JSON at the API URL, free-tier quota daily, Pro $9/mo for 10k calls/day. %s is open:" % name, link, "metered API"),
        ("ask", "What would YOU build on %s data? Reply with your use case — the first consumer gets featured:" % niche, home, "open ask"),
        ("cta", "Turn any niche into a paid API in one click. Start from this live one:" % (), link, "spawn CTA"),
    ]
    s = growth_settings()
    posts = []
    for n, (tpl, text, lnk, fact) in enumerate(cands, 1):
        posts.append({"id": "%s-p%d" % (bid, n), "template": tpl,
                        "text": _fit(text, lnk), "link": lnk, "fact": fact,
                        "approved": bool(s["auto_approve"]), "posted": False,
                        "posted_at": None})
    return posts


def business_live_stats(b):
    """Live stats for one business record (nothing cached, all counted now)."""
    ds = b.get("dataset_id", "")
    owner = b.get("owner", "")
    recs = [r for r in load_lines(p("records_path", "data/records.jsonl"))
              if r.get("dataset") == ds]
    calls = load_business_calls().get(b.get("business_id", ""), 0)
    db = auth_db()
    accts = db.get("nodes", {}) if isinstance(db, dict) else {}
    signups = sum(1 for nid, a in accts.items()
                    if isinstance(a, dict) and a.get("referred_by") == owner)
    earn = earnings(include_test=True)
    mine = next((n for n in earn["nodes"] if n["node_id"] == owner), {})
    return {"records": len(recs),
            "calls": int(calls or 0),
            "signups": signups,
            "revenue": mine.get("referral_earnings", 0.0),
            "revenue_token": earn.get("token", "SCRAPE")}


def suggest_spawn_niches():
    """Top-3 spawnable niches derived from LIVE data gaps (never hardcoded
    copy — every 'why' cites a number counted above it)."""
    rows = load_lines(p("records_path", "data/records.jsonl"))
    per, per_nodes = {}, {}
    for r in rows:
        ds = r.get("dataset", "unknown")
        per[ds] = per.get(ds, 0) + 1
        per_nodes.setdefault(ds, set()).add(r.get("node_id", "?"))
    pub = published(include_test=True)
    lb = leaderboard(include_test=True)
    taken = {norm_niche(b.get("niche", "")) for b in load_businesses().values()
             if isinstance(b, dict)}
    out = []

    def add(niche, why, first_customer):
        niche = (niche or "")[:120]
        if not niche or norm_niche(niche) in taken:
            return
        taken.add(norm_niche(niche))
        out.append({"niche": niche, "why": why,
                      "first_customer": first_customer,
                      "spawn_call": {"method": "POST",
                                       "path": "/api/businesses/spawn",
                                       "body": {"niche": niche}}})
    # gap 1+2: thinnest datasets with real rows (supply exists, API missing)
    thin = sorted(per.items(), key=lambda x: (x[1], x[0]))
    for ds, n in thin:
        if len(out) >= 2:
            break
        if ds in pub:
            continue
        fields, _ = dataset_fields(ds)
        ideas = suggest_ideas(fields, ds)
        lead = ideas[0]["title"] if ideas else "metered API"
        add("%s (%s)" % (lead, ds),
            "%s has only %d rows from %d node(s) and no public API — thinnest live dataset, cheapest to own." % (
                ds, n, len(per_nodes.get(ds, set()))),
            "An indie hacker already scraping %s who wants those rows as a billable API." % ds)
    # gap 3: leaderboard demand — what the referral network already rewards
    if len(out) < 3:
        top = max(per.items(), key=lambda x: x[1]) if per else ("product-prices", 0)
        fields, _ = dataset_fields(top[0])
        ideas = suggest_ideas(fields, top[0])
        pick = ideas[1] if len(ideas) > 1 else (ideas[0] if ideas else None)
        if pick:
            add("%s for %s" % (pick["title"], top[0]),
                "%d referral-attributed signup(s) on the live leaderboard prove distribution works; %s (%d rows) is the demand pool." % (
                    (lb.get("totals") or {}).get("referred_signups", 0), top[0], top[1]),
                "A bot builder or niche publisher who pays for %s feeds today." % top[0])
    # honest padding (still live-cited) so the endpoint always returns 3
    pads = [
        ("Price-drop alerts across every thin dataset",
         "%d total records banked and counting — alerting is the idea the live data supports but nobody sells yet." % len(rows),
         "A deal-hunter who checks prices daily and would pay per tracked SKU."),
        ("Weekly lead-list export from the network's rows",
         "%d node(s) already contribute rows; packaging them weekly needs no new scraping." % len({r.get('node_id') for r in rows}),
         "A solo founder doing outreach who buys verified rows by the thousand."),
    ]
    for niche, why, fc in pads:
        if len(out) >= 3:
            break
        add(niche, why, fc)
    return out[:3]


# ---- HTTP ----

MIME = {".html": "text/html", ".js": "text/javascript", ".css": "text/css",
        ".svg": "image/svg+xml", ".json": "application/json", ".png": "image/png"}


def send(h, code, body, ctype="application/json", extra=None):
    b = body if isinstance(body, bytes) else body.encode()
    h.send_response(code)
    h.send_header("Content-Type", ctype + "; charset=utf-8")
    h.send_header("Content-Length", str(len(b)))
    h.send_header("Access-Control-Allow-Origin", "*")
    for k, v in (extra or {}).items():
        h.send_header(k, v)
    h.end_headers()
    h.wfile.write(b)


def read_json(h, max_bytes=1_000_000):
    try:
        n = int(h.headers.get("Content-Length", 0) or 0)
        if n <= 0:
            return {}
        if n > max_bytes:
            return {"_error": "body too large"}
        return json.loads(h.rfile.read(n) or b"{}")
    except Exception:
        return {"_error": "invalid json"}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        path = u.path
        q = urllib.parse.parse_qs(u.query)
        c = cfg()
        if path == "/api/health":
            # HONEST counters: test/agent rows hidden by default (real zero
            # beats fake 14); ?include_test=1 audits the full totals.
            inc = (q.get("include_test", [""])[0] == "1")
            tids = set() if inc else test_node_ids()
            rows = load_lines(p("records_path", "data/records.jsonl"))
            honest = [r for r in rows if r.get("node_id") not in tids]
            return send(self, 200, json.dumps({
                "alive": True, "site": c.get("site_name", "ScrapeNet"),
                "records": len(honest), "recipes": len(recipes()),
                "nodes": len(earnings(include_test=inc)["nodes"]),
                "test_records_hidden": 0 if inc else len(rows) - len(honest),
                "at": now_iso()}))
        if path == "/api/config":
            # Secret values never leave the server: stripe keys (matched by
            # name) plus the X bearer (an explicit secret slot whose name
            # does not contain "secret"). Public symbols like
            # payout_token_symbol stay visible — the dashboard needs them.
            pub = {k: v for k, v in c.items()
                   if k not in ("bind", "x_bearer_token", "owner_token")
                   and "secret" not in k.lower()}
            return send(self, 200, json.dumps(pub))
        if path == "/api/records":
            lim, err = parse_limit((q.get("limit", [None])[0]),
                                   int(c.get("records_limit_default", 100)))
            if err:
                return send(self, 400, json.dumps({"error": err}))
            mkey, mtier, mqs, blocked = meter_allow(dict(self.headers), q)
            if blocked is not None:
                return send(self, 429, json.dumps(blocked))
            return send(self, 200, json.dumps(records(
                limit=lim,
                dataset=(q.get("dataset", [""])[0] or None),
                node_id=(q.get("node_id", [""])[0] or None),
                include_test=(q.get("include_test", [""])[0] == "1"))),
                extra=quota_headers(mkey, mtier, mqs))
        if path == "/api/audit":
            lim, err = parse_limit((q.get("limit", [None])[0]), 100)
            if err:
                return send(self, 400, json.dumps({"error": err}))
            rows = load_lines(p("audit_path", "data/audit.jsonl"))
            return send(self, 200, json.dumps(list(reversed(rows))[:lim]))
        if path == "/api/recipes":
            items = recipes()
            for r in items:
                if r.get("where") not in WHERE_MODES:
                    r["where"] = "client"
                if not isinstance(r.get("ops"), list):
                    r["ops"] = []
            return send(self, 200, json.dumps(items))
        if path == "/api/published":
            return send(self, 200, json.dumps(published(
                include_test=(q.get("include_test", [""])[0] == "1"))))
        if path == "/api/earnings":
            return send(self, 200, json.dumps(earnings(
                include_test=(q.get("include_test", [""])[0] == "1"))))
        if path == "/api/ideas":
            ds = q.get("dataset", [""])[0] or ""
            inc = (q.get("include_test", [""])[0] == "1")
            fields, n = dataset_fields(ds, include_test=inc)
            if not fields and not ds:
                # global: union of fields
                fields, n = dataset_fields("", include_test=inc)
            return send(self, 200, json.dumps({
                "dataset": ds, "fields": fields, "rows": n,
                "ideas": suggest_ideas(fields, ds)}))
        if path == "/api/me":
            # The payer's mirror: tier, live quota, referral credit.
            # Auth via node_id + token (query or Authorization header).
            authed, auth_err = check_write_auth({}, dict(self.headers), q)
            if auth_err:
                code, payload = auth_err
                return send(self, code, json.dumps(payload))
            tier = node_tier(authed)
            qs = quota_status("node:" + authed, tier)
            e = earnings()
            mine = next((n for n in e["nodes"]
                         if n["node_id"] == authed), {})
            pub_all = load_json(p("published_path", "data/published.json"),
                                {})
            mine_ds = sum(1 for m in (pub_all or {}).values()
                          if isinstance(m, dict)
                          and m.get("published_by") == authed)
            t = tiers_cfg()
            return send(self, 200, json.dumps({
                "node_id": authed, "tier": tier,
                "quota_used": qs["used"], "quota_left": qs["left"],
                "quota_limit": qs["limit"], "resets_at": qs["resets_at"],
                "referral_credit": (mine or {}).get(
                    "referral_earnings", 0.0),
                "token": e["token"],
                "datasets_used": mine_ds,
                "datasets_limit": int(t.get(tier, {}).get("datasets", 1))}))
        if path == "/api/leaderboard":
            return send(self, 200, json.dumps(leaderboard(
                include_test=(q.get("include_test", [""])[0] == "1"))))
        if path == "/api/funnel":
            return send(self, 200, json.dumps(funnel(
                include_bots=(q.get("bots", [""])[0] == "1"),
                include_test=(q.get("include_test", [""])[0] == "1"))))
        if path == "/api/last-capture":
            cap = last_capture(include_test=(q.get("include_test", [""])[0] == "1"))
            if cap is None:
                return send(self, 404, json.dumps({"error": "no captures yet"}))
            return send(self, 200, json.dumps(cap))
        if path == "/api/last-payout":
            pay = last_payout(include_test=(q.get("include_test", [""])[0] == "1"))
            if pay is None:
                return send(self, 404, json.dumps({"error": "no payouts yet"}))
            return send(self, 200, json.dumps(pay))
        if path == "/api/growth/queue":
            return send(self, 200, json.dumps(get_growth_queue()))
        if path == "/api/gaps":
            return send(self, 200, json.dumps({
                "gaps": list_gaps(include_test=(q.get("include_test", [""])[0] == "1")),
                "source": LOOP_SOURCE}))
        if path == "/api/growth/stats":
            return send(self, 200, json.dumps(growth_stats(
                include_test=(q.get("include_test", [""])[0] == "1"))))
        if path == "/api/businesses/suggest":
            return send(self, 200, json.dumps({
                "suggest": suggest_spawn_niches()}))
        if path == "/api/businesses":
            inc = (q.get("include_test", [""])[0] == "1")
            tids = set() if inc else test_node_ids()
            items = []
            for bid, b in sorted(load_businesses().items()):
                if not isinstance(b, dict):
                    continue
                if b.get("owner", "") in tids:
                    continue
                items.append({**b, "stats": business_live_stats(b),
                              "test": b.get("owner", "") in test_node_ids()})
            return send(self, 200, json.dumps({"businesses": items,
                                               "count": len(items)}))
        if path == "/api/brief":
            return send(self, 200, json.dumps(brief()))
        if path == "/api/owner/status":
            if not check_owner_auth({}, dict(self.headers), q):
                return send(self, 401, json.dumps({
                    "error": ("owner locked — unlock the Owner drawer with "
                                "the master token from needs.json")} ))
            st = owner_status()
            return send(self, 200, json.dumps(st))
        if path == "/download/extension.zip":
            # Zip extension/ on the fly (stdlib zipfile) so a stranger can
            # install without cloning the repo or touching the server disk.
            extdir = os.path.join(DIR, "extension")
            try:
                names = sorted(os.listdir(extdir))
            except Exception:
                return send(self, 404, json.dumps({"error": "extension not found"}))
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for root, dirs, files in os.walk(extdir):
                    dirs[:] = sorted(d for d in dirs if not d.startswith("."))
                    for fn in sorted(files):
                        if fn.startswith("."):
                            continue
                        fp = os.path.join(root, fn)
                        z.write(fp, os.path.relpath(fp, extdir))
            data = buf.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition",
                             'attachment; filename="scrapenet-extension.zip"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            return
        if path.startswith("/dataset/"):
            ds = path[len("/dataset/"):].strip("/")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", ds or ""):
                return send(self, 400, json.dumps({"error": "bad dataset id"}))
            ref = (q.get("ref", [""])[0] or "").strip()
            html = render_dataset_page(
                ds, ref,
                include_test=(q.get("include_test", [""])[0] == "1"))
            if html is None:
                return send(self, 404, json.dumps({"error": "dataset not found"}))
            return send(self, 200, html, "text/html")
        if path.startswith("/api/public/"):
            ds = path[len("/api/public/"):].strip("/")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", ds or ""):
                return send(self, 400, json.dumps({"error": "bad dataset id"}))
            # HONEST gate: snapshots published by test/agent nodes are
            # hidden by default (?include_test=1 audits them). This is
            # what keeps agent exhaust out of the public product.
            if (q.get("include_test", [""])[0] != "1") and \
                    str((published(include_test=True).get(ds) or {}).get("published_by", "")) in test_node_ids():
                return send(self, 404, json.dumps({
                    "error": ("dataset has no honest rows yet: its snapshot was "
                              "published by a test/agent node (counts exclude "
                              "test traffic; audit with ?include_test=1)")}))
            mkey, mtier, mqs, blocked = meter_allow(dict(self.headers), q)
            if blocked is not None:
                return send(self, 429, json.dumps(blocked))
            fp = os.path.join(p("published_dir", "data/published"), ds + ".json")
            if not os.path.exists(fp):
                return send(self, 404, json.dumps({"error": "dataset not published"}))
            bump_business_calls(ds)
            with open(fp, "rb") as f:
                data = f.read()
            return send(self, 200, data,
                        extra=quota_headers(mkey, mtier, mqs))
        # static — confined to public/ (blocks ../ traversal incl. %2e encodings)
        raw = urllib.parse.unquote(path)
        if "\x00" in raw:
            return send(self, 404, json.dumps({"error": "not found"}))
        rel = raw[1:] if raw != "/" else "index.html"
        base = os.path.normpath(PUB)
        fp = os.path.normpath(os.path.join(base, rel))
        if fp != base and not fp.startswith(base + os.sep):
            return send(self, 404, json.dumps({"error": "not found"}))
        if os.path.isdir(fp):
            fp = os.path.join(fp, "index.html")
        if os.path.isfile(fp):
            with open(fp, "rb") as f:
                data = f.read()
            return send(self, 200, data, MIME.get(os.path.splitext(fp)[1], "text/plain"))
        return send(self, 404, json.dumps({"error": "not found"}))

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/stripe-webhook":
            return self.handle_stripe_webhook()
        b = read_json(self)
        if "_error" in b:
            return send(self, 400, json.dumps({"error": b["_error"]}))
        c = cfg()
        if path == "/api/signup":
            # Self-serve account: {name, referral_code?, agent?} -> {node_id,
            # token, referral_code, test?}. agent:<name> (driven-browser
            # self-id, AGENT CONVENTION 2026-09-29) or a test-pattern
            # name/node_id (needs.json test_node_patterns) flags the node
            # test:true — excluded from public earnings/leaderboard/published
            # by default, auditable via ?include_test=1, purgeable via
            # POST /api/nodes/purge-test. The token is returned ONCE here
            # and never again.
            name, err = clean_str(b.get("name", ""), 40)
            if err or not name:
                return send(self, 400, json.dumps({
                    "error": "name required (string, max 40 chars)"}))
            agent = b.get("agent", "")
            if agent in (None, ""):
                agent = ""
            elif not valid_agent(agent):
                return send(self, 400, json.dumps({
                    "error": "agent: 1..64 chars [A-Za-z0-9_.-] (your driven-browser name)"}))
            db = auth_db()
            accts = db.setdefault("nodes", {})
            refcode = b.get("referral_code", "") or b.get("ref", "")
            refcode = refcode.strip().upper() if isinstance(refcode, str) else ""
            referred_by = None
            if refcode:
                for nid, a in accts.items():
                    if a.get("referral_code") == refcode:
                        referred_by = nid
                        break
                if referred_by is None and refcode == "GROWTH":
                    # Growth-loop attribution (?ref=growth on dataset/share
                    # links). Pseudo-referrer: no account holds this code,
                    # signups citing it count as growth-attributed in
                    # GET /api/growth/stats. Real codes still resolve above.
                    referred_by = "growth"
                if referred_by is None:
                    return send(self, 400, json.dumps({
                        "error": "unknown referral_code — check the ?ref= link"}))
            base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:24] or "node"
            node_id = f"{base}-{secrets.token_hex(3)}"
            while node_id in accts:
                node_id = f"{base}-{secrets.token_hex(3)}"
            token = secrets.token_hex(16)
            my_code = new_referral_code(db)
            is_test = bool(agent) or _matches_test(node_id) or _matches_test(name)
            accts[node_id] = {
                "name": name,
                "token_sha256": token_hash(token),
                "referral_code": my_code,
                "referred_by": referred_by,
                "created": now_iso(),
                "test": is_test,
                "agent": agent,
            }
            save_auth(db)
            audit("signup", node_id=node_id, referred_by=referred_by or "",
                  test=is_test, agent=agent)
            return send(self, 200, json.dumps({
                "node_id": node_id,
                "token": token,
                "referral_code": my_code,
                "referred_by": referred_by,
                "test": is_test,
                "agent": agent,
                "collector_url": (c.get("public_url") or "").strip(),
                "note": "Save the token now — it is never shown again. "
                          "Pass it as Authorization: Bearer <token> or JSON 'token' "
                          "on /api/ingest, /api/recipes, /api/publish."}))
        if path == "/api/ingest":
            recs = b.get("records", None)
            if not isinstance(recs, list) or not recs:
                return send(self, 400, json.dumps({"error": "records[] required (non-empty array of objects)"}))
            if len(recs) > int(c.get("max_records_per_ingest", 200)):
                return send(self, 400, json.dumps({
                    "error": f"too many records (max {int(c.get('max_records_per_ingest', 200))} per request)"}))
            node_id, err = clean_str(b.get("node_id", ""), 64)
            if err or not node_id:
                return send(self, 400, json.dumps({"error": "node_id required (string, max 64 chars)"}))
            authed, auth_err = check_write_auth(b, dict(self.headers))
            if auth_err:
                code, payload = auth_err
                return send(self, code, json.dumps(payload))
            node_id = authed
            dataset = b.get("dataset", "")
            if not isinstance(dataset, str) or not DS_RE.fullmatch(dataset.strip()):
                return send(self, 400, json.dumps({
                    "error": "dataset required: 1..64 chars, letters/digits/._- only"}))
            dataset = dataset.strip()
            recipe_id, err = clean_str(b.get("recipe_id", "") or "", 64)
            if err:
                return send(self, 400, json.dumps({"error": f"recipe_id {err}"}))
            wallet, err = clean_str(b.get("wallet", "") or "", 128)
            if err:
                return send(self, 400, json.dumps({"error": f"wallet {err}"}))
            try:
                max_rec_bytes = int(c.get("max_record_bytes", 10240))
            except (TypeError, ValueError):
                max_rec_bytes = 10240
            raw_cap = b.get("raw", None)
            if raw_cap is not None:
                if not isinstance(raw_cap, (dict, list)):
                    return send(self, 400, json.dumps({"error": "raw must be an object/array (the page capture the records came from)"}))
                if len(json.dumps(raw_cap)) > max_rec_bytes:
                    return send(self, 400, json.dumps({
                        "error": f"raw too large (max {max_rec_bytes} bytes JSON)"}))
            for i, r in enumerate(recs):
                if not isinstance(r, dict):
                    return send(self, 400, json.dumps({"error": f"records[{i}] must be an object"}))
                if len(json.dumps(r)) > max_rec_bytes:
                    return send(self, 400, json.dumps({
                        "error": f"records[{i}] too large (max {max_rec_bytes} bytes JSON)"}))
            if rate_hit(node_id):
                audit("ingest_rate_limited", node_id=node_id, dataset=dataset)
                return send(self, 429, json.dumps({
                    "error": f"rate limit: max {c.get('ingest_rate_per_minute', 30)} ingests/minute per node"}))
            consent = b.get("publish_ok", True)
            consent = bool(consent) if isinstance(consent, bool) else True
            seen = recent_hashes(dataset)
            batch = set()
            at = now_iso()
            # Stamp the test flag at ingest so rows are self-describing;
            # public reads filter on test_node_ids() dynamically anyway.
            row_test = node_id in test_node_ids()
            n = skipped = 0
            for r in recs:
                h = record_hash(dataset, node_id, r)
                if h in batch or h in seen:
                    skipped += 1
                    continue
                batch.add(h)
                row = {
                    "at": at, "dataset": dataset, "node_id": node_id,
                    "recipe_id": recipe_id, "record": r, "consent": consent,
                    "test": row_test}
                if raw_cap is not None:
                    row["raw"] = raw_cap
                append_line(p("records_path", "data/records.jsonl"), row)
                n += 1
            if wallet:
                append_line(p("ledger_path", "data/ledger.jsonl"),
                            {"at": at, "node_id": node_id, "wallet": wallet})
            audit("ingest", node_id=node_id, dataset=dataset, accepted=n,
                  duplicates_skipped=skipped)
            return send(self, 200, json.dumps({
                "ok": True, "accepted": n, "duplicates_skipped": skipped,
                "dataset": dataset, "node_id": node_id}))
        if path == "/api/recipes":
            authed, auth_err = check_write_auth(b, dict(self.headers))
            if auth_err:
                code, payload = auth_err
                return send(self, code, json.dumps(payload))
            items = recipes()
            name, err = clean_str(b.get("name", ""), 120)
            if err or not name:
                return send(self, 400, json.dumps({"error": "name required (string, max 120 chars)"}))
            raw_id = b.get("id", "")
            if raw_id in (None, ""):
                raw_id = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or f"r{int(time.time())}"
            if not isinstance(raw_id, str) or not DS_RE.fullmatch(raw_id.strip()):
                return send(self, 400, json.dumps({
                    "error": "id: 1..64 chars, letters/digits/._- only"}))
            rid = raw_id.strip()
            if any(r.get("id") == rid for r in items):
                return send(self, 409, json.dumps({"error": "recipe id exists"}))
            dataset = b.get("dataset", "default")
            if not isinstance(dataset, str) or not DS_RE.fullmatch(dataset.strip()):
                return send(self, 400, json.dumps({
                    "error": "dataset: 1..64 chars, letters/digits/._- only"}))
            fn = b.get("fn", "")
            if not isinstance(fn, str):
                return send(self, 400, json.dumps({"error": "fn must be a string"}))
            ops = b.get("ops", [])
            if ops in (None, ""):
                ops = []
            if not isinstance(ops, list):
                return send(self, 400, json.dumps({
                    "error": "ops must be a list of declarative transform ops"}))
            ops_errs = validate_ops(ops) if ops else []
            if ops_errs:
                return send(self, 400, json.dumps({
                    "error": "recipe ops rejected", "details": ops_errs,
                    "note": "Allowed ops: css-select, json-path, regex, map, filter."}))
            if fn.strip():
                verdict = analyze_fn(fn)
                if not verdict["ok"]:
                    return send(self, 400, json.dumps({
                        "error": "recipe fn rejected", "details": verdict["errors"],
                        "note": verdict["note"]}))
            elif not ops:
                return send(self, 400, json.dumps({
                    "error": "recipe needs either fn (client transform) or ops (server transform)"}))
            schema = b.get("schema", [])
            if not isinstance(schema, list) or len(schema) > 50 or \
                    any(not isinstance(s, str) or len(s) > 64 for s in schema):
                return send(self, 400, json.dumps({
                    "error": "schema must be a list of <=50 field names (each max 64 chars)"}))
            match, err = clean_str(b.get("match", "") or "", 500)
            desc, err2 = clean_str(b.get("description", "") or "", 500)
            if err or err2:
                return send(self, 400, json.dumps({"error": "match/description too long (max 500 chars)"}))
            where = normalize_where(b.get("where", "client"))
            if where is None:
                return send(self, 400, json.dumps({
                    "error": "where must be client|server|both"}))
            rec = {"id": rid, "name": name,
                   "dataset": dataset.strip(),
                   "match": match, "description": desc,
                   "schema": schema, "fn": fn, "where": where, "ops": ops}
            items.append(rec)
            save_recipes(items)
            audit("recipe_create", id=rid, by=authed)
            return send(self, 200, json.dumps(rec))
        if path == "/api/recipes/test":
            # Sandbox check: static analysis ONLY, never executes the fn.
            # Also validates declarative ops when present.
            if "fn" not in b and "ops" not in b:
                return send(self, 400, json.dumps({"error": "fn or ops required"}))
            out = dict(analyze_fn(b.get("fn", ""))) if "fn" in b else \
                {"ok": True, "errors": [], "warnings": [], "note": "no fn supplied"}
            if "ops" in b:
                ops_errs = validate_ops(b["ops"]) if isinstance(b["ops"], list) else ["ops must be a list"]
                out["ops_ok"] = not ops_errs
                out["ops_errors"] = ops_errs
                if ops_errs:
                    out["ok"] = False
                    out["errors"] = out.get("errors", []) + ["ops: " + e for e in ops_errs]
            return send(self, 200, json.dumps(out))
        if path == "/api/publish":
            authed, auth_err = check_write_auth(b, dict(self.headers))
            if auth_err:
                code, payload = auth_err
                return send(self, code, json.dumps(payload))
            ds = b.get("dataset", "")
            if not isinstance(ds, str) or not DS_RE.fullmatch(ds.strip()):
                return send(self, 400, json.dumps({"error": "valid dataset id required"}))
            ds = ds.strip()
            pub_by = authed
            # Publish cap: free tier covers N datasets (needs.json tiers).
            tier_now = node_tier(authed)
            try:
                ds_limit = int(tiers_cfg().get(tier_now, {}).get(
                    "datasets", 1))
            except (TypeError, ValueError):
                ds_limit = 1
            pub_all = load_json(p("published_path", "data/published.json"),
                                {})
            mine_ds = {d for d, m in (pub_all or {}).items()
                       if isinstance(m, dict)
                       and m.get("published_by") == authed}
            if ds not in mine_ds and len(mine_ds) >= ds_limit:
                t = tiers_cfg()
                pro = t.get("pro", {}) if isinstance(
                    t.get("pro"), dict) else {}
                return send(self, 403, json.dumps({
                    "error": (f"free tier covers {ds_limit} dataset(s) \u2014 you "
                              f"already publish {sorted(mine_ds)}. Pro "
                              f"(${pro.get('price_usd', 9)}/mo) covers "
                              f"{pro.get('datasets', 50)}."),
                    "tier": tier_now, "datasets_used": len(mine_ds),
                    "datasets_limit": ds_limit,
                    "upgrade": {
                        "checkout": ("POST /api/checkout {\"tier\": \"pro\"} "
                                     "(with your node_id + token)"),
                        "note": pro.get("note", "")}}))
            rows = [r for r in load_lines(p("records_path", "data/records.jsonl"))
                    if r.get("dataset") == ds]
            skipped = sum(1 for r in rows if r.get("consent", True) is False)
            rows = [r for r in rows if r.get("consent", True) is not False]
            if not rows:
                return send(self, 400, json.dumps({
                    "error": "nothing publishable: dataset has no consenting records"}))
            # HONEST snapshot: test/agent rows never ship in the public
            # product (a real zero beats a fake 224). The audit surface
            # (/api/records?include_test=1) still reveals them.
            tids = test_node_ids()
            test_hidden = sum(1 for r in rows if r.get("node_id") in tids)
            rows = [r for r in rows if r.get("node_id") not in tids]
            snap = {"dataset": ds, "at": now_iso(), "count": len(rows),
                    "test_rows_hidden": test_hidden,
                    "records": [r.get("record", {}) for r in rows]}
            pubdir = p("published_dir", "data/published")
            os.makedirs(pubdir, exist_ok=True)
            with open(os.path.join(pubdir, ds + ".json"), "w") as f:
                json.dump(snap, f)
            pub = load_json(p("published_path", "data/published.json"), {})
            pub[ds] = {"at": snap["at"], "count": len(rows),
                       "url_path": f"/api/public/{ds}",
                       "skipped_no_consent": skipped,
                       "test_rows_hidden": test_hidden,
                       "published_by": pub_by}
            save_json(p("published_path", "data/published.json"), pub)
            audit("publish", dataset=ds, count=len(rows),
                  skipped_no_consent=skipped, published_by=pub_by)
            return send(self, 200, json.dumps({"ok": True, **pub[ds], "dataset": ds}))
        if path == "/api/checkout":
            # Upgrade path: {node_id, token, tier} -> {checkout_url, status}.
            # Provider flips live: manual (default) vs stripe (secret set).
            authed, auth_err = check_write_auth(b, dict(self.headers))
            if auth_err:
                code, payload = auth_err
                return send(self, code, json.dumps(payload))
            tier = (b.get("tier", "") or "").strip().lower()
            t = tiers_cfg()
            paid = {k: v for k, v in t.items() if k != "free"}
            if tier not in paid:
                return send(self, 400, json.dumps({
                    "error": f"tier must be one of {sorted(paid)}",
                    "tiers": {k: {"price_usd": v.get("price_usd"),
                                   "api_calls_per_day": v.get(
                                       "api_calls_per_day"),
                                   "datasets": v.get("datasets"),
                                   "note": v.get("note", "")}
                              for k, v in paid.items()}}))
            if node_tier(authed) == tier:
                return send(self, 200, json.dumps(
                    {"status": "already", "tier": tier, "node_id": authed}))
            if checkout_provider() == "manual":
                return send(self, 200, json.dumps(
                    manual_checkout(authed, tier)))
            try:
                sess = stripe_checkout_session(authed, tier)
            except Exception as ex:
                audit("checkout_stripe_failed", node_id=authed, tier=tier,
                      error=str(ex)[:200])
                return send(self, 502, json.dumps({
                    "error": f"stripe checkout failed: {str(ex)[:200]}"}))
            audit("checkout_stripe", node_id=authed, tier=tier,
                  session_id=sess.get("id", ""))
            return send(self, 200, json.dumps({
                "status": "stripe", "provider": "stripe", "tier": tier,
                "price_usd": t[tier].get("price_usd"),
                "checkout_url": sess.get("url"),
                "session_id": sess.get("id"),
                "note": ("Complete payment at the URL; the webhook flips "
                           "your tier to pro automatically.")}))
        if path == "/api/nodes/purge-test":
            # One authenticated endpoint to purge test traffic. GUARD: the
            # body must carry {"test_only": true} (plus node_id+token for
            # auth) — without the flag the request is REFUSED and nothing
            # is touched. With it, ONLY test:true/pattern nodes and their
            # records/ledger/published rows are deleted (backed up first).
            authed, auth_err = check_write_auth(b, dict(self.headers))
            if auth_err:
                code, payload = auth_err
                return send(self, code, json.dumps(payload))
            if b.get("test_only") is not True:
                return send(self, 400, json.dumps({
                    "error": ("refuse: pass {\"test_only\": true} to purge "
                              "TEST nodes only — without the flag nothing is deleted. "
                              "Prod nodes are never touched either way.")}))
            return send(self, 200, json.dumps(
                {**purge_test_nodes(), "purged_by": authed}))
        if path == "/api/ideas":
            ds = b.get("dataset", "")
            if ds not in (None, "") and (not isinstance(ds, str) or len(ds.strip()) > 64):
                return send(self, 400, json.dumps({"error": "dataset too long (max 64 chars)"}))
            ds = ds.strip() if isinstance(ds, str) else ""
            fields = b.get("fields") or b.get("schema") or []
            if not fields:
                fields, _ = dataset_fields(ds)
            return send(self, 200, json.dumps({
                "dataset": ds, "fields": fields,
                "ideas": suggest_ideas(fields, ds)}))
        if path == "/api/events":
            # Telemetry intake: {v:1, session, ts, page, event, detail?, ms?}.
            # No IPs stored - only the random client session id. Public so
            # anonymous visitors count in the funnel before they sign up.
            if not isinstance(b, dict) or b.get("v") != 1:
                return send(self, 400, json.dumps({"error": "need {v:1, session, ts, page, event}"}))
            sess = b.get("session", "")
            ev = b.get("event", "")
            page = b.get("page", "")
            if not valid_session(sess):
                return send(self, 400, json.dumps({"error": "session: 1..64 chars [A-Za-z0-9_.-]"}))
            if not valid_event(ev):
                return send(self, 400, json.dumps({"error": "unknown event (page_view, download, signup, first_proof_seen, js_error, idle_45s, publish, generate, proof, click:<id>)"}))
            if not isinstance(page, str) or len(page) > 200:
                return send(self, 400, json.dumps({"error": "page: string max 200 chars"}))
            detail = b.get("detail", "")
            if detail not in (None, "") and (not isinstance(detail, str) or len(detail) > 2000):
                return send(self, 400, json.dumps({"error": "detail: string max 2000 chars"}))
            ms = b.get("ms")
            if ms not in (None, "") and not isinstance(ms, (int, float)):
                return send(self, 400, json.dumps({"error": "ms: number"}))
            agent = b.get("agent", "")
            if agent in (None, ""):
                agent = ""
            elif not valid_agent(agent):
                return send(self, 400, json.dumps({
                    "error": "agent: 1..64 chars [A-Za-z0-9_.-] (your driven-browser name)"}))
            append_line(events_path(), {
                "at": now_iso(), "v": 1, "session": sess,
                "ts": b.get("ts"), "page": page, "event": ev,
                "detail": detail if isinstance(detail, str) else "",
                "ms": ms if isinstance(ms, (int, float)) else None,
                "agent": agent,
                "synthetic": bool(is_bot_session(sess) or agent != "" or is_bot_ua(
                    self.headers.get("User-Agent", "")))})
            return send(self, 200, json.dumps({"ok": True}))
        if path == "/api/generate":
            # AI-prefill: propose a selector/recipe from pasted HTML or a
            # URL's fetched sample. Rule-based today; LLM slot documented in
            # the response (same pattern as /api/refine). Public on purpose
            # (prefill happens before signup); saving still needs the token.
            html = b.get("html", "") or ""
            url = (b.get("url", "") or "").strip() if isinstance(b.get("url", ""), str) else ""
            if not isinstance(html, str):
                return send(self, 400, json.dumps({"error": "html must be a string"}))
            if len(html) > 200_000:
                return send(self, 400, json.dumps({"error": "html too large (max 200000 chars)"}))
            if len(url) > 2000:
                return send(self, 400, json.dumps({"error": "url too long (max 2000 chars)"}))
            if url and not html:
                html, ferr = fetch_url_sample(url)
                if ferr:
                    return send(self, 400, json.dumps({"error": ferr}))
            if not html.strip():
                return send(self, 400, json.dumps({"error": "paste HTML or give a url"}))
            name_h, _ = clean_str(b.get("name", "") or "", 120)
            ds_h = b.get("dataset", "") or ""
            ds_h = ds_h.strip() if isinstance(ds_h, str) else ""
            return send(self, 200, json.dumps(
                propose_recipe(html, url, name_h or "", ds_h)))
        if path == "/api/refine":
            sample = b.get("sample") or b.get("records") or []
            if not isinstance(sample, list):
                return send(self, 400, json.dumps({"error": "sample[] required (array of objects)"}))
            fn = b.get("fn", "")
            if fn not in (None, "") and (not isinstance(fn, str) or len(fn) > 32768):
                return send(self, 400, json.dumps({"error": "fn too large (max 32768 chars)"}))
            return send(self, 200, json.dumps(refine(sample[:200], fn if isinstance(fn, str) else "")))
        if path == "/api/recipes/suggest":
            # Rule-based extraction proposal for a client-stripped DOM
            # snapshot (public: analysis only, nothing stored, html never echoed).
            # Differs from /api/generate (fn-recipe prefill from pasted HTML
            # or a server-fetched URL): this one returns a declarative *ops*
            # mapping for visit-time Suggest, approved with one click.
            url = b.get("url", "")
            html = b.get("html", "")
            if not isinstance(url, str) or len(url) > 2000 or not url.strip():
                return send(self, 400, json.dumps({"error": "url required (max 2000 chars)"}))
            if not isinstance(html, str) or not html.strip():
                return send(self, 400, json.dumps({"error": "html snapshot required (client-stripped, max 100KB)"}))
            if len(html) > 100000:
                html = html[:100000]
            return send(self, 200, json.dumps({"ok": True, "url": url[:2000],
                                               **suggest_mapping(url, html)}))
        if path == "/api/gaps":
            # Loop hands: file one backlog gap {item, evidence, priority?}.
            # Owner key OR any node token. source is always e082-loop.
            by_owner = check_owner_auth(b, dict(self.headers))
            if by_owner:
                authed = "owner"
            else:
                authed, auth_err = check_write_auth(b, dict(self.headers))
                if auth_err:
                    code, payload = auth_err
                    return send(self, code, json.dumps(payload))
            row, err = file_gap(b.get("item", ""), b.get("evidence", ""),
                                b.get("priority", "normal") or "normal",
                                by=authed, test=bool(b.get("test", False)))
            if err:
                return send(self, 400, json.dumps({"error": err}))
            return send(self, 200, json.dumps({"ok": True, **row}))
        if path == "/api/growth/draft":
            # Loop hands: draft ONE growth post (source:loop, unapproved).
            # The scheduler only posts approved rows, so human/auto-approve
            # rules decide — this endpoint can never auto-post.
            by_owner = check_owner_auth(b, dict(self.headers))
            if by_owner:
                authed = "owner"
            else:
                authed, auth_err = check_write_auth(b, dict(self.headers))
                if auth_err:
                    code, payload = auth_err
                    return send(self, code, json.dumps(payload))
            post, err = queue_loop_draft(b.get("text", ""),
                                         b.get("link", "") or "",
                                         b.get("fact", "") or "",
                                         by=authed)
            if err:
                return send(self, 400, json.dumps({"error": err}))
            return send(self, 200, json.dumps({"ok": True, **post}))
        if path == "/api/growth/approve":
            # Token-authed approval for one queued post {id, node_id, token}
            # (or the master owner token from the Owner drawer). Skipped
            # when needs.json growth_auto_approve=true (queue ships
            # approved). Approving clears a previous rejection.
            by_owner = check_owner_auth(b, dict(self.headers))
            if by_owner:
                authed = "owner"
            else:
                authed, auth_err = check_write_auth(b, dict(self.headers))
                if auth_err:
                    code, payload = auth_err
                    return send(self, code, json.dumps(payload))
            pid = b.get("id", "")
            if not isinstance(pid, str) or not pid.strip():
                return send(self, 400, json.dumps({"error": "id required"}))
            pid = pid.strip()
            qp, _, _ = growth_paths()
            q = get_growth_queue()
            for post in q.get("posts", []):
                if post.get("id") == pid:
                    post["approved"] = True
                    post["rejected"] = False
                    save_json(qp, q)
                    audit("growth_approve", id=pid, by=authed)
                    return send(self, 200, json.dumps({"ok": True, **post}))
            return send(self, 404, json.dumps({"error": "queued post not found"}))
        if path == "/api/growth/reject":
            # Mirror of approve: park one queued post (never posts, never
            # deletes). Any node token or the master owner token decides.
            by_owner = check_owner_auth(b, dict(self.headers))
            if by_owner:
                authed = "owner"
            else:
                authed, auth_err = check_write_auth(b, dict(self.headers))
                if auth_err:
                    code, payload = auth_err
                    return send(self, code, json.dumps(payload))
            pid = b.get("id", "")
            if not isinstance(pid, str) or not pid.strip():
                return send(self, 400, json.dumps({"error": "id required"}))
            pid = pid.strip()
            qp, _, _ = growth_paths()
            q = get_growth_queue()
            for post in q.get("posts", []):
                if post.get("id") == pid:
                    post["approved"] = False
                    post["rejected"] = True
                    save_json(qp, q)
                    audit("growth_reject", id=pid, by=authed)
                    return send(self, 200, json.dumps({"ok": True, **post}))
            return send(self, 404, json.dumps({"error": "queued post not found"}))
        if path == "/api/owner/keys":
            # Write-only secrets: values go to data/secrets.json (0600) and
            # are NEVER echoed back — GETs only return `set` booleans.
            # Empty string clears a key. Owner master-token gated.
            if not check_owner_auth(b, dict(self.headers)):
                return send(self, 401, json.dumps({
                    "error": "owner locked — wrong master token"}))
            s = load_secrets()
            updated = []
            for k in SECRET_KEYS:
                if k not in b:
                    continue
                v = b[k]
                if v is None:
                    continue
                if not isinstance(v, str) or len(v) > 2000:
                    return send(self, 400, json.dumps({
                        "error": f"{k} must be a string (max 2000 chars)"}))
                v = v.strip()
                if v:
                    s[k] = v
                elif k in s:
                    del s[k]
                updated.append(k)
            if not updated:
                return send(self, 400, json.dumps({
                    "error": ("nothing to store — send one of "
                                + ", ".join(SECRET_KEYS))}))
            save_secrets(s)
            audit("owner_keys_updated", keys=updated)
            return send(self, 200, json.dumps({
                "ok": True, "updated": updated,
                "set": {k: bool(secret(k)) for k in SECRET_KEYS}}))
        if path == "/api/owner/config":
            # Live non-secret config: the page edits needs.json (the source
            # of truth) through here — the server never hardcodes values.
            # Effective immediately, no restart (cfg() is read per request).
            if not check_owner_auth(b, dict(self.headers)):
                return send(self, 401, json.dumps({
                    "error": "owner locked — wrong master token"}))
            c = cfg()
            changed = []
            if "growth_channel" in b:
                ch = b["growth_channel"]
                if ch not in ("dryrun", "x_api"):
                    return send(self, 400, json.dumps({
                        "error": "growth_channel must be dryrun|x_api"}))
                c["growth_channel"] = ch
                changed.append("growth_channel")
            if "growth_auto_approve" in b:
                c["growth_auto_approve"] = bool(b["growth_auto_approve"])
                changed.append("growth_auto_approve")
            if "tiers" in b:
                tiers = b["tiers"]
                if not isinstance(tiers, dict):
                    return send(self, 400, json.dumps({
                        "error": "tiers must be {free:{...}, pro:{...}}"}))
                t = c.get("tiers", {}) if isinstance(
                    c.get("tiers"), dict) else {}
                for tier_name in ("free", "pro"):
                    if tier_name not in tiers:
                        continue
                    patch = tiers[tier_name]
                    if not isinstance(patch, dict):
                        return send(self, 400, json.dumps({
                            "error": f"tiers.{tier_name} must be an object"}))
                    cur = dict(t.get(tier_name, {})) if isinstance(
                        t.get(tier_name), dict) else {}
                    for fk, lo, hi in (("api_calls_per_day", 1, 10000000),
                                       ("datasets", 1, 10000)):
                        if fk in patch:
                            try:
                                iv = int(patch[fk])
                            except (TypeError, ValueError):
                                return send(self, 400, json.dumps({
                                    "error": f"tiers.{tier_name}.{fk} must be an integer"}))
                            if not (lo <= iv <= hi):
                                return send(self, 400, json.dumps({
                                    "error": (f"tiers.{tier_name}.{fk} out of range "
                                                f"{lo}..{hi}")}))
                            cur[fk] = iv
                    if tier_name == "pro":
                        if "price_usd" in patch:
                            try:
                                pv = float(patch["price_usd"])
                            except (TypeError, ValueError):
                                return send(self, 400, json.dumps({
                                    "error": "tiers.pro.price_usd must be a number"}))
                            if not (0 <= pv <= 10000):
                                return send(self, 400, json.dumps({
                                    "error": "tiers.pro.price_usd out of range 0..10000"}))
                            cur["price_usd"] = pv
                        if "note" in patch:
                            note = patch["note"]
                            if not isinstance(note, str) or len(note) > 500:
                                return send(self, 400, json.dumps({
                                    "error": "tiers.pro.note must be a string (max 500 chars)"}))
                            cur["note"] = note
                    t[tier_name] = cur
                    changed.append("tiers." + tier_name)
                c["tiers"] = t
            if not changed:
                return send(self, 400, json.dumps({
                    "error": ("nothing to change — send growth_channel, "
                                "growth_auto_approve, or tiers")}))
            try:
                with open(NEEDS, "w") as f:
                    json.dump(c, f, indent=1)
            except Exception as ex:
                return send(self, 500, json.dumps({
                    "error": f"could not write needs.json: {ex}"[:200]}))
            audit("owner_config", changed=changed)
            out = {"ok": True, "changed": changed,
                   "growth_channel": c.get("growth_channel"),
                   "growth_auto_approve": bool(
                       c.get("growth_auto_approve", True)),
                   "tiers": c.get("tiers", {})}
            if (c.get("growth_channel") == "x_api"
                    and not secret("x_bearer_token")):
                out["warning"] = ("channel is x_api but no X key is stored "
                                    "— posts will refuse until you paste it")
            return send(self, 200, json.dumps(out))
        if path == "/api/owner/growth/test":
            # Dryrun-safe self-test: shows EXACTLY what would post, writes a
            # `selftest` outbox row with a unique id (never collides with
            # dedupe), never touches X even when channel=x_api, and never
            # marks the queue post as sent.
            if not check_owner_auth(b, dict(self.headers)):
                return send(self, 401, json.dumps({
                    "error": "owner locked — wrong master token"}))
            q = get_growth_queue()
            posts = q.get("posts", [])
            live = [x for x in posts
                    if x.get("approved") and not x.get("rejected")
                    and not x.get("posted")] or posts
            if not live:
                return send(self, 404, json.dumps(
                    {"error": "queue empty — nothing to test"}))
            post = live[0]
            _, op, _ = growth_paths()
            entry = {"at": now_iso(),
                     "id": post["id"] + "-selftest-" + now_iso().replace(
                         ":", "").replace("+", ""),
                     "backend": "dryrun", "status": "selftest",
                     "text": post.get("text", ""),
                     "link": post.get("link", ""),
                     "note": ("Owner self-test: dryrun-safe, never posts "
                              "to X, never marks the queue item as sent.")}
            append_line(op, entry)
            audit("owner_growth_selftest", id=post.get("id", ""))
            return send(self, 200, json.dumps({"ok": True, **entry}))
        if path == "/api/owner/intents/decide":
            # Manual payout review: approve = flip the tier now, reject =
            # park it. Money movement stays human-approved, logged either way.
            if not check_owner_auth(b, dict(self.headers)):
                return send(self, 401, json.dumps({
                    "error": "owner locked — wrong master token"}))
            try:
                index = int(b.get("index", -1))
            except (TypeError, ValueError):
                return send(self, 400, json.dumps(
                    {"error": "index must be an integer"}))
            intents = load_lines(intents_path())
            if not (0 <= index < len(intents)) or not isinstance(
                    intents[index], dict):
                return send(self, 404, json.dumps(
                    {"error": "intent not found"}))
            if intent_decision_for(index) is not None:
                return send(self, 409, json.dumps(
                    {"error": "already decided — see decisions log"}))
            if not isinstance(b.get("approve"), bool):
                return send(self, 400, json.dumps(
                    {"error": "approve must be true|false"}))
            row = intents[index]
            ok = bool(b["approve"])
            tier = row.get("tier", "pro")
            if ok and not set_node_tier(row.get("node_id", ""), tier):
                return send(self, 404, json.dumps(
                    {"error": "node not found — cannot flip tier"}))
            append_line(decisions_path(), {
                "at": now_iso(), "kind": "intent", "ref": index,
                "node_id": row.get("node_id", ""), "tier": tier,
                "approve": ok, "by": "owner"})
            audit("owner_intent_decide", node_id=row.get("node_id", ""),
                  tier=tier, approve=ok)
            return send(self, 200, json.dumps({
                "ok": True, "node_id": row.get("node_id", ""),
                "tier": node_tier(row.get("node_id", "")),
                "approved": ok}))
        if path == "/api/owner/payouts/decide":
            # Referral-credit review: approve = credit becomes payable
            # (owner pays the wallet on file, manually), reject = park it.
            if not check_owner_auth(b, dict(self.headers)):
                return send(self, 401, json.dumps({
                    "error": "owner locked — wrong master token"}))
            ref = b.get("referrer", "")
            if not isinstance(ref, str) or not ref.strip():
                return send(self, 400, json.dumps(
                    {"error": "referrer (node id or code) required"}))
            ref = ref.strip()
            if not isinstance(b.get("approve"), bool):
                return send(self, 400, json.dumps(
                    {"error": "approve must be true|false"}))
            lb = leaderboard(include_test=True)
            hit = next((x for x in lb.get("leaders", [])
                        if x["node_id"] == ref
                        or x["referral_code"] == ref.upper()), None)
            if hit is None:
                db = auth_db()
                acct = (db.get("nodes", {}) or {}).get(ref)
                if not isinstance(acct, dict):
                    return send(self, 404, json.dumps(
                        {"error": "referrer not found"}))
                amount, code = 0.0, acct.get("referral_code", "")
            else:
                ref, amount, code = (hit["node_id"],
                                    hit["referral_credit"], hit["referral_code"])
            append_line(decisions_path(), {
                "at": now_iso(), "kind": "payout", "referrer": ref,
                "code": code, "amount": amount,
                "approve": bool(b["approve"]), "by": "owner"})
            audit("owner_payout_decide", referrer=ref, amount=amount,
                  approve=bool(b["approve"]))
            return send(self, 200, json.dumps({
                "ok": True, "referrer": ref, "amount": amount,
                "approved": bool(b["approve"])}))
        if path == "/api/transform":
            # Server-side execution of the SAFE declarative op subset.
            # Body: {recipe_id? | ops?, raw, url?}. Never executes JS.
            ops = b.get("ops", None)
            if ops is None and b.get("recipe_id"):
                rec = next((r for r in recipes() if r.get("id") == b["recipe_id"]), None)
                if rec is None:
                    return send(self, 404, json.dumps({"error": "recipe not found"}))
                ops = rec.get("ops", [])
            if not isinstance(ops, list):
                return send(self, 400, json.dumps({"error": "ops[] (or a recipe_id with ops) required"}))
            ops_errs = validate_ops(ops)
            if ops_errs:
                return send(self, 400, json.dumps({
                    "error": "ops rejected", "details": ops_errs}))
            raw = b.get("raw", {})
            if isinstance(raw, dict) and len(json.dumps(raw)) > 200000:
                return send(self, 400, json.dumps({"error": "raw too large (max 200KB JSON)"}))
            rows = execute_ops(ops, raw)
            return send(self, 200, json.dumps({"ok": True, "rows": rows,
                                               "count": len(rows)}))
        if path == "/api/businesses/spawn":
            # ONE-BUTTON BUSINESS: strict token auth (the legacy grandfather
            # carve-out does not apply — a spawned business needs a real
            # account to own it, bill it, and pay referrals to).
            raw_tok = bearer_token(dict(self.headers),
                                   b if isinstance(b, dict) else {})
            if not raw_tok:
                return send(self, 401, json.dumps({
                    "error": ("spawning needs your signup token (Authorization: "
                              "Bearer <token>) — legacy tokenless writes cannot own a business")}))
            authed, auth_err = check_write_auth(b, dict(self.headers))
            if auth_err:
                code, payload = auth_err
                return send(self, code, json.dumps(payload))
            owner = authed
            niche, ds_hint, idea = None, "", None
            if isinstance(b.get("idea_id"), str) and b["idea_id"].strip():
                niche, ds_hint, idea = resolve_idea(
                    b["idea_id"], b.get("dataset", "") if isinstance(
                        b.get("dataset", ""), str) else "")
                if niche is None:
                    return send(self, 400, json.dumps({"error": ds_hint}))
            else:
                niche = b.get("niche", "")
                if not isinstance(niche, str) or not niche.strip():
                    return send(self, 400, json.dumps({
                        "error": "niche (<=120 chars) or idea_id required"}))
                niche = niche.strip()
            if len(niche) > 120:
                return send(self, 400, json.dumps({
                    "error": "niche too long (max 120 chars)"}))
            bizs = load_businesses()
            for bid, ex in bizs.items():
                if (isinstance(ex, dict) and
                        norm_niche(ex.get("niche", "")) == norm_niche(niche)):
                    return send(self, 409, json.dumps({
                        "error": "niche already spawned", "business_id": bid}))
            left, cap = spawn_rate_left(owner)
            if left <= 0:
                return send(self, 429, json.dumps({
                    "error": (f"spawn rate cap: {cap}/hour per owner — "
                              "wait before spawning again (prevents garbage fleets)"),
                    "cap_per_hour": cap}))
            # dataset scaffold: slug from the niche, de-collided live
            slug = slugify_niche(ds_hint or niche)
            if not DS_RE.fullmatch(slug):
                slug = "niche"
            ds = slug
            pub_all = load_json(p("published_path", "data/published.json"), {}) or {}
            if ds in (pub_all or {}) or any(
                    isinstance(v, dict) and v.get("dataset_id") == ds
                    for v in bizs.values()):
                ds = ("%s-%s" % (slug, secrets.token_hex(2)))[:64]
            # recipe: the same rule-based builder behind POST /api/generate,
            # fed a 3-card sample carrying the niche words so kind detection
            # is meaningful (price/job/crypto/generic).
            sample = "".join(
                '<div class="product-card"><h3>%s item %d</h3>'
                "<span>$%.2f</span>" % (niche[:40], i, 9.99 + i * 5.5)
                + '<a href="https://example.com/%s/%d">view</a></div>' % (slug, i)
                for i in (1, 2, 3))
            prop = propose_recipe(sample, "", niche[:120], ds)
            rid = ("%s-recipe" % ds)[:64]
            if any(r.get("id") == rid for r in recipes()):
                rid = ("%s-recipe-%s" % (ds, secrets.token_hex(2)))[:64]
            verdict = analyze_fn(prop["recipe"]["fn"])
            if not verdict["ok"]:
                return send(self, 500, json.dumps({
                    "error": "generated recipe failed sandbox",
                    "details": verdict["errors"]}))
            rec = {"id": rid, "name": prop["recipe"]["name"][:120],
                   "dataset": ds, "match": prop["recipe"]["match"][:120],
                   "description": ("Spawner (%s) for niche %r: %s" % (
                       prop["kind"], niche[:60], prop["explanation"]))[:500],
                   "schema": prop["recipe"]["schema"],
                   "fn": prop["recipe"]["fn"], "where": "client", "ops": []}
            items = recipes()
            items.append(rec)
            save_recipes(items)
            # seed rows matching the recipe schema (accepted via the same
            # dedupe the ingest path uses), owned by the caller
            seen = recent_hashes(ds)
            batch, at, accepted = set(), now_iso(), 0
            for i in (1, 2, 3):
                row = {f: _seed_val(f, niche, slug, i) for f in rec["schema"]}
                h = record_hash(ds, owner, row)
                if h in batch or h in seen:
                    continue
                batch.add(h)
                append_line(p("records_path", "data/records.jsonl"),
                            {"at": at, "dataset": ds, "node_id": owner,
                             "recipe_id": rid, "record": row, "consent": True})
                accepted += 1
            audit("ingest", node_id=owner, dataset=ds, accepted=accepted,
                  duplicates_skipped=3 - accepted, via="spawn")
            # publish: the SAME free-tier cap as POST /api/publish (reuse,
            # not bypass — a capped owner gets the 403+upgrade, not a fleet)
            tier_now = node_tier(owner)
            try:
                ds_limit = int(tiers_cfg().get(tier_now, {}).get("datasets", 1))
            except (TypeError, ValueError):
                ds_limit = 1
            mine_ds = {d for d, m in (pub_all or {}).items()
                       if isinstance(m, dict) and m.get("published_by") == owner}
            if ds not in mine_ds and len(mine_ds) >= ds_limit:
                # rollback recipe + seeds so a capped spawn leaves nothing
                save_recipes([r for r in recipes() if r.get("id") != rid])
                pro = tiers_cfg().get("pro", {}) if isinstance(
                    tiers_cfg().get("pro"), dict) else {}
                return send(self, 403, json.dumps({
                    "error": (f"free tier covers {ds_limit} dataset(s) — "
                              f"upgrade to spawn more (rolled back recipe {rid})"),
                    "tier": tier_now, "upgrade": {
                        "checkout": ("POST /api/checkout {\"tier\": \"pro\"} "
                                     "(with your node_id + token)"),
                        "note": pro.get("note", "")}}))
            snap_rows = [r for r in load_lines(
                p("records_path", "data/records.jsonl")) if r.get("dataset") == ds]
            snap = {"dataset": ds, "at": now_iso(), "count": len(snap_rows),
                    "records": [r.get("record", {}) for r in snap_rows]}
            pubdir = p("published_dir", "data/published")
            os.makedirs(pubdir, exist_ok=True)
            with open(os.path.join(pubdir, ds + ".json"), "w") as f:
                json.dump(snap, f)
            pub_all[ds] = {"at": snap["at"], "count": len(snap_rows),
                           "url_path": f"/api/public/{ds}",
                           "skipped_no_consent": 0, "published_by": owner}
            save_json(p("published_path", "data/published.json"), pub_all)
            audit("publish", dataset=ds, count=len(snap_rows),
                  skipped_no_consent=0, published_by=owner, via="spawn")
            # tier attach: default free quota (shared metering engine) +
            # pro upsell (same tiers_cfg the paywall renders from)
            t = tiers_cfg()
            pro = t.get("pro", {}) if isinstance(t.get("pro"), dict) else {}
            db = auth_db()
            acct = (db.get("nodes", {}) or {}).get(owner, {})
            refcode = acct.get("referral_code", "") if isinstance(acct, dict) else ""
            if not refcode:
                refcode = new_referral_code(db)
                if isinstance(acct, dict) and owner in db.get("nodes", {}):
                    db["nodes"][owner]["referral_code"] = refcode
                    save_auth(db)
            base = (c.get("public_url", "") or "").strip().rstrip("/")
            bid = ("biz-%s-%s" % (slug, secrets.token_hex(3)))[:64]
            name = ((niche[:100] + " API") if len(niche) <= 100 else niche[:120])
            posts = build_biz_posts(bid, niche, name, ds, refcode, base)
            bizs[bid] = {"business_id": bid, "name": name, "niche": niche,
                         "dataset_id": ds, "recipe_id": rid, "owner": owner,
                         "referral_code": refcode, "quota_tier": tier_now,
                         "growth_posts": posts, "created": now_iso(),
                         "idea": idea}
            save_businesses(bizs)
            _, sp, _ = _biz_paths()
            append_line(sp, {"at": now_iso(), "ts": time.time(),
                             "owner": owner, "business_id": bid})
            audit("spawn", business_id=bid, dataset=ds, recipe_id=rid,
                  owner=owner, niche=niche[:120])
            return send(self, 200, json.dumps({
                "business_id": bid, "name": name,
                "public_url": ("%s/dataset/%s" % (base, ds) if base
                                 else "/dataset/%s" % ds),
                "api_url": ("%s/api/public/%s" % (base, ds) if base
                              else "/api/public/%s" % ds),
                "dataset_id": ds, "recipe_id": rid,
                "growth_posts_queued": len(posts),
                "referral_code": refcode, "quota_tier": tier_now,
                "upgrade": {
                    "checkout": ("POST /api/checkout {\"tier\": \"pro\"} "
                                 "(with your node_id + token)"),
                    "pro_price_usd": pro.get("price_usd", 9),
                    "pro_quota": pro.get("api_calls_per_day", 10000)},
            }))
        return send(self, 404, json.dumps({"error": "not found"}))

    def handle_stripe_webhook(self):
        """Stripe webhook: signature-check the raw body, flip tier to pro on
        checkout.session.completed. Needs stripe_webhook_secret in needs.json."""
        wh_secret = secret("stripe_webhook_secret")
        if not wh_secret:
            return send(self, 400, json.dumps({
                "error": ("stripe webhook not configured "
                            "(no stripe_webhook_secret in needs.json)")}))
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
        except (TypeError, ValueError):
            n = 0
        raw = self.rfile.read(min(n, 1_000_000)) if n > 0 else b""
        if not verify_stripe_sig(raw,
                                 self.headers.get("Stripe-Signature", ""),
                                 wh_secret):
            return send(self, 401, json.dumps({
                "error": "bad stripe signature"}))
        try:
            ev = json.loads(raw.decode("utf-8", "replace") or "{}")
        except Exception:
            return send(self, 400, json.dumps({"error": "invalid json"}))
        if ev.get("type") == "checkout.session.completed":
            sess = ((ev.get("data") or {}).get("object") or {})
            nid = sess.get("client_reference_id", "") or ""
            if nid and set_node_tier(nid, "pro"):
                append_line(intents_path(), {
                    "at": now_iso(), "node_id": nid, "tier": "pro",
                    "provider": "stripe",
                    "session_id": sess.get("id", "")})
                audit("checkout_stripe_completed", node_id=nid,
                      session_id=sess.get("id", ""))
                return send(self, 200, json.dumps(
                    {"ok": True, "node_id": nid, "tier": "pro"}))
            return send(self, 404, json.dumps({
                "error": "unknown node for this checkout session"}))
        return send(self, 200, json.dumps(
            {"ok": True, "ignored": ev.get("type", "?")}))

    def do_PUT(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != "/api/recipes":
            return send(self, 404, json.dumps({"error": "not found"}))
        q = urllib.parse.parse_qs(u.query)
        rid = (q.get("id", [""])[0] or "").strip()
        if not rid:
            return send(self, 400, json.dumps({"error": "id query param required"}))
        b = read_json(self)
        if "_error" in b:
            return send(self, 400, json.dumps({"error": b["_error"]}))
        authed, auth_err = check_write_auth(b, dict(self.headers), q)
        if auth_err:
            code, payload = auth_err
            return send(self, code, json.dumps(payload))
        items = recipes()
        for r in items:
            if r.get("id") == rid:
                for k in ("name", "dataset", "match", "description", "schema", "fn", "where", "ops"):
                    if k in b:
                        v = b[k]
                        if k == "ops":
                            if not isinstance(v, list):
                                return send(self, 400, json.dumps({
                                    "error": "ops must be a list of declarative transform ops"}))
                            ops_errs = validate_ops(v) if v else []
                            if ops_errs:
                                return send(self, 400, json.dumps({
                                    "error": "recipe ops rejected", "details": ops_errs}))
                            r[k] = v
                            continue
                        if k == "where":
                            w = normalize_where(v)
                            if w is None:
                                return send(self, 400, json.dumps({
                                    "error": "where must be client|server|both"}))
                            r[k] = w
                            continue
                        if k == "fn":
                            if not isinstance(v, str):
                                return send(self, 400, json.dumps({"error": "fn must be a string"}))
                            if not v.strip() and not r.get("ops") and "ops" not in b:
                                return send(self, 400, json.dumps({
                                    "error": "recipe needs either fn or ops"}))
                            if v.strip():
                                verdict = analyze_fn(v)
                                if not verdict["ok"]:
                                    return send(self, 400, json.dumps({
                                        "error": "recipe fn rejected", "details": verdict["errors"]}))
                        if k == "schema" and (not isinstance(v, list) or len(v) > 50 or
                                any(not isinstance(s, str) or len(s) > 64 for s in v)):
                            return send(self, 400, json.dumps({
                                "error": "schema must be a list of <=50 field names (each max 64 chars)"}))
                        if k in ("name", "dataset", "match", "description") and \
                                (not isinstance(v, str) or len(v) > 500 or
                                 (k == "dataset" and not DS_RE.fullmatch(v.strip())) or
                                 (k == "name" and not v.strip())):
                            return send(self, 400, json.dumps({"error": f"invalid {k}"}))
                        r[k] = v
                save_recipes(items)
                audit("recipe_update", id=rid, by=authed)
                return send(self, 200, json.dumps(r))
        return send(self, 404, json.dumps({"error": "recipe not found"}))

    def do_DELETE(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api/gaps":
            # Proof-tick cleanup: owner may delete any gap; a node token
            # may only delete test gaps. Prod evidence is owner-only.
            q = urllib.parse.parse_qs(u.query)
            b = read_json(self) if int(self.headers.get(
                "Content-Length", 0) or 0) > 0 else {}
            if isinstance(b, dict) and "_error" in b:
                return send(self, 400, json.dumps({"error": b["_error"]}))
            body = b if isinstance(b, dict) else {}
            by_owner = check_owner_auth(body, dict(self.headers), q)
            if by_owner:
                authed, owner = "owner", True
            else:
                authed, auth_err = check_write_auth(body, dict(self.headers), q)
                if auth_err:
                    code, payload = auth_err
                    return send(self, code, json.dumps(payload))
                owner = False
            gid = ((body.get("id", "") if isinstance(body, dict) else "")
                   or (q.get("id", [""])[0] or "")).strip()
            if not gid:
                return send(self, 400, json.dumps({"error": "id required"}))
            ok, err = delete_gap(gid, by=authed, owner=owner)
            if not ok:
                return send(self, 404 if err == "gap not found" else 403,
                            json.dumps({"error": err}))
            return send(self, 200, json.dumps({"ok": True, "id": gid}))
        if u.path == "/api/growth/draft":
            # Proof-tick cleanup: delete one UNPOSTED loop draft.
            q = urllib.parse.parse_qs(u.query)
            b = read_json(self) if int(self.headers.get(
                "Content-Length", 0) or 0) > 0 else {}
            if isinstance(b, dict) and "_error" in b:
                return send(self, 400, json.dumps({"error": b["_error"]}))
            body = b if isinstance(b, dict) else {}
            by_owner = check_owner_auth(body, dict(self.headers), q)
            if by_owner:
                authed = "owner"
            else:
                authed, auth_err = check_write_auth(body, dict(self.headers), q)
                if auth_err:
                    code, payload = auth_err
                    return send(self, code, json.dumps(payload))
            pid = ((body.get("id", "") if isinstance(body, dict) else "")
                   or (q.get("id", [""])[0] or "")).strip()
            if not pid:
                return send(self, 400, json.dumps({"error": "id required"}))
            ok, err = delete_loop_draft(pid, by=authed)
            if not ok:
                return send(self, 404 if err == "queued post not found" else 409,
                            json.dumps({"error": err}))
            return send(self, 200, json.dumps({"ok": True, "id": pid}))
        if u.path.startswith("/api/businesses/"):
            # OWNER-ONLY teardown: unpublish + snapshot delete, recipe
            # delete, owner's seed-row delete, posts dequeued (they live on
            # the record), calls counter dropped. Strict token auth.
            bid = u.path[len("/api/businesses/"):].strip("/")
            q = urllib.parse.parse_qs(u.query)
            b = read_json(self) if int(self.headers.get(
                "Content-Length", 0) or 0) > 0 else {}
            if isinstance(b, dict) and "_error" in b:
                return send(self, 400, json.dumps({"error": b["_error"]}))
            body = b if isinstance(b, dict) else {}
            raw_tok = bearer_token(dict(self.headers), body)
            if not raw_tok and q:
                vals = q.get("token", []) + q.get("auth_token", [])
                raw_tok = next((v.strip() for v in vals
                                if isinstance(v, str) and v.strip()), "")
            if not raw_tok:
                return send(self, 401, json.dumps({
                    "error": "deleting a business needs your signup token"}))
            authed, auth_err = check_write_auth(body, dict(self.headers), q)
            if auth_err:
                code, payload = auth_err
                return send(self, code, json.dumps(payload))
            bizs = load_businesses()
            biz = bizs.get(bid)
            if not isinstance(biz, dict):
                return send(self, 404, json.dumps({
                    "error": "business not found"}))
            if biz.get("owner") != authed:
                return send(self, 403, json.dumps({
                    "error": "only the owning node can delete this business"}))
            cleaned = {"published": False, "snapshot": False,
                       "recipe": False, "seed_rows": 0, "posts": 0}
            ds, rid = biz.get("dataset_id", ""), biz.get("recipe_id", "")
            pub = load_json(p("published_path", "data/published.json"), {}) or {}
            if ds in pub:
                del pub[ds]
                save_json(p("published_path", "data/published.json"), pub)
                cleaned["published"] = True
            try:
                fp = os.path.join(p("published_dir", "data/published"), ds + ".json")
                if os.path.exists(fp):
                    os.remove(fp)
                    cleaned["snapshot"] = True
            except Exception:
                pass
            if any(r.get("id") == rid for r in recipes()):
                save_recipes([r for r in recipes() if r.get("id") != rid])
                cleaned["recipe"] = True
            arec = p("records_path", "data/records.jsonl")
            rows = load_lines(arec)
            keep = [r for r in rows if not (
                r.get("dataset") == ds and r.get("node_id") == authed)]
            cleaned["seed_rows"] = len(rows) - len(keep)
            if cleaned["seed_rows"]:
                with open(arec, "w") as f:
                    for r in keep:
                        f.write(json.dumps(r) + "\n")
            cleaned["posts"] = len(biz.get("growth_posts", []) or [])
            calls = load_business_calls()
            calls.pop(bid, None)
            save_business_calls(calls)
            del bizs[bid]
            save_businesses(bizs)
            audit("unspawn", business_id=bid, dataset=ds, by=authed,
                  **{k: v for k, v in cleaned.items() if not isinstance(v, bool) or v})
            return send(self, 200, json.dumps({"ok": True,
                                               "business_id": bid,
                                               "cleaned": cleaned}))
        if u.path != "/api/recipes":
            return send(self, 404, json.dumps({"error": "not found"}))
        q = urllib.parse.parse_qs(u.query)
        rid = (q.get("id", [""])[0] or "").strip()
        if not rid:
            return send(self, 400, json.dumps({"error": "id query param required"}))
        authed, auth_err = check_write_auth({}, dict(self.headers), q)
        if auth_err:
            code, payload = auth_err
            return send(self, code, json.dumps(payload))
        found = any(r.get("id") == rid for r in recipes())
        if not found:
            return send(self, 404, json.dumps({"error": "recipe not found"}))
        items = [r for r in recipes() if r.get("id") != rid]
        save_recipes(items)
        audit("recipe_delete", id=rid, by=authed)
        return send(self, 200, json.dumps({"ok": True, "id": rid}))


if __name__ == "__main__":
    c = cfg()
    port = int(c.get("port", 8383))
    bind = c.get("bind", "0.0.0.0")
    for key, default in (("records_path", "data/records.jsonl"),
                         ("recipes_path", "data/recipes.json"),
                         ("ledger_path", "data/ledger.jsonl"),
                         ("published_path", "data/published.json"),
                         ("published_dir", "data/published")):
        pp = p(key, default)
        if key == "published_dir":
            os.makedirs(pp, exist_ok=True)
        elif key.endswith(".json") and not os.path.exists(pp):
            save_json(pp, [] if key != "published_path" else {})
        elif key.endswith(".jsonl"):
            os.makedirs(os.path.dirname(pp), exist_ok=True)
            if not os.path.exists(pp):
                open(pp, "a").close()
    owner_token()  # mint the master token into needs.json on first boot
    print(f"scrapenet on {bind}:{port}", flush=True)
    ThreadingHTTPServer((bind, port), H).serve_forever()
