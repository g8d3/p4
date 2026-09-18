#!/usr/bin/env python3
"""e070 trend scout: always-on web radar. $0 inference (no model calls).
Runs 2 time-boxed searches, appends digest to data/trends.jsonl.
Only keeps items newer than the last digest (by URL). $0 OpenRouter spend;
uses the Tavily key (free-tier credits, ~2 searches/run).
Usage: python3 bin/trends.py  (needs TAVILY_API_KEY in env)
"""
import datetime
import json
import os
import urllib.request

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRENDS = os.path.join(DIR, "data", "trends.jsonl")
QUERIES = [
    "AI agents earning money autonomously new platform past week",
    # Demand-side radar: who PAYS for alerts/signals (buyers, not rails).
    # x402 was here; killed 2026-09-18 (rail aggregator, never a task).
    "crypto traders paying for funding rate alerts signals service",
]


def tsearch(q):
    key = os.environ.get("TAVILY_API_KEY", "")
    body = json.dumps({"api_key": key, "query": q, "max_results": 5,
                       "time_range": "week", "include_answer": True,
                       "include_answer_search_depth": "basic"}).encode()
    req = urllib.request.Request("https://api.tavily.com/search", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def known():
    try:
        urls = set()
        for l in open(TRENDS):
            try:
                urls.update(json.loads(l).get("urls", []))
            except ValueError:
                pass
        return urls
    except FileNotFoundError:
        return set()


def main():
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%FT%TZ")
    seen = known()
    digests = []
    for q in QUERIES:
        try:
            d = tsearch(q)
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"query": q, "error": type(e).__name__}), flush=True)
            continue
        urls = [r.get("url", "") for r in d.get("results", [])]
        new_urls = [u for u in urls if u and u not in seen]
        seen.update(urls)
        digests.append({"ts": ts, "who": "trend-scout", "query": q,
                        "brief": (d.get("answer") or "")[:600],
                        "urls": new_urls})
    with open(TRENDS, "a") as f:
        for dg in digests:
            f.write(json.dumps(dg) + "\n")
    print(json.dumps({"ts": ts, "digests": len(digests),
                      "new_urls": sum(len(d["urls"]) for d in digests)}), flush=True)


if __name__ == "__main__":
    main()
