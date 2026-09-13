#!/bin/bash
# e062 rung-3 e2e: verifies fleet board root + /api/board JSON shape. Exit nonzero on any failure.
# Usage: tests/e2e.sh [base_url]   (default http://100.102.52.59:8322)
BASE="${1:-http://100.102.52.59:8322}"
fail() { echo "E2E FAIL: $1"; exit 1; }

code=$(curl -s -m 10 -o /tmp/e62_root.html -w "%{http_code}" "$BASE/") || fail "root unreachable"
[ "$code" = "200" ] || fail "root http=$code"
grep -q "fleet board" /tmp/e62_root.html || fail "board missing title"
grep -q "run fleet now" /tmp/e62_root.html || fail "run-fleet button missing"
grep -q 'id=cards' /tmp/e62_root.html || fail "project cards missing"
grep -q "history + message" /tmp/e62_root.html || fail "cards hint missing"
curl -s -m 10 "$BASE/app.js" -o /tmp/e62_app.js || fail "app.js unreachable"
grep -q "sendNoteRun" /tmp/e62_app.js || fail "send+run-now flow missing"
grep -q "sendUniNoteRun" /tmp/e62_app.js || fail "row-level send+run-now missing (owner must decide when from any row)"
grep -q "attachDrafts" /tmp/e62_app.js || fail "run-attach-drafts missing (Run must carry typed words)"
grep -q 'data-track' /tmp/e62_app.js || fail "row reply track tag missing"
grep -q "sendNoteQueued" /tmp/e62_app.js || fail "queue flow missing"
grep -q "toggleCard" /tmp/e62_app.js || fail "card expand missing"
grep -q "cardHist" /tmp/e62_app.js || fail "per-card history missing"
node --check /tmp/e62_app.js || fail "app.js syntax"
grep -q 'id=seg-report' /tmp/e62_root.html || fail "report toggle missing"
grep -q 'thumbbar' /tmp/e62_root.html || fail "thumb-zone bar missing"
grep -q 'id=waiting' /tmp/e62_root.html || fail "thumbbar waiting signal missing"
grep -q 'needbadge' /tmp/e62_app.js || fail "per-card waiting badge missing"
grep -q 'id=widgets' /tmp/e62_root.html || fail "configurable views missing"
grep -q "addViewPreset" /tmp/e62_app.js || fail "preset add buttons missing"
grep -q "renderWidgets" /tmp/e62_app.js || fail "renderWidgets missing"
grep -q "renderGates" /tmp/e62_app.js || fail "money-gate cards missing"
grep -q "waitFor" /tmp/e62_app.js || fail "waiting tap-to-filter missing"
grep -q "addViewPreset" /tmp/e62_app.js || fail "preset view buttons missing"
grep -q "projRoot" /tmp/e62_app.js || fail "projects root table missing"
grep -q "wProjToggle" /tmp/e62_app.js || fail "row expand missing"
grep -q "sesRoot" /tmp/e62_app.js || fail "sessions root table missing"
grep -q "waitRoot" /tmp/e62_app.js || fail "waiting root table missing"
grep -q "wSort" /tmp/e62_app.js || fail "tap-to-sort missing"
grep -q "relTabs" /tmp/e62_app.js || fail "nested relation tabs missing"
grep -q "clampCell" /tmp/e62_app.js || fail "long-text clamp missing"
grep -q "colPicker" /tmp/e62_app.js || fail "column SELECT picker missing"
grep -q "sqlCaption" /tmp/e62_app.js || fail "live SQL caption missing"
grep -q "after:" /tmp/e62_app.js || fail "date WHERE tokens missing"
grep -q "waitBanner" /tmp/e62_app.js || fail "waiting explainer banner missing"
grep -qi "announced" /tmp/e62_root.html || fail "rung ladder explainer missing"
out=$(curl -s -m 10 "$BASE/api/version") || fail "version unreachable"
echo "$out" | grep -q '"running"' || fail "version shape bad"
echo "$out" | grep -q '"stale":false' || fail "server STALE — restart after edits"
python3 -c "import json;d=json.load(open('/tmp/e62_board.json'));assert all('focus' in t for t in d['tracks'])" 2>/dev/null || {
curl -s -m 15 "$BASE/api/board" -o /tmp/e62_board.json || fail "board refetch"
python3 -c "import json;d=json.load(open('/tmp/e62_board.json'));assert all('focus' in t for t in d['tracks']), 'focus missing'"; } || fail "focus missing"
grep -q "renderAuth" /tmp/e62_app.js || fail "auth UI missing"
! grep -q "keep at least one" /tmp/e62_app.js || fail "views still locked to min 1"
grep -q "is:waiting" /tmp/e62_app.js || fail "waiting query missing"
grep -q "ses " /tmp/e62_app.js || fail "session short-id display missing"
grep -q "rtable" /tmp/e62_app.js || fail "root tables missing"
grep -q "ntable" /tmp/e62_app.js || fail "nested tables missing"
grep -q "sesChips" /tmp/e62_app.js || fail "tappable run/ses chips missing"
grep -q "LATEST" /tmp/e62_app.js || fail "projects header missing"
grep -q "sesChips" /tmp/e62_app.js || fail "tappable run/ses chips missing"
grep -q "sesFilter" /tmp/e62_app.js || fail "session isolate filter missing"
grep -q "getHours" /tmp/e62_app.js || fail "local-time conversion missing"
grep -q "THIS LEG" bin/runner.sh 2>/dev/null || grep -q "THIS LEG" e062-agent-ops/bin/runner.sh || fail "leg identity line missing"
grep -q "run #N" e062-agent-ops/RUNNER_PROMPT.md || fail "step run-tag contract missing"
! grep -q '<table' /tmp/e62_root.html || fail "page-level tables still present (must be cards)"
curl -s -m 10 "$BASE/api/board" -o /tmp/e62_b.json || fail "board json unreachable"
python3 -c "import json;d=json.load(open('/tmp/e62_b.json'))" || fail "board json bad"
grep -q "setReport" /tmp/e62_app.js || fail "setReport missing"
grep -q "fmtDetail" /tmp/e62_app.js || fail "fmtDetail missing"
grep -q 'id=gates' /tmp/e62_root.html || fail "money zone missing"
grep -q "buildUnified" /tmp/e62_app.js || fail "buildUnified missing"
grep -q "uniWatchLive" /tmp/e62_app.js || fail "live session watch missing"
grep -q 'id=live' /tmp/e62_root.html || fail "live panel missing"
grep -q 'seg-persona' /tmp/e62_root.html || fail "persona switch missing"
grep -q "setPersona" /tmp/e62_app.js || fail "setPersona missing"
grep -q "renderLive" /tmp/e62_app.js || fail "renderLive missing"
grep -q "def ack" ../bin/ops.py 2>/dev/null || grep -q "def ack" e062-agent-ops/bin/ops.py || fail "ops ack command missing"
grep -q "NARRATE AS YOU GO" RUNNER_PROMPT.md 2>/dev/null || grep -q "NARRATE AS YOU GO" e062-agent-ops/RUNNER_PROMPT.md || fail "runner step-emit contract missing"
# OWNER-FIRST reporting (owner law): run rows render a plain sentence in simple
# mode with tech after ' | ' — fail closed so jargon can never creep back.
grep -q '| tech:' /tmp/e62_app.js || fail "runLine missing owner | tech format"

