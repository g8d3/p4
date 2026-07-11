"""
form_interact.py — Interact with web forms reliably.

LESSONS LEARNED (from higgsfield.ai reverse engineering):
1. Always re-snapshot after every click — new controls appear
2. Always verify state after every action — don't assume it worked
3. Check console for JS errors after each action
4. Check network for failed requests after each action
5. If anything fails, return error clearly — don't continue silently
6. The caller decides whether to retry, fix, or abort

Usage:
    python3 form_interact.py <url>    # Interactive mode
"""

import subprocess
import json
import time
import sys
import re


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


def printt(msg):
    print(msg)
    sys.stdout.flush()


# ── Snapshot ──

def snapshot():
    """Take snapshot and return structured data."""
    _, snap, _ = ab("snapshot", "-i", timeout=15)
    elements = []
    for line in (snap or "").split("\n"):
        if "ref=" not in line:
            continue
        ref = re.search(r'ref=(e\d+)', line)
        if not ref:
            continue

        # Extract role
        role = "unknown"
        if "button" in line.lower(): role = "button"
        elif "link" in line.lower(): role = "link"
        elif "textbox" in line.lower() or "input" in line.lower(): role = "input"
        elif "switch" in line.lower(): role = "switch"
        elif "slider" in line.lower(): role = "slider"
        elif "option" in line.lower(): role = "option"
        elif "listbox" in line.lower(): role = "listbox"

        # Extract text
        m = re.search(r'"([^"]+)"', line)
        text = m.group(1) if m else ""

        # Extract states
        checked = "checked=true" in line
        expanded = "expanded=true" in line
        disabled = "disabled" in line
        selected = "selected" in line

        elements.append({
            "ref": ref.group(1),
            "role": role,
            "text": text,
            "checked": checked,
            "expanded": expanded,
            "disabled": disabled,
            "selected": selected,
            "line": line.strip(),
        })

    return elements


def print_snapshot(elements):
    """Print snapshot in readable format."""
    printt("\n--- SNAPSHOT ---")
    for e in elements:
        states = []
        if e["checked"]: states.append("CHECKED")
        if e["expanded"]: states.append("OPEN")
        if e["disabled"]: states.append("DISABLED")
        if e["selected"]: states.append("SELECTED")
        state_str = f" [{','.join(states)}]" if states else ""
        printt(f"  {e['ref']:6s} {e['role']:10s} \"{e['text']}\"{state_str}")
    printt("--- END SNAPSHOT ---\n")


# ── Verification ──

def verify_textbox(ref, expected_text):
    """Verify textbox contains expected text."""
    elements = snapshot()
    for e in elements:
        if e["ref"] == ref and e["role"] == "input":
            if expected_text[:20] in (e["text"] or ""):
                return True, f"OK: contains '{e['text'][:30]}...'"
            else:
                return False, f"FAIL: expected '{expected_text[:30]}...' but got '{e['text'][:30]}...'"
    return False, f"FAIL: element {ref} not found"


def verify_switch(ref, expected_checked):
    """Verify switch is in expected state."""
    elements = snapshot()
    for e in elements:
        if e["ref"] == ref and e["role"] == "switch":
            if e["checked"] == expected_checked:
                return True, f"OK: checked={e['checked']}"
            else:
                return False, f"FAIL: expected checked={expected_checked} but got {e['checked']}"
    return False, f"FAIL: switch {ref} not found"


def verify_no_new_errors():
    """Check console for JS errors."""
    _, out, _ = ab("console", timeout=10)
    errors = [l for l in out.split("\n") if "[error]" in l.lower()]
    if errors:
        return False, f"JS errors: {errors[-1][:100]}"
    return True, "OK"


def verify_network_ok(domain=None):
    """Check network for failed requests."""
    _, out, _ = ab("network", "requests", timeout=10)
    failures = []
    for line in out.split("\n"):
        if "[403]" in line or "[500]" in line or "[404]" in line:
            if domain and domain not in line:
                continue
            failures.append(line[:80])
    if failures:
        return False, f"Failed requests: {failures[-1]}"
    return True, "OK"


# ── Actions ──

def click(ref, label=""):
    """Click an element and verify."""
    printt(f"  -> Click {label or ref}")
    code, out, err = ab("click", f"@{ref}", timeout=15)
    time.sleep(1.5)

    if code != 0:
        return False, f"Click failed: {err[:100]}"

    # Re-snapshot to see what changed
    elements = snapshot()
    return True, f"OK: {len(elements)} elements visible"


def fill(ref, text, label=""):
    """Fill textbox and verify."""
    printt(f"  -> Fill {label or ref}: '{text[:30]}...'")

    # Click first
    ab("click", f"@{ref}", timeout=10)
    time.sleep(0.5)

    # Select all and type
    ab("press", "Control+a", timeout=5)
    ab("keyboard", "type", text, timeout=10)
    time.sleep(0.5)

    # Verify
    ok, msg = verify_textbox(ref, text)
    if not ok:
        return False, msg

    return True, "OK"


def select_option(listbox_ref, option_text):
    """Click a listbox to open it, then select an option."""
    printt(f"  -> Select '{option_text}' from listbox {listbox_ref}")

    # Click to open
    ab("click", f"@{listbox_ref}", timeout=10)
    time.sleep(1)

    # Snapshot to find option
    elements = snapshot()
    for e in elements:
        if e["role"] == "option" and option_text in e["text"]:
            ab("click", f"@{e['ref']}", timeout=10)
            time.sleep(1)
            return True, f"OK: selected '{option_text}'"

    return False, f"FAIL: option '{option_text}' not found"


# ── Main interaction loop ──

def interact(url):
    """Interact with a form page."""
    printt(f"\n  Navigating to {url}...")
    ab("open", url, timeout=20)
    time.sleep(3)

    elements = snapshot()
    print_snapshot(elements)

    printt("Commands: click <ref>, fill <ref> <text>, select <ref> <text>, snapshot, verify, errors, network, quit")
    printt("")

    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            continue

        parts = cmd.split(maxsplit=2)
        action = parts[0].lower()

        if action == "quit" or action == "q":
            break

        elif action == "snapshot":
            elements = snapshot()
            print_snapshot(elements)

        elif action == "click" and len(parts) >= 2:
            ref = parts[1]
            label = ""
            for e in elements:
                if e["ref"] == ref:
                    label = e["text"]
                    break
            ok, msg = click(ref, label)
            printt(f"  Result: {msg}")
            if not ok:
                printt("  ERROR: Action failed. Returning control.")
                continue
            elements = snapshot()
            print_snapshot(elements)

        elif action == "fill" and len(parts) >= 3:
            ref = parts[1]
            text = parts[2]
            ok, msg = fill(ref, text)
            printt(f"  Result: {msg}")
            if not ok:
                printt("  ERROR: Fill failed. Returning control.")

        elif action == "select" and len(parts) >= 3:
            ref = parts[1]
            text = parts[2]
            ok, msg = select_option(ref, text)
            printt(f"  Result: {msg}")
            if not ok:
                printt("  ERROR: Select failed. Returning control.")
            elements = snapshot()
            print_snapshot(elements)

        elif action == "errors":
            ok, msg = verify_no_new_errors()
            printt(f"  Console: {msg}")

        elif action == "network":
            ok, msg = verify_network_ok()
            printt(f"  Network: {msg}")

        elif action == "verify":
            printt("  What to verify? (text/switch/errors/network)")

        else:
            printt(f"  Unknown: {cmd}")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://higgsfield.ai/ai/image?model=seedream_v4_5"
    interact(url)
