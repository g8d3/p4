#!/usr/bin/env python3
"""e108 — what the three workflows actually cost, measured, not estimated.

The pitch "sell it at cost" only works if cost is a number we can print. This runs the
three workflows a field-service business actually uses — text a quote when a lead calls,
move an estimate to paid, pull Friday's revenue report — against the cheapest real model
we have, and prices the tokens at the published rate.

Cost is the whole product decision: $2,000-$3,000/month incumbent vs measured dollars here.
Nothing hardcoded: model, rates, volumes and price book live in config.json.

Usage:
  python3 costo.py            # measure (~1 min), write data/costo.json, print the sheet
  python3 costo.py --json     # the dict, by stdout
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())
INF = CFG["inference"]
KEY = os.environ.get(INF["key_env"], "")

JOBS = {
    "quote-by-text": {
        "system": "You are the office assistant of {biz}. Price book: {book}. "
                  "Write the SMS the customer receives: the visit window, the diagnostic fee, "
                  "the likely range for the job, and one question that unlocks the exact price. "
                  "Under 90 words, no emoji, no hedging.",
        "user": "Lead at 2:41pm, voicemail transcript: \"Hi, it's Dana, the AC upstairs stopped "
                "cooling last night, it's a 3 ton unit, about 9 years old, and the fan outside is "
                "running but the air is warm. Can someone come today? I'm home after 4.\"",
    },
    "estimate-to-paid": {
        "system": "You are the office assistant of {biz}. Price book: {book}. "
                  "Turn the approved estimate into: invoice line items with quantities and prices, "
                  "the payment request text, and the two follow-ups with their day offsets. "
                  "Plain text, no markdown tables.",
        "user": "Approved estimate: 1x condenser fan motor (OEM, 1/3 HP) 268.00 labor 1.5h; "
                "1x dual run capacitor 42.00 labor 0.3h; system recharge R-410A 3 lb 135.00. "
                "Customer Dana, card on file declined twice, wants a text link.",
    },
    "revenue-report": {
        "system": "You are the office assistant of {biz}. Given the week's jobs as JSON, write "
                  "Friday's report for the owner: revenue booked, revenue collected, unpaid "
                  "invoices with age, jobs that never got an estimate, and the one number that "
                  "moved most. Under 200 words, numbers first.",
        "user": "{{\"jobs\":[{{\"id\":1,\"type\":\"no-cool\",\"quoted\":412,\"paid\":412,\"closed\":\"mon\"}},"
                "{{\"id\":2,\"type\":\"maintenance\",\"quoted\":189,\"paid\":0,\"closed\":\"tue\"}},"
                "{{\"id\":3,\"type\":\"install\",\"quoted\":7400,\"paid\":3700,\"closed\":\"wed\"}},"
                "{{\"id\":4,\"type\":\"no-heat\",\"quoted\":0,\"paid\":0,\"closed\":\"thu\"}},"
                "{{\"id\":5,\"type\":\"water-heater\",\"quoted\":1650,\"paid\":1650,\"closed\":\"fri\"}}]}}",
    },
}


def call(system, user, max_tokens=700):
    body = {
        "model": INF["model"],
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        # GLM-5.3 thinks by default and would spend the whole budget before writing a word
        "thinking": {"type": "disabled"},
    }
    req = urllib.request.Request(
        INF["base_url"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.load(r)
    u = out.get("usage", {})
    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    return {
        "prompt_tokens": u.get("prompt_tokens", 0),
        "cached_tokens": cached,
        "completion_tokens": u.get("completion_tokens", 0),
        "text": (out.get("choices") or [{}])[0].get("message", {}).get("content", ""),
    }


def usd(prompt, cached, completion):
    fresh = max(prompt - cached, 0)
    return (fresh * INF["usd_per_m_in"] + cached * INF["usd_per_m_cached"]
            + completion * INF["usd_per_m_out"]) / 1_000_000


def main(argv):
    if not KEY:
        sys.exit("%s is not set — cost can only be measured with a real key" % INF["key_env"])
    out = {"model": INF["model"], "measured": {}, "assumptions": CFG["volumes"]}
    for name, job in JOBS.items():
        sysmsg = job["system"].format(biz=CFG["business"]["name"], book=CFG["business"]["price_book"])
        runs = []
        for i in range(3):  # run 1 pays for the cache, runs 2-3 show what a warm prompt costs
            r = call(sysmsg, job["user"])
            runs.append({"usd": round(usd(r["prompt_tokens"], r["cached_tokens"],
                                          r["completion_tokens"]), 6),
                         "prompt": r["prompt_tokens"], "cached": r["cached_tokens"],
                         "completion": r["completion_tokens"]})
            if i == 0:
                sample = r["text"]
        out["measured"][name] = {"runs": runs, "cold_usd": runs[0]["usd"],
                                 "warm_usd": round(sum(x["usd"] for x in runs[1:]) / 2, 6),
                                 "sample": sample[:400]}
    v = CFG["volumes"]
    per_month = (
        v["leads_per_day"] * 30 * out["measured"]["quote-by-text"]["warm_usd"]
        + v["invoices_per_day"] * 30 * out["measured"]["estimate-to-paid"]["warm_usd"]
        + v["reports_per_week"] * 4.3 * out["measured"]["revenue-report"]["warm_usd"]
    )
    out["per_business_month_usd"] = round(per_month, 4)
    out["at_cost_price_usd"] = round(per_month * (1 + CFG["offer"]["network_fee"]), 2)
    out["incumbent_usd_month"] = CFG["offer"]["incumbent_month"]
    out["ratio"] = round(CFG["offer"]["incumbent_month"] / out["at_cost_price_usd"], 1) if per_month else None
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "costo.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    if "--json" in argv:
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return
    print("model %s  (%.2f/M in, %.2f/M cached, %.2f/M out)" % (
        INF["model"], INF["usd_per_m_in"], INF["usd_per_m_cached"], INF["usd_per_m_out"]))
    for name, m in out["measured"].items():
        print("%-16s cold $%0.5f  warm $%0.5f  (%d in / %d cached / %d out)"
              % (name, m["cold_usd"], m["warm_usd"],
                 m["runs"][-1]["prompt"], m["runs"][-1]["cached"], m["runs"][-1]["completion"]))
    print("\nvolumes: %s" % json.dumps(v))
    print("inference cost / business / month: $%.2f" % per_month)
    print("at-cost price (cost + %.0f%% network fee): $%.2f" % (
        CFG["offer"]["network_fee"] * 100, out["at_cost_price_usd"]))
    print("incumbent: $%s/month -> %.0fx cheaper" % (out["incumbent_usd_month"], out["ratio"]))
    print("\nsample output (quote-by-text):\n%s" % out["measured"]["quote-by-text"]["sample"])


if __name__ == "__main__":
    main(sys.argv[1:])
