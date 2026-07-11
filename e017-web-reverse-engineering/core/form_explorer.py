"""
form_explorer.py — Form/options extractor for websites.

WHAT IT DOES:
- Navigates to a URL
- Finds all buttons, inputs, toggles, tabs
- Clicks each button to see if it opens a dropdown
- Captures options if they appear
- Records URL changes

WHAT IT DOESN'T DO (LIMITATIONS):
- Does NOT detect custom React/Vue dropdowns (they don't use standard <option> tags)
- Does NOT detect modals/dialogs that open on click
- Does NOT detect elements inside iframes
- Does NOT handle pagination or infinite scroll
- Does NOT handle authentication walls
- Only explores buttons, not all clickable elements (links, icons, etc.)

HOW IT ACTUALLY WORKS (tested on higgsfield.ai):
The model selector is NOT a <select> with <option> tags. It's a button
("Nano Banana Pro") that, when clicked, opens a panel with other buttons.
agent-browser snapshot shows all elements in the panel once it's open.

So the approach is: click → snapshot → read everything that appeared.

This is how I found 27 models on higgsfield:
1. Click "Nano Banana Pro" button
2. Panel opens with all models as buttons
3. Snapshot shows: "Higgsfield Soul 2.0", "GPT Image 2 NEW", etc.
4. Each button has badges (NEW, UNLIMITED, TOP) in its text

TO IMPROVE:
- Compare snapshot BEFORE and AFTER click (DOM diff)
- Any new elements = dropdown/modal opened
- This would detect ANY type of UI pattern, not just standard HTML
"""

import subprocess
import json
import time
import re
import sys
import os


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


def wait_stable(timeout=5):
    js = """new Promise(r => {
        let t;
        const o = new MutationObserver(() => { clearTimeout(t); t = setTimeout(() => { o.disconnect(); r('ok'); }, 500); });
        o.observe(document.body, {childList:true, subtree:true});
        t = setTimeout(() => { o.disconnect(); r('ok'); }, %d);
    })""" % (timeout * 1000)
    ab("eval", js, timeout=timeout + 2)


def printt(msg):
    print(msg)
    sys.stdout.flush()


def get_snap():
    _, snap, _ = ab("snapshot", "-i", timeout=15)
    return snap or ""


def extract_refs(snap):
    """Extract all refs with their type and text."""
    elements = []
    for line in snap.split("\n"):
        if "ref=" not in line:
            continue
        ref_match = re.search(r'ref=(e\d+)', line)
        if not ref_match:
            continue
        ref = ref_match.group(1)

        # Detect type
        elem_type = "unknown"
        lower = line.lower()
        if "button" in lower:
            elem_type = "button"
        elif "link" in lower:
            elem_type = "link"
        elif "textbox" in lower or "input" in lower:
            elem_type = "input"
        elif "combobox" in lower or "listbox" in lower:
            elem_type = "dropdown"
        elif "switch" in lower or "checkbox" in lower:
            elem_type = "toggle"
        elif "option" in lower:
            elem_type = "option"
        elif "tab" in lower:
            elem_type = "tab"
        elif "slider" in lower:
            elem_type = "slider"

        # Extract text
        m = re.search(r'"([^"]+)"', line)
        text = m.group(1) if m else ""

        # Check badges
        badges = []
        if "new" in lower:
            badges.append("NEW")
        if "unlimited" in lower:
            badges.append("UNLIMITED")
        if "top" in lower:
            badges.append("TOP")
        if "premium" in lower:
            badges.append("PREMIUM")

        # Check selected
        selected = "selected" in lower or "checked" in lower

        elements.append({
            "ref": ref,
            "type": elem_type,
            "text": text,
            "badges": badges,
            "selected": selected,
            "line": line.strip(),
        })

    return elements


def is_nav_element(text):
    """Check if element is navigation/header (skip these)."""
    nav_texts = {
        "Higgsfield", "Explore", "Image", "Video", "Audio",
        "Supercomputer", "MCP & CLI", "Cinema Studio", "Plugins",
        "Marketing Studio", "Shorts Studio", "Explainer", "Originals",
        "Canvas", "AI Influencer", "Apps", "Upgrade", "Assets",
        "Search Higgsfield", "Notifications", "Account menu",
        "Buy credits", "Chats",
    }
    return text in nav_texts or text.startswith("Folder")


