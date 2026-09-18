#!/usr/bin/env python3
"""e070 metrics: prove the system improves or force a pivot. $0 spend, read-only.
Reads ledger + watch + trends, prints KPIs. Improvement rule: week-over-week
finds up OR cost-per-find down; else the owner logs a pivot decision.
Usage: python3 bin/metrics.py
"""
import datetime
import json
import os

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rows(path):
    try:
        return [json.loads(l) for l in open(path) if l.strip()]
    except FileNotFoundError:
        return []


def main():
    week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    ledger = rows(os.path.join(DIR, "data", "ledger.jsonl"))
    watch = rows(os.path.join(DIR, "data", "watch.jsonl"))
    trends = rows(os.path.join(DIR, "data", "trends.jsonl"))

    def recent(rs):
        out = []
        for r in rs:
            try:
                out.append(r if datetime.datetime.strptime(
                    r.get("ts", "")[:10], "%Y-%m-%d").date() >= week_ago.date() else None)
            except ValueError:
                pass
        return [r for r in out if r]

    rw, rt = recent(watch), recent(trends)
    spend = 0.0
    for r in ledger:
        spend += float(r.get("cost_usd") or 0)
        tr = r.get("triage") or {}
        spend += float(tr.get("cost_usd") or 0)
    confirmed = sum(1 for r in ledger if r.get("kind") == "CONFIRMED")
    revenue = sum(float(r.get("amount_usd") or 0) for r in ledger
                  if r.get("kind") == "CONFIRMED")
    finds = len(rw)
    kpis = {
        "finds_7d": finds,
        "trend_items_7d": sum(len(t.get("urls", [])) for t in rt),
        "inference_spend_total": round(spend, 6),
        "cost_per_find_7d": round(spend / finds, 6) if finds else None,
        "confirmed_payouts": confirmed,
        "revenue_usd": round(revenue, 2),
        "roi": round((revenue - spend) / spend, 2) if spend else None,
        "ledger_rows": len(ledger),
    }
    try:
        with open(os.path.join(DIR, "data", "metrics.jsonl")) as f:
            prev = [json.loads(l) for l in f if l.strip()]
    except FileNotFoundError:
        prev = []
    last = {k: v for k, v in prev[-1].items() if k != "ts"} if prev else None
    if last == kpis:
        print(json.dumps({"unchanged": True, **kpis}, indent=1))
        return
    with open(os.path.join(DIR, "data", "metrics.jsonl"), "a") as f:
        f.write(json.dumps({"ts": datetime.datetime.now(
            datetime.timezone.utc).strftime("%FT%TZ"), **kpis}) + "\n")
    print(json.dumps(kpis, indent=1))


if __name__ == "__main__":
    main()
