#!/usr/bin/env python3
"""History must survive a listener restart (q79): without persisted samples,
every restart (deploy, crash) costs an hour of blindness because coin_rules
needs 12 five-minute samples. Paper only, temp dirs, no network (RS_DRY_RUN).
"""
import csv
import json
import os
import sys
import tempfile

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(B, "scripts"))
os.environ["RS_DRY_RUN"] = "1"
import rstrength_listener as L


def fresh_env():
    d = tempfile.mkdtemp()
    L.DATA, L.SERIES, L.FLAGS = d, d + "/s.csv", d + "/f.csv"
    L.LOWT, L.STATE, L.LAUNCH = d + "/l.csv", d + "/st.json", d + "/lw.json"
    return d


def sample(vol, liq, price=1.0):
    return {"price": price, "vol_m5": vol, "vol_h1": 0, "liq_usd": liq}


fails = []

# 1) 11 flat samples, "restart", 12th spikes -> STRONG fires (no re-warm)
fresh_env()
e1 = L.Engine()
assert e1.hist == {}, "fresh engine starts with empty history"
t0 = 1_800_000_000
for i in range(11):
    e1.handle_sample(t0 + i * 300, {"TOK": sample(1000, 100000)})
e2 = L.Engine()  # simulated restart: new process, same STATE file
if len(e2.hist.get("TOK", [])) != 11:
    fails.append(f"history not restored across restart: {len(e2.hist.get('TOK', []))} samples")
out = e2.handle_sample(t0 + 11 * 300, {"TOK": sample(5000, 130000)})
if not any(r["token"] == "TOK" and r["rule"] == "STRONG" for r in out):
    fails.append(f"no STRONG on 12th sample after restart: {[(r['token'], r['rule']) for r in out]}")

# 2) corrupt/legacy state still boots with empty history (never crash the loop)
fresh_env()
json.dump({"cool": {}, "hist": "garbage"}, open(L.STATE, "w"))
try:
    e3 = L.Engine()
    if e3.hist != {}:
        fails.append("corrupt hist not ignored")
except Exception as ex:
    fails.append(f"corrupt state crashed Engine: {ex!r}")

# 3) state file actually carries the samples (and stays small)
fresh_env()
e4 = L.Engine()
for i in range(15):
    e4.handle_sample(t0 + i * 300, {"TOK": sample(1000, 100000)})
st = json.load(open(L.STATE))
n = len((st.get("hist") or {}).get("TOK", []))
if n != 13:
    fails.append(f"state keeps {n} samples, want capped 13")

if fails:
    print("FAIL hist_persist:")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("OK hist_persist: restart keeps samples, corrupt state ignored, capped at 13")
