#!/usr/bin/env python3
"""Jev gate: task in -> scam/EV/fit/difficulty out. Cheap first pass.

Usage:
  echo '{"id":"t1","text":"Fix flaky login test..."}' | python3 bin/triage.py
  python3 bin/triage.py --text "Build Telegram alert bot, $50 fixed"

Reads OPENROUTER_API_KEY from env. Never prints the key.
"""
import json
import os
import sys
import urllib.request

URL = os.environ.get("OPENROUTER_DECISIONS_URL",
                "https://openrouter.ai/api/alpha/decisions")
MODEL = "typesafe/jev-1.13"
STATE_CTX = (
    "We are a coding agent with $9.81 inference credits, no trading capital. "
    "We take fixed-price coding gigs and bounties for cash. Reject scams, "
    "wallet-connect traps, and upfront-fee tasks."
)

QUESTIONS = {
    "is_scam": {"type": "noul",
                "instructions": "Is this task a scam, wallet trap, or upfront-fee fraud?"},
    "payout_likely": {"type": "noul",
                      "instructions": "Will a real buyer pay cash on delivery for this?"},
    "fit": {"type": "choice",
            "instructions": "How well does this fit a coding agent with repo + API skills?",
            "criteria": {"perfect": "Pure code, tests verifiable",
                         "stretch": "Code plus light domain work",
                         "poor": "Needs capital, access, or skills we lack"}},
    "value": {"type": "score",
              "instructions": "Expected net cash value after effort?",
              "criteria": ["Negative or zero", "Small positive, tens of dollars",
                           "Meaningful, hundreds+ of dollars"]},
}


def triage(task_id, text):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return {"id": task_id, "error": "OPENROUTER_API_KEY missing"}
    body = json.dumps({
        "model": MODEL,
        "state": STATE_CTX + " TASK: " + text[:2000],
        "questions": QUESTIONS,
    }).encode()
    req = urllib.request.Request(
        URL, data=body,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/p4",
                 "X-Title": "e070-triage"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.loads(r.read())
    except Exception as e:  # noqa: BLE001 - report, don't crash the loop
        return {"id": task_id, "error": type(e).__name__ + ": " + str(e)[:200]}
    a = out.get("answers", {})
    scam = a.get("is_scam", {}).get("noul", 1)
    payout = a.get("payout_likely", {}).get("noul", 0)
    value = a.get("value", {}).get("score", 0)
    # Tuned 2026-09-18: Jev is honestly uncertain about buyers (~0.5 on legit
    # tasks), so borderline goes to REVIEW instead of silent SKIP.
    verdict = "SKIP"
    if scam < 0.5 and value >= 1.0 and payout > 0.55:
        verdict = "ESCALATE"
    elif scam < 0.5 and value >= 0.7 and payout > 0.4:
        verdict = "REVIEW"
    return {"id": task_id, "verdict": verdict,
            "scam": a.get("is_scam", {}).get("noul"),
            "payout": a.get("payout_likely", {}).get("noul"),
            "fit": a.get("fit", {}).get("choice"),
            "value": a.get("value", {}).get("score"),
            "cost_usd": out.get("usage", {}).get("cost")}


def main():
    if "--text" in sys.argv:
        items = [{"id": "cli-1", "text": sys.argv[sys.argv.index("--text") + 1]}]
    else:
        raw = sys.stdin.read().strip()
        if not raw:
            print(json.dumps({"error": "no input; pipe task JSON or use --text"}))
            return
        obj = json.loads(raw)
        items = obj if isinstance(obj, list) else [obj]
    for it in items:
        print(json.dumps(triage(it.get("id", "?"), it.get("text", ""))))


if __name__ == "__main__":
    main()
