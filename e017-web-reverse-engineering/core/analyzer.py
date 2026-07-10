"""
Analyzer — DOM structure, network traffic, interaction probing, and screenshots.

This is the core engine. It:
1. Injects JS to intercept all network calls (fetch, XHR, websocket)
2. Analyzes DOM structure (frameworks, components, patterns)
3. Captures screenshots (full page + annotated with element labels)
4. Probes every interactive element and records what happens
"""

import subprocess
import json
import re
import time
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def ab(*args, timeout=30):
    """Run agent-browser command."""
    cmd = ["agent-browser", "--auto-connect"]
    for arg in args:
        cmd.append(str(arg))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def ab_eval(js, timeout=15):
    """Run JavaScript via agent-browser eval and return result."""
    _, out, _ = ab("eval", js, timeout=timeout)
    if out.startswith('"') and out.endswith('"'):
        out = out[1:-1]
    return out


def find_ref(snapshot, pattern):
    """Find ref matching pattern in snapshot text."""
    for line in snapshot.split("\n"):
        if pattern in line and "ref=" in line:
            ref = line.split("ref=")[1].split("]")[0]
            return ref
    return None


def find_all_refs(snapshot, pattern=""):
    """Find all refs in snapshot, optionally filtering by pattern."""
    refs = []
    for line in snapshot.split("\n"):
        if "ref=" in line:
            if not pattern or pattern in line:
                ref = line.split("ref=")[1].split("]")[0]
                # Also extract the element type and text
                refs.append({
                    "ref": ref,
                    "line": line.strip(),
                })
    return refs


# ─────────────────────────────────────────────────────────────
# PHASE 1: Network Interception
# ─────────────────────────────────────────────────────────────

NETWORK_INTERCEPT_JS = """
(() => {
    if (window.__re_network_intercepted) return 'already_installed';
    window.__re_network_intercepted = true;
    window.__re_network_calls = [];

    // Intercept fetch
    const origFetch = window.fetch;
    window.fetch = function(...args) {
        const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
        const method = args[1]?.method || 'GET';
        const body = args[1]?.body || null;

        const entry = {
            type: 'fetch',
            method: method,
            url: url,
            body: typeof body === 'string' ? body : (body ? JSON.stringify(body) : null),
            timestamp: Date.now(),
            response_status: null,
            response_body: null,
        };
        window.__re_network_calls.push(entry);

        return origFetch.apply(this, args).then(resp => {
            entry.response_status = resp.status;
            const clone = resp.clone();
            clone.text().then(t => {
                entry.response_body = t.substring(0, 2000);
            }).catch(() => {});
            return resp;
        });
    };

    // Intercept XMLHttpRequest
    const origOpen = XMLHttpRequest.prototype.open;
    const origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url) {
        this.__re_entry = {
            type: 'xhr',
            method: method,
            url: url,
            timestamp: Date.now(),
            response_status: null,
            response_body: null,
        };
        window.__re_network_calls.push(this.__re_entry);
        return origOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function(body) {
        if (this.__re_entry) {
            this.__re_entry.body = typeof body === 'string' ? body : null;
        }
        this.addEventListener('load', function() {
            if (this.__re_entry) {
                this.__re_entry.response_status = this.status;
                this.__re_entry.response_body = (this.responseText || '').substring(0, 2000);
            }
        });
        return origSend.apply(this, arguments);
    };

    // Intercept WebSocket
    const OrigWS = window.WebSocket;
    window.WebSocket = function(url, protocols) {
        const ws = new OrigWS(url, protocols);
        window.__re_network_calls.push({
            type: 'websocket',
            method: 'CONNECT',
            url: url,
            timestamp: Date.now(),
        });
        return ws;
    };

    return 'installed';
})()
"""


def install_network_intercept():
    """Inject JS to intercept all network calls."""
    print("[analyzer] Installing network intercept...")
    result = ab_eval(NETWORK_INTERCEPT_JS, timeout=10)
    return result == "installed" or result == "already_installed"


def get_network_calls():
    """Retrieve all intercepted network calls."""
    raw = ab_eval("JSON.stringify(window.__re_network_calls || [])", timeout=10)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []


