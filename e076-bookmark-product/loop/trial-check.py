#!/usr/bin/env python3
"""T1 trial scorer: same task across versions, scored (0-100). See loop/TRIAL.md.
Usage: python3 loop/trial-check.py [--port P] [--save FILE]
Default: boot backend/server.py on an ephemeral port, run T1, kill it.
Stdlib only. No keys, no network beyond localhost.
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
BACKEND = os.path.join(EXP, "backend", "server.py")
PORT_ARG = None
SAVE = None
for i, a in enumerate(sys.argv[1:]):
    if a == "--port" and i + 1 < len(sys.argv[1:]):
        PORT_ARG = int(sys.argv[1:][i + 1])
    if a == "--save" and i + 1 < len(sys.argv[1:]):
        SAVE = sys.argv[1:][i + 1]

TOKEN = "Bearer t1-trial-token"
checks = []  # (group, name, pts, ok, detail)


def rec(group, name, pts, ok, detail=""):
    checks.append({"group": group, "name": name, "pts": pts if ok else 0,
                   "max": pts, "ok": bool(ok), "detail": str(detail)[:160]})


def req(port, method, path, body=None, headers=None):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json", "Authorization": TOKEN}
    h.update(headers or {})
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, dict(resp.headers), json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, dict(e.headers), json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}, {}
    except Exception as e:
        return 0, {}, {"_err": str(e)[:120]}


def run_api(port):
    T = [
        {"id": "t1", "text": "hello world backup one", "author": "alice",
         "created_at": "2026-01-01T00:00:00Z", "source": "xhr"},
        {"id": "t2", "text": "second tweet dom", "author": "bob",
         "created_at": "2026-01-02T00:00:00Z", "source": "dom"},
        {"id": "t3", "text": "third xhr note", "author": "carol",
         "created_at": "2026-01-03T00:00:00Z", "source": "xhr"},
        {"id": "t4", "text": "fourth dom note", "author": "dave",
         "created_at": "2026-01-04T00:00:00Z", "source": "dom"},
        {"id": "t1", "text": "DUPE dom must not overwrite xhr", "author": "mallory",
         "created_at": "2026-01-05T00:00:00Z", "source": "dom"},
    ]
    s, _, imp = req(port, "POST", "/v1/bookmarks/import", {"tweets": T})
    # 5 submitted, 1 dupe -> accepted 4, dupes 1, total 4
    rec("import", "accepted==4", 5, imp.get("accepted") == 4 and s == 200, imp)
    rec("import", "dupes==1", 5, imp.get("dupes") == 1, imp)
    rec("import", "total==4", 5, imp.get("total") == 4, imp)
    s, _, allb = req(port, "GET", "/v1/bookmarks")
    t1 = next((t for t in allb.get("tweets", []) if t.get("id") == "t1"), {})
    rec("import", "xhr-wins", 5, t1.get("text") == "hello world backup one"
        and t1.get("author") == "alice", t1)
    rec("import", "sources-valid", 5,
        all(t.get("source") in ("xhr", "dom") for t in allb.get("tweets", [])), "")

    for lb in ("read-later", "invoice"):
        req(port, "POST", "/v1/labels", {"name": lb})
    s, _, labs = req(port, "GET", "/v1/labels")
    names = {l.get("name") for l in labs.get("labels", [])}
    rec("labels", "2-created", 5, {"read-later", "invoice"} <= names, sorted(names))
    s, _, att = req(port, "POST", "/v1/bookmarks/t1/labels", {"label": "read-later"})
    s, _, att2 = req(port, "POST", "/v1/bookmarks/t1/labels", {"label": "invoice"})
    rec("labels", "attach-both", 5, "read-later" in att2.get("labels", [])
        and "invoice" in att2.get("labels", []), att2)
    s, _, labs = req(port, "GET", "/v1/labels")
    names = {l.get("name") for l in labs.get("labels", [])}
    rec("labels", "list-both", 5, {"read-later", "invoice"} <= names, sorted(names))
    s, _, filt = req(port, "GET", "/v1/bookmarks?label=read-later")
    rec("labels", "filter-t1", 5, any(t.get("id") == "t1" for t in filt.get("tweets", [])), filt.get("total"))

    s, _, q1 = req(port, "GET", "/v1/bookmarks?q=hello")
    rec("search", "q-finds-t1", 5, any(t.get("id") == "t1" for t in q1.get("tweets", [])), q1.get("total"))
    s, _, qall = req(port, "GET", "/v1/bookmarks")
    rec("search", "empty-q-all", 5, qall.get("total") == 4, qall.get("total"))
    s, _, q0 = req(port, "GET", "/v1/bookmarks?q=zzz-no-match-zzz")
    rec("search", "unknown-q-zero", 5, q0.get("total") == 0, q0.get("total"))

    s, _, w1 = req(port, "POST", "/v1/webhooks/bookmarks", {"url": "https://example.com/hook"})
    rec("webhooks", "add-ok", 4, s == 200, w1)
    s, _, w2 = req(port, "POST", "/v1/webhooks/bookmarks", {"url": "https://example.com/hook"})
    rec("webhooks", "dupe-ignored", 3, len(w2.get("webhooks", [])) == 1, len(w2.get("webhooks", [])))
    s, _, imp2 = req(port, "POST", "/v1/bookmarks/import",
                     {"tweets": [{"id": "t9", "text": "hook probe", "source": "xhr"}]})
    s, _, wl = req(port, "GET", "/v1/webhooks/bookmarks")
    rec("webhooks", "import-fires", 3, imp2.get("accepted") == 1, imp2)

    s, _, ap = req(port, "POST", "/v1/approvals",
                   {"kind": "sync", "title": "Resume paused sync"})
    aid = ap.get("approval", {}).get("id")
    rec("approvals", "propose-pending", 3,
        s == 200 and ap.get("approval", {}).get("status") == "pending", ap)
    s400, _, e400 = req(port, "POST", "/v1/approvals", {"title": ""})
    rec("approvals", "empty-400", 2, s400 == 400, e400)
    s, _, ok = req(port, "POST", f"/v1/approvals/{aid}/approve", {})
    rec("approvals", "approve", 3, ok.get("approval", {}).get("status") == "approved", ok)
    s, _, re = req(port, "POST", f"/v1/approvals/{aid}/approve", {})
    rec("approvals", "re-approve-safe", 2,
        re.get("note") == "already-decided" and re.get("approval", {}).get("status") == "approved", re)

    s, _, me = req(port, "GET", "/v1/billing/me")
    cat = {p.get("id"): p.get("price_usd") for p in me.get("catalog", [])}
    rec("billing", "catalog-prices", 3,
        cat == {"free": 0, "monthly": 7, "yearly": 99, "lifetime": 198}, cat)
    for k in ("FIAT_WEBHOOK_SECRET", "CRYPTO_WEBHOOK_SECRET"):
        os.environ.pop(k, None)
    s, _, f = req(port, "POST", "/v1/billing/fiat-webhook", {"type": "checkout.completed"})
    rec("billing", "fiat-test", 2, f.get("plan") == "test", f)
    s, _, c = req(port, "POST", "/v1/billing/crypto-webhook", {"status": "confirmed"})
    rec("billing", "crypto-test", 2, c.get("plan") == "test", c)
    s, h, r = req(port, "POST", "/v1/referrals/attribute", {"code": "FRIEND1"})
    cookie = h.get("Set-Cookie", "") or h.get("set-cookie", "")
    rec("billing", "referral", 3, r.get("attributed") is True and "bv_ref=FRIEND1" in cookie
        and req(port, "POST", "/v1/referrals/attribute", {"code": "DEMO42"})[2].get("reason") == "self-referral",
        cookie)


def run_static():
    pages = ["index.html", "sites/landing/index.html", "sites/landing/pricing.html",
             "sites/landing/terms.html", "sites/landing/privacy.html",
             "sites/landing/refunds.html", "sites/landing/contact.html",
             "sites/landing/dev.html", "ops/cycle.html", "ext/sidepanel/index.html"]
    missing = [p for p in pages if not os.path.exists(os.path.join(EXP, p))]
    rec("static", "hub-pages-exist", 3, not missing, missing or f"{len(pages)} present")
    sp = open(os.path.join(EXP, "ext/sidepanel/index.html")).read()
    tabs = re.findall(r'data-pane="pane-([a-z]+)"', sp)
    rec("static", "sidepanel-5-tabs", 2, tabs == ["saved", "labels", "sync", "hooks", "export"], tabs)
    # English-only scan: user-facing html files must not contain Spanish diacritics/phrases
    es_markers = ["á", "é", "í", "ó", "ú", "ñ", "¿", "¡", "usted", "está", "para la"]
    hits = []
    for p in pages:
        fp = os.path.join(EXP, p)
        if os.path.exists(fp):
            low = open(fp, encoding="utf-8", errors="replace").read().lower()
            for m in es_markers:
                if m in low:
                    hits.append(f"{p}:{m}")
                    break
    rec("static", "english-only", 3, not hits, hits or "en ok")
    # JS syntax via node --check
    js = ["ext/sidepanel/sidepanel.js", "ext/background.js", "ext/content.js", "ext/resilience.js"]
    bad = []
    for j in js:
        fp = os.path.join(EXP, j)
        if not os.path.exists(fp):
            continue
        r = subprocess.run(["node", "--check", fp], capture_output=True, text=True)
        if r.returncode != 0:
            bad.append(j)
    rec("static", "js-syntax", 2, not bad, bad or "ok")


def main():
    port = PORT_ARG
    proc = None
    if port is None:
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        # isolate webhook log: point backend at temp copy? backend writes next to itself.
        # Instead snapshot + restore the log file around the run.
        proc = subprocess.Popen([sys.executable, BACKEND, "--port", str(port)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1).read()
                break
            except Exception:
                time.sleep(0.1)
    try:
        run_api(port)
    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=5)
    run_static()
    total = sum(c["pts"] for c in checks)
    out = {"task": "T1-core-backup-loop", "score": total, "max": 100,
           "pass": total >= 80, "checks": checks,
           "presentable_static": all(c["ok"] for c in checks if c["group"] == "static"),
           "note": "static green is necessary, NOT sufficient: real Chrome @390px still required for PRESENTABLE."}
    print(json.dumps(out, indent=1))
    if SAVE:
        json.dump(out, open(SAVE, "w"), indent=1)


if __name__ == "__main__":
    import urllib.error
    main()
