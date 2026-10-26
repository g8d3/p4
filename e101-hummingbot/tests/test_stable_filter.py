#!/usr/bin/env python3
"""Stablecoin/pegged exclusion for the relative-strength listener (paper only).

1. es_pegado() recognises fiat-pegged symbols, including wrappers.
2. Engine.flag() drops VOL_SPIKE/LIQ_ADD/STRONG on a stable but keeps RUG_RISK.
3. Replay today's real rs_event_flags.csv: before vs after count.
"""
import csv
import os
import sys
import tempfile

B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(B, "scripts"))
import rstrength_listener as L

# 1) symbol recognition
for t in ("USDC", "SYRUPUSDC", "PSTUSDC", "EURC", "PYUSD", "USDE", "USDT", "USDS"):
    assert L.es_pegado(t), t
for t in ("SOL", "WSOL", "JITOSOL", "ORE", "GRASS", "JUP", "RAY"):
    assert not L.es_pegado(t), t

# 2) engine filter: stable VOL_SPIKE dropped, stable RUG_RISK kept
d = tempfile.mkdtemp()
L.DATA, L.FLAGS, L.LOWT, L.STATE = d, d + "/f.csv", d + "/l.csv", d + "/st.json"
eng = L.Engine()
s = {"price": 1.0, "vol_m5": 9000, "vol_h1": 0, "liq_usd": 1000000}
assert eng.flag(1, "COIN", "USDC", "VOL_SPIKE", s, {}, None, None) is None
assert eng.flag(1, "COIN", "SYRUPUSDC", "LIQ_ADD", s, {}, None, None) is None
rug = eng.flag(1, "COIN", "USDC", "RUG_RISK", s, {}, None, None)
assert rug and rug["token"] == "USDC" and rug["rule"] == "RUG_RISK"
rows = list(csv.DictReader(open(L.FLAGS)))
assert [(r["token"], r["rule"]) for r in rows] == [("USDC", "RUG_RISK")]

# 3) replay today's real flags with the same filter
path = os.path.join(B, "data", "rs_event_flags.csv")
before = list(csv.DictReader(open(path)))
kept = [r for r in before if r["rule"] == "RUG_RISK" or not L.es_pegado(r["token"])]
removed = [r for r in before if r not in kept]
print(f"today flags: before={len(before)} after={len(kept)} removed={len(removed)}")
for r in removed:
    print(f"  removed {r['ts']} {r['token']} {r['rule']}")
assert len(kept) < len(before), "replay should remove stablecoin noise"
assert all(r["rule"] == "RUG_RISK" or not L.es_pegado(r["token"]) for r in kept)
assert all(r["token"] in ("EURC", "PYUSD", "SYRUPUSDC", "USDC", "USDE", "USDG") for r in removed)
print("PASS stable filter: pegged symbols excluded, RUG_RISK kept")
