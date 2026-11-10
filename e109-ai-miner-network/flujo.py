#!/usr/bin/env python3
"""e109 — the whole loop, measured: job -> worker -> receipt -> verification -> ledger -> batch.

This is the MVP step 1 and the honest test of "is a blockchain needed here":
it runs the real loop with **no chain at all** — ed25519 signatures, a SQLite ledger, one merkle
root per batch — and measures the three numbers that decide whether a chain earns its place:

  1. signature verification rate (should be 100%: it is deterministic maths),
  2. re-execution match rate (spot-checks: can an independent verifier catch a liar?),
  3. the cost of the loop per job, in joules, and what the settlement anchor would add.

Settlement is a plug: `close_batch` writes the merkle root; anchoring it on Solana changes one
row (`batches.anchor`), never the loop. Usage:

  python3 flujo.py [jobs]      # default 9 jobs
"""
import difflib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import energia
import libro
import recibo

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())
M = CFG["machine"]
PORT = 11509
BASE = "http://127.0.0.1:%d" % PORT
PRICE = CFG["api_cost_usd_per_job"]

JOBS = [
    ("quote-by-text",
     "You are the office assistant of {biz}. Price book: {book}. Write the SMS the customer "
     "receives: the visit window, the diagnostic fee, the likely range, and one question that "
     "unlocks the exact price. Under 90 words, no emoji, no hedging.",
     "Lead at 2:41pm, voicemail transcript: \"Hi, it's Dana, the AC upstairs stopped cooling last "
     "night, it's a 3 ton unit, about 9 years old, and the fan outside is running but the air is "
     "warm. Can someone come today? I'm home after 4.\""),
    ("estimate-to-paid",
     "You are the office assistant of {biz}. Price book: {book}. Turn the approved estimate into "
     "invoice line items, the payment request text, and two follow-ups with day offsets. Plain text.",
     "Approved estimate: 1x condenser fan motor (OEM, 1/3 HP) 268.00 labor 1.5h; 1x dual run "
     "capacitor 42.00 labor 0.3h; recharge R-410A 3 lb 135.00. Card on file declined twice."),
    ("revenue-report",
     "You are the office assistant of {biz}. Given the week's jobs as JSON, write Friday's report: "
     "revenue booked, collected, unpaid invoices with age, and the number that moved most. "
     "Under 200 words, numbers first.",
     "{\"jobs\":[{\"id\":1,\"quoted\":412,\"paid\":412,\"closed\":\"mon\"},{\"id\":2,\"quoted\":189,"
     "\"paid\":0,\"closed\":\"tue\"},{\"id\":3,\"quoted\":7400,\"paid\":3700,\"closed\":\"wed\"},"
     "{\"id\":4,\"quoted\":0,\"paid\":0,\"closed\":\"thu\"},{\"id\":5,\"quoted\":1650,\"paid\":1650,"
     "\"closed\":\"fri\"}]}"),
]


def post(path, obj, timeout=300):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def wait_health(tries=40):
    """GET, not POST: the worker serves health as a plain read."""
    for _ in range(tries):
        try:
            with urllib.request.urlopen(BASE + "/health", timeout=2) as r:
                return json.load(r)
        except Exception:
            time.sleep(0.5)
    raise SystemExit("worker did not come up")


def rerun(spec):
    """An independent verifier: same spec, its own inference, compare the answer hash."""
    body = {"model": M["model"],
            "messages": [{"role": "system", "content": spec["system"]},
                         {"role": "user", "content": spec["user"]}],
            "stream": False,
            "options": {"temperature": 0, "seed": 42, "num_predict": M["max_tokens"]}}
    req = urllib.request.Request(M["url"].rstrip("/") + "/api/chat",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return (json.load(r).get("message") or {}).get("content", "")


def main(argv):
    n = int(argv[0]) if argv else 9
    db = libro.connect()
    now = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")

    _, buyer_pub = recibo.keypair("buyer")
    libro.register(db, "buyer_local", "client", buyer_pub, now())

    proc = subprocess.Popen([sys.executable, "worker.py", str(PORT), "miner_a"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        health = wait_health()
        libro.register(db, "miner_a", "worker", health["worker"], now())
        receipts, sig_ok, matches, lat, joules = [], 0, [], [], []
        for i in range(n):
            wf, system, user = JOBS[i % len(JOBS)]
            spec = {"workflow": wf, "client": "biz_%02d" % (i % 3),
                    "ref": "agent_ref_%d" % (i % 2),          # first-touch attribution
                    "price_usd": PRICE,
                    "system": system.format(biz=M["biz"], book=M["price_book"]),
                    "user": user}
            jid = recibo.job_id(spec)
            t0 = time.time()
            res = post("/job", {"spec": spec})
            lat.append(time.time() - t0)
            r = res["receipt"]
            ok = recibo.verify(res["pub"], r, res["sig"]) and r["job"] == jid
            sig_ok += ok
            spot, match = False, ""
            if i % 3 == 0:                                    # spot-check one in three
                spot = True
                again = rerun(spec)
                if recibo.sha(again.encode()) == r["out_sha"]:
                    match = "exact"
                elif difflib.SequenceMatcher(None, again, res["output"]).ratio() >= 0.98:
                    match = "fuzzy"
                else:
                    match = "MISMATCH"
                matches.append(match)
            libro.add_job(db, spec, jid, now())
            libro.add_receipt(db, jid, r, res["sig"], ok, spot, match, now())
            libro.owe_commission(db, jid, spec["ref"])
            receipts.append(r)
            joules.append(r["joules"])

        root = recibo.merkle(receipts)
        batch = libro.close_batch(db, root, now())
        rep = libro.report(db)
        out = {
            "batch": batch, "root": root, "jobs": n,
            "signature_verified": sig_ok,
            "spot_checked": len(matches),
            "match_exact": matches.count("exact"),
            "match_fuzzy": matches.count("fuzzy"),
            "match_mismatch": matches.count("MISMATCH"),
            "latency_s_mean": round(sum(lat) / len(lat), 2),
            "joules_mean": round(sum(joules) / len(joules), 1),
            "joules_total": round(sum(joules), 1),
            "usd_per_job_energy": round(sum(joules) / 3_600_000 * M["usd_per_kwh"] / n, 8),
            "price_per_job_usd": PRICE,
            "batch_ledger": rep,
            "anchor": None,
            "anchor_note": "no chain used: the merkle root is the anchor. A Solana memo would "
                           "write this root for ~$0.00043 per BATCH, not per job.",
        }
        (ROOT / "data").mkdir(exist_ok=True)
        (ROOT / "data" / "flujo.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
        print(json.dumps(out, indent=1, ensure_ascii=False))
    finally:
        proc.terminate()
        proc.wait(timeout=10)


if __name__ == "__main__":
    main(sys.argv[1:])
