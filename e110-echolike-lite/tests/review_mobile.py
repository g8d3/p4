"""The page fits a phone, because a phone is where it runs.

The crx is installed in a mobile browser (Quetta on Android), and the reported bug was
"extension window doesn't show full on mobile": the header was one 445px row, so on a
360-412px screen the Settings tab sat outside the viewport and the page scrolled
sideways. This loads the real page at phone sizes and pins both halves of the fix:

  * nothing is wider than the screen, and the page never scrolls sideways;
  * all four tabs are inside the viewport, on their own row, and each one is a real
    tap target (>= 30px tall) that switches the panel.

    xvfb-run -a python3 tests/review_mobile.py
"""
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ids import extension_id  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
EXT = str((ROOT.parent / "extension").resolve())
TABS = ["inbox", "spaces", "import", "settings"]
SIZES = [(320, 640), (360, 780), (390, 844), (412, 915)]
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


MEASURE = """() => {
  const vw = innerWidth;
  const over = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width && (r.right > vw + 1 || r.left < -1)) over.push([el.tagName, el.id || el.className.toString().slice(0, 24)]);
  }
  const tabs = {};
  for (const b of document.querySelectorAll('nav button')) {
    const r = b.getBoundingClientRect();
    tabs[b.id] = { left: Math.round(r.left), right: Math.round(r.right), h: Math.round(r.height), text: b.textContent };
  }
  return { vw, scrollW: document.documentElement.scrollWidth, bodyW: document.body.scrollWidth,
           over: over.slice(0, 6), overCount: over.length, tabs };
}"""

prof = tempfile.mkdtemp(prefix="echolike-lite-mobile-")
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        prof, headless=False,
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--no-first-run"],
    )
    try:
        eid = extension_id()
        page = ctx.new_page()
        for w, h in SIZES:
            page.set_viewport_size({"width": w, "height": h})
            page.goto(f"chrome-extension://{eid}/app.html#inbox")
            page.wait_for_timeout(350)
            m = page.evaluate(MEASURE)
            print("  ..   %dx%d: page %dpx wide, %d element(s) outside, header tabs %s"
                  % (w, h, m["scrollW"], m["overCount"], {k: v["right"] for k, v in m["tabs"].items()}))
            check("%dpx: the page is not wider than the screen" % w, m["scrollW"] <= w, True)
            check("%dpx: nothing sticks out of the viewport" % w, m["overCount"], 0)
            check("%dpx: all four tabs are on screen" % w, sorted(m["tabs"]), sorted("tab-" + t for t in TABS))
            check("%dpx: every tab ends inside the viewport" % w,
                  all(v["right"] <= w for v in m["tabs"].values()), True)
            check("%dpx: every tab is a real tap target" % w,
                  all(v["h"] >= 30 for v in m["tabs"].values()), True)
            # And they work: the panel each one owns becomes visible.
            for tab in TABS:
                page.click("#tab-" + tab)
                page.wait_for_timeout(120)
                check("%dpx: %s opens its panel" % (w, tab),
                      page.eval_on_selector("#panel-" + tab, "e => e.classList.contains('on')"), True)
            check("%dpx: the workspace fits with the settings panel open" % w,
                  page.evaluate("document.documentElement.scrollWidth") <= w, True)
    finally:
        ctx.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
