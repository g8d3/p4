#!/usr/bin/env python3
"""Print OpenCode Go usage percentages. Stdlib only.

Config comes from ../needs.json + env (see needs.json):
  base URL: $OPENCODE_GO_BASE_URL (default from needs.json)
  key:      $OPENCODE_API_KEY or $OPENCODE_GO_API_KEY
  endpoint: {base}/usage  (endpoint_path from needs.json)

Usage:
  usage.py          human: 3 lines (rolling/weekly/monthly + resets)
  usage.py --json   raw API JSON
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "needs.json")) as f:
    NEEDS = json.load(f)


def config():
    base = os.environ.get(NEEDS["base_url_env"], NEEDS["base_url_default"])
    base = base.rstrip("/") + "/"
    url = base + NEEDS["endpoint_path"].lstrip("/")
    key = ""
    for name in NEEDS["key_envs"]:
        if os.environ.get(name):
            key = os.environ[name]
            break
    return url, key


def fetch(url, key):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": "pi-agent/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=NEEDS.get("timeout_seconds", 20)) as r:
        return json.loads(r.read().decode())


def main(argv):
    url, key = config()
    if not key:
        print(
            f"missing API key: set one of {', '.join(NEEDS['key_envs'])}",
            file=sys.stderr,
        )
        return 2
    try:
        data = fetch(url, key)
    except Exception as e:  # noqa: BLE001 - surface any network/API error plainly
        print(f"request failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    if "--json" in argv:
        print(json.dumps(data, indent=2))
        return 0
    try:
        usage = data["usage"]
        for window in ("rolling", "weekly", "monthly"):
            w = usage[window]
            print(f"{window} {w['percent']}% (resets {w['resetsAt']})")
    except KeyError:
        print(json.dumps(data, indent=2))
        print("unexpected response shape (printed raw above)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
