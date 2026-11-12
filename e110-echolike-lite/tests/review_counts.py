"""Number parsing for counts: the one place where a locale can corrupt the data.

X writes "1.234 respuestas", "1,234 replies", "1,2 mil visualizaciones", "3.4K",
"56", "3 bookmarks". Reading "3 bookmarks" as three billion is a real bug that
shipped once; this keeps it from shipping twice.
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

CONTENT = (pathlib.Path(__file__).resolve().parent.parent / "extension" / "content.js").read_text()
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


# Pull `num()` out of the content script: same source, no copy to drift.
start = CONTENT.index("  function num(value) {")
end = CONTENT.index("  const countOf = (art, testid) => {")
fn = CONTENT[start:end]

CASES = {
    "1.234 respuestas": 1234,
    "1,234 replies": 1234,
    "1,2 mil visualizaciones": 1200,
    "3.4K": 3400,
    "2 M": 2000000,
    "56": 56,
    "3 bookmarks": 3,
    "98.765": 98765,
    "0": 0,
    "1.234.567": 1234567,
    "sin números": None,
    "": None,
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_content("<html><body></body></html>")
    page.add_script_tag(content="window.__num = (function () {" + fn + " return num; })();")
    for raw, want in CASES.items():
        got = page.evaluate("raw => window.__num(raw)", raw)
        check(repr(raw), got, want)
    browser.close()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
