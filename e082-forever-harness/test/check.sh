#!/bin/bash
# API + first-paint smoke. Reads are public; writes need the owner TOKEN.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=$(python3 -c "import json;print(json.load(open('$DIR/needs.json'))['port'])")
TOK=$(python3 -c "import json;print(json.load(open('$DIR/needs.json')).get('TOKEN',''))")
BASE="http://127.0.0.1:$PORT"
AUTH=(-H "Authorization: Bearer $TOK")
fail(){ echo "FAIL: $1"; exit 1; }
[ -n "$TOK" ] || fail "no TOKEN in needs.json"
curl -s "$BASE/api/health" | grep -q alive || fail "health"
curl -s "$BASE/api/policy" | grep -q max_cycles || fail "policy GET"
# unauthenticated writes must be rejected
curl -s -X POST "$BASE/api/control/tick" -H 'Content-Type: application/json' -d '{"by":"anon"}' | grep -q unauthorized || fail "auth: tick without token not rejected"
curl -s -X POST "$BASE/api/policy" -H 'Content-Type: application/json' -d '{"quality_floor":70}' | grep -q unauthorized || fail "auth: policy without token not rejected"
curl -s -X POST "$BASE/api/stress" -H 'Content-Type: application/json' -d '{"ticks":0}' | grep -q unauthorized || fail "auth: stress without token not rejected"
curl -s -X POST "$BASE/api/restore" -H 'Content-Type: application/json' -d '{"checkpoint_id":"k001"}' | grep -q unauthorized || fail "auth: restore without token not rejected"
# authenticated writes work
curl -s -X POST "$BASE/api/policy" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"quality_floor":70}' | grep -q quality_floor || fail "policy POST (authed)"
curl -s -X POST "$BASE/api/control/start" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{}' | grep -q '"running"' || echo "(start: already running or limited)"
curl -s -X POST "$BASE/api/control/tick" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"by":"check"}' | grep -q '"cycle"' || fail "tick (authed)"
curl -s "$BASE/api/status" | python3 -c "import json,sys;s=json.load(sys.stdin);assert s['cycle']>=1,s;assert s['quality'] is not None,s;print('status OK cycle',s['cycle'],'quality',s['quality'])" || fail "status"
curl -s -X POST "$BASE/api/verify" | grep -q quality || fail "verify"
curl -s "$BASE/api/checkpoints" | grep -q '\[' || fail "checkpoints"
curl -s "$BASE/api/proof" | python3 -c "import json,sys;p=json.load(sys.stdin);assert p['cycles_shipped']>=1,p;assert 'quality_history' in p and 'uptime_seconds' in p and 'ledger' in p, p;print('proof OK shipped',p['cycles_shipped'],'uptime',p['uptime_seconds'])" || fail "proof"
curl -s "$BASE/api/auth" -H "Authorization: Bearer $TOK" | grep -q '"ok": true' || fail "auth check"
# AUTH DECISION 2026-09-29 (single-user tool): public demo-mint is DISABLED
# by default — assert the 403 + owner-only message, master TOKEN untouched.
# Previously minted fh-* tokens (if any) must still authenticate.
curl -s -X POST "$BASE/api/token/mint" -H 'Content-Type: application/json' -d '{"session":"check-suite"}' | grep -q "owner-only" || fail "token mint not disabled (expected owner-only 403)"
DEMO=$(python3 -c "import json;d=json.load(open('$DIR/data/demo_tokens.json'));print(next(iter(d)) if d else '')")
if [ -n "$DEMO" ]; then curl -s "$BASE/api/auth" -H "Authorization: Bearer $DEMO" | grep -q '"ok": true' || fail "legacy demo token auth"; echo "legacy demo token OK"; else echo "(no legacy demo tokens yet — master TOKEN only)"; fi
# FOREVER CEILING: max_cycles=null/0 accepted = unbounded; live stays unbounded
curl -s -X POST "$BASE/api/policy" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"max_cycles":null}' | grep -q 'max_cycles' || fail "unbounded policy (null) rejected"
curl -s "$BASE/api/status" | python3 -c "import json,sys;s=json.load(sys.stdin);assert s['max_cycles'] is None,s;assert s['unbounded'] is True,s;assert s['cycles_remaining'] is None,s;print('unbounded OK: cycle',s['cycle'],'/inf')" || fail "unbounded status"
curl -s -X POST "$BASE/api/policy" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"max_cycles":0}' | grep -q 'max_cycles' || fail "unbounded policy (0) rejected"
curl -s -X POST "$BASE/api/policy" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"max_cycles":null}' | grep -q 'max_cycles' || fail "unbounded restore"
# REAL WORKLOAD: evidence gate exists and last tick carries live evidence
curl -s -X POST "$BASE/api/verify" | python3 -c "import json,sys;v=json.load(sys.stdin);n=[g['name'] for g in v['gates']];assert 'evidence_present' in n,n;assert 'critic_accept' in n,n;print('gates OK:',','.join(n))" || fail "evidence/critic gates"
curl -s "$BASE/api/last-tick" | python3 -c "import json,sys;t=json.load(sys.stdin);assert 'evidence:' in (t.get('notes') or ''),t;assert t.get('evidence',{}).get('ok') is True,t;print('evidence OK cycle',t.get('cycle'),'rows',t['evidence'].get('rows'))" || fail "last tick evidence"
curl -s "$BASE/api/backlog" | python3 -c "import json,sys;b=json.load(sys.stdin);assert len(b['items'])>=3,b;assert b['current']['id'],b;print('backlog OK current',b['current']['id'])" || fail "backlog"
# ADVERSARIAL REVIEWER: hollow tick must be REJECTED (R1+R2)
curl -s -X POST "$BASE/api/review" -H 'Content-Type: application/json' -d '{"notes":"tick done"}' | python3 -c "import json,sys;r=json.load(sys.stdin);assert r['verdict']=='reject',r;assert any('R1' in x for x in r['reasons']),r;print('critic OK: hollow rejected:',r['reasons'][0][:60])" || fail "critic rejection"
curl -s "$BASE/api/suggest-goals" | python3 -c "import json,sys;g=json.load(sys.stdin);assert len(g['goals'])==3,g;assert all(len(x)>10 for x in g['goals']),g;print('suggest OK:',g['based_on'])" || fail "suggest-goals"
# proof receipts: last tick + 5-tick timeline
curl -s "$BASE/api/last-tick" | python3 -c "import json,sys;t=json.load(sys.stdin);assert 'gates' in t or 'empty' in t,t;print('last-tick OK cycle',t.get('cycle'))" || fail "last-tick"
curl -s "$BASE/api/ticks?limit=5" | python3 -c "import json,sys;t=json.load(sys.stdin);assert type(t) is list and 1<=len(t)<=5,t;print('ticks OK n=',len(t))" || fail "ticks timeline"
# LIMIT-PUSHER scoreboard (authed; absorbs live ticks, advances cycle)
curl -s -X POST "$BASE/api/stress" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"ticks":1}' | python3 -c "import json,sys;r=json.load(sys.stdin);assert 'score' in r and 'probes' in r and len(r['probes'])>=7,r;print('stress OK',r['score'],r['verdict'])" || fail "stress"
# telemetry: ingest one event, funnel reflects it, no IPs stored
SESS="check-$(date +%s)"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d "{\"v\":1,\"session\":\"$SESS\",\"ts\":1,\"page\":\"/\",\"event\":\"page_view\"}" | grep -q '"ok": true' || fail "events ingest"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d '{"v":1,"session":"x"}' | grep -q '"error"' || fail "events validation"
curl -s "$BASE/api/funnel" | python3 -c "import json,sys;f=json.load(sys.stdin);assert all(k in f for k in ('views','installs','tokens','proofs','stuck_sessions','bots_hidden','bots_total','dismissed_count','verdict')),f;assert f['views']>=1,f;assert f['verdict']['level'] in ('NOISE','FAILING','HEALTHY','QUIET','WATCH','UNKNOWN'),f;assert f['verdict']['line'],f;print('funnel OK views',f['views'],'stuck',len(f['stuck_sessions']),'bots_hidden',f['bots_hidden'],'verdict',f['verdict']['level'])" || fail "funnel"
# FUNNEL-TRUTH: bot filter + verdict + dismiss + R4 (deterministic, self-cleaning)
# 1. bot exclusion: fresh synthetic sessions are hidden by default, revealed by ?bots=1
B0=$(curl -s "$BASE/api/funnel" | python3 -c "import json,sys;print(json.load(sys.stdin)['bots_hidden'])")
H0=$(curl -s "$BASE/api/funnel" | python3 -c "import json,sys;f=json.load(sys.stdin);print(sum(1 for r in f['stuck_sessions'] if not r.get('synthetic')))")
NBOT=$((H0 + 3))
[ "$NBOT" -lt 3 ] && NBOT=3
FTS="check-r4-$(date +%s)"
for i in $(seq 1 $NBOT); do
  curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d "{\"v\":1,\"session\":\"$FTS-$i\",\"ts\":1,\"page\":\"/\",\"event\":\"page_view\"}" | grep -q '"ok": true' || fail "fixture bot ingest $i"
