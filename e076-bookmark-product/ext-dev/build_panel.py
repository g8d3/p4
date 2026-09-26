#!/usr/bin/env python3
"""Assemble panel.js from single-truth sources (fixes HTML-in-JS + duplication).

Sources (edit THESE): ext-dev/panel-engine.js, panel-shell.js, panel-app.js,
panel.css, panel.html (+ panel-head.txt wrapper).
Artifacts (GENERATED, do not edit): ext-dev/panel.js, ext/panel.js.

Usage: python3 ext-dev/build_panel.py [--check]
  --check: verify committed artifacts match a fresh assembly (CI-style).
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def read(n):
    with io.open(os.path.join(HERE, n), encoding='utf-8') as f:
        return f.read()


def assemble():
    head = read('panel-head.txt')
    engine = read('panel-engine.js')
    shell = read('panel-shell.js')
    app = read('panel-app.js')
    css = read('panel.css')
    html = read('panel.html')
    for name, s in (('css', css), ('html', html)):
        if '`' in s or '${' in s:
            raise SystemExit('FATAL: %s breaks template literals' % name)
    assert '/*__BV_CSS__*/' in shell and '/*__BV_HTML__*/' in shell
    shell = shell.replace('/*__BV_CSS__*/""', '`' + css + '`', 1)
    shell = shell.replace('/*__BV_HTML__*/""', '`' + html + '`', 1)
    return head + engine + '\n' + shell + '\n' + app + '\n})();\n'


def main():
    out = assemble()
    targets = [os.path.join(HERE, 'panel.js'),
               os.path.join(HERE, '..', 'ext', 'panel.js')]
    if '--check' in sys.argv:
        bad = [t for t in targets
               if io.open(t, encoding='utf-8').read() != out]
        if bad:
            raise SystemExit('STALE: %s (run build_panel.py)' % bad)
        print('panel artifacts in sync')
        return
    for t in targets:
        with io.open(t, 'w', encoding='utf-8') as f:
            f.write(out)
    print('assembled panel.js (%d lines) -> ext-dev + ext' % len(out.splitlines()))


if __name__ == '__main__':
    main()
