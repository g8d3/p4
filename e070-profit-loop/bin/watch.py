#!/usr/bin/env python3
"""e070 watcher v0: find just-opened bounties/contests. $0 inference (no model calls).
Sources: Tavily time-boxed search over bounty venues. Diffs against data/watch.jsonl,
appends only NEW items. Output: new finds printed + appended.
Usage: python3 bin/watch.py  (needs TAVILY_API_KEY in env)
"""
import datetime
import json
import os
import sys
import urllib.request

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCH = os.path.join(DIR, "data", "watch.jsonl")
QUERIES = [
    "new bug bounty program launched web3 past week",
    "new Code4rena Cantina audit contest started",
    "new crypto bounty issue opened github reward",
]


def tsearch(q):
    key = os.environ.get("TAVILY_API_KEY", "")
    if not key:
        return {"error": "TAVILY_API_KEY missing"}
    body = json.dumps({"api_key": key, "query": q, "max_results": 5,
                       "time_range": "week", "include_answer": False}).encode()
    req = urllib.request.Request("https://api.tavily.com/search", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def known():
    try:
        return {json.loads(l).get("url") for l in open(WATCH) if l.strip()}
    except FileNotFoundError:
        return set()


def main():
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%FT%TZ")
    seen = known()
    fresh = []
    for q in QUERIES:
        try:
            d = tsearch(q)
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"query": q, "error": type(e).__name__}), flush=True)
            continue
        for r in d.get("results", []):
            url = r.get("url", "")
            if url and url not in seen:
                row = {"ts": ts, "who": "watcher", "query": q,
                       "title": (r.get("title") or "")[:160],
                       "url": url, "score_hint": round(r.get("score", 0), 3)}
                fresh.append(row)
                seen.add(url)
    if fresh:
        with open(WATCH, "a") as f:
            for row in fresh:
                f.write(json.dumps(row) + "\n")
    print(json.dumps({"ts": ts, "fresh": len(fresh),
                      "items": fresh[:10]}), flush=True)


if __name__ == "__main__":
    sys.exit(main())