done
curl -s "$BASE/api/funnel" | python3 -c "import json,sys;f=json.load(sys.stdin);assert f['bots_hidden']==$B0+$NBOT,f;assert not any(r['session'].startswith('$FTS') for r in f['stuck_sessions']),f;print('bot exclusion OK: bots_hidden',f['bots_hidden'])" || fail "bot exclusion"
curl -s "$BASE/api/funnel?bots=1" | python3 -c "import json,sys;f=json.load(sys.stdin);got=[r for r in f['stuck_sessions'] if r['session'].startswith('$FTS')];assert len(got)==$NBOT,sorted(r['session'] for r in f['stuck_sessions']);assert all(r['synthetic'] is True for r in got),got;assert all(r.get('short') and r.get('last_at') for r in got),got;assert all(r['last_detail']!='none' for r in got),got;print('bot toggle OK:',len(got),'synthetic rows revealed')" || fail "bot toggle"
# curl-UA polls are synthetic too (localhost health-poll shape)
HPUA="healthpoll-ua-$(date +%s)"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -A 'curl/8.0 (health-poll)' -d "{\"v\":1,\"session\":\"$HPUA\",\"ts\":1,\"page\":\"/\",\"event\":\"page_view\"}" | grep -q '"ok": true' || fail "ua bot ingest"
curl -s "$BASE/api/funnel?bots=1" | python3 -c "import json,sys;f=json.load(sys.stdin);got=[r for r in f['stuck_sessions'] if r['session']=='$HPUA'];assert got and got[0]['synthetic'] is True,got;print('ua-bot OK: curl UA flagged synthetic')" || fail "ua bot flag"
curl -s -X POST "$BASE/api/funnel/dismiss" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"session\":\"$HPUA\"}" | grep -q '"ok": true' || fail "dismiss $HPUA"
# 1b. AGENT SELF-ID: driven browsers send agent:<name> (via ?agent=) -> synthetic,
# hidden by default, name preserved + revealed by ?bots=1. Browser UA proves the
# flag alone (not the UA rule) triggers it. Fixtures dismissed below.
AGTS="attrcheck-$(date +%s)"
BUA="Mozilla/5.0 (X11; Linux x86_64) Chrome/126.0 Safari/537.36"
curl -s -X POST "$BASE/api/events" -A "$BUA" -H 'Content-Type: application/json' -d "{\"v\":1,\"session\":\"$AGTS\",\"ts\":1,\"page\":\"/\",\"event\":\"page_view\",\"agent\":\"seat-review\"}" | grep -q '"ok": true' || fail "agent ingest"
curl -s "$BASE/api/funnel" | python3 -c "import json,sys;f=json.load(sys.stdin);assert not any(r['session']=='$AGTS' for r in f['stuck_sessions']),f;print('agent hidden OK')" || fail "agent hidden"
curl -s "$BASE/api/funnel?bots=1" | python3 -c "import json,sys;f=json.load(sys.stdin);got=[r for r in f['stuck_sessions'] if r['session']=='$AGTS'];assert got and got[0]['synthetic'] is True and got[0].get('agent')=='seat-review',got;print('agent tag OK: synthetic + name kept')" || fail "agent tag"
curl -s -X POST "$BASE/api/events" -A "$BUA" -H 'Content-Type: application/json' -d '{"v":1,"session":"x","ts":1,"page":"/","event":"page_view","agent":"bad name!"}' | grep -q '"error"' || fail "agent validation"
# 1c. ATTRIBUTION: polluted-only traffic -> UNKNOWN (no quality penalty via R4);
# one real click-path (page_view -> click, no agent flag) -> normal scoring.
python3 - "$DIR" <<'EOF' || fail "attribution rules"
import sys; sys.path.insert(0, sys.argv[1] + "/server"); import app
v = app.attribution_gate({"level":"FAILING","line":"FAILING: 0 downloads after 10 visits"}, 0)
assert v["level"]=="UNKNOWN" and "not enough human traffic \u2014 unattributed" in v["line"], v
assert app.attribution_gate({"level":"FAILING","line":"x"}, 3)["level"]=="FAILING"
assert app.is_engagement("click:show-proof") and app.is_engagement("download") and not app.is_engagement("page_view")
assert app.valid_agent("seat-review") and not app.valid_agent("bad name!")
print("attribution rules OK")
EOF
HUM="attrhuman-$(date +%s)"
HA0=$(curl -s "$BASE/api/funnel" | python3 -c "import json,sys;print(json.load(sys.stdin)['human_attributed'])")
curl -s -X POST "$BASE/api/events" -A "$BUA" -H 'Content-Type: application/json' -d "{\"v\":1,\"session\":\"$HUM\",\"ts\":1,\"page\":\"/\",\"event\":\"page_view\"}" | grep -q '"ok": true' || fail "click-path ingest 1"
curl -s -X POST "$BASE/api/events" -A "$BUA" -H 'Content-Type: application/json' -d "{\"v\":1,\"session\":\"$HUM\",\"ts\":2,\"page\":\"/\",\"event\":\"click:show-proof\"}" | grep -q '"ok": true' || fail "click-path ingest 2"
curl -s "$BASE/api/funnel" | python3 -c "import json,sys;f=json.load(sys.stdin);assert f['human_attributed']==$HA0+1,(f['human_attributed'],$HA0);got=[r for r in f['stuck_sessions'] if r['session']=='$HUM'];assert len(got)==1 and got[0]['synthetic'] is False,got;print('click-path human OK: attributed',f['human_attributed'])" || fail "click-path human"
CYC_U=$(curl -s "$BASE/api/status" | python3 -c "import json,sys;print(json.load(sys.stdin)['cycle'])")
python3 - "$DIR" "$CYC_U" <<'EOF' || fail "UNKNOWN no-penalty"
import sys; sys.path.insert(0, sys.argv[1] + "/server"); import app
v = {"level":"UNKNOWN","line":"UNKNOWN: not enough human traffic \u2014 unattributed (0/3 human-attributed sessions) \u2014 watching, not scoring"}
r = app.review_tick(cycle=int(sys.argv[2]), _funnel={"verdict":v,"bots_hidden":4,"stuck_sessions":[]})
assert not any(x.startswith("R4:") and "data-truth" in x for x in r["reasons"]), r
assert any("discounting" in x for x in r["reasons"]), r
print("UNKNOWN no-penalty OK: verdict=%s" % r["verdict"])
EOF
curl -s -X POST "$BASE/api/funnel/dismiss" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"session\":\"$AGTS\"}" | grep -q '"ok": true' || fail "dismiss agent fixture"
curl -s -X POST "$BASE/api/funnel/dismiss" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"session\":\"$HUM\"}" | grep -q '"ok": true' || fail "dismiss click-path fixture"
# 2. verdict unit asserts (pure rules — thresholds from needs.json)
python3 - "$DIR" <<'EOF' || fail "verdict rules"
import sys; sys.path.insert(0, sys.argv[1] + "/server"); import app
assert app.funnel_verdict(15, 0, 5, 7, 3)["level"] == "NOISE"
assert app.funnel_verdict(15, 0, 5, 0, 8)["level"] == "FAILING"
assert "0 downloads after 15 visits" in app.funnel_verdict(15, 0, 5, 0, 8)["line"]
assert app.funnel_verdict(15, 2, 6, 0, 3)["level"] == "HEALTHY"
assert app.funnel_verdict(2, 0, 0, 0, 2)["level"] == "QUIET"
assert app.is_bot_session("check-1") and app.is_bot_session("x-probe") and app.is_bot_session("growth-probe")
assert not app.is_bot_session("aa35e5fe0c86d2080351b0b5f8d8c815")
assert app.is_bot_ua("curl/7.81.0") and not app.is_bot_ua("Mozilla/5.0 Chrome/126.0 Safari/537.36")
t = app.funnel_thresholds()
assert all(k in t for k in ("min_visits", "download_alarm_ratio", "bot_noise_ratio", "proof_healthy_ratio", "critic_fail_streak")), t
print("verdict rules OK:", t)
EOF
# 3. R4 fires on the replayed polluted funnel: score the live tick, bot share > threshold
CYC=$(curl -s "$BASE/api/status" | python3 -c "import json,sys;print(json.load(sys.stdin)['cycle'])")
curl -s -X POST "$BASE/api/review" -H 'Content-Type: application/json' -d "{\"cycle\":$CYC}" | python3 -c "import json,sys;r=json.load(sys.stdin);assert r['verdict']=='reject',r;assert any('R4' in x for x in r['reasons']),r;print('R4 OK: live tick rejected:',[x for x in r['reasons'] if 'R4' in x][0][:100])" || fail "R4 rejection"
# 4. dismiss persists (authed), unauth rejected, undismiss restores; then clean fixtures
curl -s -X POST "$BASE/api/funnel/dismiss" -H 'Content-Type: application/json' -d '{"session":"should-fail"}' | grep -q unauthorized || fail "dismiss without token not rejected"
for i in $(seq 1 $NBOT); do
  curl -s -X POST "$BASE/api/funnel/dismiss" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"session\":\"$FTS-$i\"}" | grep -q '"ok": true' || fail "dismiss fixture $i"
