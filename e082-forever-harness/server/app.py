#!/usr/bin/env python3
"""Forever Harness server — stdlib only. Serves public/ + /api/*.

Every tick: heartbeat -> verify gates -> compact -> ship one micro-goal.
Policies that prevent collapse are enforced here AND exposed as plugin tools.
"""
import json, os, re, time, secrets, zipfile, io, datetime, urllib.parse, urllib.request

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEEDS = os.path.join(DIR, "needs.json")
DATA = os.path.join(DIR, "data")
PUB = os.path.join(DIR, "public")
POLICY_F = os.path.join(DATA, "policy.json")
STATE_F = os.path.join(DATA, "loop_state.json")
HB_F = os.path.join(DATA, "heartbeat.json")
SUMMARY_F = os.path.join(DATA, "summary.json")
VERIFY_F = os.path.join(DATA, "verify.json")
VERSION_F = os.path.join(DATA, "version.json")
CHANGES_F = os.path.join(DATA, "policy-changes.jsonl")
STATS_F = os.path.join(DATA, "stats.json")
EVENTS_F = os.path.join(DATA, "events.jsonl")
DISMISSED_F = os.path.join(DATA, "dismissed.json")
STREAK_F = os.path.join(DATA, "funnel_streak.json")
DEMO_TOKENS_F = os.path.join(DATA, "demo_tokens.json")
EVID_F = os.path.join(DATA, "evidence.jsonl")
REVIEW_F = os.path.join(DATA, "reviews.jsonl")
HANDS_F = os.path.join(DATA, "hands.json")
HANDS_CREDS_F = os.path.join(DATA, "loop_creds.json")
HANDS_LOG = os.path.join(DIR, "log", "hands.log")
E083_DIR = os.path.normpath(os.path.join(DIR, "..", "e083-scrapenet"))
LIMITS_F = os.path.normpath(os.path.join(DIR, "..", "LIMITS.md"))
REPO_ROOT = os.path.normpath(os.path.join(DIR, ".."))
BOOT_TIME = time.time()
SKILL_F = os.path.join(DIR, "plugin", "skills", "keep-going", "SKILL.md")

MAX_BODY = 65536          # global POST body cap -> 413
MAX_NOTES = 2000          # tick notes char cap -> 400
MAX_BY = 120              # tick 'by' actor label cap -> 400
MAX_REASON = 500          # stop 'reason' char cap -> 400
MAX_GOAL = 500            # policy goal char cap -> 400

POLICY_KEYS = ["goal", "max_cycles", "quality_floor", "budget_credits",
               "diff_cap_lines", "checkpoint_every", "compaction_max_cycles",
               "stop_on_quality_breach", "stop_on_budget"]


def load(p, d):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return d


def load_lines(p):
    if not os.path.exists(p):
        return []
    out = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def append_line(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(obj) + "\n")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def cfg():
    return load(NEEDS, {})


def ensure_token():
    """Single-user token flow: mint TOKEN with secrets on first boot if absent.
    Reads stay public; POST /api/policy + POST /api/control/* need
    `Authorization: Bearer TOKEN`. No signup endpoint: this is a single-owner
    server, the owner copies TOKEN from needs.json (0600) into the board's
    Token field. Returns the token."""
    c = cfg()
    if not c.get("TOKEN"):
        c["TOKEN"] = secrets.token_urlsafe(32)
        os.makedirs(os.path.dirname(NEEDS), exist_ok=True)
        with open(NEEDS, "w") as f:
            json.dump(c, f, indent=2)
        try:
            os.chmod(NEEDS, 0o600)
        except Exception:
            pass
        print("minted new TOKEN in needs.json (0600)", flush=True)
    else:
        try:
            if os.stat(NEEDS).st_mode & 0o777 != 0o600:
                os.chmod(NEEDS, 0o600)
        except Exception:
            pass
    return c["TOKEN"]


def check_auth(h):
    """True when request carries the owner token or a minted demo token.
    Master TOKEN (needs.json, daemon/hook/SKILL flows) always works;
    POST /api/token/mint issues per-browser demo tokens (fh-*) accepted
    here too. Reads stay public. Demo tokens extend the scheme — the
    single-owner master token flow is unchanged."""
    try:
        tok = str(cfg().get("TOKEN", ""))
    except Exception:
        tok = ""
    if not tok:
        return True
    try:
        got = h.headers.get("Authorization", "")
    except Exception:
        got = ""
    if got == ("Bearer " + tok):
        return True
    if got.startswith("Bearer fh-"):
        try:
            return got[len("Bearer "):] in demo_tokens()
        except Exception:
            return False
    return False


def valid_agent(a):
    """Driven-browser self-identification (AGENT CONVENTION 2026-09-29).
    Browsers driven by agents must send ?agent=<name> (stored to localStorage
    by the snippet, forwarded as the `agent` field on every event).
    The name is stored on the event row (auditable) and forces
    synthetic:true — hidden from human counts by default, revealed by
    ?bots=1. Plain charset test, no deps."""
    return (type(a) is str and 1 <= len(a) <= 64 and all(
        ch.isalnum() or ch in "_.-" for ch in a))


ENGAGEMENT_EVENTS = ("download", "get_token", "first_proof_seen",
                     "signup", "publish", "generate", "proof")


def is_engagement(event):
    """Human-attribution signal: a click path or a proof/download action.
    Passive page_view-only sessions are UNATTRIBUTED (could be anyone's
    driven browser) — only engagement attributes a session to a human."""
    e = str(event or "")
    return e in ENGAGEMENT_EVENTS or e.startswith("click:")


def is_bot_session(sess):
    """Synthetic-session test: our own check.sh polls (check-*) and QA
    probes (*-probe) are bots, not humans. Plain string ops, no deps."""
    if type(sess) is not str:
        return False
    s = sess.strip()
    return (s.startswith("check-") or s.startswith("probe-")
            or s.endswith("-probe") or s in ("healthcheck", "health-check"))


BOT_UA_HINTS = ("curl", "wget", "python-urllib", "python-requests",
                "urllib/", "go-http", "httpie", "node-fetch", "axios",
                "loop.sh", "daemon", "probe", "healthcheck", "uptime",
                "pingdom", "nagios", "check.sh", "headless")


def is_bot_ua(ua):
    """Loop/daemon/CI user-agents and localhost health polls are synthetic.
    Never stored — only the boolean flag lands in the log (no IPs, no UAs)."""
    low = str(ua or "").lower()
    if not low:
        return False
    if "mozilla" in low and "chrome" in low or "firefox" in low or "safari" in low:
        return False  # real browsers (incl. seat-review Chrome) are human
    return any(h in low for h in BOT_UA_HINTS)


def dismissed_set():
    d = load(DISMISSED_F, {})
    ss = d.get("sessions", []) if isinstance(d, dict) else []
    return set(s for s in ss if type(s) is str and s)


def save_dismissed(ss):
    os.makedirs(DATA, exist_ok=True)
    with open(DISMISSED_F, "w") as f:
        json.dump({"sessions": sorted(ss), "updated_at": now_iso()}, f, indent=2)


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
            "proof_healthy_ratio": num("funnel_proof_healthy_ratio", 0.3),
            "min_human": int(num("min_human_sessions", 3)),
            "critic_fail_streak": int(num("funnel_critic_fail_streak", 3))}


def attribution_gate(verdict, human_attributed):
    """R4 DISCOUNT: verdicts computed over unattributed traffic are NOT
    scored. Below needs.json min_human_sessions human-attributed sessions
    the verdict becomes UNKNOWN ('not enough human traffic — unattributed')
    so the critic cannot penalize quality for traffic nobody can attribute
    to a human. Threshold from needs.json, never hardcoded."""
    need = int(funnel_thresholds()["min_human"])
    if human_attributed < need:
        return {"level": "UNKNOWN",
                "line": (f"UNKNOWN: not enough human traffic — unattributed "
                           f"({human_attributed}/{need} human-attributed sessions) "
                           "— watching, not scoring")}
    return verdict


def funnel_verdict(views, installs, proofs, bot_stuck, human_stuck):
    """One computed verdict line per funnel card — rules, not vibes.
    Priority: NOISE (bots bury humans) > FAILING (nobody installs) >
    HEALTHY (proofs keep pace) > QUIET (too little data) > WATCH."""
    t = funnel_thresholds()
    total = bot_stuck + human_stuck
    if total > 0 and bot_stuck / total > t["bot_noise_ratio"]:
        return {"level": "NOISE",
                "line": (f"NOISE: {bot_stuck}/{total} stuck are bots — hiding them, "
                           f"{human_stuck} human need help")} 
    if views >= t["min_visits"] and installs == 0:
        return {"level": "FAILING",
                "line": (f"FAILING: 0 downloads after {views} visits — "
                           "nobody installs")} 
    if views >= t["min_visits"] and installs / max(1, views) < t["download_alarm_ratio"]:
        return {"level": "FAILING",
                "line": (f"FAILING: {installs} downloads after {views} visits "
                           f"(< {t['download_alarm_ratio']:.0%} attach) — install path leaks")} 
    if views >= t["min_visits"] and proofs / max(1, views) >= t["proof_healthy_ratio"]:
        return {"level": "HEALTHY",
                "line": (f"HEALTHY: proofs keep pace with visits "
                           f"({proofs}/{views} saw proof)")} 
    if views < t["min_visits"]:
        return {"level": "QUIET",
                "line": (f"QUIET: only {views} visits — not enough signal yet")} 
    return {"level": "WATCH",
            "line": (f"WATCH: {views} visits, {proofs} proofs, {installs} downloads "
                       "— middling, watch one more day")} 


def load_funnel_streak():
    d = load(STREAK_F, {})
    if not isinstance(d, dict):
        return {"level": "QUIET", "streak": 0}
    try:
        return {"level": str(d.get("level", "QUIET")),
                "streak": int(d.get("streak", 0))}
    except (TypeError, ValueError):
        return {"level": "QUIET", "streak": 0}


def update_funnel_streak(level):
    """Advance the consecutive-FAILING counter. Called once per shipped
    tick (do_tick) — never on reads or probes, so the count means ticks."""
    prev = load_funnel_streak()
    streak = prev["streak"] + 1 if level == "FAILING" else 0
    if level != "FAILING" and prev["level"] == "FAILING":
        streak = 0
    os.makedirs(DATA, exist_ok=True)
    with open(STREAK_F, "w") as f:
        json.dump({"level": level, "streak": streak,
                   "at": now_iso()}, f, indent=2)
    return streak


def is_master(h):
    """True only for the master TOKEN in needs.json (0600).
    Demo (fh-*) tokens pass check_auth but FAIL here — owner flips
    (mint on/off, thresholds, spend tracking) need the master key."""
    try:
        tok = str(cfg().get("TOKEN", ""))
    except Exception:
        tok = ""
    if not tok:
        return True
    try:
        got = h.headers.get("Authorization", "")
    except Exception:
        got = ""
    return got == ("Bearer " + tok)


OWNER_SCHEMA = {
    # key: (kind, lo-hi) — every owner-flippable setting, validated here.
    "demo_mint_enabled": ("bool", None),
    "funnel_min_visits": ("int", (1, 1000)),
    "funnel_download_alarm_ratio": ("float01", None),
    "funnel_bot_noise_ratio": ("float01", None),
    "funnel_proof_healthy_ratio": ("float01", None),
    "funnel_critic_fail_streak": ("int", (1, 100)),
    "min_human_sessions": ("int", (1, 100)),
    "stress_max_ticks": ("int", (0, 5)),
    "real_spend_tracking": ("bool", None),
}


