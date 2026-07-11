#!/usr/bin/env python3
"""
form_snapshot.py — Snapshot that maps UI controls to API parameters.

Captures a HAR to see the real request, then shows each UI control
with its corresponding server parameter name and value.

Usage:
    python3 form_snapshot.py              # snapshot current page
    python3 form_snapshot.py --capture    # also capture a request to map params
"""

import subprocess
import json
import sys
import os
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


FORM_TREE_JS = """
(function() {
    var form = document.querySelector('form');
    if (!form) return JSON.stringify({error: 'no form'});

    var fieldset = form.querySelector('fieldset');
    var model = fieldset ? fieldset.getAttribute('data-model') : null;

    var controls = [];
    var all = form.querySelectorAll('button, input, select, textarea');
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        var rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue;

        var role = el.getAttribute('role') || el.tagName.toLowerCase();
        var text = el.textContent.trim().substring(0, 40);
        var aria = el.getAttribute('aria-label') || '';
        var name = el.name || el.id || '';
        var value = el.value || '';
        var checked = el.getAttribute('aria-checked');
        var expanded = el.getAttribute('aria-expanded');

        var label = text || aria || name || el.tagName.toLowerCase();

        controls.push({
            role: role,
            label: label,
            name: name,
            value: value,
            checked: checked,
            expanded: expanded
        });
    }

    return JSON.stringify({model: model, controls: controls});
})()
"""


def get_form_tree():
    """Get form structure with all controls."""
    raw = ab_eval(FORM_TREE_JS, timeout=10)
    try:
        return json.loads(raw)
    except:
        return {"error": "parse failed", "raw": raw}


def map_params_to_controls(controls, request_body):
    """Map UI controls to API parameters based on request body."""
    params = request_body.get("params", {})
    mapping = {}

    for ctrl in controls:
        label = ctrl["label"]
        role = ctrl["role"]
        name = ctrl["name"]

        # Try to match by name
        if name and name in params:
            mapping[ctrl["label"]] = {"param": name, "value": params[name]}
            continue

        # Try to match by label/text
        label_lower = label.lower()
        for key, val in params.items():
            if key in label_lower or label_lower in str(val).lower():
                mapping[label] = {"param": key, "value": val}
                break

        # Match specific patterns
        if re.match(r'^\d+:\d+$', label):
            mapping[label] = {"param": "aspect_ratio", "value": label}
        elif re.match(r'^\d+K$', label):
            mapping[label] = {"param": "resolution", "value": label}
        elif re.match(r'^\d+/\d+$', label):
            mapping[label] = {"param": "batch_size", "value": label}
        elif role == 'switch':
            mapping[label] = {"param": "use_unlim", "value": ctrl.get("checked") == "true"}

    return mapping


def format_output(tree, mapping=None):
    """Format the form tree with parameter mapping."""
    lines = []
    model = tree.get("model", "unknown")
    controls = tree.get("controls", [])

    lines.append("form {")
    lines.append(f"  model: \"{model}\"")
    lines.append("")

    for ctrl in controls:
        role = ctrl["role"]
        label = ctrl["label"]
        name = ctrl["name"]
        value = ctrl["value"]
        checked = ctrl["checked"]
        expanded = ctrl["expanded"]

        # Find param mapping
        param_name = ""
        param_value = ""
        if mapping and label in mapping:
            param_name = f" -> {mapping[label]['param']}"
            param_value = f" = {mapping[label]['value']}"

        if role == "switch":
            state = "true" if checked == "true" else "false"
            lines.append(f"  {label}: {state}{param_name}{param_value} [switch]")
        elif expanded is not None:
            state = "open" if expanded == "true" else "closed"
            lines.append(f"  {label}: {state}{param_name}{param_value} [dropdown]")
        elif role in ("textbox", "textarea"):
            lines.append(f"  {label}: \"{value[:30]}\"{param_name} [input]")
        elif "Decrement" in label or "Increment" in label:
            continue
        elif "Generate" in label or "Submit" in label:
            lines.append(f"  {label}{param_name} [submit]")
        elif role == "file" or (tag == "input" and type == "file"):
            lines.append(f"  {label}: [file upload]")
        else:
            lines.append(f"  {label}{param_name}{param_value} [{role}]")

    lines.append("}")
    return "\n".join(lines)


if __name__ == "__main__":
    capture = "--capture" in sys.argv

    tree = get_form_tree()
    mapping = None

    if capture and "error" not in tree:
        # Capture a request to map params
        print("Capturing request...", file=sys.stderr)
        ab("network", "har", "start", timeout=10)

        # Find and click generate
        controls = tree.get("controls", [])
        gen = [c for c in controls if "Generate" in c.get("label", "") or "Submit" in c.get("label", "")]
        if gen:
            # Find the ref for this button
            snap = ab("snapshot", "-i", timeout=10)[1] if not ab("snapshot", "-i", timeout=10)[0] else ""
            for line in snap.split("\n"):
                if gen[0]["label"] in line and "ref=" in line:
                    ref = re.search(r'ref=(e\d+)', line)
                    if ref:
                        ab("click", f"@{ref.group(1)}", timeout=10)
                        time.sleep(5)
                        break

        _, har_out, _ = ab("network", "har", "stop", "/tmp/re_form_params.har", timeout=30)

        # Parse HAR for request body
        try:
            with open("/tmp/re_form_params.har") as f:
                har = json.load(f)
            for e in har["log"]["entries"]:
                req = e["request"]
                if req["method"] == "POST" and "fnf" in req["url"]:
                    body = req.get("postData", {}).get("text", "")
                    mapping = map_params_to_controls(controls, json.loads(body))
                    break
        except Exception as e:
            print(f"Har parse error: {e}", file=sys.stderr)

    print(format_output(tree, mapping))