done
curl -s "$BASE/api/funnel" | python3 -c "import json,sys;f=json.load(sys.stdin);assert f['bots_hidden']==$B0,f;assert not any(r['session'].startswith('$FTS') for r in f['stuck_sessions']),f;print('dismiss OK: bots_hidden back to',f['bots_hidden'],'dismissed',f['dismissed_count'])" || fail "dismiss persist"
UD="check-undismiss-$(date +%s)"
curl -s -X POST "$BASE/api/events" -H 'Content-Type: application/json' -d "{\"v\":1,\"session\":\"$UD\",\"ts\":1,\"page\":\"/\",\"event\":\"page_view\"}" | grep -q '"ok": true' || fail "undismiss fixture ingest"
curl -s -X POST "$BASE/api/funnel/dismiss" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"session\":\"$UD\"}" | grep -q '"ok": true' || fail "dismiss throwaway"
curl -s -X POST "$BASE/api/funnel/undismiss" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"session\":\"$UD\"}" | grep -q '"ok": true' || fail "undismiss"
curl -s -X POST "$BASE/api/funnel/undismiss" -H 'Content-Type: application/json' -d "{\"session\":\"$UD\"}" | grep -q unauthorized || fail "undismiss without token not rejected"
curl -s "$BASE/api/funnel?bots=1" | python3 -c "import json,sys;f=json.load(sys.stdin);assert any(r['session']=='$UD' for r in f['stuck_sessions']),f;print('undismiss OK: row restored')" || fail "undismiss restore"
curl -s -X POST "$BASE/api/funnel/dismiss" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"session\":\"$UD\"}" | grep -q '"ok": true' || fail "dismiss throwaway again"
# 5. streak helper roundtrip (restored after — one tick of skew at most)
python3 - "$DIR" <<'EOF' || fail "streak helper"
import sys; sys.path.insert(0, sys.argv[1] + "/server"); import app
prev = app.load_funnel_streak()
assert isinstance(prev.get("streak"), int), prev
s1 = app.update_funnel_streak("FAILING")
assert app.load_funnel_streak()["streak"] == s1, (s1, app.load_funnel_streak())
s0 = app.update_funnel_streak("HEALTHY")
assert s0 == 0, s0
with open(sys.argv[1] + "/data/funnel_streak.json", "w") as f:
    import json; json.dump(prev, f)
