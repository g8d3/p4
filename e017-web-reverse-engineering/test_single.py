#!/usr/bin/env python3
"""Test: navigate to one page, wait stable, capture API calls."""
import subprocess, json, time, re, sys

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

def get_api(filter_domain=None):
    _, out, _ = ab("network", "requests", timeout=15)
    reqs = []
    for line in (out or "").split("\n"):
        m = re.match(r'\[[\w]+\]\s+(GET|POST|PUT|DELETE|PATCH|OPTIONS)\s+(\S+)\s+\((\w+)\)\s*(\d+)?', line)
        if m:
            method, url, rtype, status = m.groups()
            if filter_domain and filter_domain not in url:
                continue
            if rtype in ("Font","Stylesheet","Script","Image","Manifest"):
                continue
            reqs.append({"method":method, "url":url, "type":rtype, "status":int(status) if status else None})
    # debug: show raw lines that didn't match
    unmatched = [l for l in (out or "").split("\n") if l.strip() and not re.match(r'\[[\w]+\]\s+(GET|POST|PUT|DELETE|PATCH|OPTIONS)', l)]
    if unmatched:
        print(f"  [debug] {len(unmatched)} lines didn't match regex")
        for l in unmatched[:3]:
            print(f"    {l[:100]}")
    return reqs

# ── Test 1: Navigate + detect APIs ──
print("TEST 1: Navigate to page and capture APIs\n")

ab("open", "https://higgsfield.ai/ai/image?model=nano-banana-pro", timeout=20)
wait_stable(timeout=10)
time.sleep(2)  # extra settle time

print("Page loaded. Capturing APIs...")
apis = get_api("higgsfield.ai")
print(f"  Found {len(apis)} API calls:\n")
for a in apis:
    print(f"  {a['method']:6s} {a['url'][:80]}")

# ── Test 2: Click a nav item + wait stable + capture ──
print("\n\nTEST 2: Click 'Video' nav, wait stable, capture APIs\n")

ab("network", "requests", "--clear", timeout=10)
_, snap, _ = ab("snapshot", "-i", timeout=10)

# Find Video link
video_ref = None
for line in snap.split("\n"):
    if 'link "Video"' in line and "ref=" in line:
        video_ref = line.split("ref=")[1].split("]")[0]
        break

if video_ref:
    print(f"  Clicking ref={video_ref}...")
    ab("click", f"@{video_ref}", timeout=15)
    wait_stable(timeout=6)
    
    url = ab_eval("location.href", timeout=10)
    print(f"  URL: {url}")
    
    apis = get_api("higgsfield.ai")
    print(f"  APIs: {len(apis)}")
    for a in apis:
        print(f"    {a['method']:6s} {a['url'][:70]}")
else:
    print("  Video ref not found")

# ── Test 3: Screenshot ──
print("\n\nTEST 3: Screenshot\n")
import os
os.makedirs("/tmp/re_screenshots", exist_ok=True)
code, out, err = ab("screenshot", "/tmp/re_screenshots/test.png", timeout=30)
print(f"  Exit: {code}, file exists: {os.path.exists('/tmp/re_screenshots/test.png')}")

print("\nDONE")