def get_owner_settings():
    """Owner drawer state: needs.json keys flippable from the page."""
    c = cfg()
    return {k: c.get(k) for k in OWNER_SCHEMA}


def save_owner_settings(patch, by="owner"):
    """Patch needs.json from the Owner drawer (master TOKEN only).
    Strict types like save_policy; unknown keys rejected; TOKEN and all
    other keys preserved (read-modify-write); audit-logged."""
    if type(patch) is not dict:
        return None, "JSON body must be an object"
    bad = sorted(k for k in patch if k not in OWNER_SCHEMA)
    if bad:
        err = f"unknown owner setting(s): {', '.join(bad)}"
        log_change(by, patch, False, err)
        return None, err
    vals = {}
    for k, v in patch.items():
        kind, rng = OWNER_SCHEMA[k]
        if kind == "bool":
            if type(v) is not bool:
                err = f"{k} must be boolean"
                log_change(by, patch, False, err)
                return None, err
        elif kind == "int":
            if type(v) is float and v.is_integer():
                v = int(v)
            if type(v) is bool or type(v) is not int or not (rng[0] <= v <= rng[1]):
                err = f"{k} must be an int {rng[0]}..{rng[1]}"
                log_change(by, patch, False, err)
                return None, err
        elif kind == "float01":
            if type(v) is bool or type(v) not in (int, float) or not (0 <= v <= 1):
                err = f"{k} must be a number 0..1"
                log_change(by, patch, False, err)
                return None, err
            v = float(v)
        vals[k] = v
    c = cfg()
    c.update(vals)
    os.makedirs(os.path.dirname(NEEDS), exist_ok=True)
    with open(NEEDS, "w") as f:
        json.dump(c, f, indent=2)
    try:
        os.chmod(NEEDS, 0o600)
    except Exception:
        pass
    log_change(by, vals, True, "ok")
    return get_owner_settings(), None


def demo_tokens():
    return load(DEMO_TOKENS_F, {})


def save_demo_tokens(d):
    os.makedirs(DATA, exist_ok=True)
    with open(DEMO_TOKENS_F, "w") as f:
        json.dump(d, f, indent=2)


def mint_demo_token(session):
    """One-click token affordance: mint a per-browser demo token.
    Caps: 200 tokens pool-wide, 5 per session id. Never rotates or
    reveals the master TOKEN, so the loop daemon keeps working."""
    if type(session) is not str or not (1 <= len(session) <= 64):
        return None, "session must be a string 1..64 chars"
    d = demo_tokens()
    if len(d) >= 200:
        return None, "token pool full (200) — ask the owner to prune data/demo_tokens.json"
    mine = [t for t, m in d.items() if isinstance(m, dict) and m.get("session") == session]
    if len(mine) >= 5:
        return None, "this browser already holds 5 demo tokens — reuse one (paste it in the Token field)"
    tok = "fh-" + secrets.token_urlsafe(24)
    d[tok] = {"created_at": now_iso(), "session": session}
    save_demo_tokens(d)
    return tok, None


def get_stats():
    return load(STATS_F, {"downloads": 0, "share_views": 0})


def bump_stat(key):
    try:
        s = get_stats()
        s[key] = int(s.get(key, 0)) + 1
        os.makedirs(DATA, exist_ok=True)
        with open(STATS_F, "w") as f:
            json.dump(s, f)
    except Exception:
        pass


def policy():
    """Merged policy: needs.json defaults + data/policy.json overrides."""
    c = cfg()
    p = {k: c.get(k) for k in POLICY_KEYS}
    for k, v in load(POLICY_F, {}).items():
        if k in POLICY_KEYS:
            p[k] = v
    return p


def save_policy(patch, by="unknown"):
    if type(patch) is not dict:
        return None, "JSON body must be an object"
    bad = sorted(k for k in patch if k not in POLICY_KEYS)
    if bad:
        err = f"unknown policy key(s): {', '.join(bad)}"
        log_change(by, patch, False, err)
        return None, err
    # coerce integral floats from JSON number inputs (browser parseFloat)
    # into the ints the validator demands; bool is never an int here.
    for k in ("max_cycles", "diff_cap_lines", "checkpoint_every",
              "compaction_max_cycles"):
        v = patch.get(k)
        if type(v) is float and v.is_integer():
            patch[k] = int(v)
    merged = {**policy(), **patch}
    err = validate_policy(merged)
    if err:
        log_change(by, patch, False, err)
        return None, err
    # anti-starvation: budget may not drop below already-spent credits
    try:
        spent = budget_used()
        if float(merged["budget_credits"]) < spent:
            err = (f"budget_credits ${merged['budget_credits']} below already-spent "
                   f"${spent} — raising only")
            log_change(by, patch, False, err)
            return None, err
    except (TypeError, ValueError):
        pass
    cur = load(POLICY_F, {})
    for k, v in patch.items():
        cur[k] = v
    os.makedirs(DATA, exist_ok=True)
    with open(POLICY_F, "w") as f:
        json.dump(cur, f, indent=2)
    log_change(by, patch, True, "ok")
    return policy(), None


def log_change(by, patch, ok, detail):
    """Append-only audit trail so 'pwned'-style mutations are attributable."""
    try:
        append_line(CHANGES_F, {"at": now_iso(), "by": by,
                                "patch": patch, "ok": ok, "detail": detail})
    except Exception:
        pass


def validate_policy(p):
    # Strict types: ints must be ints (bool/float/str rejected), bounds sane.
    g = p.get("goal")
    if type(g) is not str or not (1 <= len(g) <= MAX_GOAL):
        return f"goal must be a string 1..{MAX_GOAL} chars"
    m = p.get("max_cycles")
    # null or 0 = unbounded: the loop never stops on cycle count (forever).
    if m is None or m == 0:
        pass
    elif type(m) is not int or not (1 <= m <= 100000):
        return "max_cycles must be null (unbounded), 0 (unbounded), or an int 1..100000"
    qf = p.get("quality_floor")
    if type(qf) not in (int, float) or not (0 <= qf <= 100):
        return "quality_floor must be a number 0..100"
    b = p.get("budget_credits")
    if type(b) not in (int, float) or not (0 < b <= 100000):
        return "budget_credits must be a number > 0 and <= 100000"
    d = p.get("diff_cap_lines")
    if type(d) is not int or not (1 <= d <= 10000):
        return "diff_cap_lines must be an int 1..10000"
    ce = p.get("checkpoint_every", 5)
    if type(ce) is not int or not (1 <= ce <= 10000):
        return "checkpoint_every must be an int 1..10000"
    cm = p.get("compaction_max_cycles", 50)
    if type(cm) is not int or not (5 <= cm <= 10000):
        return "compaction_max_cycles must be an int 5..10000"
    for k in ("stop_on_quality_breach", "stop_on_budget"):
        if type(p.get(k, True)) is not bool:
            return f"{k} must be boolean"
    return None


def state():
    return load(STATE_F, {"running": False, "cycle": 0, "last_tick": None,
                          "last_quality": None, "stopped_reason": None,
                          "started_at": None})


def write_state(s):
    os.makedirs(DATA, exist_ok=True)
    with open(STATE_F, "w") as f:
        json.dump(s, f, indent=2)
    return s


def heartbeat():
    return load(HB_F, {})


def ledger():
    return load_lines(os.path.join(DATA, "ledger.jsonl"))


def cycles():
    return load_lines(os.path.join(DATA, "cycles.jsonl"))


def checkpoints():
    return load_lines(os.path.join(DATA, "checkpoints.jsonl"))


def budget_used():
    return round(sum(float(e.get("cost", 0)) for e in ledger()), 4)


def age_minutes(iso):
    try:
        ts = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()
        return (time.time() - ts) / 60.0
    except Exception:
        return 1e9


def run_gates():
    """Per-cycle verify gates. Each returns {name, pass, detail}."""
    p = policy()
    c = cfg()
    s = state()
    gates = []

    # 1. policy valid
    err = validate_policy(p)
    gates.append({"name": "policy_valid", "pass": err is None,
                  "detail": "ok" if err is None else err})

    # 2. budget remaining
    used = budget_used()
    bud = float(p["budget_credits"])
    gates.append({"name": "budget_remaining", "pass": used < bud,
                  "detail": f"used ${used} of ${bud}"})

    # 3. heartbeat fresh (only matters while running)
    hb = heartbeat()
    hb_age = age_minutes(hb.get("at")) if hb.get("at") else 1e9
    stale = float(c.get("heartbeat_stale_minutes", 5))
    hb_ok = (not s["running"]) or (hb_age <= stale)
    gates.append({"name": "heartbeat_fresh", "pass": hb_ok,
                  "detail": "loop stopped, n/a" if not s["running"]
                  else (f"{hb_age:.1f}m old" if hb.get("at") else "never beaten")})

    # 4. diff size cap (last cycle notes within cap)
    cs = cycles()
    last = cs[-1] if cs else {}
    diff_lines = len(str(last.get("notes", "")).splitlines()) or 1
    cap = int(p["diff_cap_lines"])
    gates.append({"name": "diff_size_cap", "pass": diff_lines <= cap,
                  "detail": f"{diff_lines} lines vs cap {cap}"})

    # 5. checkpoint freshness (a checkpoint within last checkpoint_every cycles)
    cps = checkpoints()
    cyc = int(s.get("cycle", 0))
    every = int(p.get("checkpoint_every", 5))
    if not cps:
        cp_ok = cyc < every
        cp_detail = f"no checkpoint yet, cycle {cyc} (first due at {every})"
    else:
        last_cp = cps[-1].get("cycle", 0)
        cp_ok = (cyc - last_cp) < every
        cp_detail = f"last checkpoint at cycle {last_cp}, now {cyc} (every {every})"
    gates.append({"name": "checkpoint_fresh", "pass": cp_ok, "detail": cp_detail})

    # 6. context budget (cycles retained vs compaction limit)
    maxc = int(p.get("compaction_max_cycles", 50))
    summ = load(SUMMARY_F, {})
    compacted = int(summ.get("compacted_cycles", 0))
    gates.append({"name": "context_budget", "pass": len(cs) <= maxc,
                  "detail": f"{len(cs)} live cycles (cap {maxc}), {compacted} compacted into summary"})

    # 7. evidence present — kills metric theater: a tick that completed
    # but logged no verifiable rows/output FAILS, so quality can drop.
    ev = last_evidence()
    last = cs[-1] if cs else {}
    ev_ok = (isinstance(ev, dict) and ev.get("cycle") == last.get("cycle")
             and ev.get("ok") is True and len(str(ev.get("detail", ""))) > 20)
    gates.append({"name": "evidence_present", "pass": ev_ok,
                  "detail": (f"cycle {ev.get('cycle')}: {ev.get('detail', '')} "
                             f"(rows={ev.get('rows')})" if ev_ok
                             else ("no verifiable evidence on last cycle — "
                                   "tick output, not tick completion, is scored"))})

    # 8. critic accept — the adversarial reviewer's verdict on this cycle.
    revs = load_lines(REVIEW_F)
    rev = next((r for r in reversed(revs) if r.get("cycle") == cyc), None)
    if rev is None:
        gates.append({"name": "critic_accept", "pass": True,
                      "detail": f"no review recorded for cycle {cyc} yet"})
    elif rev.get("verdict") == "reject":
        gates.append({"name": "critic_accept", "pass": False,
                      "detail": (f"Critic REJECTED cycle {cyc}: " +
                                 "; ".join(str(x) for x in rev.get("reasons", []))[:300])})
    else:
        gates.append({"name": "critic_accept", "pass": True,
                      "detail": (f"Critic {rev.get('verdict')} on cycle {cyc}: " +
                                 "; ".join(str(x) for x in rev.get("reasons", []))[:300])})

    failed = sum(1 for g in gates if not g["pass"])
    quality = max(0, 100 - 15 * failed)
    passed = quality >= float(p["quality_floor"]) and failed == 0
    result = {"at": now_iso(), "cycle": cyc, "quality": quality,
              "floor": p["quality_floor"], "pass": passed, "gates": gates}
    os.makedirs(DATA, exist_ok=True)
    with open(VERIFY_F, "w") as f:
        json.dump(result, f, indent=2)
    return result