print("streak OK: FAILING +1, HEALTHY reset, restored", prev)
EOF
python3 -c "
import json
lines=[json.loads(l) for l in open('$DIR/data/events.jsonl') if l.strip()]
assert lines, 'events.jsonl empty'
mine=[l for l in lines if l.get('session')=='$SESS']
assert mine, 'check event missing'
for l in lines[-20:]:
    assert 'ip' not in l and 'client' not in l and 'address' not in l, l
print('privacy OK: no ip/client/address keys in events.jsonl')" || fail "events privacy"
# plugin zip downloads and contains manifest + SKILL doc
curl -s -o /tmp/fh-plugin-test.zip "$BASE/download/plugin.zip" || fail "plugin zip download"
python3 -c "import zipfile;z=zipfile.ZipFile('/tmp/fh-plugin-test.zip');n=z.namelist();assert any(x.endswith('plugin.json') for x in n),n;assert any(x.endswith('SKILL.md') for x in n),n;print('zip OK',len(n),'files')" || fail "plugin zip contents"
# CALM OWNER-DRAWER (2026-09-29): every SSH-class flip works from the page API.
# Master TOKEN gates owner settings; demo (fh-*) keys get 403; flips are
# live with no restart and are restored after so the suite leaves no drift.
curl -s "$BASE/api/owner/settings" | grep -q unauthorized || fail "owner: GET without token not rejected"
curl -s -X POST "$BASE/api/owner/settings" -H 'Content-Type: application/json' -d '{"funnel_min_visits":5}' | grep -q unauthorized || fail "owner: POST without token not rejected"
curl -s "$BASE/api/owner/settings" "${AUTH[@]}" | python3 -c "import json,sys;o=json.load(sys.stdin);assert set(o)=={'demo_mint_enabled','funnel_min_visits','funnel_download_alarm_ratio','funnel_bot_noise_ratio','funnel_proof_healthy_ratio','funnel_critic_fail_streak','min_human_sessions','stress_max_ticks','real_spend_tracking'},o;assert 'TOKEN' not in json.dumps(o),o;print('owner GET OK (master, no secrets):',o['funnel_min_visits'],'visits')" || fail "owner: GET (master)"
curl -s -X POST "$BASE/api/owner/settings" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"funnel_min_visits":"x"}' | grep -q '"error"' || fail "owner: bad type not rejected"
curl -s -X POST "$BASE/api/owner/settings" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"nope":1}' | grep -q '"error"' || fail "owner: unknown key not rejected"
# threshold flip roundtrip from the page API (restored: no drift)
V0=$(curl -s "$BASE/api/owner/settings" "${AUTH[@]}" | python3 -c "import json,sys;print(json.load(sys.stdin)['funnel_min_visits'])")
V1=$((V0 + 1))
curl -s -X POST "$BASE/api/owner/settings" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"funnel_min_visits\":$V1}" | grep -q "\"funnel_min_visits\": $V1" || fail "owner: threshold flip"
curl -s "$BASE/api/funnel" | grep -q verdict || fail "owner: funnel still serves after flip"
curl -s -X POST "$BASE/api/owner/settings" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"funnel_min_visits\":$V0}" | grep -q "\"funnel_min_visits\": $V0" || fail "owner: threshold restore"
# mint on/off flip from the page API: on -> public mint works -> demo key
# minted -> demo key gets 403 on owner paths but still passes /api/auth ->
# off again -> public mint 403s. Proves the Owner drawer end to end.
curl -s -X POST "$BASE/api/owner/settings" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"demo_mint_enabled":true}' | grep -q '"demo_mint_enabled": true' || fail "owner: mint on"
MINTSESS="check-owner-$(date +%s)"
DEMOTOK=$(curl -s -X POST "$BASE/api/token/mint" -H 'Content-Type: application/json' -d "{\"session\":\"$MINTSESS\"}" | python3 -c "import json,sys;print(json.load(sys.stdin).get('token',''))")
[ -n "$DEMOTOK" ] || fail "owner: mint while enabled"
curl -s "$BASE/api/owner/settings" -H "Authorization: Bearer $DEMOTOK" | grep -q "owner-only" || fail "owner: demo key not gated (expected 403 owner-only)"
curl -s "$BASE/api/auth" -H "Authorization: Bearer $DEMOTOK" | grep -q '"ok": true' || fail "owner: demo key should still auth"
curl -s -X POST "$BASE/api/policy" -H "Authorization: Bearer $DEMOTOK" -H 'Content-Type: application/json' -d '{"quality_floor":70}' | grep -q quality_floor || fail "owner: demo key policy write (scheme kept)"
curl -s -X POST "$BASE/api/owner/settings" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"demo_mint_enabled":false}' | grep -q '"demo_mint_enabled": false' || fail "owner: mint off (restored)"
curl -s -X POST "$BASE/api/token/mint" -H 'Content-Type: application/json' -d '{"session":"check-suite"}' | grep -q "owner-only" || fail "owner: mint not disabled after restore"
# unbounded toggle from the page API (policy path the Owner drawer uses):
# cap -> bounded status -> back to null -> unbounded (live stays unbounded).
curl -s -X POST "$BASE/api/policy" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"max_cycles":1000}' | grep -q max_cycles || fail "owner: cap at 1000"
curl -s "$BASE/api/status" | python3 -c "import json,sys;s=json.load(sys.stdin);assert s['unbounded'] is False and s['cycles_remaining']==1000-s['cycle'],s;print('bounded OK:',s['cycle'],'/1000')" || fail "owner: bounded status"
curl -s -X POST "$BASE/api/policy" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"max_cycles":null}' | grep -q max_cycles || fail "owner: back to forever"
curl -s "$BASE/api/status" | python3 -c "import json,sys;s=json.load(sys.stdin);assert s['unbounded'] is True,s;print('forever OK: cycle',s['cycle'],'/inf')" || fail "owner: unbounded status"
# share page is public and shows live state
curl -s "$BASE/share" | grep -q "cycle" || fail "share page"
curl -s "$BASE/" | grep -q "Forever Harness" || fail "first paint"
curl -s "$BASE/" | grep -q "already running" || fail "landing: standalone-first missing"
curl -s "$BASE/" | grep -q "Show what it did" || fail "landing: proof button missing"
curl -s "$BASE/" | grep -q "Get token" || fail "landing: token affordance missing"
curl -s "$BASE/" | grep -q "master key" || fail "landing: owner drawer missing"
curl -s "$BASE/" | grep -q "To-do list" || fail "landing: real-backlog card missing"
curl -s "$BASE/" | grep -q "Forever" || fail "landing: forever preset missing"
curl -s "$BASE/" | grep -q "Suggest" || fail "landing: AI-prefill missing"
curl -s "$BASE/" | grep -q "Stress test" || fail "landing: limit-pusher missing"
curl -s "$BASE/" | grep -q "Visitors" || fail "landing: visitors card missing"
curl -s "$BASE/" | grep -q "Advanced" || fail "landing: presets-first (Advanced) missing"
curl -s "$BASE/" | grep -q "Plain words" || fail "landing: jargon glossary missing"
curl -s "$BASE/" | grep -q "tidying memory" || fail "landing: inline jargon translation missing"
# LOOP HANDS: rules in needs.json, R1b fixtures, one live tick with real ids,
# gate/critic proof, then full cleanup (no permanent junk).
python3 - "$DIR" <<'EOF' || fail "hands rules in needs.json"
import sys, json
c = json.load(open(sys.argv[1] + "/needs.json"))
assert c.get("hands_enabled") is True, c.get("hands_enabled")
assert "hands_e083_url" in c and "hands_rules_doc" in c, sorted(c)
assert "publishes stalled" in c["hands_rules_doc"] and "records grew" in c["hands_rules_doc"], c["hands_rules_doc"]
print("hands rules OK: enabled, e083 auto-url, stall/grow/fail rules documented")
EOF
E083D="$(cd "$DIR/../e083-scrapenet" && pwd)"
E083B="http://127.0.0.1:$(python3 -c "import json;print(json.load(open('$E083D/needs.json'))['port'])")"
E083OWNER=$(python3 -c "import json;print(json.load(open('$E083D/needs.json')).get('owner_token',''))")
[ -n "$E083OWNER" ] || fail "e083 owner token"
python3 - "$DIR" <<'EOF' || fail "R1b fixtures"
import sys; sys.path.insert(0, sys.argv[1] + "/server"); import app
assert app.check_hands_claim("micro-goal: x\nevidence: y (rows=1, ok=True)") is None
r = app.check_hands_claim("micro-goal: x\nevidence: y\nhands: filed gap (e083 hiccup)")
assert r and r.startswith("R1"), r
r = app.check_hands_claim("micro-goal: x\nevidence: y\nhands: queued post (no id yet)")
assert r and r.startswith("R1"), r
r = app.check_hands_claim("hands: filed gap gap-20990101-000000-ffff (stalled)")
assert r and "e083 gaps store" in r, r
r = app.check_hands_claim("hands: queued post loop-2099-01-01-ffff (grew)")
assert r and "e083 growth queue" in r, r
print("R1b fixtures OK: id-less + phantom ids rejected")
EOF
SNAP_GAPS=$(curl -s "$E083B/api/gaps?include_test=1" | python3 -c "import json,sys;print(' '.join(g['id'] for g in json.load(sys.stdin)['gaps']))")
SNAP_POSTS=$(curl -s "$E083B/api/growth/queue" | python3 -c "import json,sys;print(' '.join(p['id'] for p in json.load(sys.stdin)['posts']))")
# stale-state guard: prior runs / daemon ticks may have left open e082-loop
# gaps (dedupe keys on the stall level, so a leftover gap at the current
# publishes count would be referenced instead of filing fresh) or a pending
# loop draft. Resolve them here (owner auth) so the live tick below files +
# queues FRESH ids; the R1b store-verified asserts below still require both
# ids to exist in the e083 store with source marks.
for id in $(curl -s "$E083B/api/gaps?include_test=1" | python3 -c "import json,sys;print(' '.join(g['id'] for g in json.load(sys.stdin)['gaps'] if g.get('source')=='e082-loop'))"); do
  curl -s -X DELETE "$E083B/api/gaps?id=$id&owner_token=$E083OWNER" | grep -q '"ok": *true' || fail "stale gap resolve $id"
