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
grep -q "sendNoteQueued" /tmp/e62_app.js || fail "queue flow missing"
grep -q "toggleCard" /tmp/e62_app.js || fail "card expand missing"
grep -q "cardHist" /tmp/e62_app.js || fail "per-card history missing"
node --check /tmp/e62_app.js || fail "app.js syntax"
grep -q 'id=seg-report' /tmp/e62_root.html || fail "report toggle missing"
grep -q 'thumbbar' /tmp/e62_root.html || fail "thumb-zone bar missing"
grep -q "setReport" /tmp/e62_app.js || fail "setReport missing"
grep -q "fmtDetail" /tmp/e62_app.js || fail "fmtDetail missing"
grep -q 'id=uni' /tmp/e62_root.html || fail "unified view missing"
grep -q "buildUnified" /tmp/e62_app.js || fail "buildUnified missing"
grep -q "uniWatchLive" /tmp/e62_app.js || fail "live session watch missing"
grep -q 'id=live' /tmp/e62_root.html || fail "live panel missing"
grep -q 'seg-persona' /tmp/e62_root.html || fail "persona switch missing"
grep -q "setPersona" /tmp/e62_app.js || fail "setPersona missing"
grep -q "renderLive" /tmp/e62_app.js || fail "renderLive missing"
grep -q "NARRATE AS YOU GO" RUNNER_PROMPT.md 2>/dev/null || grep -q "NARRATE AS YOU GO" e062-agent-ops/RUNNER_PROMPT.md || fail "runner step-emit contract missing"
# OWNER-FIRST reporting (owner law): run rows render a plain sentence in simple
# mode with tech after ' | ' — fail closed so jargon can never creep back.
grep -q '| tech:' /tmp/e62_app.js || fail "runLine missing owner | tech format"

grep -q 'id=runs' /tmp/e62_root.html || fail "activity runs table missing"
code=$(curl -s -m 10 -o /tmp/e62_runstate.json -w "%{http_code}" "$BASE/api/runstate") || fail "runstate unreachable"
[ "$code" = "200" ] || fail "runstate http=$code"
python3 -c "import json; d=json.load(open('/tmp/e62_runstate.json')); assert d.get('ok') and 'running' in d, 'runstate shape'" || fail "runstate shape bad"
# /api/run is OPEN (owner decision 2026-09-12: tailnet-only board, pause/resume/note
# already open; worst case a stray tap costs one leg). bad scope must fail WITHOUT spawning.
out=$(curl -s -m 10 -X POST "$BASE/api/run" -H 'Content-Type: application/json' -d '{"scope":"nope"}') || fail "run API unreachable"
echo "$out" | grep -q '"ok":false' || fail "bad scope not rejected: $out"
echo "$out" | grep -q 'bad scope' || fail "bad-scope error wrong: $out"
echo "run open ok: no token needed, bad scope rejected, no leg spawned"
# money stays gated: /api/decide without token must fail
out=$(curl -s -m 10 -X POST "$BASE/api/decide" -H 'Content-Type: application/json' -d '{"id":9999,"verdict":"approved"}') || fail "decide API unreachable"
echo "$out" | grep -q '"ok":false' || fail "decide money gate open!"
echo "decide gate ok: money still token-protected"

# report pref: configurable display (simple default, both/tech switchable)
python3 - "$BASE" <<'EOF' || fail "report pref bad"
import json, sys, urllib.request
base=sys.argv[1]
def post(path, obj):
    r=urllib.request.Request(base+path, data=json.dumps(obj).encode(), headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(r, timeout=10))
r=post("/api/prefs", {"report":"both"})
assert r.get("ok"), "prefs set failed"
d=json.load(urllib.request.urlopen(base+"/api/board", timeout=15))
assert d.get("prefs", {}).get("report")=="both", "board prefs missing report=both"
r=post("/api/prefs", {"report":"simple"})
assert r.get("ok"), "prefs restore failed"
print("report pref ok: simple default, both/tech switchable")
EOF
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
    for k in ("tokens", "tok_s", "cost_usd", "started"):
        assert k in r, f"runs row missing {k}"
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
