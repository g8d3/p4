"""Per-plugin reload cost for a PI WEB page.

Loads a PI WEB URL in headless Chromium (cache disabled, like a hard
reload) and ranks every fetched resource by duration, attributing each
URL to its plugin id (via /pi-web-plugins/manifest.json + /api/plugins).
Also reports the heaviest API calls and total request count, so repeated
small roundtrips show up next to big single assets.

Usage:
    python3 page-load.py [URL]

Default URL is the p4 master workspace + TPS tab from the original report.
"""
import json
import sys
import time
import urllib.request

DEFAULT_URL = (
    "http://127.0.0.1:8504/?project=5252bfc1-300e-4ada-bef9-f68534964180"
    "&workspace=f93c700afa07&session=01a19d20-a5d7-730e-b898-662b7515a336"
    "&tool=tps-monitor.panel%3Atps&view=chat"
)
BASE = "http://127.0.0.1:8504"


def get_json(path):
    with urllib.request.urlopen(BASE + path, timeout=20) as r:
        return json.loads(r.read())


def build_owner_map():
    """Map URL substrings to plugin ids."""
    owners = {}
    try:
        m = get_json("/pi-web-plugins/manifest.json")
        for p in m.get("plugins", []):
            mod = p.get("module", "")
            if mod:
                owners[mod.split("?")[0]] = p["id"]
    except Exception as e:
        print(f"manifest fetch failed: {e}", file=sys.stderr)
    try:
        d = get_json("/api/plugins")
        for p in d.get("plugins", []):
            pid = p.get("id", "")
            owners[f"/{pid}/"] = pid
            owners[pid] = pid
    except Exception as e:
        print(f"plugins fetch failed: {e}", file=sys.stderr)
    return owners


def owner_of(url, owners):
    for sub, pid in owners.items():
        if sub and sub in url:
            return pid
    if "/assets/" in url:
        return "(core main.js)"
    if "/api/" in url or "/pi-web" in url:
        return "(core api)"
    return "(other)"


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    owners = build_owner_map()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--disable-gpu"])
        ctx = b.new_context()
        pg = ctx.new_page()
        # hard reload: empty cache via fresh context + cache disabled
        pg.route("**/*", lambda r: r.continue_())
        t0 = time.time()
        pg.goto(url, wait_until="load", timeout=60000)
        load_s = time.time() - t0
        pg.wait_for_timeout(8000)
        res = pg.evaluate(
            """() => performance.getEntriesByType('resource').map(r => (
                {name: r.name, dur: Math.round(r.duration), size: r.transferSize || 0}
            ))"""
        )
        b.close()

    by_plugin = {}
    api_calls = []
    for r in res:
        name = r["name"].replace("http://127.0.0.1:8504", "")
        own = owner_of(r["name"], owners)
        by_plugin.setdefault(own, {"count": 0, "ms": 0, "bytes": 0, "max": []})
        e = by_plugin[own]
        e["count"] += 1
        e["ms"] += r["dur"]
        e["bytes"] += r["size"]
        e["max"].append((r["dur"], r["size"], name[-90:]))
        if name.startswith("/api/") or "terminal.list" in name or "paired-plugin" in name:
            api_calls.append((r["dur"], r["size"], name[-110:]))

    print(f"URL: {url}")
    print(f"window.load: {load_s:.1f}s + 8s settle, {len(res)} resources total\n")
    print(f"{'plugin':28s} {'reqs':>4s} {'sum ms':>7s} {'KB':>7s}  slowest resource")
    print("-" * 100)
    for pid, e in sorted(by_plugin.items(), key=lambda kv: -kv[1]["ms"]):
        slow = sorted(e["max"], reverse=True)[0]
        print(
            f"{pid:28s} {e['count']:4d} {e['ms']:7d} {e['bytes']//1024:7d}  "
            f"{slow[0]}ms {slow[2]}"
        )
    print("\nTop 15 slowest API calls:")
    for d, s, n in sorted(api_calls, reverse=True)[:15]:
        print(f"  {d:4d}ms {s:7d}B  {n}")


if __name__ == "__main__":
    main()