done
for id in $(curl -s "$E083B/api/growth/queue" | python3 -c "import json,sys;print(' '.join(p['id'] for p in json.load(sys.stdin)['posts'] if p.get('source')=='loop' and not p.get('posted')))"); do
  curl -s -X POST "$E083B/api/growth/reject" -H 'Content-Type: application/json' -d "{\"id\":\"$id\",\"owner_token\":\"$E083OWNER\"}" | grep -q '"rejected"' || true
  curl -s -X DELETE "$E083B/api/growth/draft?id=$id&owner_token=$E083OWNER" | grep -q '"ok": *true' || fail "stale draft resolve $id"
done
echo "stale-state cleared (open e082-loop gaps + pending loop drafts resolved)"
# force BOTH rules deterministically: baseline publishes=current (stalled next
# tick); ingest one real test row so records genuinely grow.
PUBL=$(curl -s "$E083B/api/funnel" | python3 -c "import json,sys;print(json.load(sys.stdin)['publishes'])")
RECN=$(curl -s "$E083B/api/health" | python3 -c "import json,sys;print(json.load(sys.stdin)['records'])")
python3 - "$DIR" "$PUBL" "$RECN" <<'EOF' || fail "hands baseline seed"
import sys, json
# HONEST-COUNTERS: /api/health counts honest rows only, so the test:true
# row ingested below never moves it. Offset the baseline by exactly that
# one row so the grow rule fires deterministically and the tick queues a
# fresh draft (the row itself is real and audit-visible via ?include_test=1).
json.dump({"publishes": int(sys.argv[2]), "records": int(sys.argv[3]) - 1,
           "verdict": "seed", "updated_at": "check.sh"},
          open(sys.argv[1] + "/data/hands.json", "w"), indent=2)