grep -q "nwrap" /tmp/e62_root.html || fail "nested-scroll CSS missing"
code=$(curl -s -m 10 -o /tmp/e62_runstate.json -w "%{http_code}" "$BASE/api/runstate") || fail "runstate unreachable"
[ "$code" = "200" ] || fail "runstate http=$code"
python3 -c "import json; d=json.load(open('/tmp/e62_runstate.json')); assert d.get('ok') and 'running' in d, 'runstate shape'" || fail "runstate shape bad"
# AUTH: app accounts (register/login/logout), mutations need login, money needs admin.
# bad scope must fail WITHOUT spawning; nothing here spawns a leg or moves money.
python3 - "$BASE" "$(cd "$(dirname "$0")/.." && pwd)/ops.db" <<'EOF' || fail "auth bad"
import http.cookiejar, json, sqlite3, sys, time, urllib.request
base, dbpath = sys.argv[1], sys.argv[2]
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
def post(path, obj):
    r = urllib.request.Request(base+path, data=json.dumps(obj).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(op.open(r, timeout=10))
def anon(path, obj):
    r = urllib.request.Request(base+path, data=json.dumps(obj).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=10))
# 1. anonymous mutations rejected (run/note/decide/prefs)
for path, obj in [("/api/run", {"scope": "nope"}), ("/api/note", {"track": "e062", "message": "x"}),
                  ("/api/decide", {"id": 999999, "verdict": "approved"}), ("/api/prefs", {"report": "both"})]:
    r = anon(path, obj)
    assert r.get("ok") is False and "login" in (r.get("error") or "").lower(), f"{path} not login-gated: {r}"