# ─────────────────────────────────────────────────────────────
# PHASE 2: DOM Analysis (via agent-browser snapshot)
# ─────────────────────────────────────────────────────────────

def analyze_dom():
    """Analyze DOM using agent-browser snapshot — no custom JS needed."""
    print("[analyzer] Analyzing DOM via snapshot...")

    # Full snapshot — structure of all elements
    _, snap_full, _ = ab("snapshot", timeout=15)

    # Interactive snapshot — buttons, links, inputs only
    _, snap_interactive, _ = ab("snapshot", "-i", timeout=10)

    # Quick metadata via simple eval
    title = ab_eval("document.title", timeout=5)
    url = ab_eval("location.href", timeout=5)

    # Count elements via tiny eval calls
    buttons = ab_eval("document.querySelectorAll('button, [role=\"button\"]').length", timeout=5)
    links = ab_eval("document.querySelectorAll('a[href]').length", timeout=5)
    forms = ab_eval("document.querySelectorAll('form').length", timeout=5)
    inputs = ab_eval("document.querySelectorAll('input, textarea, select').length", timeout=5)
    images = ab_eval("document.querySelectorAll('img').length", timeout=5)

    return {
        "title": title,
        "url": url,
        "element_counts": {
            "buttons": int(buttons) if buttons.isdigit() else 0,
            "links": int(links) if links.isdigit() else 0,
            "forms": int(forms) if forms.isdigit() else 0,
            "inputs": int(inputs) if inputs.isdigit() else 0,
            "images": int(images) if images.isdigit() else 0,
        },
        "snapshot_full": snap_full,
        "snapshot_interactive": snap_interactive,
    }


# ─────────────────────────────────────────────────────────────
# PHASE 3: Interaction Probing
# ─────────────────────────────────────────────────────────────

def get_interactive_elements():
    """Get all interactive elements via snapshot."""
    _, snap, _ = ab("snapshot", "-i", timeout=15)
    refs = find_all_refs(snap)
    return refs, snap


def probe_element(ref: str, element_type: str, timeout: int = 10) -> dict:
    """Probe a single element: hover, then click, record network calls before/after."""
    result = {"ref": ref, "type": element_type, "actions": []}

    # Count network calls before
    before_count = len(get_network_calls())

    # Try hover first
    try:
        ab("hover", f"@{ref}", timeout=5)
        time.sleep(0.5)
        result["actions"].append("hover")
    except Exception:
        pass

    # Take snapshot after hover to see any new elements
    _, snap_after_hover, _ = ab("snapshot", "-i", timeout=5)
    new_after_hover = len(get_network_calls())
    if new_after_hover > before_count:
        result["hover_triggered_requests"] = True

    # Try click
    try:
        ab("click", f"@{ref}", timeout=timeout)
        time.sleep(1)
        result["actions"].append("click")
    except Exception as e:
        result["click_error"] = str(e)
        return result

    # Check what happened
    time.sleep(1)
    after_count = len(get_network_calls())
    result["requests_after_click"] = after_count - before_count

    # Check URL change
    current_url = ab_eval("window.location.href", timeout=5)
    result["url_after_click"] = current_url

    # Check for new modals/popups
    _, snap_after_click, _ = ab("snapshot", "-i", timeout=5)
    if "dialog" in snap_after_click.lower() or "modal" in snap_after_click.lower():
        result["opened_modal"] = True

    # Check for navigation
    if result.get("url_after_click") != ab_eval("window.location.href", timeout=5):
        result["navigated"] = True

    return result


