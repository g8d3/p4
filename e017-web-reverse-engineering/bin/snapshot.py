#!/usr/bin/env python3
"""snapshot.py — Enhanced snapshot with descriptive labels for all elements."""

import subprocess
import sys


def ab(*args, timeout=30):
    cmd = ["agent-browser", "--auto-connect"] + [str(a) for a in args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"


SNAPSHOT_JS = """
var lines = [];
document.querySelectorAll('button, [role=button], a, input, select, textarea, [role=combobox], [role=switch], [role=slider], [role=tab]').forEach(el => {
    var rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    var text = el.textContent.trim().substring(0, 40);
    var aria = el.getAttribute('aria-label') || '';
    var title = el.getAttribute('title') || '';
    var placeholder = el.getAttribute('placeholder') || '';
    var role = el.getAttribute('role') || el.tagName.toLowerCase();
    var expanded = el.getAttribute('aria-expanded');
    var checked = el.getAttribute('aria-checked');
    var disabled = el.disabled ? ' [disabled]' : '';
    var value = el.value || '';

    var label = text || aria || title || placeholder || '';
    if (!label) {
        var prev = el.previousElementSibling;
        if (prev) label = prev.textContent.trim().substring(0, 30);
    }

    // Context from parent/siblings
    if (!label || label === '(button)' || label === '(unknown)') {
        var parent = el.parentElement;
        if (parent) {
            var sibs = parent.querySelectorAll('span, label, p, div');
            for (var s of sibs) {
                var t = s.textContent.trim();
                if (t && t.length < 30 && t !== text) { label = t; break; }
            }
        }
    }
    if (!label) label = '(element)';

    // Detect function
    var func = '';
    if (role === 'switch') func = 'Unlimited';
    else if (role === 'slider') func = 'Slider';
    else if (text.includes('Decrement')) func = 'Decrement';
    else if (text.includes('Increment')) func = 'Increment';
    else if (text.includes('Generate')) func = 'Submit';
    else if (/^\\d+:\\d+$/.test(text)) func = 'Aspect ratio';
    else if (/^\\d+K$/.test(text)) func = 'Resolution';
    else if (/^\\d+\\/\\d+$/.test(text)) func = 'Count';
    else if (role === 'textbox' || role === 'textarea') func = 'Input';

    var attrs = [];
    if (expanded !== null) attrs.push('expanded=' + expanded);
    if (checked !== null) attrs.push('checked=' + checked);
    if (disabled) attrs.push('disabled');
    if (value && role === 'slider') attrs.push('value=' + value);

    var attrStr = attrs.length ? ' [' + attrs.join(', ') + ']' : '';
    var funcStr = func ? ' (' + func + ')' : '';
    lines.push(role + ' \"' + label + '\"' + funcStr + attrStr);
});
lines.join('\\n');
"""


def snapshot():
    """Get enhanced snapshot with descriptive labels."""
    _, out, _ = ab("eval", SNAPSHOT_JS, timeout=10)
    # Clean up escaped quotes
    out = out.replace('\\"', '"').replace('\\n', '\n')
    if out.startswith('"') and out.endswith('"'):
        out = out[1:-1]
    return out


if __name__ == "__main__":
    print(snapshot())
