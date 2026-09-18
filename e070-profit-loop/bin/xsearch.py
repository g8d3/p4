#!/usr/bin/env python3
"""X radar via twitterapis.com ($0.0008/call on user key). $0 inference.
Usage: python3 bin/xsearch.py "query" [max_results]
Prints compact JSON lines: {user, text, url, created_at}.
Key from TWITTERAPIS_API_KEY env (see ~/.secrets/.env). Never prints the key.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = "https://api.twitterapis.com/twitter/tweet/advanced_search"


def search(query, max_results=10):
    key = os.environ.get("TWITTERAPIS_API_KEY", "")
    if not key:
        print(json.dumps({"error": "TWITTERAPIS_API_KEY missing"}))
        return 1
    qs = urllib.parse.urlencode({"query": query, "max_results": max_results})
    req = urllib.request.Request(BASE + "?" + qs,
                                 headers={"Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    for t in d.get("tweets", []):
        u = (t.get("author") or {})
        print(json.dumps({
            "user": u.get("username", "?"),
            "verified": u.get("verified", False),
            "followers": u.get("followers_count", "?"),
            "text": (t.get("text") or "")[:280].replace("\n", " "),
            "url": t.get("url", ""),
            "likes": t.get("favorite_count", "?"),
            "rts": t.get("retweet_count", "?"),
            "views": t.get("view_count", "?"),
            "created_at": t.get("created_at", ""),
        }))
    return 0


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "new bug bounty program launched"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    sys.exit(search(q, n))
