#!/usr/bin/env python3
"""Credit watcher. Prints balance JSON. Exit 2 if below floor (loop gate).

Usage: python3 bin/credits.py [--floor 0.80]
Reads OPENROUTER_API_KEY from env. Never prints the key.
"""
import json
import os
import sys
import urllib.request

URL = os.environ.get("OPENROUTER_CREDITS_URL",
                "https://openrouter.ai/api/v1/credits")


def main():
    floor = float(sys.argv[sys.argv.index("--floor") + 1]
                  if "--floor" in sys.argv else 0.80)
    key = os.environ.get("OPENROUTER_API_KEY", "")
    req = urllib.request.Request(URL, headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())["data"]
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(e)[:200]}))
        return 1
    total, used = d["total_credits"], d["total_usage"]
    remaining = total - used
    print(json.dumps({"ok": True, "total": total, "used": round(used, 6),
                      "remaining": round(remaining, 6), "floor": floor,
                      "below_floor": remaining < floor}))
    return 2 if remaining < floor else 0


if __name__ == "__main__":
    sys.exit(main())
