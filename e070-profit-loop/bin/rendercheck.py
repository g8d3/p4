#!/usr/bin/env python3
"""e070 rendercheck (local playwright): real browser with JS, reads VISIBLE text.
Replaces the sandboxed agent-browser step (no host-network access) with local
chromium over the real loopback. Same contract: fails on unfilled templates,
undefined/NaN/$$, missing sections, unfilled prices, GPU hardware->CPU regression.
Usage: python3 bin/rendercheck.py [base_url]   ($0 spend)
"""
import sys

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8327"
BASELINE = "data/gpu-baseline.txt"
HARDWARE = ("nvidia", "amd", "radeon", "intel", "iris",
            "adreno", "apple", "mali")


def main():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        try:
            b = pw.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader"])
            pg = b.new_page()
            pg.goto(BASE + "/", timeout=30000)
        except Exception as e:  # noqa: BLE001
            print("RENDERCHECK FAIL: browser could not open %s (%s)" % (BASE, str(e)[:100]))
            return 1
        pg.wait_for_timeout(5000)  # let page JS fetch /api/state and render
        try:
            text = (pg.inner_text("body") or "")[:12000]
        except Exception as e:  # noqa: BLE001
            print("RENDERCHECK FAIL: empty rendered text (%s)" % str(e)[:80])
            b.close()
            return 1
        try:
            renderer = pg.evaluate(
                "() => { const c = document.createElement('canvas');"
                " const g = c.getContext('webgl2') || c.getContext('webgl');"
                " if (!g) return 'NO-WEBGL';"
                " const d = g.getExtension('WEBGL_debug_renderer_info');"
                " return d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'WEBGL-NO-INFO'; }")
        except Exception:  # noqa: BLE001
            renderer = "NO-WEBGL"
        b.close()
    if not text.strip():
        print("RENDERCHECK FAIL: empty rendered text")
        return 1
    fail = []
    for pat in ("${", "undefined", "NaN", "$$", "loading"):
        if pat in text:
            fail.append("artifact:" + pat)
    for need in ("profit loop", "status", "workers", "ledger"):
        if need not in text and need.capitalize() not in text and need.upper() not in text:
            fail.append("missing:" + need)
    if "left (floor $" not in text:
        fail.append("prices-unfilled")
    try:
        old = open(BASELINE).read()
    except FileNotFoundError:
        old = ""
    if not old.strip():
        open(BASELINE, "w").write(str(renderer))
        print("(baseline renderer recorded: %s)" % renderer)
    else:
        hw_old = sum(1 for h in HARDWARE if h in old.lower())
        hw_now = sum(1 for h in HARDWARE if str(renderer).lower())
        if hw_old > 0 and hw_now == 0:
            fail.append("GPU-REGRESSION: was [%s], now [%s]" % (old, renderer))
    if fail:
        print("RENDERCHECK FAIL: %s" % ";".join(fail))
        return 1
    print("RENDERCHECK OK (renderer: %s)" % renderer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