print("auth ok: anonymous run/note/decide/prefs rejected")
# 2. validation + login failures
r = post("/api/register", {"name": "a", "pw": "short"})
assert not r.get("ok"), "weak credentials accepted"
r = post("/api/login", {"name": "nosuchuser_e2e", "pw": "whatever123"})
assert not r.get("ok"), "unknown login accepted"
# 3. register e2e account (admin iff first user ever — else viewer; both paths asserted)
me = "e2euser_%d" % int(time.time())
r = post("/api/register", {"name": me, "pw": "e2e-pass-123"})
assert r.get("ok") and r.get("name") == me, f"register failed: {r}"
role = r.get("role")
assert role in ("admin", "viewer"), role
r = post("/api/login", {"name": me, "pw": "wrongpass"})
assert not r.get("ok"), "wrong password accepted"
# 4. authed bad-scope run: passes auth, fails scope, spawns nothing
r = post("/api/run", {"scope": "nope"})
assert r.get("ok") is False and "bad scope" in (r.get("error") or ""), f"bad scope: {r}"
# 5. money gate by role
r = post("/api/decide", {"id": 999999, "verdict": "approved"})
if role == "admin":
    assert r.get("ok"), f"admin decide failed: {r}"
else:
    assert r.get("ok") is False and "admin" in (r.get("error") or "").lower(), f"viewer decide: {r}"
# 6. prefs round-trips need auth too (report + widgets)
r = post("/api/prefs", {"report": "both"})
assert r.get("ok"), "authed prefs failed"
d = json.load(op.open(base + "/api/board", timeout=15))
assert d.get("prefs", {}).get("report") == "both", "board prefs mismatch"
assert (d.get("me") or {}).get("name") == me, "board me missing"
mine = [{"t": "projects", "q": "", "root": "projects", "n": 20}]
r = post("/api/prefs", {"widgets": json.dumps(mine)})
assert r.get("ok"), "widgets set failed"
d = json.load(op.open(base + "/api/board", timeout=15))
assert json.loads(d.get("prefs", {}).get("widgets") or "[]") == mine, "widgets mismatch"
post("/api/prefs", {"report": "simple"})
post("/api/prefs", {"widgets": ""})
# 7. logout kills the session
r = post("/api/logout", {})
assert r.get("ok"), "logout failed"
r = anon("/api/note", {"track": "e062", "message": "x"})
assert r.get("ok") is False, "session survived logout"
# 8. cleanup test accounts (same-host DB)
c = sqlite3.connect(dbpath)
c.execute("DELETE FROM sessions WHERE uid IN (SELECT id FROM users WHERE name LIKE 'e2euser\\_%' ESCAPE '\\')")
c.execute("DELETE FROM users WHERE name LIKE 'e2euser\\_%' ESCAPE '\\'")
c.commit()
left = c.execute("SELECT COUNT(*) FROM users WHERE name LIKE 'e2euser\\_%' ESCAPE '\\'").fetchone()[0]
c.close()
assert left == 0, "e2e users left behind"
print(f"auth ok: register/login/logout/me, role={role}, prefs round-trip, cleanup done")
EOF
curl -s -m 15 "$BASE/api/board" -o /tmp/e62_board.json || fail "board API unreachable"
curl -s -m 15 "$BASE/api/board" -o /tmp/e62_board.json || fail "board API unreachable"
python3 - <<'EOF' || fail "board shape bad"
import json
d = json.load(open("/tmp/e62_board.json"))
tracks = d.get("tracks")
assert isinstance(tracks, list) and len(tracks) >= 5, "tracks < 5"
names = {t["track"] for t in tracks}
assert {"e058", "e059", "e060", "e061", "e062"} <= names, f"missing tracks: {names}"
for t in tracks:
    assert "rung" in t and "beat" in t, f"track {t.get('track')} missing rung/beat"
rw = d.get("runway", {})
for k in ("spent", "earned", "left"):
    assert k in rw, f"runway missing {k}"
assert isinstance(d.get("runs"), list), "runs missing"
for r in d["runs"]:
    for k in ("tokens", "tok_s", "cost_usd", "started", "session"):
        assert k in r, f"runs row missing {k}"
assert any(r.get("session") for r in d["runs"]), "no run carries a session id"
print(f"runs ok: {len(d['runs'])} rows with tokens/tok-s/cost")
assert isinstance(d.get("runner"), dict) and "running" in d["runner"], "runner missing"
assert isinstance(d.get("leg_tail"), str), "leg_tail missing"
print(f"board ok: {len(tracks)} tracks, runway left=${rw['left']:.2f}")
# OWNER-FIRST: every owner-facing card beat ships `plain sentence | tech: detail`
# (empty note allowed). Simple mode shows only the plain half on the phone.
for t in tracks:
    if t["track"] in ("e058", "e059", "e060", "e061", "e062", "runner"):
        note = ((t.get("beat") or {}).get("note")) or ""
        assert (not note.strip()) or (" | " in note), \
            f"beat MISSING owner|tech separator on {t['track']}: {note[:80]}"
print("owner-first ok: all card beats carry plain sentence + tech half")
EOF
echo "E2E PASS ($BASE)"
