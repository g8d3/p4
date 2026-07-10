"""
Explorer — Record HAR per interaction, extract auth, clean analysis.
"""
import subprocess
import json
import time
import os
import sys
import re

sys.path.insert(0, os.path.dirname(__file__))


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


def printt(msg):
    print(msg)
    sys.stdout.flush()


# ── Auth ──

def extract_token():
    token = ab_eval("""
    (async () => {
        if (window.Clerk && window.Clerk.session && window.Clerk.session.getToken) {
            const t = await window.Clerk.session.getToken();
            return t || '';
        }
        return '';
    })()
    """, timeout=10)
    return token if token and token != "" else None


def save_token(token, domain):
    secrets_dir = os.path.expanduser("~/.secrets")
    os.makedirs(secrets_dir, exist_ok=True)
    env_path = os.path.join(secrets_dir, ".env")
    key = f"BEARER_TOKEN_{domain.replace('.', '_').upper()}"
    lines = []
    if os.path.exists(env_path):
        with open(env_path) as f:
            lines = f.readlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"export {key}="):
            lines[i] = f"export {key}='{token}'\n"
            found = True
            break
    if not found:
        lines.append(f"export {key}='{token}'\n")
    with open(env_path, "w") as f:
        f.writelines(lines)
    printt(f"  Token saved: {key}")


# ── HAR parsing ──

def parse_har(har_path, filter_domain=None):
    with open(har_path) as f:
        har = json.load(f)
    entries = har.get("log", {}).get("entries", [])
    calls = []
    for e in entries:
        req = e.get("request", {})
        resp = e.get("response", {})
        url = req.get("url", "")
        method = req.get("method", "")
        status = resp.get("status", 0)
        mime = resp.get("content", {}).get("mimeType", "")
        if any(x in mime for x in ["font", "javascript", "css", "image"]):
            continue
        skip = [".js", ".css", ".woff", ".png", ".jpg", ".ico", ".webp", ".svg", ".gif"]
        if any(url.endswith(ext) or f"{ext}?" in url for ext in skip):
            continue
        if filter_domain and filter_domain not in url:
            continue
        headers = {h["name"]: h["value"] for h in req.get("headers", [])}
        body = None
        pd = req.get("postData", {})
        if pd:
            body = pd.get("text", "")[:1000]
        resp_body = resp.get("content", {}).get("text", "")[:500] if resp.get("content") else None
        calls.append({
            "method": method, "url": url, "status": status,
            "auth": bool(headers.get("Authorization")),
            "body": body, "resp_body": resp_body,
        })
    return calls


def deduplicate(calls):
    seen = set()
    unique = []
    for c in calls:
        key = f"{c['method']} {re.sub(r'[?].*', '', c['url'])}"
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def parse_nav(snapshot):
    items = []
    in_nav = False
    for line in snapshot.split("\n"):
        if 'navigation "Main"' in line:
            in_nav = True
            continue
        if in_nav:
            stripped = line.strip()
            if stripped.startswith("- main"):
                break
            if stripped and not stripped.startswith("-") and "listitem" not in stripped and "separator" not in stripped:
                break
            if "link" in line and "ref=" in line:
                ref = line.split("ref=")[1].split("]")[0]
                m = re.search(r'"([^"]+)"', line)
                text = m.group(1) if m else ""
                text = text.replace(" New", "").strip()
                if text and len(text) < 30:
                    safe = re.sub(r'[^a-z0-9]', '_', text.lower())[:20]
                    items.append({"text": text, "ref": ref, "safe_name": safe})
    return items


# ── Explorer ──

