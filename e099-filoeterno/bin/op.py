#!/usr/bin/env python3
"""Operator snapshot: everything the human sees, now readable by the loop.

Reads (all stdlib, key from env only):
  - credits: GET {base}usage -> rolling/weekly/monthly % + resets
  - live models: GET {base}models (session header required)
  - list prices + context windows: ~/.pi/agent/models.json (provider config)
  - empirical table: data/operator.jsonl (tokens, $/call, tok/s, task scores
    per model — built by the loop itself over time; starts empty)

Writes data/operator.json. Print human summary with `op.py`.
Decisions the loop can take from this: pick free/fast models for cheap checks,
1.3 for hard builds; stop before the weekly cap; report true $/call.
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NEEDS = json.load(open(os.path.join(ROOT, "needs.json")))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

PI_MODELS = os.path.expanduser("~/.pi/agent/models.json")


def headers(key):
    return {"Authorization": f"Bearer {key}",
            NEEDS["session_header"]: NEEDS["session_id"],
            "User-Agent": NEEDS["user_agent"]}


def api_key():
    for n in NEEDS["key_envs"]:
        if os.environ.get(n):
            return os.environ[n]
    sys.exit("missing API key env")


def base():
    return os.environ.get(NEEDS["base_url_env"], "").rstrip("/") + "/"


def get(path):
    req = urllib.request.Request(base() + path.lstrip("/"), headers=headers(api_key()))
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def snapshot():
    usage = get("usage").get("usage", {})
    live = [m["id"] for m in get("models").get("data", [])]
    catalog = {}
    try:
        provs = json.load(open(PI_MODELS)).get("providers", {})
        for p in ("opencode-go", "opencode"):
            for m in provs.get(p, {}).get("models", []):
                catalog.setdefault(m["id"], {
                    "providers": [], "ctx": m.get("contextWindow"),
                    "price_in": (m.get("cost") or {}).get("input"),
                    "price_out": (m.get("cost") or {}).get("output")})
                catalog[m["id"]]["providers"].append(p)
    except OSError:
        pass
    emp = {}
    fp = os.path.join(DATA, "operator.jsonl")
    if os.path.exists(fp):
        for line in open(fp):
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            m = emp.setdefault(e.get("model", "?"),
                               {"calls": 0, "tok_in": 0, "tok_out": 0,
                                "usd": 0.0, "secs": 0.0, "scores": []})
            if e.get("tok_in", 0) + e.get("tok_out", 0) > 0 or "score" not in e:
                m["calls"] += 1  # pure score notes don't inflate call counts
            m["tok_in"] += e.get("tok_in", 0)
            m["tok_out"] += e.get("tok_out", 0)
            m["usd"] += e.get("usd", 0)
            m["secs"] += e.get("secs", 0)
            if "score" in e:
                m["scores"].append(e["score"])
    for m in emp.values():
        tot = m["tok_in"] + m["tok_out"]
        m["avg_tps"] = round(tot / m["secs"], 1) if m["secs"] else 0
        m["avg_usd_call"] = round(m["usd"] / m["calls"], 5) if m["calls"] else 0
        m["avg_score"] = round(sum(m["scores"]) / len(m["scores"]), 3) if m["scores"] else None
    snap = {
        "credits_pct": {k: v.get("percent") for k, v in usage.items()},
        "credits_resets": {k: v.get("resetsAt") for k, v in usage.items()},
        "live_models": live,
        "catalog": {mid: catalog.get(mid, {}) for mid in live},
        "configured_model": current_model(),
        "empirical": emp,
    }
    json.dump(snap, open(os.path.join(DATA, "operator.json"), "w"), indent=2)
    return snap


def current_model():
    return NEEDS.get("model") or os.environ.get(NEEDS["model_env"], "")


def record_call(model, usage, secs, score=None):
    """Called by loop.py after every model call. List-price math, labeled."""
    tin = (usage or {}).get("input_tokens", 0)
    tout = (usage or {}).get("output_tokens", 0)
    price = catalog_price(model)
    usd = tin / 1e6 * price[0] + tout / 1e6 * price[1]
    with open(os.path.join(DATA, "operator.jsonl"), "a") as f:
        f.write(json.dumps({"model": model, "tok_in": tin, "tok_out": tout,
                            "secs": round(secs, 1), "usd": round(usd, 6),
                            **({"score": score} if score is not None else {})}) + "\n")


def catalog_price(model):
    try:
        provs = json.load(open(PI_MODELS)).get("providers", {})
        for p in ("opencode-go", "opencode"):
            for m in provs.get(p, {}).get("models", []):
                if m["id"] == model:
                    c = m.get("cost") or {}
                    return (c.get("input") or 0, c.get("output") or 0)
    except OSError:
        pass
    return (0, 0)


def weekly_pct():
    try:
        return float(get("usage").get("usage", {}).get("weekly", {}).get("percent", 0))
    except Exception:
        return 0.0


if __name__ == "__main__":
    s = snapshot()
    c = s["credits_pct"]
    print(f"credits used: rolling {c.get('rolling')}% / "
          f"weekly {c.get('weekly')}% / monthly {c.get('monthly')}%")
    print(f"live models on go: {len(s['live_models'])}")
    m = s["configured_model"]
    print(f"configured: {m} | ctx {(s['catalog'].get(m) or {}).get('ctx')} | "
          f"list price in/out per 1M: {(s['catalog'].get(m) or {}).get('price_in')}/"
          f"{(s['catalog'].get(m) or {}).get('price_out')}")
    free = [k for k, v in s["catalog"].items()
            if v.get("price_in") == 0 and v.get("price_out") == 0]
    print(f"free models: {len(free)} ({', '.join(free[:8])}{'...' if len(free) > 8 else ''})")
    for mod, e in s["empirical"].items():
        print(f"empirical {mod}: {e['calls']} calls, {e['avg_tps']} tok/s, "
              f"${e['avg_usd_call']}/call, avg score {e['avg_score']}")
    if not s["empirical"]:
        print("empirical table empty — fills as the loop runs")