print("baseline seeded publishes=%s records=%s (honest-1: one test row ingested below)" % (sys.argv[2], int(sys.argv[3]) - 1))
EOF
HTS="$(date +%s)"
HSIGN=$(curl -s -X POST "$E083B/api/signup" -H 'Content-Type: application/json' -d '{"name":"hands-proof"}')
echo "$HSIGN" | grep -q '"test": *true' || fail "hands seed node must be test:true: $HSIGN"
HSNODE=$(echo "$HSIGN" | python3 -c "import json,sys;print(json.load(sys.stdin)['node_id'])")
HSTOK=$(echo "$HSIGN" | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
curl -s -X POST "$E083B/api/ingest" -H 'Content-Type: application/json' -d "{\"node_id\":\"$HSNODE\",\"token\":\"$HSTOK\",\"dataset\":\"product-prices\",\"records\":[{\"name\":\"Hands Proof $HTS\",\"price\":7.77,\"url\":\"https://shop.example/p/hands\"}]}" | grep -q '"accepted": *1' || fail "hands growth seed ingest"
curl -s -X POST "$BASE/api/control/tick" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"by":"check-hands"}' | grep -q '"cycle"' || fail "hands tick"
LT=$(curl -s "$BASE/api/last-tick")
echo "$LT" | python3 -c "import json,sys;t=json.load(sys.stdin);h=t.get('hands') or {};assert h.get('acted') is True,h;assert h.get('gap_id') and h.get('post_id'),h;s=h.get('summary','');assert ('filed gap' in s or 'gap already open' in s or 'escalation already open' in s) and ('queued post' in s or 'draft already pending' in s),s;assert h.get('links'),h;print('live tick acted OK:',h['gap_id'],h['post_id'])" || fail "hands live ids"
HCYC=$(echo "$LT" | python3 -c "import json,sys;print(json.load(sys.stdin)['cycle'])")
GAPID=$(echo "$LT" | python3 -c "import json,sys;print(json.load(sys.stdin)['hands']['gap_id'])")
POSTID=$(echo "$LT" | python3 -c "import json,sys;print(json.load(sys.stdin)['hands']['post_id'])")
# freshness: with stale state resolved above, both ids must be new this run
# (a racing daemon tick may file seconds earlier — still fresh, still verified below).
case " $SNAP_GAPS " in *" $GAPID "*) fail "gap id not fresh (stale $GAPID referenced)";; esac
case " $SNAP_POSTS " in *" $POSTID "*) fail "draft id not fresh (stale $POSTID referenced)";; esac
echo "fresh ids OK: $GAPID + $POSTID (not in pre-run snapshots)"
# e083 side: gap stored with source mark, draft queued unapproved with source mark
curl -s "$E083B/api/gaps?include_test=1" | grep -q "$GAPID" || fail "gap stored: $GAPID"
curl -s "$E083B/api/gaps?include_test=1" | python3 -c "import json,sys;g={x['id']:x for x in json.load(sys.stdin)['gaps']};assert g['$GAPID']['source']=='e082-loop',g['$GAPID'];assert g['$GAPID']['evidence'],g['$GAPID'];print('gap attributed OK: source e082-loop + evidence')" || fail "gap attribution"
curl -s "$E083B/api/growth/queue" | grep -q "$POSTID" || fail "draft queued: $POSTID"
curl -s "$E083B/api/growth/queue" | python3 -c "import json,sys;ps={x['id']:x for x in json.load(sys.stdin)['posts']};p=ps['$POSTID'];assert p['source']=='loop',p;assert p['approved'] is False,p;print('draft OK: source loop, unapproved (never auto-posted)')" || fail "draft attribution"
# gate + critic proof on the live tick (BEFORE cleanup deletes the artifacts)
curl -s -X POST "$BASE/api/verify" | python3 -c "import json,sys;v=json.load(sys.stdin);g={x['name']:x for x in v['gates']};assert g['evidence_present']['pass'],g;print('gate OK: evidence_present green')" || fail "hands gate"
curl -s -X POST "$BASE/api/review" -H 'Content-Type: application/json' -d "{\"cycle\":$HCYC}" | python3 -c "import json,sys;r=json.load(sys.stdin);assert not any('hands claim' in x for x in r['reasons']),r;print('critic OK: no R1 hands rejection (verdict=%s)' % r['verdict'])" || fail "hands critic"
# board receipt shows the action with links
curl -s "$BASE/api/last-tick" | python3 -c "import json,sys;t=json.load(sys.stdin);h=t.get('hands') or {};assert h.get('links') and all(u['url'].startswith('http') for u in h['links']),h;print('receipt OK: action + %d links' % len(h['links']))" || fail "receipt links"
# cleanup: delete every gap/draft id created during this suite run (owner auth
# covers any gap; drafts delete while unposted). Test ingest row stays as
# test:true audit-hidden traffic (purge-test would wipe other harnesses' rows).
NEW_GAPS=$(curl -s "$E083B/api/gaps?include_test=1" | python3 -c "import json,sys;cur=[g['id'] for g in json.load(sys.stdin)['gaps']];want=set('$GAPID'.split()+cur);print(' '.join(i for i in cur if i not in '$SNAP_GAPS'.split() or i=='$GAPID'))")
NEW_POSTS=$(curl -s "$E083B/api/growth/queue" | python3 -c "import json,sys;cur=[p['id'] for p in json.load(sys.stdin)['posts']];print(' '.join(i for i in cur if i not in '$SNAP_POSTS'.split() or i=='$POSTID'))")
for id in $NEW_GAPS; do curl -s -X DELETE "$E083B/api/gaps?id=$id&owner_token=$E083OWNER" | grep -q '"ok": *true' || fail "gap cleanup $id"; done
for id in $NEW_POSTS; do curl -s -X POST "$E083B/api/growth/reject" -H 'Content-Type: application/json' -d "{\"id\":\"$id\",\"owner_token\":\"$E083OWNER\"}" | grep -q '"rejected"' || true; curl -s -X DELETE "$E083B/api/growth/draft?id=$id&owner_token=$E083OWNER" | grep -q '"ok": *true' || fail "draft cleanup $id"; done
curl -s "$E083B/api/gaps?include_test=1" | grep -q "$GAPID" && fail "gap not cleaned"
curl -s "$E083B/api/growth/queue" | grep -q "$POSTID" && fail "draft not cleaned"
test -s "$DIR/log/hands.log" || fail "hands.log empty"
grep -q "$GAPID\|$POSTID" "$DIR/log/hands.log" || fail "hands.log missing live ids"
echo "hands OK: live tick filed $GAPID + queued $POSTID, gate/critic green, cleaned"
# LIMITS LOOP: LIMITS.md open checkboxes are the second backlog source
# (needs.json limits_*): every 4th tick consumes one, smallest slice first.
python3 - "$DIR" <<'EOF' || fail "limits rules in needs.json"
import sys, json
c = json.load(open(sys.argv[1] + "/needs.json"))
assert c.get("limits_every_n_ticks") == 4, c.get("limits_every_n_ticks")
assert "limits_doc" in c and "OPEN [limits-lN]" in c["limits_doc"], c.get("limits_doc")
print("limits rules OK: every 4th tick consumes one open LIMITS checkbox")
EOF
python3 - "$DIR" <<'EOF' || fail "limits fixtures"
import sys; sys.path.insert(0, sys.argv[1] + "/server"); import app
items = app.limits_open_items()
assert len(items) == 6, items
assert all(i["id"].startswith("limits-l") and i["slice"] for i in items), items
assert app.backlog_current(4)["id"].startswith("limits-"), app.backlog_current(4)
assert app.backlog_current(5)["id"].startswith("e083-"), app.backlog_current(5)
ev = app.collect_limits_evidence(-1, {"id": "limits-l4", "slice": "fixture"})
assert ev["ok"] is True and ev["rows"] >= 1, ev
print("limits fixtures OK: 6 open parsed, 4th-tick diversion, l4 probe green")
EOF
python3 - "$DIR" <<'EOF'
import sys
p = sys.argv[1] + "/data/evidence.jsonl"
ls = [l for l in open(p) if '"cycle": -1' not in l]
open(p, "w").writelines(ls)
print("fixture evidence row removed")
EOF
curl -s "$BASE/api/backlog" | python3 -c "import json,sys;b=json.load(sys.stdin);assert len(b['items'])>=9,b;assert any(str(i.get('id','')).startswith('limits-') for i in b['items']),b;print('backlog OK: e083 + LIMITS items served')" || fail "backlog limits items"
# live tick consuming one LIMITS item: fire ticks until a fresh cycle lands on
# a multiple of 4 (snapshot e083 first — hands may file gaps/drafts en route).
LSNAP_GAPS=$(curl -s "$E083B/api/gaps?include_test=1" | python3 -c "import json,sys;print(' '.join(g['id'] for g in json.load(sys.stdin)['gaps']))")
LSNAP_POSTS=$(curl -s "$E083B/api/growth/queue" | python3 -c "import json,sys;print(' '.join(p['id'] for p in json.load(sys.stdin)['posts']))")
LCYC=$(curl -s "$BASE/api/status" | python3 -c "import json,sys;print(json.load(sys.stdin)['cycle'])")
LNEED=$(( (4 - LCYC % 4) % 4 )); [ "$LNEED" -eq 0 ] && LNEED=4
for i in $(seq 1 $LNEED); do curl -s -X POST "$BASE/api/control/tick" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"by":"check-limits"}' | grep -q '"cycle"' || fail "limits tick $i"; done
LT2=$(curl -s "$BASE/api/last-tick")
LCYC2=$(echo "$LT2" | python3 -c "import json,sys;print(json.load(sys.stdin)['cycle'])")
[ $((LCYC2 % 4)) -eq 0 ] || fail "limits tick did not land on 4-divisible cycle: $LCYC2"
python3 - "$DIR" "$LCYC2" <<'EOF' || fail "limits live evidence"
import sys, json
ls = [json.loads(l) for l in open(sys.argv[1] + "/data/evidence.jsonl")]
ev = next(e for e in ls if e.get("cycle") == int(sys.argv[2]))
assert str(ev.get("item", "")).startswith("limits-"), ev
assert ev.get("ok") is True and ev.get("rows", 0) >= 1, ev
assert len(ev.get("detail", "")) > 20, ev
print("live LIMITS tick OK: cycle %s consumed %s (rows=%s)" % (ev["cycle"], ev["item"], ev["rows"]))
EOF
echo "$LT2" | python3 -c "import json,sys;t=json.load(sys.stdin);assert 'limits-l' in (t.get('notes') or ''),t;print('receipt OK: tick notes carry the LIMITS item')" || fail "limits receipt"
# cleanup: any gap/draft hands filed during the limits ticks (owner auth).
LNEW_GAPS=$(curl -s "$E083B/api/gaps?include_test=1" | python3 -c "import json,sys;cur=[g['id'] for g in json.load(sys.stdin)['gaps']];print(' '.join(i for i in cur if i not in '$LSNAP_GAPS'.split()))")
LNEW_POSTS=$(curl -s "$E083B/api/growth/queue" | python3 -c "import json,sys;cur=[p['id'] for p in json.load(sys.stdin)['posts']];print(' '.join(i for i in cur if i not in '$LSNAP_POSTS'.split()))")
for id in $LNEW_GAPS; do curl -s -X DELETE "$E083B/api/gaps?id=$id&owner_token=$E083OWNER" | grep -q '"ok": *true' || fail "limits gap cleanup $id"; done
for id in $LNEW_POSTS; do curl -s -X POST "$E083B/api/growth/reject" -H 'Content-Type: application/json' -d "{\"id\":\"$id\",\"owner_token\":\"$E083OWNER\"}" | grep -q '"rejected"' || true; curl -s -X DELETE "$E083B/api/growth/draft?id=$id&owner_token=$E083OWNER" | grep -q '"ok": *true' || fail "limits draft cleanup $id"; done
echo "limits OK: live tick consumed a LIMITS item, side-effects cleaned"
# test hygiene: dismiss this run's own poll session so bots_hidden stays flat across runs
curl -s -X POST "$BASE/api/funnel/dismiss" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"session\":\"$SESS\"}" | grep -q '"ok": true' || fail "dismiss own poll session"
curl -s "$BASE/" | grep -q "plugin.zip" || fail "landing: install-missing"
curl -s "$BASE/" | grep -q "no IPs stored" || fail "landing: privacy line missing"
curl -s "$BASE/skill" | grep -qi "keep-going" || fail "skill doc"
echo "PASS"