def probe_all_interactions(max_elements: int = 50) -> list[dict]:
    """Probe all interactive elements on the page."""
    print("[analyzer] Probing interactive elements...")
    refs, snapshot = get_interactive_elements()
    print(f"[analyzer] Found {len(refs)} interactive elements")

    results = []
    for i, elem in enumerate(refs[:max_elements]):
        ref = elem["ref"]
        line = elem["line"]

        # Detect element type from snapshot line
        elem_type = "unknown"
        if "button" in line.lower():
            elem_type = "button"
        elif "link" in line.lower() or "href" in line.lower():
            elem_type = "link"
        elif "textbox" in line.lower() or "input" in line.lower():
            elem_type = "input"
        elif "checkbox" in line.lower():
            elem_type = "checkbox"
        elif "combobox" in line.lower() or "dropdown" in line.lower():
            elem_type = "dropdown"
        elif "tab" in line.lower():
            elem_type = "tab"

        # Skip non-actionable elements
        if elem_type in ("input", "checkbox", "dropdown"):
            continue

        print(f"  [{i+1}/{min(len(refs), max_elements)}] Probing {elem_type} ref={ref}")
        result = probe_element(ref, elem_type)
        result["snapshot_line"] = line
        results.append(result)

        # Go back if navigated
        if result.get("navigated"):
            ab("open", ab_eval("window.history.back()", timeout=5), timeout=10)
            time.sleep(1)

    return results


# ─────────────────────────────────────────────────────────────
# PHASE 4: Screenshots
# ─────────────────────────────────────────────────────────────

SCREENSHOT_DIR = "/tmp/re_screenshots"


def ensure_screenshot_dir():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def capture_screenshot(name: str = "page") -> str:
    """Capture screenshot via agent-browser, return file path."""
    ensure_screenshot_dir()
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    ab("screenshot", path, timeout=15)
    if os.path.exists(path):
        size_kb = os.path.getsize(path) / 1024
        print(f"[screenshot] Saved: {path} ({size_kb:.0f} KB)")
        return path
    # Fallback: try without path
    ab("screenshot", "--full", timeout=15)
    print(f"[screenshot] Captured (default location)")
    return ""


def capture_annotated_screenshot(name: str = "page_annotated") -> str:
    """Capture annotated screenshot showing element refs."""
    ensure_screenshot_dir()
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    ab("screenshot", "--annotate", path, timeout=15)
    if os.path.exists(path):
        size_kb = os.path.getsize(path) / 1024
        print(f"[screenshot] Annotated: {path} ({size_kb:.0f} KB)")
        return path
    return ""


def capture_full_page_screenshot(name: str = "page_full") -> str:
    """Capture full-page (scrollable) screenshot."""
    ensure_screenshot_dir()
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    ab("screenshot", "--full", path, timeout=20)
    if os.path.exists(path):
        size_kb = os.path.getsize(path) / 1024
        print(f"[screenshot] Full page: {path} ({size_kb:.0f} KB)")
        return path
    return ""


# ─────────────────────────────────────────────────────────────
# PHASE 5: Full Analysis
# ─────────────────────────────────────────────────────────────

def analyze_page(url: str, probe_interactions: bool = True) -> dict:
    """Run full analysis on a page.

    Returns dict with all findings including screenshot paths.
    """
    print(f"\n{'='*60}")
    print(f"[analyzer] Analyzing: {url}")
    print(f"{'='*60}")

    # Navigate
    ab("open", url, timeout=20)
    time.sleep(3)
    ab("set", "viewport", "1280", "800")
    time.sleep(1)

    # Capture initial screenshots (before DOM manipulation)
    print("\n[analyzer] Capturing screenshots...")
    screenshot_main = capture_screenshot("main")
    screenshot_annotated = capture_annotated_screenshot("annotated")
    screenshot_full = capture_full_page_screenshot("full")

    # Phase 1: Install network intercept
    install_network_intercept()
    time.sleep(1)

    # Phase 2: DOM analysis
    dom = analyze_dom()

    # Phase 3: Probe interactions
    interactions = []
    if probe_interactions:
        interactions = probe_all_interactions(max_elements=40)

    # Collect final network calls
    network_calls = get_network_calls()

    return {
        "url": url,
        "dom": dom,
        "network_calls": network_calls,
        "interactions": interactions,
        "screenshots": {
            "main": screenshot_main,
            "annotated": screenshot_annotated,
            "full": screenshot_full,
        },
    }


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    result = analyze_page(url)
    print(json.dumps(result, indent=2, default=str)[:5000])
