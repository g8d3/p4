#!/usr/bin/env python3
"""e109 — can the customer be the miner? Measure a real AI job on real local hardware.

The proposal: a network where people mine AI results and are paid a small profit over cost.
Before designing a chain around it, one number has to exist: what does *one useful job* cost
on hardware somebody already owns? This measures it — same prompt the business actually sends
(text a quote for an inbound lead) — on this machine's CPU, with the energy counter
(`intel-rapl`, microjoules) read around the run, priced at a configurable $/kWh.

Then the comparison that decides the whole design: local miner cost vs the wholesale API cost
we measured for the same job in e108/costo.py.

Usage:
  python3 mina.py                    # measure (~1 min), write data/mina.json
  python3 mina.py --json             # the dict by stdout
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())
M = CFG["machine"]

PROMPT = {
    "system": "You are the office assistant of {biz}. Price book: {book}. Write the SMS the customer "
              "receives: the visit window, the diagnostic fee, the likely range, and one question that "
              "unlocks the exact price. Under 90 words, no emoji, no hedging.",
    "user": "Lead at 2:41pm, voicemail transcript: \"Hi, it's Dana, the AC upstairs stopped cooling "
            "last night, it's a 3 ton unit, about 9 years old, and the fan outside is running but the "
            "air is warm. Can someone come today? I'm home after 4.\"",
}


def energy_uj():
    p = M["energy_counter"]
    try:
        return int(Path(p).read_text().strip())
    except Exception:
        pass
    # the RAPL counter is root-only on this box; sudo is passwordless and the counter is read-only
    out = subprocess.run(["sudo", "-n", "cat", p], capture_output=True, text=True)
    try:
        return int(out.stdout.strip())
    except Exception:
        return None


def run_local():
    body = {
        "model": M["model"],
        "messages": [{"role": "system", "content": PROMPT["system"].format(
                          biz=M["biz"], book=M["price_book"])},
                     {"role": "user", "content": PROMPT["user"]}],
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": M["max_tokens"]},
    }
    req = urllib.request.Request(M["url"].rstrip("/") + "/api/chat",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    e0 = energy_uj()
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.load(r)
    wall = time.time() - t0
    e1 = energy_uj()
    joules = (e1 - e0) / 1e6 if (e0 is not None and e1 is not None) else None
    return {
        "wall_s": round(wall, 2),
        "prompt_tokens": out.get("prompt_eval_count", 0),
        "completion_tokens": out.get("eval_count", 0),
        "joules": round(joules, 1) if joules is not None else None,
        "text": (out.get("message") or {}).get("content", ""),
    }


def main(argv):
    r = run_local()
    usd = None
    if r["joules"]:
        usd = r["joules"] / 3_600_000 * M["usd_per_kwh"]
    tok_s = (r["completion_tokens"] / r["wall_s"]) if r["wall_s"] else None
    api = CFG["api_cost_usd_per_job"]
    out = {
        "machine": M["label"],
        "model": M["model"],
        "measured": r,
        "tokens_per_s": round(tok_s, 1) if tok_s else None,
        "usd_per_job_local": round(usd, 8) if usd is not None else None,
        "usd_per_job_api": api,
        "ratio_local_over_api": round(usd / api, 2) if usd and api else None,
        "note": "energy covers the CPU package only (intel-rapl), not the whole machine; "
                "the API price is the wholesale rate we already pay (e108/costo.py).",
    }
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "mina.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    if "--json" in argv:
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return
    print("machine: %s — %s" % (out["machine"], out["model"]))
    print("job: %.1fs wall, %d in / %d out, %.1f tok/s, %.0f J" % (
        r["wall_s"], r["prompt_tokens"], r["completion_tokens"],
        out["tokens_per_s"] or 0, r["joules"] or 0))
    print("local cost: $%.8f  vs API $%.8f  = %.1fx the API price" % (
        usd or 0, api, out["ratio_local_over_api"] or 0))
    print("\noutput:\n%s" % r["text"])


if __name__ == "__main__":
    main(sys.argv[1:])