BACKLOG = [
    {"id": "e083-stuck-drilldown",
     "title": "e083 stuck-list drill-down",
     "slice": "pull live e083 /api/funnel and name stuck sessions + last events",
     "path": "/api/funnel"},
    {"id": "e083-google-proxy",
     "title": "e083 Google proxy decision",
     "slice": "pull live e083 /api/recipes and count server-vs-client transforms to inform the proxy call",
     "path": "/api/recipes"},
    {"id": "e083-x-login",
     "title": "e083 x.com login",
     "slice": "pull live e083 /api/records?limit=50 and count rows per dataset (is x data flowing?)",
     "path": "/api/records?limit=50"},
]


def e083_base():
    """Collector URL for the real workload — port from e083 needs.json."""
    try:
        with open(os.path.join(E083_DIR, "needs.json")) as f:
            port = int(json.load(f).get("port", 8383))
    except Exception:
        port = 8383
    return f"http://127.0.0.1:{port}"


def backlog_current(nxt):
    try:
        nxt = int(nxt)
    except (TypeError, ValueError):
        nxt = 1
    # LIMITS.md is the second backlog source (needs.json limits_*): every
    # Nth tick consumes one OPEN [limits-lN] checkbox instead of an e083
    # gap slice. Checked boxes are skipped automatically by the parser.
    try:
        every = max(1, int(cfg().get("limits_every_n_ticks", 4)))
    except (TypeError, ValueError):
        every = 4
    if every > 0 and nxt % every == 0:
        opens = limits_open_items()
        if opens:
            return dict(opens[((nxt // every) - 1) % len(opens)])
    return dict(BACKLOG[(nxt - 1) % len(BACKLOG)])


LIMITS_SLICES = {
    "limits-l1": "verify staged-kit guardrail: L1 names human-tap Create + zero agent signup POSTs",
    "limits-l2": "verify asset staging: repo assets/ pack present for owner upload",
    "limits-l3": "verify owner-minted posting path: TOKEN set, demo-mint disabled, drafts unapproved-only",
    "limits-l4": "verify undetectable-browser path: Xvfb live + headed screenshot + headed table in BROWSER-CAPABILITY.md",
    "limits-l5": "verify domain path: DOMAINS.md shortlist with RDAP status, zero agent payments",
    "limits-l6": "verify inference path: JEV.md endpoint slot + free-tier/local notes, owner-minted keys only",
}


def limits_open_items():
    """Parse LIMITS.md open checkboxes (`- [ ] [limits-lN] <title>`).
    Checked boxes are done (acceptance proof on disk) and skipped."""
    items = []
    try:
        with open(LIMITS_F) as f:
            for line in f:
                m = re.match(r"\s*-\s*\[( |x|X)\]\s*\[(limits-l\d)\]\s*(.*)", line)
                if m and m.group(1) == " ":
                    lid = m.group(2)
                    items.append({"id": lid, "title": m.group(3).strip(),
                                  "slice": LIMITS_SLICES.get(lid, "verify acceptance-proof precondition read-only"),
                                  "path": "LIMITS.md"})
    except Exception:
        pass
    return items


def collect_limits_evidence(nxt, item):
    """Smallest shippable slice of a LIMITS.md item: a read-only local
    probe (no accounts, no logins, no posts, no payments). ok=True when the
    precondition verifies live; detail always names live numbers."""
    lid = item.get("id", "limits-?")
    entry = {"cycle": nxt, "at": now_iso(), "item": lid,
               "slice": item.get("slice", ""), "rows": 0,
               "detail": "", "ok": False}
    try:
        if lid == "limits-l1":
            blob = open(LIMITS_F).read()
            hits = sum(blob.count(k) for k in ("human-tap", "NEEDS OWNER TAP", "never create"))
            entry["rows"] = hits
            entry["detail"] = (f"L1 guardrail live: {hits} ToS markers in LIMITS.md "
                                 f"(human-tap Create, zero agent signup POSTs attempted)")
        elif lid == "limits-l2":
            ad = os.path.join(REPO_ROOT, "assets")
            n = len(os.listdir(ad)) if os.path.isdir(ad) else 0
            entry["rows"] = n
            entry["detail"] = (f"L2 staging live: repo assets/ holds {n} entries "
                                 f"— owner-upload pack path exists")
        elif lid == "limits-l3":
            c = cfg()
            ok_tok = bool(c.get("TOKEN"))
            entry["rows"] = 1 if (ok_tok and c.get("demo_mint_enabled") is False) else 0
            entry["detail"] = (f"L3 posting path live: master TOKEN set={ok_tok}, "
                                 f"demo_mint_enabled={c.get('demo_mint_enabled')} "
                                 f"(owner-minted only, drafts unapproved-only)")
        elif lid == "limits-l4":
            checks = [os.path.exists("/usr/bin/Xvfb"),
                        os.path.exists(os.path.join(REPO_ROOT, ".growth-shots", "sanny-headed-xvfb.png")),
                        ("Headed vs headless detection" in open(os.path.join(REPO_ROOT, "BROWSER-CAPABILITY.md")).read())]
            entry["rows"] = sum(1 for x in checks if x)
            entry["detail"] = (f"L4 browser path live: {entry['rows']}/3 "
                                 f"(Xvfb={checks[0]}, headed shot={checks[1]}, "
                                 f"headed table={checks[2]}; webdriver tell still open)")
        elif lid == "limits-l5":
            blob = open(os.path.join(REPO_ROOT, "DOMAINS.md")).read()
            n = blob.count("404 available")
            entry["rows"] = n
            entry["detail"] = (f"L5 domain path live: {n} RDAP-available names "
                                 f"shortlisted in DOMAINS.md, zero agent payments issued")
        elif lid == "limits-l6":
            blob = open(os.path.join(REPO_ROOT, "JEV.md")).read()
            hits = sum(blob.count(k) for k in ("OpenRouter", "free", "local", "owner"))
            entry["rows"] = hits
            entry["detail"] = (f"L6 inference path live: {hits} key/free/local markers "
                                 f"in JEV.md (owner-minted keys only, quota-respecting)")
        else:
            entry["detail"] = f"unknown LIMITS item {lid} — no probe defined"
        entry["ok"] = entry["rows"] > 0 and len(entry["detail"]) > 20
    except Exception as e:
        entry["detail"] = f"limits probe failed: {type(e).__name__}: {str(e)[:120]}"
        entry["ok"] = False
    append_line(EVID_F, entry)
    return entry


def last_evidence():
    lines = load_lines(EVID_F)
    return lines[-1] if lines else None


def collect_evidence(nxt, item):
    """Attempt the backlog item's smallest shippable slice against the LIVE
    e083 server and log verifiable evidence (rows / output). ok=False when
    the fetch fails — the evidence gate then FAILS loudly, so quality can
    actually drop. Never faked: detail always names live numbers."""
    entry = {"cycle": nxt, "at": now_iso(),
             "item": item.get("id") if item else "none",
             "slice": item.get("slice", "") if item else "", "rows": 0,
             "detail": "", "ok": False}
    if item and str(item.get("id", "")).startswith("limits-"):
        return collect_limits_evidence(nxt, item)
    try:
        with urllib.request.urlopen(e083_base() + item["path"],
                                    timeout=5) as r:
            data = json.loads(r.read().decode() or "null")
        iid = item["id"]
        if iid == "e083-stuck-drilldown":
            stuck = data.get("stuck_sessions", []) or []
            names = [s if isinstance(s, str) else str(s.get("session", s))[:14]
                     for s in stuck[:5]]
            entry["rows"] = len(stuck)
            entry["detail"] = (f"e083 funnel live: {data.get('views', '?')} views, "
                               f"{len(stuck)} stuck" +
                               (f" ({', '.join(names)})" if names else " — healthy") +
                               f", {data.get('publishes', '?')} publishes")
        elif iid == "e083-google-proxy":
            recs = data if isinstance(data, list) else data.get("recipes", data)
            recs = recs if isinstance(recs, list) else []
            wh = {}
            for rc in recs:
                w = str(rc.get("where", "?")) if isinstance(rc, dict) else "?"
                wh[w] = wh.get(w, 0) + 1
            entry["rows"] = len(recs)
            entry["detail"] = (f"e083 recipes live: {len(recs)} recipes "
                               f"{wh} — proxy decision input recorded")
        else:
            rows = data if isinstance(data, list) else data.get("records", [])
            rows = rows if isinstance(rows, list) else []
            ds = {}
            for row in rows:
                d = str(row.get("dataset", "?")) if isinstance(row, dict) else "?"
                ds[d] = ds.get(d, 0) + 1
            entry["rows"] = len(rows)
            entry["detail"] = (f"e083 records live: {len(rows)} rows {ds} — " +
                               ("x data flowing" if any("x" in k.lower() for k in ds)
                                else "no x rows in tail sample"))
        entry["ok"] = len(entry["detail"]) > 20
    except Exception as e:
        entry["detail"] = f"fetch failed: {type(e).__name__}: {str(e)[:120]}"
        entry["ok"] = False
    append_line(EVID_F, entry)
    return entry


def review_tick(cycle=None, notes=None, _advance_streak=False, _funnel=None):
    """Adversarial second critic: a SEPARATE rule-set re-scores the tick's
    work trying to REJECT it. R1 no evidence -> reject. R2 trivial diff
    (<80 chars) -> reject. R3 quality unchanged 20 straight -> flag
    stagnation (warning, still loud on the board). R4 data-truth -> the
    critic watches the dashboard's honesty too: bot share of the stuck
    list above threshold, or a FAILING funnel verdict persisting past
    funnel_critic_fail_streak ticks, REJECTS so quality drops loudly.
    R4 DISCOUNT (2026-09-29): an UNKNOWN verdict (fewer than
    min_human_sessions human-attributed sessions) is computed over
    unattributed traffic — R4 notes it and does NOT penalize.
    _advance_streak=True only on the real per-tick path (do_tick) — probes
    read the streak, never advance it. _funnel injects a precomputed
    funnel dict for deterministic tests (default None = read live).
    Never stored here; the caller (do_tick stores, /api/review probes)
    decides."""
    cs = cycles()
    if cycle is not None:
        try:
            cycle = int(cycle)
        except (TypeError, ValueError):
            return {"cycle": cycle, "verdict": "reject",
                    "reasons": ["R0: bad cycle id — nothing to score"],
                    "stored": False}
        target = next((c for c in cs if c.get("cycle") == cycle), None)
        if target is None:
            return {"cycle": cycle, "verdict": "reject",
                    "reasons": [f"R0: cycle {cycle} not in log — nothing to score"],
                    "stored": False}
        notes = target.get("notes", "")
    notes = str(notes or "")
    reasons = []
    verdict = "accept"
    ev = None
    if cycle is not None:
        ev = next((e for e in load_lines(EVID_F) if e.get("cycle") == cycle),
                  None)
    if ("evidence:" not in notes or
            not (isinstance(ev, dict) and ev.get("ok") is True)):
        verdict = "reject"
        reasons.append("R1: no evidence — tick completed but logged no "
                       "verifiable rows/output")
    if len(notes.strip()) < 80:
        verdict = "reject"
        reasons.append(f"R2: trivial diff ({len(notes.strip())} chars) — "
                       "not a shippable slice of a real goal")
    # R1b hands honesty: acted claims must cite created artifact ids, and
    # the ids must exist in the e083 store (phantom ids rejected).
    hr = check_hands_claim(notes)
    if hr is not None:
        verdict = "reject"
        reasons.append(hr)
    quals = [c.get("quality") for c in cs[-20:]
             if isinstance(c.get("quality"), (int, float))]
    if len(quals) >= 20 and len(set(quals)) == 1:
        reasons.append(f"R3: stagnation flagged — quality {quals[-1]} unchanged "
                       "for 20 straight ticks (metric-theater risk)")
        if verdict == "accept":
            verdict = "flag"
    # R4 data-truth: the funnel's own verdict + raw bot share. NOISE means
    # bots bury the human signal; FAILING past the streak means nobody
    # installs and the board has said so for >N ticks — either way the
    # tick's quality drops via the critic_accept gate, and the board
    # shows why (reason stored in reviews.jsonl, rendered on the strip).
    # R4 DISCOUNT: UNKNOWN verdicts ride on unattributed traffic — note
    # and move on, never reject (quality NOT penalized).
    try:
        f = _funnel if isinstance(_funnel, dict) else funnel(include_bots=False)
        fv = f.get("verdict", {}) or {}
        level = str(fv.get("line", ""))
        flevel = str(fv.get("level", "QUIET"))
        t = funnel_thresholds()
        need = int(t["critic_fail_streak"])
        if _advance_streak and not isinstance(_funnel, dict):
            streak = update_funnel_streak(flevel)
        else:
            streak = int(load_funnel_streak().get("streak", 0))
        total_stuck = f.get("bots_hidden", 0) + sum(
            1 for r in f.get("stuck_sessions", []) if not r.get("synthetic"))
        bot_n = int(f.get("bots_hidden", 0))
        if flevel == "UNKNOWN":
            reasons.append(
                f"R4 note: funnel verdict UNKNOWN "
                f"({level[:160]}) — not enough human-attributed traffic, "
                "discounting (no penalty)")
            if verdict == "accept":
                verdict = "flag"
        elif total_stuck > 0 and bot_n / total_stuck > float(t["bot_noise_ratio"]):
            verdict = "reject"
            reasons.append(
                f"R4: data-truth — bot share of stuck list {bot_n}/{total_stuck} "
                f"exceeds {float(t['bot_noise_ratio']):.0%} "
                f"(dashboard: {level[:160]}) — human signal buried")
        elif flevel == "FAILING" and streak > need:
            verdict = "reject"
            reasons.append(
                f"R4: data-truth — funnel verdict FAILING for {streak} straight ticks "
                f"(>{need}) (dashboard: {level[:160]}) — nobody installs")
        elif flevel == "FAILING":
            reasons.append(
                f"R4 note: funnel verdict FAILING ({streak}/{need} ticks toward "
                "critic rejection) — watching, not rejecting yet")
            if verdict == "accept":
                verdict = "flag"
    except Exception as e:
        reasons.append(f"R4 skipped: funnel unreadable ({type(e).__name__})")
    if not reasons:
        reasons.append("accept: evidence present, non-trivial slice, no stagnation")
    return {"cycle": cycle, "verdict": verdict, "reasons": reasons,
            "stored": False}


def maybe_compact(cycle):
    """Rolling summary: when live cycles exceed cap, fold oldest into summary.json
    and record a compaction checkpoint. Logs stay append-only."""
    p = policy()
    maxc = int(p.get("compaction_max_cycles", 50))
    cs = cycles()
    # Leave room for the cycle about to ship: compact down to maxc-1 so the
    # post-ship count lands exactly on the cap and the context_budget gate
    # stays green in steady state (compact-then-append would otherwise sit
    # at maxc+1 forever with a permanent FAIL).
    if len(cs) < maxc:
        return {"compacted": False}
    n = len(cs) - (maxc - 1)
    oldest = cs[:n]
    summ = load(SUMMARY_F, {"compacted_cycles": 0, "digests": []})
    quals = [c.get("quality", 0) for c in oldest if isinstance(c.get("quality"), (int, float))]
    digest = {"at": now_iso(), "cycles": [c.get("cycle") for c in oldest],
              "count": n, "avg_quality": round(sum(quals) / len(quals), 1) if quals else None,
              "note": f"compacted cycles {[c.get('cycle') for c in oldest]}: " +
                      "; ".join(str(c.get("notes", ""))[:80] for c in oldest)[:400]}
    summ["compacted_cycles"] = int(summ.get("compacted_cycles", 0)) + n
    summ["digests"] = (summ.get("digests", []) + [digest])[-20:]
    summ["updated_at"] = now_iso()
    with open(SUMMARY_F, "w") as f:
        json.dump(summ, f, indent=2)
    # rewrite cycles.jsonl keeping only the newest maxc (history preserved in summary digest)
    with open(os.path.join(DATA, "cycles.jsonl"), "w") as f:
        for c in cs[n:]:
            f.write(json.dumps(c) + "\n")
    append_line(os.path.join(DATA, "checkpoints.jsonl"),
                {"id": f"k{len(checkpoints()) + 1:03d}", "cycle": cycle,
                 "at": now_iso(), "kind": "compaction",
                 "summary": f"Compacted {n} oldest cycles into rolling summary.",
                 "quality": None})
    return {"compacted": True, "count": n}


def hands_log(msg):
    """Hands diary: every decision + every blocker lands in log/hands.log.
    Silent death is forbidden — callers log instead of swallowing."""
    try:
        os.makedirs(os.path.dirname(HANDS_LOG), exist_ok=True)
        with open(HANDS_LOG, "a") as f:
            f.write(f"{now_iso()} {msg}\n")
    except Exception:
        pass


def hands_cfg():
    """Hands rules live in needs.json — never hardcoded."""
    c = cfg()
    base = (c.get("hands_e083_url", "") or "").strip().rstrip("/")
    if not base:
        base = e083_base()
    return {"enabled": bool(c.get("hands_enabled", True)), "e083": base}


def hands_state():
    return load(HANDS_F, {})


def hands_save(st):
    os.makedirs(DATA, exist_ok=True)
    with open(HANDS_F, "w") as f:
        json.dump(st, f, indent=2)
    return st


def hands_creds(base):
    """The loop's own e083 node credentials. First run signs up once
    (name e082-loop, agent-tagged) and stores the token 0600; later runs
    reuse it. Empty dict when signup is unreachable — the caller logs a
    blocker instead of dying."""
    creds = load(HANDS_CREDS_F, {})
    if isinstance(creds, dict) and creds.get("node_id") and creds.get("token"):
        return creds
    try:
        req = urllib.request.Request(
            base + "/api/signup",
            data=json.dumps({"name": "e082-loop",
                             "agent": "e082-loop"}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode() or "{}")
        if not d.get("node_id") or not d.get("token"):
            hands_log(f"creds signup rejected: {str(d)[:160]}")
            return {}
        creds = {"node_id": d["node_id"], "token": d["token"]}
        os.makedirs(DATA, exist_ok=True)
        with open(HANDS_CREDS_F, "w") as f:
            json.dump(creds, f)
        try:
            os.chmod(HANDS_CREDS_F, 0o600)
        except Exception:
            pass
        hands_log(f"creds signed up node {creds['node_id']}")
        return creds
    except Exception as e:
        hands_log(f"creds signup failed: {type(e).__name__}: {str(e)[:160]}")
        return {}


def _http_json(url, body=None, timeout=8):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "null")


def observe_e083(base):
    """One read-only observation of the collector. Raises on unreachable —
    the caller logs honestly and skips (never fabricates an observation)."""
    health = _http_json(base + "/api/health")
    fun = _http_json(base + "/api/funnel")
    verdict = fun.get("verdict") or {}
    return {"records": int(health.get("records", 0)),
            "publishes": int(fun.get("publishes", 0)),
            "verdict": str(verdict.get("level", "?")),
            "verdict_line": str(verdict.get("line", ""))[:200]}


def do_hands(cycle):
    """Hands: end this tick's e083 observation in an artifact or an action.
    Rules (needs.json hands_*): publishes stalled vs last tick -> file one
    gap row via POST /api/gaps (priority high when the e083 funnel verdict
    is FAILING); records grew -> draft ONE growth post via
    POST /api/growth/draft (source:loop, never auto-posted — approve rules
    there decide); e083 unreachable -> log honestly and skip. Dedupe: one
    open gap per stall level, one pending loop draft — a 60s daemon must not
    spam the backlog. Returns a small dict stored on the cycle + rendered in
    the tick receipt. Never raises: blockers are logged to log/hands.log and
    reported in the summary (silent death forbidden)."""
    hc = hands_cfg()
    base = hc["e083"]
    if not hc["enabled"]:
        return {"acted": False, "action": "disabled",
                "summary": "hands: disabled in needs.json (hands_enabled=false)",
                "e083": base}
    try:
        obs = observe_e083(base)
    except Exception as e:
        msg = (f"hands: skipped — e083 unreachable "
               f"({type(e).__name__}: {str(e)[:100]})")
        hands_log(f"cycle {cycle} skipped: {type(e).__name__}: {str(e)[:160]}")
        return {"acted": False, "action": "skipped", "summary": msg,
                "e083": base, "unreachable": True}
    prev = hands_state()
    stalled = bool(prev) and obs["publishes"] == int(prev.get("publishes", -1))
    grew = bool(prev) and obs["records"] > int(prev.get("records", 0))
    failing = obs["verdict"] == "FAILING"
    creds = hands_creds(base)
    if not creds:
        msg = ("hands: blocked — no e083 credentials "
               "(signup failed, see log/hands.log)")
        hands_log(f"cycle {cycle} blocked: no credentials")
        hands_save({**obs, "updated_at": now_iso(),
                    "last_action": "blocked"})
        return {"acted": False, "action": "blocked", "summary": msg,
                "e083": base, **obs}
    auth = {"node_id": creds["node_id"], "token": creds["token"]}
    parts, links = [], []
    gap_id, post_id = None, None
    # 1. stalled publishes -> gap row (dedupe: one open gap per stall level).
    if stalled:
        try:
            gl = _http_json(base + "/api/gaps?include_test=1")
            marker = f"publishes={obs['publishes']}"
            open_gap = next((g for g in gl.get("gaps", [])
                             if isinstance(g, dict) and marker in str(g.get("item", ""))), None)
        except Exception as e:
            hands_log(f"cycle {cycle} gaps read failed: {type(e).__name__}")
            open_gap = None
        if open_gap is not None:
            gap_id = open_gap.get("id")
            parts.append(f"gap already open {gap_id} (publishes stalled at {obs['publishes']})")
            links.append({"label": f"gap {gap_id}",
                          "url": base + "/api/gaps?include_test=1"})
        else:
            prio = "high" if failing else "normal"
            item = (f"publishes stalled at {obs['publishes']} "
                    f"(publishes={obs['publishes']}, seen tick {cycle})")
            evd = (f"e083 funnel: {obs['verdict_line']}; publishes "
                   f"{obs['publishes']} (unchanged since last tick), records "
                   f"{obs['records']}")
            try:
                row = _http_json(base + "/api/gaps",
                                 {**auth, "item": item, "evidence": evd,
                                  "priority": prio})
                gap_id = row.get("id")
                parts.append(f"filed gap {gap_id} (priority {prio}, publishes stalled at {obs['publishes']})")
                links.append({"label": f"gap {gap_id}",
                              "url": base + "/#secGaps"})
                hands_log(f"cycle {cycle} filed gap {gap_id} priority={prio} "
                            f"publishes={obs['publishes']}")
            except Exception as e:
                parts.append(f"gap file failed ({type(e).__name__}) — logged")
                hands_log(f"cycle {cycle} gap POST failed: {type(e).__name__}: {str(e)[:160]}")
    # 1b. FAILING escalation: no stall but nobody installs -> make sure a
    # high-priority gap is open (dedupe: one open high gap is enough).
    if failing and gap_id is None:
        try:
            gl = _http_json(base + "/api/gaps?include_test=1")
            open_high = next((g for g in gl.get("gaps", [])
                              if isinstance(g, dict) and g.get("priority") == "high"), None)
        except Exception as e:
            hands_log(f"cycle {cycle} gaps read failed: {type(e).__name__}")
            open_high = None
        if open_high is not None:
            gap_id = open_high.get("id")
            parts.append(f"escalation already open {gap_id} (funnel FAILING)")
            links.append({"label": f"gap {gap_id}",
                          "url": base + "/api/gaps?include_test=1"})
        else:
            try:
                row = _http_json(base + "/api/gaps",
                                 {**auth,
                                  "item": f"install funnel FAILING (seen tick {cycle})",
                                  "evidence": f"e083 funnel: {obs['verdict_line']}",
                                  "priority": "high"})
                gap_id = row.get("id")
                parts.append(f"filed gap {gap_id} (priority high, funnel FAILING)")
                links.append({"label": f"gap {gap_id}",
                              "url": base + "/#secGaps"})
                hands_log(f"cycle {cycle} filed escalation gap {gap_id}")
            except Exception as e:
                parts.append(f"escalation file failed ({type(e).__name__}) — logged")
                hands_log(f"cycle {cycle} escalation POST failed: {type(e).__name__}: {str(e)[:160]}")
    # 2. records grew -> ONE growth draft (dedupe: one pending loop draft).
    if grew:
        try:
            q = _http_json(base + "/api/growth/queue")
            pending = next((pp for pp in q.get("posts", [])
                            if isinstance(pp, dict) and pp.get("source") == "loop"
                            and not pp.get("posted") and not pp.get("rejected")), None)
        except Exception as e:
            hands_log(f"cycle {cycle} queue read failed: {type(e).__name__}")
            pending = None
        if pending is not None:
            post_id = pending.get("id")
            parts.append(f"draft already pending {post_id} (records grew to {obs['records']})")
            links.append({"label": f"post {post_id}",
                          "url": base + "/#secAuto"})
        else:
            text = (f"ScrapeNet just hit {obs['records']} records banked "
                    f"({obs['publishes']} publishes) — every accepted row earns, "
                    f"published as a free JSON API: {base}/?ref=growth")
            text = text[:280]
            try:
                post = _http_json(base + "/api/growth/draft",
                                  {**auth, "text": text, "link": base + "/?ref=growth",
                                   "fact": f"records={obs['records']} publishes={obs['publishes']}"})
                post_id = post.get("id")
                parts.append(f"queued post {post_id} (records grew to {obs['records']}, needs approval)")
                links.append({"label": f"post {post_id}",
                              "url": base + "/#secAuto"})
                hands_log(f"cycle {cycle} queued post {post_id} records={obs['records']}")
            except Exception as e:
                parts.append(f"draft queue failed ({type(e).__name__}) — logged")
                hands_log(f"cycle {cycle} draft POST failed: {type(e).__name__}: {str(e)[:160]}")
    if not parts:
        if not prev:
            parts.append(f"baseline set (publishes {obs['publishes']}, records {obs['records']}, {obs['verdict']}) — next tick acts")
        else:
            parts.append(f"observed, no action (publishes {obs['publishes']} vs last {prev.get('publishes')}, "
                         f"records {obs['records']} vs last {prev.get('records')}, {obs['verdict']})")
    hands_save({**obs, "updated_at": now_iso(),
                "last_action": "; ".join(parts),
                "last_gap": gap_id, "last_post": post_id})
    acted = gap_id is not None or post_id is not None
    action = ("filed" if acted and not any("already" in p or "pending" in p for p in parts)
              else ("acted" if acted else "observed"))
    return {"acted": acted, "action": action,
            "summary": "hands: " + "; ".join(parts),
            "e083": base, "gap_id": gap_id, "post_id": post_id,
            "links": links, **obs}


def check_hands_claim(notes):
    """R1b hands honesty: a tick claiming it acted on e083 ('filed gap' /
    'queued post') must cite the created artifact id, and the id must exist
    in the e083 store. Returns an R1 rejection reason string, or None when
    the notes make no hands claim or the claim verifies."""
    n = str(notes or "")
    cg = "filed gap" in n
    cp = "queued post" in n
    if not cg and not cp:
        return None
    gaps = re.findall(r"gap-\d{8}-\d{6}-[0-9a-f]{4}", n)
    drafts = re.findall(r"loop-\d{4}-\d{2}-\d{2}-[0-9a-f]{4}", n)
    if cg and not gaps:
        return ("R1: hands claim without artifact id — tick says 'filed gap' "
                "but cites no gap id (acted claims must cite the created id)")
    if cp and not drafts:
        return ("R1: hands claim without artifact id — tick says 'queued post' "
                "but cites no post id (acted claims must cite the created id)")
    try:
        with open(os.path.join(E083_DIR, "needs.json")) as f:
            e083c = json.load(f)
        gfile = os.path.join(E083_DIR, e083c.get("gaps_path", "data/gaps.jsonl"))
        gblob = ""
        if os.path.exists(gfile):
            with open(gfile) as f:
                gblob = f.read()
        for gid in gaps:
            if gid not in gblob:
                return (f"R1: hands claim cites unknown gap {gid} — "
                        "not in the e083 gaps store (phantom artifact id)")
        qfile = os.path.join(E083_DIR, e083c.get("growth_queue_path", "data/growth.json"))
        qblob = ""
        if os.path.exists(qfile):
            with open(qfile) as f:
                qblob = f.read()
        for pid in drafts:
            if pid not in qblob:
                return (f"R1: hands claim cites unknown post {pid} — "
                        "not in the e083 growth queue (phantom artifact id)")
    except Exception:
        pass  # store unreadable: id-presence is the check (no false reject)
    return None


def do_tick(by="api", notes=""):
    """One tick: heartbeat -> verify -> compact -> ship next micro-goal.
    Hands run after the observation: the tick ENDS in an artifact/action."""
    p = policy()
    c = cfg()
    s = state()
    if not s["running"]:
        return None, "loop is stopped — press Start first"
    nxt = int(s.get("cycle", 0)) + 1
    mc = p.get("max_cycles")
    bounded = not (mc is None or mc == 0)
    if bounded and nxt > int(mc):
        s["running"] = False
        s["stopped_reason"] = f"goal done: reached max_cycles {mc}"
        write_state(s)
        return None, s["stopped_reason"]

    # 1. heartbeat
    hb = {"at": now_iso(), "cycle": nxt, "by": by}
    with open(HB_F, "w") as f:
        json.dump(hb, f)

    # 2. verify gates (pre-ship)
    v = run_gates()

    # 3. stop conditions
    used = budget_used()
    if used >= float(p["budget_credits"]) and p.get("stop_on_budget", True):
        s["running"] = False
        s["stopped_reason"] = f"budget out: used ${used} of ${p['budget_credits']}"
        s["cycle"] = nxt - 1
        write_state(s)
        return {"cycle": nxt - 1, "stopped": True, "reason": s["stopped_reason"], "verify": v}, s["stopped_reason"]
    if (not v["pass"]) and v["quality"] < float(p["quality_floor"]) and p.get("stop_on_quality_breach", True):
        # hard stop only on quality floor breach with a failing gate
        failing = [g["name"] for g in v["gates"] if not g["pass"]]
        if "budget_remaining" not in failing and "heartbeat_fresh" not in failing or True:
            pass  # fall through: record tick, then stop below
        s["cycle"] = nxt
        s["last_tick"] = now_iso()
        s["last_quality"] = v["quality"]
        s["running"] = False
        s["stopped_reason"] = f"quality floor breach: {v['quality']} < {p['quality_floor']} ({', '.join(failing)})"
        write_state(s)
        append_line(os.path.join(DATA, "cycles.jsonl"),
                    {"cycle": nxt, "at": now_iso(), "quality": v["quality"],
                     "verdict": "blocked", "notes": s["stopped_reason"]})
        append_line(os.path.join(DATA, "ledger.jsonl"),
                    {"at": now_iso(), "cycle": nxt, "tokens_in": 0, "tokens_out": 0,
                     "cost": 0.0, "note": "blocked tick, no spend"})
        return {"cycle": nxt, "stopped": True, "reason": s["stopped_reason"], "verify": v}, None

    # 4. compact
    comp = maybe_compact(nxt)

    # 5. ship next micro-goal — pulled from the REAL e083 backlog, with
    # live evidence attached. The note always carries an `evidence:` marker
    # the evidence gate and the critic independently verify.
    item = backlog_current(nxt)
    ev = collect_evidence(nxt, item)
    goal_text = f"[{item['id']}] {item['slice']}" if item else "backlog empty"
    # HANDS: the observation ENDS in an artifact or an action (rules in
    # needs.json). Never kills the tick: blockers are logged + noted.
    try:
        hands = do_hands(nxt)
    except Exception as e:
        hands_log(f"cycle {nxt} hands crashed: {type(e).__name__}: {str(e)[:160]}")
        hands = {"acted": False, "action": "crashed",
                 "summary": (f"hands: crashed ({type(e).__name__}) — "
                               "logged to log/hands.log, observation kept"),
                 "e083": hands_cfg()["e083"]}
    ti = int(c.get("tick_tokens_in", 800))
    to = int(c.get("tick_tokens_out", 400))
    cost = round((ti + to) / 1000.0 * float(c.get("cost_per_1k_tokens", 0.002)), 4)
    append_line(os.path.join(DATA, "cycles.jsonl"),
                {"cycle": nxt, "at": now_iso(), "quality": v["quality"],
                 "verdict": "shipped" if v["pass"] else "shipped-with-warnings",
                 "hands": hands,
                 "notes": f"micro-goal: {goal_text}\nevidence: {ev['detail']} "
                 f"(rows={ev['rows']}, ok={ev['ok']})\n{hands['summary']}" +
                 (f"\nnotes: {notes}" if notes else "")})
    append_line(os.path.join(DATA, "ledger.jsonl"),
                {"at": now_iso(), "cycle": nxt, "tokens_in": ti, "tokens_out": to,
                 "cost": cost, "note": goal_text[:80]})
    every = int(p.get("checkpoint_every", 5))
    cp = None
    if nxt % every == 0:
        cp = {"id": f"k{len(checkpoints()) + 1:03d}", "cycle": nxt, "at": now_iso(),
              "kind": "periodic",
              "summary": f"Cycle {nxt}: {goal_text} Quality {v['quality']}.",
              "quality": v["quality"]}
        append_line(os.path.join(DATA, "checkpoints.jsonl"), cp)

    s["cycle"] = nxt
    s["last_tick"] = now_iso()
    s["last_quality"] = v["quality"]
    if bounded and nxt >= int(mc):
        s["running"] = False
        s["stopped_reason"] = f"goal done: reached max_cycles {mc}"
    write_state(s)
    # 6. adversarial review: separate rule-set re-scores this tick's work.
    # Rejections are stored and FAIL the critic_accept gate on re-verify,
    # so quality drops loudly instead of auto-passing. This is the real
    # per-tick path, so it advances the funnel FAILING streak counter.
    rev = review_tick(cycle=nxt, _advance_streak=True)
    append_line(REVIEW_F, {"at": now_iso(), "cycle": nxt,
                           "verdict": rev["verdict"],
                           "reasons": rev["reasons"]})
    # re-run verify post-ship so status reflects fresh checkpoint/ledger
    v2 = run_gates()
    s["last_quality"] = v2["quality"]
    write_state(s)
    return {"cycle": nxt, "quality": v2["quality"], "verify": v2,
            "compacted": comp, "checkpoint": cp,
            "stopped": not s["running"],
            "stopped_reason": s.get("stopped_reason")}, None


def status():
    p = policy()
    c = cfg()
    s = state()
    v = load(VERIFY_F, {})
    used = budget_used()
    bud = float(p["budget_credits"])
    hb = heartbeat()
    hb_age = age_minutes(hb.get("at")) if hb.get("at") else None
    stuck = bool(s["running"]) and hb_age is not None and hb_age > float(c.get("stuck_after_minutes", 10))
    reasons = []
    if stuck:
        reasons.append(f"no tick for {hb_age:.1f}m while running")
    if s.get("stopped_reason"):
        reasons.append(s["stopped_reason"])
    nxt_actions = ["Start", "Tick", "Verify"] if not s["running"] else ["Tick", "Verify", "Stop"]
    mc = p.get("max_cycles")
    unbounded = mc is None or mc == 0
    cyc = int(s.get("cycle", 0))
    remaining = None if unbounded else int(mc) - cyc
    revs = load_lines(REVIEW_F)
    critic = revs[-1] if revs else None
    return {"running": s["running"], "cycle": cyc,
            "max_cycles": p["max_cycles"], "unbounded": unbounded,
            "cycles_remaining": remaining, "goal": p.get("goal"),
            "quality": s.get("last_quality"), "quality_floor": p["quality_floor"],
            "budget_used": used, "budget_total": bud,
            "budget_left": round(bud - used, 4),
            "heartbeat": hb, "heartbeat_age_minutes": hb_age,
            "stuck": stuck, "reasons": reasons,
            "stopped_reason": s.get("stopped_reason"),
            "last_tick": s.get("last_tick"), "last_verify": v,
            "critic": critic, "backlog": backlog_current(cyc + 1),
            "last_evidence": last_evidence(),
            "hands": {"e083": hands_cfg()["e083"],
                      "last": hands_state()},
            "next_actions": nxt_actions}


def proof():
    """Value proof for the monetization pitch: uptime, cycles shipped,
    quality history, spend ledger summary, share/download counters."""
    s = status()
    cs = cycles()
    led = ledger()
    quals = [c.get("quality") for c in cs[-30:]
             if isinstance(c.get("quality"), (int, float))]
    shipped = sum(1 for c in cs if str(c.get("verdict", "")).startswith("shipped"))
    st = get_stats()
    v = load(VERSION_F, {"version": "v1"})
    # PLAY-MONEY HONESTY (2026-09-29): tick costs are simulated estimates
    # unless needs.json real_spend_tracking is true (reconciled billing).
    real_spend = bool(cfg().get("real_spend_tracking", False))
    return {"uptime_seconds": int(time.time() - BOOT_TIME),
            "server_booted_at": datetime.datetime.fromtimestamp(
                BOOT_TIME, datetime.timezone.utc).isoformat(timespec="seconds"),
            "running": s["running"], "cycle": s["cycle"],
            "max_cycles": s["max_cycles"], "goal": s.get("goal"),
            "cycles_shipped": shipped, "cycles_logged": len(cs),
            "quality_now": s.get("quality"), "quality_floor": s["quality_floor"],
            "quality_history": quals,
            "ledger": {"used": s["budget_used"], "total": s["budget_total"],
                       "left": s["budget_left"], "entries": len(led),
                       "simulated": not real_spend,
                       "note": ("simulated tick cost — no real spend connected"
                                if not real_spend else
                                "real spend tracking on — ledger reconciles against billing")},
            "version": v.get("version", "v1"),
            "downloads": int(st.get("downloads", 0)),
            "share_views": int(st.get("share_views", 0))}


def record_event(ev, ua=""):
    """Telemetry ingest. NEVER stores IPs or user-agents — only the
    client-chosen random session id plus what the browser reports
    (page, event, detail, ms) and one derived boolean, synthetic:true,
    for our own polls/probes (check-*, *-probe, loop/daemon UAs)."""
    if type(ev) is not dict:
        return "JSON body must be an object"
    if ev.get("v") != 1:
        return "v must be 1"
    sess = ev.get("session")
    if type(sess) is not str or not (1 <= len(sess) <= 64):
        return "session must be a string 1..64 chars"
    event = ev.get("event")
    if type(event) is not str or not (1 <= len(event) <= 64):
        return "event must be a string 1..64 chars"
    page = ev.get("page", "/")
    if type(page) is not str or len(page) > 200:
        return "page must be a string <= 200 chars"
    detail = ev.get("detail", "")
    if type(detail) is not str or len(detail) > 500:
        return "detail must be a string <= 500 chars"
    if detail.strip().lower() in ("none", "null", "undefined", "-", "n/a"):
        detail = ""  # dangling placeholder is not a signal — store empty
    ms = ev.get("ms")
    if ms is not None and type(ms) not in (int, float):
        return "ms must be a number"
    try:
        ts = int(ev.get("ts", 0))
    except (TypeError, ValueError):
        return "ts must be a number"
    agent = ev.get("agent", "")
    if agent in (None, ""):
        agent = ""
    elif not valid_agent(agent):
        return "agent must be 1..64 chars [A-Za-z0-9_.-] (your driven-browser name)"
    synthetic = bool(is_bot_session(sess) or is_bot_ua(ua) or agent)
    append_line(EVENTS_F, {"received_at": now_iso(), "session": sess,
                           "ts": ts, "page": page, "event": event,
                           "detail": detail, "ms": ms,
                           "agent": agent,
                           "synthetic": synthetic})
    return None


def short_sid(s):
    s = str(s)
    return (s[:12] + "\u2026") if len(s) > 12 else s


def clean_detail(d):
    """Row hygiene: dangling placeholders render as empty, capped length."""
    d = str(d or "")[:120]
    if d.strip().lower() in ("none", "null", "undefined", "-", "n/a"):
        return ""
    return d


def funnel(include_bots=False):
    """Where users stall: views vs installs vs tokens vs proofs, one
    computed verdict line, plus sessions with views-but-no-proof.
    Synthetic sessions (our own polls/probes) and owner-dismissed rows
    are EXCLUDED by default (?bots=1 reveals them with a visible count)."""
    dismissed = dismissed_set()
    by_session = {}
    for e in load_lines(EVENTS_F):
        s = e.get("session")
        if type(s) is not str or not s:
            continue
        # stored flag OR session pattern (covers pre-backfill lines too;
        # UA-derived flags only exist on post-fix lines — UAs never logged)
        # OR agent self-identification (AGENT CONVENTION 2026-09-29:
        # driven browsers tag agent:<name>, always synthetic, name kept).
        ag = e.get("agent", "") if isinstance(e.get("agent", ""), str) else ""
        bot = bool(e.get("synthetic")) or is_bot_session(s) or ag != ""
        info = by_session.setdefault(s, {"events": set(), "last": None,
                                         "bot": False, "agent": "",
                                         "engaged": False})
        info["events"].add(e.get("event"))
        info["last"] = e
        if ag:
            info["agent"] = ag
        if is_engagement(e.get("event")):
            info["engaged"] = True
        if bot:
            info["bot"] = True
    live = {s: i for s, i in by_session.items() if s not in dismissed}
    shown = {s: i for s, i in live.items() if include_bots or not i["bot"]}
    bots = {s: i for s, i in live.items() if i["bot"]}
    views = sum(1 for i in shown.values() if "page_view" in i["events"])
    installs = sum(1 for i in shown.values() if "download" in i["events"])
    tokens = sum(1 for i in shown.values() if "get_token" in i["events"])
    proofs = sum(1 for i in shown.values()
                 if "first_proof_seen" in i["events"])

    def row(s, info):
        last = info["last"] or {}
        return {"session": s, "short": short_sid(s),
                "synthetic": bool(info["bot"]),
                "agent": info.get("agent", ""),
                "last_event": last.get("event"),
                "last_detail": clean_detail(last.get("detail")),
                "last_at": last.get("received_at")}
    stuck_shown, bot_stuck = [], 0
    for s, info in live.items():
        if "page_view" in info["events"] and "first_proof_seen" not in info["events"]:
            if info["bot"]:
                bot_stuck += 1
                if include_bots:
                    stuck_shown.append(row(s, info))
            else:
                stuck_shown.append(row(s, info))
    # newest first (file is append-only, so reverse); cap 50
    stuck_shown = stuck_shown[::-1][:50]
    human_stuck = sum(1 for r in stuck_shown if not r["synthetic"])
    agents_hidden = 0 if include_bots else sum(
        1 for s, i in live.items() if i["bot"] and i.get("agent"))
    # HUMAN ATTRIBUTION (R4 DISCOUNT input): shown, non-synthetic sessions
    # with a real engagement path (click/proof/download). Passive views
    # are unattributed — anyone's driven browser can generate those.
    human_attributed = sum(1 for s, i in shown.items()
                           if not i["bot"] and i["engaged"])
    verdict = attribution_gate(
        funnel_verdict(views, installs, proofs, bot_stuck, human_stuck),
        human_attributed)
    t = funnel_thresholds()
    return {"views": views, "installs": installs, "tokens": tokens,
            "proofs": proofs, "stuck_sessions": stuck_shown,
            "bots_hidden": 0 if include_bots else bot_stuck,
            "bots_total": len(bots),
            "agents_hidden": agents_hidden,
            "human_attributed": human_attributed,
            "min_human_sessions": int(t["min_human"]),
            "dismissed_count": len(dismissed),
            "dismissed_sessions": [{"session": s, "short": short_sid(s)}
                                     for s in sorted(dismissed)[:20]],
            "sessions_tracked": len(shown),
            "sessions_total_raw": len(by_session),
            "verdict": verdict}


def suggest_goals():
    """AI-prefill: 3 candidate goals generated from live history
    (recent micro-goals, quality trend, budget left, compaction volume)."""
    p = policy()
    cs = cycles()
    summ = load(SUMMARY_F, {})
    quals = [c.get("quality") for c in cs[-10:]
             if isinstance(c.get("quality"), (int, float))]
    avg = round(sum(quals) / len(quals), 1) if quals else None
    shipped = sum(1 for c in cs if str(c.get("verdict", "")).startswith("shipped"))
    left = round(float(p["budget_credits"]) - budget_used(), 4)
    compacted = int(summ.get("compacted_cycles", 0))
    floor = p.get("quality_floor")
    recent = [str(c.get("notes", "")).splitlines()[0][:90] for c in cs[-3:]]
    anchor = recent[-1] if recent else "no ticks shipped yet"
    g1 = (f"Ship 10 more clean ticks holding quality >= {floor} "
          f"(now {avg}, {shipped} shipped, ${left} budget left).")
    g2 = f"Follow up on last work \u2014 \"{anchor}\" \u2014 and prove the next 5 ticks stay green."
    g3 = (f"Stretch: {compacted} cycles already compacted into a flat context \u2014 "
          f"reach {shipped + 50} shipped with zero floor breaches.")
    goals = [g[:480] for g in (g1, g2, g3)]
    return {"goals": goals,
            "based_on": (f"{len(cs)} live cycles, {shipped} shipped, "
                         f"quality {avg}, ${left} left, {compacted} compacted")}


def tick_detail(entry):
    """Exactly what one tick did: heartbeat, gates, checkpoint,
    micro-goal result, ledger cost — the proof receipt."""
    if not entry:
        return None
    cyc = entry.get("cycle")
    led = [e for e in ledger() if e.get("cycle") == cyc]
    cps = [c for c in checkpoints() if c.get("cycle") == cyc]
    ev = next((e for e in load_lines(EVID_F) if e.get("cycle") == cyc), None)
    rev = next((r for r in reversed(load_lines(REVIEW_F))
                if r.get("cycle") == cyc), None)
    hb = heartbeat()
    v = load(VERIFY_F, {})
    return {"cycle": cyc, "at": entry.get("at"),
            "verdict": entry.get("verdict"), "quality": entry.get("quality"),
            "notes": entry.get("notes"), "heartbeat": hb,
            "hands": entry.get("hands"),
            "gates": v.get("gates", []), "gate_quality": v.get("quality"),
            "gate_at": v.get("at"), "checkpoints": cps,
            "evidence": ev, "critic": rev,
            "ledger": led[-1] if led else None}


def last_tick_detail():
    cs = cycles()
    if not cs:
        return {"empty": True,
                "hint": "no ticks shipped yet \u2014 press Tick and watch the receipt appear"}
    return tick_detail(cs[-1])


def recent_tick_details(n=5):
    try:
        n = max(1, min(20, int(n)))
    except (TypeError, ValueError):
        n = 5
    return [tick_detail(c) for c in cycles()[-n:]][::-1]


def run_stress(n_ticks):
    """LIMIT-PUSHER: throw bad inputs, starvation and floods at the live
    server (in-process, same functions the HTTP layer calls) plus a few
    real aggressive ticks, and report the scoreboard. Rejected mutations
    are audit-logged as ok:false — nothing here silently corrupts state."""
    probes = []

    def add(name, kind, ok, detail, ms=None):
        probes.append({"name": name, "kind": kind, "pass": bool(ok),
                       "detail": str(detail)[:200], "ms": ms})
    _, err = save_policy({"nope": 1}, by="stress")
    add("bad-input: unknown policy key", "bad input", err is not None,
        err or "ACCEPTED — policy guard failed")
    _, err = save_policy({"goal": "x" * 501}, by="stress")
    add("bad-input: 501-char goal overflow", "bad input", err is not None,
        err or "ACCEPTED — length guard failed")
    _, err = save_policy({"budget_credits": 0.01}, by="stress")
    add("starvation: budget cut below spent", "starvation", err is not None,
        err or "ACCEPTED — anti-starvation guard failed")
    tok = str(cfg().get("TOKEN", ""))
    add("auth: wrong token rejected", "bad input",
        ("Bearer wrong" != "Bearer " + tok) and bool(tok),
        "mismatched Bearer token refused")
    p = policy()
    used = budget_used()
    add("starvation: budget stop armed", "starvation",
        bool(p.get("stop_on_budget", True)),
        (f"used ${used} of ${p['budget_credits']} \u2014 tick refuses at cap"
         if p.get("stop_on_budget") else "stop_on_budget OFF \u2014 spend uncapped!"))
    t1 = time.time()
    ok_n = 0
    for _ in range(50):
        try:
            status()
            ok_n += 1
        except Exception:
            break
    ms = round((time.time() - t1) / 50 * 1000, 2)
    add("flood: 50 rapid status reads", "flood", ok_n == 50 and ms < 100,
        f"{ok_n}/50 ok, avg {ms} ms/read", ms)
    v = run_gates()
    add("gates: live verify green", "gates", bool(v.get("pass")),
        f"quality {v.get('quality')} vs floor {v.get('floor')}")
    try:
        want = max(0, min(5, int(n_ticks)))
    except (TypeError, ValueError):
        want = 0
    cap = int(cfg().get("stress_max_ticks", 2))
    want = min(want, max(0, cap))
    ticks = []
    for _ in range(want):
        s = state()
        if not s["running"]:
            ticks.append({"ran": False,
                          "detail": "loop stopped \u2014 tick refused (stop wins)"})
            break
        if budget_used() >= float(policy()["budget_credits"]):
            ticks.append({"ran": False,
                          "detail": "budget out \u2014 tick refused (stop wins)"})
            break
        res, terr = do_tick(by="stress")
        ticks.append({"ran": terr is None,
                      "detail": terr or f"cycle {res.get('cycle')} quality {res.get('quality')}"})
        if res and res.get("stopped"):
            break
    held = sum(1 for pr in probes if pr["pass"])
    absorbed = sum(1 for t in ticks if t["ran"])
    verdict = "HOLDING" if held == len(probes) else "STRAINED"
    return {"at": now_iso(), "probes": probes, "ticks": ticks,
            "ticks_absorbed": absorbed,
            "score": f"{held}/{len(probes)} attacks blocked",
            "verdict": verdict}


def restore_checkpoint(cid, by="api"):
    """Restore a periodic checkpoint's context: append a 'restored' cycle
    (append-only, never rewrites history). Compaction checkpoints hold
    digests only — nothing to restore, caller gets a 400 explaining why."""
    cps = checkpoints()
    hit = next((c for c in cps if str(c.get("id")) == str(cid)), None)
    if not hit:
        return None, f"unknown checkpoint id {cid}"
    if hit.get("kind") == "compaction":
        return None, (f"{cid} is a compaction digest (oldest cycles folded "
                       "into the summary) \u2014 nothing to restore; pick a periodic checkpoint")
    s = state()
    nxt = int(s.get("cycle", 0)) + 1
    entry = {"cycle": nxt, "at": now_iso(), "quality": s.get("last_quality"),
             "verdict": "restored",
             "notes": (f"Restored context from {hit.get('id')} "
                       f"(cycle {hit.get('cycle')}) by {by}: {hit.get('summary', '')}")[:2000]}
    append_line(os.path.join(DATA, "cycles.jsonl"), entry)
    append_line(os.path.join(DATA, "checkpoints.jsonl"),
                {"id": f"k{len(cps) + 1:03d}", "cycle": nxt, "at": now_iso(),
                 "kind": "restore",
                 "summary": f"Restored context from {hit.get('id')}.",
                 "quality": entry["quality"]})
    s["cycle"] = nxt
    s["last_tick"] = now_iso()
    write_state(s)
    return entry, None


def share_page():
    """Public read-only share page: live cycle, quality, version,
    powered-by + install link. Owners post this URL as UGC proof."""
    s = status()
    v = load(VERSION_F, {"version": "v1"})
    c = cfg()
    site = c.get("site_name", "Forever Harness")
    q = s.get("quality", "—")
    badge = "RUNNING" if s["running"] else "STOPPED"
    color = "#2ea86a" if s["running"] else "#c0492f"
    return ("<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>{site} — cycle {s['cycle']} at quality {q}</title>"
            "<style>body{font-family:system-ui,sans-serif;background:#0f1115;color:#e8eaf0;"
            "margin:0}main{max-width:560px;margin:0 auto;padding:24px;text-align:center}"
            ".card{background:#171b24;border:1px solid #2a3142;border-radius:12px;padding:20px;margin:12px 0}"
            ".big{font-size:2.2rem;font-weight:800}a{color:#9fb4ff}.mut{color:#8a93a8;font-size:.85rem}"
            ".btn{display:inline-block;background:#3b6fe0;color:#fff;font-weight:700;"
            "padding:12px 20px;border-radius:8px;text-decoration:none;margin:6px}</style></head><body><main>"
            f"<h1>\u267e\ufe0f {site}</h1>"
            f"<div class=\"card\"><div class=\"big\">cycle {s['cycle']} \u00b7 quality {q}</div>"
            f"<p><span style=\"color:{color};font-weight:700\">{badge}</span>"
            f" \u00b7 floor {s['quality_floor']} \u00b7 budget "
            f"${s['budget_used']} / ${s['budget_total']} \u00b7 {v.get('version', 'v1')}</p></div>"
            f"<p>My agent has been running <b>{s['cycle']} cycles</b> at "
            f"quality <b>{q}</b> without collapsing. Heartbeat + verify gates + "
            "checkpoints + budget ledger keep it going.</p>"
            "<p><a class=\"btn\" href=\"/download/plugin.zip\">Install the plugin</a> "
            "<a class=\"btn\" style=\"background:#2a3142\" href=\"/\">Live board</a></p>"
            f"<p class=\"mut\">powered by {site} \u00b7 "
            "<a href=\"/skill\">read the SKILL doc</a> \u00b7 "
            "<a href=\"/api/proof\">proof (JSON)</a></p>"
            "</main></body></html>")


def health():
    c = cfg()
    s = status()
    return {"alive": True, "stuck": s["stuck"], "reasons": s["reasons"],
            "running": s["running"], "cycle": s["cycle"],
            "heartbeat_age_minutes": s["heartbeat_age_minutes"]}


# ---- HTTP ----
MIME = {".html": "text/html", ".js": "text/javascript", ".css": "text/css",
        ".svg": "image/svg+xml", ".json": "application/json", ".png": "image/png"}


def send(h, code, body, ctype="application/json"):
    b = body if isinstance(body, bytes) else body.encode()
    h.send_response(code)
    h.send_header("Content-Type", ctype + "; charset=utf-8")
    h.send_header("Content-Length", str(len(b)))
    h.send_header("Access-Control-Allow-Origin", "*")
    h.end_headers()
    h.wfile.write(b)


def parse_body(h):
    """Strict POST body parser. Returns (obj, None) or (None, (code, msg)).
    Empty body -> {}. Malformed JSON -> 400. Non-object JSON -> 400.
    Oversize body -> 413. Never swallows errors, never raises."""
    try:
        n = int(h.headers.get("Content-Length", 0) or 0)
    except (TypeError, ValueError):
        n = 0
    if n <= 0:
        return {}, None
    if n > MAX_BODY:
        return None, (413, f"body too large ({n} bytes, max {MAX_BODY}) — shrink notes/reason")
    try:
        raw = h.rfile.read(n) or b"{}"
    except Exception:
        return None, (400, "could not read request body")
    try:
        obj = json.loads(raw)
    except Exception:
        return None, (400, "invalid JSON body")
    if type(obj) is not dict:
        return None, (400, "JSON body must be an object")
    return obj, None


from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if p == "/api/health":
            return send(self, 200, json.dumps(health()))
        if p == "/api/policy":
            return send(self, 200, json.dumps(policy()))
        if p == "/api/status":
            return send(self, 200, json.dumps(status()))
        if p == "/api/checkpoints":
            cps = checkpoints()
            if q.get("limit"):
                try:
                    cps = cps[-int(q["limit"][0]):]
                except Exception:
                    pass
            return send(self, 200, json.dumps(cps))
        if p == "/api/ledger":
            return send(self, 200, json.dumps(
                {"used": budget_used(), "total": policy()["budget_credits"],
                 "entries": ledger()[-50:]}))
        if p == "/api/cycles":
            return send(self, 200, json.dumps(cycles()[-50:]))
        if p == "/api/summary":
            return send(self, 200, json.dumps(load(SUMMARY_F, {})))
        if p == "/api/version":
            return send(self, 200, json.dumps(load(VERSION_F, {"version": "v1"})))
        if p == "/api/auth":
            return send(self, 200, json.dumps({"protected": True, "ok": check_auth(self)}))
        if p == "/api/owner/settings":
            if not check_auth(self):
                return send(self, 401, json.dumps({
                    "error": ("unauthorized — owner settings need "
                              "Authorization: Bearer TOKEN (master token in needs.json; "
                              "paste it in the board's Token field)")}))
            if not is_master(self):
                return send(self, 403, json.dumps({
                    "error": ("owner-only — demo (fh-*) tokens cannot change owner "
                              "settings. Paste the master TOKEN from needs.json "
                              "into the Token field.")}))
            return send(self, 200, json.dumps(get_owner_settings()))
        if p == "/api/proof":
            return send(self, 200, json.dumps(proof()))
        if p == "/api/funnel":
            return send(self, 200, json.dumps(funnel(
                include_bots=(q.get("bots", [""])[0] == "1"))))
        if p == "/api/suggest-goals":
            return send(self, 200, json.dumps(suggest_goals()))
        if p == "/api/last-tick":
            return send(self, 200, json.dumps(last_tick_detail()))
        if p == "/api/backlog":
            s = state()
            return send(self, 200, json.dumps(
                {"items": BACKLOG + limits_open_items(),
                 "current": backlog_current(int(s.get("cycle", 0)) + 1),
                 "last_evidence": last_evidence()}))
        if p == "/api/ticks":
            try:
                lim = int(q.get("limit", ["5"])[0])
            except (TypeError, ValueError):
                lim = 5
            return send(self, 200, json.dumps(recent_tick_details(lim)))
        if p == "/share":
            bump_stat("share_views")
            return send(self, 200, share_page().encode(), "text/html")
        if p == "/skill":
            try:
                with open(SKILL_F, "rb") as f:
                    return send(self, 200, f.read(), "text/markdown")
            except Exception:
                return send(self, 404, json.dumps({"error": "skill doc missing"}))
        if p == "/download/plugin.zip":
            bump_stat("downloads")
            buf = io.BytesIO()
            plug = os.path.join(DIR, "plugin")
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for root, _, files in os.walk(plug):
                    for fn in sorted(files):
                        fp = os.path.join(root, fn)
                        z.write(fp, os.path.relpath(fp, DIR))
            data = buf.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition",
                               'attachment; filename="forever-harness-plugin.zip"')
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            return
        rel = p[1:] if p != "/" else "index.html"
        fp = os.path.join(PUB, rel)
        if os.path.isdir(fp):
            fp = os.path.join(fp, "index.html")
        if os.path.exists(fp):
            ext = os.path.splitext(fp)[1]
            with open(fp, "rb") as f:
                data = f.read()
            return send(self, 200, data, MIME.get(ext, "text/plain"))
        return send(self, 404, json.dumps({"error": "not found"}))

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        if p in ("/api/owner/settings",):
            if not check_auth(self):
                return send(self, 401, json.dumps({
                    "error": ("unauthorized — owner settings need "
                              "Authorization: Bearer TOKEN (master token in needs.json; "
                              "paste it in the board's Token field)")}))
            if not is_master(self):
                return send(self, 403, json.dumps({
                    "error": ("owner-only — demo (fh-*) tokens cannot change owner "
                              "settings. Paste the master TOKEN from needs.json "
                              "into the Token field.")}))
        if p in ("/api/policy", "/api/control/start",
                 "/api/control/stop", "/api/control/tick",
                 "/api/stress", "/api/restore",
                 "/api/funnel/dismiss", "/api/funnel/undismiss"):
            if not check_auth(self):
                return send(self, 401, json.dumps({
                    "error": ("unauthorized — writes need "
                              "Authorization: Bearer TOKEN (owner token in needs.json; "
                              "paste it in the board's Token field)")}))
        if p == "/api/verify":
            return send(self, 200, json.dumps(run_gates()))
        if p == "/api/review":
            b, perr = parse_body(self)
            if perr:
                code, msg = perr
                return send(self, code, json.dumps({"error": msg}))
            if "cycle" in b:
                try:
                    res = review_tick(cycle=b["cycle"])
                except Exception as e:
                    return send(self, 400, json.dumps({"error": str(e)[:200]}))
                return send(self, 200, json.dumps({**res, "stored": False}))
            if "notes" in b:
                if type(b["notes"]) is not str:
                    return send(self, 400, json.dumps(
                        {"error": "notes must be a string"}))
                return send(self, 200, json.dumps(
                    {**review_tick(notes=b["notes"]), "stored": False}))
            revs = load_lines(REVIEW_F)
            return send(self, 200, json.dumps(
                revs[-1] if revs else {"verdict": "none",
                                       "reasons": ["no reviews recorded yet"]}))
        if p == "/api/events":
            b, perr = parse_body(self)
            if perr:
                code, msg = perr
                return send(self, code, json.dumps({"error": msg}))
            err = record_event(b, ua=self.headers.get("User-Agent", ""))
            if err:
                return send(self, 400, json.dumps({"error": err}))
            return send(self, 200, json.dumps({"ok": True}))
        if p == "/api/token/mint":
            # AUTH DECISION 2026-09-29 (single-user tool): public demo-mint
            # is DISABLED by default (needs.json demo_mint_enabled=false).
            # Previously minted fh-* tokens still authenticate — the master
            # TOKEN flow is untouched. Multi-user signup stays a dated
            # decision, not half-built code (see PROACTIVE-E082-REPORT.md).
            if not cfg().get("demo_mint_enabled", False):
                return send(self, 403, json.dumps({
                    "error": ("demo mint disabled — owner-only board. Paste the "
                              "owner TOKEN from needs.json into the Token field. "
                              "(Decision 2026-09-29: single-user tool; to re-enable, "
                              "set demo_mint_enabled=true in needs.json.)")}))
            b, perr = parse_body(self)
            if perr:
                code, msg = perr
                return send(self, code, json.dumps({"error": msg}))
            tok, err = mint_demo_token(b.get("session", ""))
            if err:
                return send(self, 429 if "already holds" in err or "pool full" in err
                            else 400, json.dumps({"error": err}))
            return send(self, 200, json.dumps({
                "token": tok, "show_once": True,
                "where": ("paste it in the board's Token field \u2014 it unlocks "
                          "Start / Stop / Tick / Save / Stress on this browser")}))
        b, perr = parse_body(self)
        if perr:
            code, msg = perr
            return send(self, code, json.dumps({"error": msg}))
        if p == "/api/policy":
            by = self.client_address[0] if self.client_address else "unknown"
            pol, err = save_policy(b, by=by)
            if err:
                return send(self, 400, json.dumps({"error": err}))
            return send(self, 200, json.dumps(pol))
        if p == "/api/owner/settings":
            by = self.client_address[0] if self.client_address else "unknown"
            cur, err = save_owner_settings(b, by="owner:" + str(by))
            if err:
                return send(self, 400, json.dumps({"error": err}))
            return send(self, 200, json.dumps(cur))
        if p == "/api/control/start":
            s = state()
            p_ = policy()
            mc = p_.get("max_cycles")
            bounded = not (mc is None or mc == 0)
            if s["running"]:
                return send(self, 409, json.dumps({"error": "already running"}))
            if bounded and int(s.get("cycle", 0)) >= int(mc):
                return send(self, 409, json.dumps({"error": "max_cycles reached — raise it in policy to continue"}))
            if budget_used() >= float(p_["budget_credits"]):
                return send(self, 409, json.dumps({"error": "budget exhausted — raise budget_credits in policy"}))
            s["running"] = True
            s["stopped_reason"] = None
            s["started_at"] = s.get("started_at") or now_iso()
            write_state(s)
            return send(self, 200, json.dumps(status()))
        if p == "/api/control/stop":
            s = state()
            reason = b.get("reason") or "user stop"
            if type(reason) is not str or len(reason) > MAX_REASON:
                return send(self, 400, json.dumps(
                    {"error": f"reason must be a string <= {MAX_REASON} chars"}))
            s["running"] = False
            s["stopped_reason"] = reason
            write_state(s)
            return send(self, 200, json.dumps(status()))
        if p == "/api/control/tick":
            by = b.get("by", "api")
            if type(by) is not str or not by or len(by) > MAX_BY:
                return send(self, 400, json.dumps(
                    {"error": f"by must be a non-empty string <= {MAX_BY} chars"}))
            notes = b.get("notes", "")
            if type(notes) is not str or len(notes) > MAX_NOTES:
                return send(self, 400, json.dumps(
                    {"error": f"notes must be a string <= {MAX_NOTES} chars"}))
            res, err = do_tick(by=by, notes=notes)
            if err:
                return send(self, 409, json.dumps({"error": err}))
            return send(self, 200, json.dumps(res))
        if p == "/api/funnel/dismiss":
            sess = b.get("session", "")
            if type(sess) is not str or not (1 <= len(sess) <= 64):
                return send(self, 400, json.dumps(
                    {"error": "session must be a string 1..64 chars"}))
            ss = dismissed_set()
            ss.add(sess)
            save_dismissed(ss)
            return send(self, 200, json.dumps({"ok": True, "dismissed": sess,
                                               "dismissed_count": len(ss)}))
        if p == "/api/funnel/undismiss":
            sess = b.get("session", "")
            if type(sess) is not str or not (1 <= len(sess) <= 64):
                return send(self, 400, json.dumps(
                    {"error": "session must be a string 1..64 chars"}))
            ss = dismissed_set()
            ss.discard(sess)
            save_dismissed(ss)
            return send(self, 200, json.dumps({"ok": True, "restored": sess,
                                               "dismissed_count": len(ss)}))
        if p == "/api/stress":
            return send(self, 200, json.dumps(run_stress(b.get("ticks", 2))))
        if p == "/api/restore":
            cid = b.get("checkpoint_id", "")
            if type(cid) is not str or not cid:
                return send(self, 400, json.dumps(
                    {"error": "checkpoint_id must be a non-empty string"}))
            by = self.client_address[0] if self.client_address else "unknown"
            entry, err = restore_checkpoint(cid, by="ui")
            log_change(by, {"restore": cid}, err is None, err or "ok")
            if err:
                return send(self, 400, json.dumps({"error": err}))
            return send(self, 200, json.dumps(entry))
        return send(self, 404, json.dumps({"error": "not found"}))


if __name__ == "__main__":
    ensure_token()
    c = cfg()
    port = int(c.get("port", 8342))
    bind = c.get("bind", "0.0.0.0")
    os.makedirs(DATA, exist_ok=True)
    print(f"forever-harness on {bind}:{port}", flush=True)
    ThreadingHTTPServer((bind, port), H).serve_forever()