class FormExplorer:
    def __init__(self, port=9222):
        self.port = port

    def explore(self, url, max_buttons=20):
        t0 = time.time()

        # Navigate
        printt(f"  Navigating to {url}...")
        ab("open", url, timeout=20)
        wait_stable(timeout=8)

        title = ab_eval("document.title", timeout=5)
        final_url = ab_eval("location.href", timeout=5)
        printt(f"  Title: {title}")
        printt(f"  URL: {final_url}\n")

        # Get all elements
        snap = get_snap()
        elements = extract_refs(snap)

        # Separate by type
        buttons = [e for e in elements if e["type"] == "button" and not is_nav_element(e["text"])]
        inputs = [e for e in elements if e["type"] == "input"]
        dropdowns = [e for e in elements if e["type"] == "dropdown"]
        toggles = [e for e in elements if e["type"] == "toggle"]
        tabs = [e for e in elements if e["type"] == "tab"]

        printt(f"  Elements: {len(buttons)} buttons, {len(inputs)} inputs, {len(dropdowns)} dropdowns, {len(toggles)} toggles, {len(tabs)} tabs\n")

        # Explore buttons (limited)
        results = []
        for i, btn in enumerate(buttons[:max_buttons]):
            printt(f"  [{i+1}/{min(len(buttons), max_buttons)}] {btn['text']}")
            sys.stdout.flush()

            url_before = ab_eval("location.href", timeout=5)

            # Click button
            ab("click", f"@{btn['ref']}", timeout=10)
            time.sleep(1.5)

            # Capture new state
            snap_after = get_snap()
            elements_after = extract_refs(snap_after)
            url_after = ab_eval("location.href", timeout=5)

            # Find new options that appeared
            new_options = [e for e in elements_after if e["type"] == "option"]
            new_modals = [e for e in elements_after if e["type"] == "button" and e["ref"] not in [b["ref"] for b in buttons]]

            entry = {
                "button": btn["text"],
                "ref": btn["ref"],
                "url_changed": url_after != url_before,
                "new_options": len(new_options),
                "options": [{"text": o["text"], "badges": o["badges"], "selected": o["selected"]} for o in new_options[:30]],
            }

            if new_options:
                printt(f"    -> {len(new_options)} options found")
                for opt in new_options[:10]:
                    badge_str = f" [{','.join(opt['badges'])}]" if opt["badges"] else ""
                    sel = " (selected)" if opt["selected"] else ""
                    printt(f"       {opt['text']}{badge_str}{sel}")
                if len(new_options) > 10:
                    printt(f"       ... +{len(new_options)-10} more")
            elif url_after != url_before:
                printt(f"    -> Navigated: {url_after[:60]}")
                entry["url"] = url_after
                # Go back
                ab("open", url, timeout=15)
                wait_stable(timeout=5)
            else:
                printt(f"    -> No dropdown (action button)")

            results.append(entry)
            printt("")

            # Reset if navigated
            if url_after != url_before and url_after != url:
                ab("open", url, timeout=15)
                wait_stable(timeout=5)

        elapsed = time.time() - t0

        # Summary
        with_options = [r for r in results if r["new_options"] > 0]
        with_nav = [r for r in results if r["url_changed"]]

        printt(f"{'='*60}")
        printt(f"  SUMMARY ({elapsed:.0f}s)")
        printt(f"{'='*60}")
        printt(f"  Buttons explored: {len(results)}")
        printt(f"  With dropdown options: {len(with_options)}")
        printt(f"  That navigate: {len(with_nav)}")
        printt(f"  Action buttons: {len(results) - len(with_options) - len(with_nav)}")
        printt(f"{'='*60}")

        return {
            "url": url,
            "title": title,
            "final_url": final_url,
            "elements": {
                "buttons": len(buttons),
                "inputs": len(inputs),
                "dropdowns": len(dropdowns),
                "toggles": len(toggles),
                "tabs": len(tabs),
            },
            "exploration": results,
        }


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    max_btns = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    explorer = FormExplorer()
    results = explorer.explore(url, max_buttons=max_btns)

    # Save
    domain = url.replace("https://", "").replace("http://", "").split("/")[0].replace(".", "_")
    out_path = f"/tmp/form_explorer_{domain}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved: {out_path}")
