#!/usr/bin/env python3
"""e109 — the quality floor, measured instead of assumed.

The network prices a job with the cheapest model that passes the workflow's floor. Until this
file existed, "passes" was an assumption. It is now two tests, both cheap and both mechanical:

  1. **acceptance checks** — what the output must contain to be usable at all (a question that
     unlocks the price, a diagnostic fee, a balance that names booked vs collected, no markdown
     tables). Deterministic, no judge, no opinion.
  2. **pairwise judge** — the candidate against the incumbent on the same case, judged by a
     stronger model, answered "A", "B" or "TIE". A cheaper model is allowed to replace the
     incumbent only if it wins or ties at least `win_rate_min` of the cases.

A model passes a workflow if **every** acceptance check passes on every case AND it clears the
pairwise floor. Cheapest passing model wins; the feed supplies the price, so the choice moves
whenever the market moves.

  python3 evalua.py                 # run the eval (~2-4 min), write data/evals.json
  python3 evalua.py --show          # print the last result without spending tokens
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())
E = CFG["eval"]
KEY = os.environ.get(E["key_env"], "")
FEED = json.loads((ROOT / "data" / "precios.json").read_text())["models"]


def call(model, messages, max_tokens=500, temperature=0):
    # GLM/other reasoning models spend the whole budget thinking and return an empty answer unless
    # reasoning is switched off — that would score "empty" as "bad quality" and poison the eval.
    def send(extra):
        body = {"model": model, "messages": messages, "max_tokens": max_tokens,
                "temperature": temperature}
        body.update(extra)
        req = urllib.request.Request(E["base_url"].rstrip("/") + "/chat/completions",
                                     data=json.dumps(body).encode(),
                                     headers={"Authorization": "Bearer " + KEY,
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)

    try:
        out = send({"reasoning": {"enabled": False}})
    except urllib.error.HTTPError:
        out = send({})  # provider rejects the reasoning hint for this model: ask without it
    u = out.get("usage", {})
    text = (out.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    if not text.strip() and u.get("completion_tokens", 0) == max_tokens:
        return call(model, messages, max_tokens=1600, temperature=temperature)  # one retry, bigger
    return text, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)


def cost(model, tin, tout):
    m = FEED.get(model) or {}
    return ((tin * m.get("in_per_m", 0)) + (tout * m.get("out_per_m", 0))) / 1_000_000


def words(t):
    return len(t.split())


# --- acceptance checks: what the output must contain to be usable at all -------------------
def checks(workflow, text, case):
    t = text.lower()
    c = {}
    if workflow == "quote-by-text":
        c["asks_a_question"] = "?" in text
        c["names_diagnostic_fee"] = "diagnostic" in t or "89" in text
        c["gives_a_range"] = sum(ch.isdigit() for ch in text) >= 6 and ("$" in text or "-" in text)
        c["short_enough"] = words(text) <= 110
    elif workflow == "estimate-to-paid":
        c["names_payment"] = "payment" in t or "link" in t or "card" in t
        c["has_line_items"] = text.count("$") + len([w for w in text.split() if w.strip("$,.").replace(".", "").isdigit()]) >= 6
        c["no_markdown_table"] = "|" not in text
        c["has_followups"] = "follow" in t or "reminder" in t or "day" in t
    else:  # revenue-report
        c["booked_vs_collected"] = "booked" in t and "collect" in t
        c["names_the_install"] = "7400" in text.replace(",", "") or "7,400" in text
        c["names_unpaid"] = "unpaid" in t or "189" in text
        c["short_enough"] = words(text) <= 320
    return c


def judge(a, b, case, workflow):
    prompt = (
        "You are the owner of a small field-service business. Two office assistants answered the "
        "same request (%s). Which answer would you actually pay for: more accurate, more useful, "
        "no invented prices, nothing the staff must fix afterwards?\n\n"
        "REQUEST:\n%s\n\n--- A ---\n%s\n\n--- B ---\n%s\n\n"
        "Answer with exactly one of: A, B, TIE." % (workflow, case["user"], a, b))
    out, _, _ = call(E["judge"], [{"role": "user", "content": prompt}], max_tokens=8)
    out = out.strip().upper()
    return "A" if out.startswith("A") else "B" if out.startswith("B") else "TIE"


def main(argv):
    res_path = ROOT / "data" / "evals.json"
    if "--show" in argv and res_path.exists():
        print(json.dumps(json.loads(res_path.read_text()), indent=1, ensure_ascii=False))
        return
    if not KEY:
        sys.exit("%s is not set" % E["key_env"])
    gold = [json.loads(l) for l in (ROOT / E["gold"]).read_text().splitlines() if l.strip()]
    incumbent = E["incumbent"]
    # cache: the incumbent's answer and the judge's verdict per case are the same for every
    # candidate, so they are computed once (a re-run then costs only the candidates' calls)
    cache_path = ROOT / "data" / "eval_cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    cache_path.parent.mkdir(exist_ok=True)
    results = {}
    for model in E["candidates"]:
        per_wf = {}
        for case in gold:
            wf = case["workflow"]
            msgs = [{"role": "system", "content": case["system"]},
                    {"role": "user", "content": case["user"]}]
            try:
                text, tin, tout = call(model, msgs)
            except Exception as e:
                per_wf.setdefault(wf, {"cases": 0, "errors": 0, "checks": {}, "wins": 0,
                                       "ties": 0, "losses": 0, "cost": 0.0, "tokens": [0, 0]})
                per_wf[wf]["cases"] += 1
                per_wf[wf]["errors"] += 1
                continue
            c = checks(wf, text, case)
            agg = per_wf.setdefault(wf, {"cases": 0, "errors": 0, "checks": {}, "wins": 0,
                                         "ties": 0, "losses": 0, "cost": 0.0, "tokens": [0, 0]})
            agg["cases"] += 1
            agg["cost"] += cost(model, tin, tout)
            agg["tokens"][0] += tin
            agg["tokens"][1] += tout
            for k, v in c.items():
                d = agg["checks"].setdefault(k, {"pass": 0, "n": 0})
                d["n"] += 1
                d["pass"] += 1 if v else 0
            if model != incumbent:  # the pair is (candidate, incumbent) on the same case
                try:
                    ck = case["workflow"] + "|" + str(gold.index(case))
                    if ck not in cache:
                        cache[ck], _, _ = call(incumbent, msgs)
                        cache_path.write_text(json.dumps(cache, ensure_ascii=False))
                    inc_text = cache[ck]
                    ck2 = model + "|" + ck
                    v = cache.get(ck2)
                    if v is None:
                        v = judge(text, inc_text, case, wf)
                        cache[ck2] = v
                        cache_path.write_text(json.dumps(cache, ensure_ascii=False))
                    agg["wins" if v == "A" else "ties" if v == "TIE" else "losses"] += 1
                except Exception as e:
                    print("  judge error %s: %s" % (model, str(e)[:90]), flush=True)
                    agg["errors"] += 1
            print("  %-34s %-16s case %d/%d" % (model, wf, gold.index(case) + 1, len(gold)),
                  flush=True)
        results[model] = per_wf

    # decide: cheapest model whose checks all pass and whose pairwise record clears the floor
    decision, report = {}, {}
    for wf in {c["workflow"] for c in gold}:
        rows = []
        for model, per_wf in results.items():
            a = per_wf.get(wf)
            if not a or a["errors"]:
                continue
            passed = sum(d["pass"] for d in a["checks"].values())
            total = sum(d["n"] for d in a["checks"].values())
            dec = a["wins"] + a["ties"] + a["losses"]
            win_rate = ((a["wins"] + 0.5 * a["ties"]) / dec) if dec else None
            per_job = cost(model, *CFG["expected_tokens"][wf])
            rows.append({"model": model, "checks_pass": "%d/%d" % (passed, total),
                         "all_checks": passed == total,
                         "win_rate": None if win_rate is None else round(win_rate, 2),
                         "per_job_usd": round(per_job, 8),
                         # the incumbent is the baseline: it clears the floor by definition
                         "ok": passed == total and (win_rate is None
                                                    or win_rate >= E["win_rate_min"])})
        ok = sorted([r for r in rows if r["ok"]], key=lambda r: r["per_job_usd"])
        report[wf] = rows
        decision[wf] = ok[0]["model"] if ok else None
    out = {"measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "incumbent": incumbent, "gold_cases": len(gold),
           "win_rate_min": E["win_rate_min"],
           "report": report, "model_by_workflow": decision}
    res_path.parent.mkdir(exist_ok=True)
    res_path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({"measured_at": out["measured_at"], "model_by_workflow": decision},
                     indent=1))
    for wf, rows in report.items():
        print("\n%s" % wf)
        for r in rows:
            print("  %-34s checks %-8s win %-5s $%.8f  %s"
                  % (r["model"], r["checks_pass"],
                     "base" if r["win_rate"] is None else "%.2f" % r["win_rate"],
                     r["per_job_usd"], "PASS" if r["ok"] else "-"))


if __name__ == "__main__":
    main(sys.argv[1:])
