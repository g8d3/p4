#!/usr/bin/env python3
"""Test: record HAR, navigate, save, analyze offline."""
import subprocess, json, time, sys

def ab(*args, timeout=30):
    cmd = ["agent-browser", "--auto-connect"] + [str(a) for a in args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"

def ab_eval(js, timeout=10):
    _, out, _ = ab("eval", js, timeout=timeout)
    if out.startswith('"') and out.endswith('"'):
        out = out[1:-1]
    return out

def wait_stable(timeout=6):
    js = """new Promise(r => {
        let t;
        const o = new MutationObserver(() => { clearTimeout(t); t = setTimeout(() => { o.disconnect(); r('ok'); }, 600); });
        o.observe(document.body, {childList:true, subtree:true, attributes:true});
        t = setTimeout(() => { o.disconnect(); r('ok'); }, %d);
    })""" % (timeout * 1000)
    ab("eval", js, timeout=timeout + 2)

# ── Record HAR ──
print("1. Start HAR recording...")
ab("network", "har", "start", timeout=10)

print("2. Navigate to page...")
ab("open", "https://higgsfield.ai/ai/image?model=nano-banana-pro", timeout=20)
wait_stable(timeout=10)
time.sleep(2)

print("3. Stop HAR and save...")
code, out, err = ab("network", "har", "stop", "/tmp/re_har_test.har", timeout=15)
print(f"   HAR saved: {out}")

# ── Analyze HAR offline ──
print("\n4. Analyzing HAR file...\n")

with open("/tmp/re_har_test.har") as f:
    har = json.load(f)

entries = har.get("log", {}).get("entries", [])
print(f"Total entries: {len(entries)}\n")

# Filter API calls (skip static assets)
api_calls = []
for e in entries:
    url = e.get("request", {}).get("url", "")
    method = e.get("request", {}).get("method", "")
    mime = e.get("response", {}).get("content", {}).get("mimeType", "")
    status = e.get("response", {}).get("status", 0)

    # Skip static assets
    if any(x in mime for x in ["font", "javascript", "css", "image"]):
        continue
    if any(x in url for x in [".js", ".css", ".woff", ".png", ".jpg", ".ico", ".webp"]):
        continue

    api_calls.append({
        "method": method,
        "url": url[:100],
        "status": status,
        "mime": mime,
    })

print(f"API calls (excluding static): {len(api_calls)}\n")
for c in api_calls:
    print(f"  {c['method']:6s} [{c['status']}] {c['url']}")