class Explorer:
    def __init__(self, port=9222):
        self.port = port

    def explore(self, url, domain=None):
        t0 = time.time()
        if not domain:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc

        out_dir = os.path.join(os.path.dirname(__file__), "output", domain.replace(".", "_"))
        os.makedirs(out_dir, exist_ok=True)

        # Token
        printt("  Extracting auth token...")
        token = extract_token()
        if token:
            save_token(token, domain)
            printt(f"  Token: {token[:30]}...\n")
        else:
            printt("  No token found\n")

        # Page load HAR
        printt("  Recording page load...")
        page_har = os.path.join(out_dir, "page_load.har")
        ab("network", "har", "start", timeout=10)
        ab("open", url, timeout=20)
        wait_stable(timeout=10)
        time.sleep(2)
        ab("network", "har", "stop", page_har, timeout=30)
        calls = parse_har(page_har, domain)
        printt(f"  Page load: {len(deduplicate(calls))} endpoints\n")

        # Nav items
        _, snap, _ = ab("snapshot", timeout=15)
        nav_items = parse_nav(snap)
        printt(f"  {len(nav_items)} nav items:\n")
        for i, item in enumerate(nav_items):
            printt(f"    {i+1:2d}. {item['text']}")

        # Click each nav, record HAR per interaction
        printt(f"\n{'─'*60}")
        printt(f"  PHASE 1: One HAR per nav item")
        printt(f"{'─'*60}\n")

        interactions = []
        for i, item in enumerate(nav_items):
            printt(f"  [{i+1}/{len(nav_items)}] {item['text']}")
            sys.stdout.flush()

            har_path = os.path.join(out_dir, f"nav_{i+1:02d}_{item['safe_name']}.har")
            ab("network", "har", "start", timeout=10)

            url_before = ab_eval("location.href", timeout=10)
            ab("click", f"@{item['ref']}", timeout=15)
            wait_stable(timeout=6)

            current_url = ab_eval("location.href", timeout=10)
            page_changed = current_url != url_before

            ab("network", "har", "stop", har_path, timeout=30)

            calls = parse_har(har_path, domain)
            unique = deduplicate(calls)

            result = {
                "nav_text": item["text"],
                "url": current_url,
                "page_changed": page_changed,
                "har_path": har_path,
                "unique_endpoints": len(unique),
                "endpoints": [{"method": c["method"], "url": c["url"], "status": c["status"], "auth": c["auth"]} for c in unique],
            }
            interactions.append(result)

            status = current_url if page_changed else "(dropdown)"
            printt(f"    -> {status} | {len(unique)} endpoints")
            if page_changed:
                ab("open", url, timeout=15)
                wait_stable(timeout=5)

        # Probe interesting pages
        interesting = [r for r in interactions if r["page_changed"] and r["unique_endpoints"] > 3]
        if interesting:
            printt(f"\n{'─'*60}")
            printt(f"  PHASE 2: Probing buttons on {len(interesting)} pages")
            printt(f"{'─'*60}\n")

            for i, page in enumerate(interesting[:5]):
                printt(f"  [{i+1}] {page['nav_text']}")
                sys.stdout.flush()

                ab("open", page["url"], timeout=15)
                wait_stable(timeout=5)

                _, snap_i, _ = ab("snapshot", "-i", timeout=10)
                refs = []
                for line in (snap_i or "").split("\n"):
                    if "ref=" in line and "button" in line.lower():
                        ref = line.split("ref=")[1].split("]")[0]
                        m = re.search(r'"([^"]+)"', line)
                        text = m.group(1) if m else ""
                        refs.append({"ref": ref, "text": text})

                for btn in refs[:4]:
                    printt(f"    -> {btn['text'][:35]}")
                    sys.stdout.flush()

                    safe = re.sub(r'[^a-z0-9]', '_', page['nav_text'].lower())[:20]
                    har_path = os.path.join(out_dir, f"probe_{safe}_{btn['text'][:15].replace(' ','_')}.har")
                    ab("network", "har", "start", timeout=10)
                    ab("click", f"@{btn['ref']}", timeout=10)
                    wait_stable(timeout=5)
                    ab("network", "har", "stop", har_path, timeout=30)

                    calls = parse_har(har_path, domain)
                    unique = deduplicate(calls)
                    new_url = ab_eval("location.href", timeout=10)

                    if unique:
                        for c in unique[:3]:
                            printt(f"       {c['method']:6s} {c['url'][:60]}")
                    if new_url != page["url"]:
                        printt(f"       -> {new_url[:50]}")
                        ab("open", page["url"], timeout=10)
                        wait_stable(timeout=3)
                printt("")

        elapsed = time.time() - t0
        all_endpoints = set()
        for r in interactions:
            for ep in r.get("endpoints", []):
                all_endpoints.add(f"{ep['method']} {re.sub(r'[?].*', '', ep['url'])}")

        printt(f"{'='*60}")
        printt(f"  DONE ({elapsed:.0f}s)")
        printt(f"  Pages: {len(interactions)} | Unique endpoints: {len(all_endpoints)}")
        printt(f"  Output: {out_dir}/")
        printt(f"{'='*60}")

        return {
            "url": url, "domain": domain, "output_dir": out_dir,
            "interactions": interactions, "all_endpoints": list(all_endpoints),
        }
