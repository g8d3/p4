import sys, time
from playwright.sync_api import sync_playwright

# usage: shot.py <url> <out.png> [frame] [width] [height]
url = sys.argv[1]; out = sys.argv[2]
frame = int(sys.argv[3]) if len(sys.argv) > 3 else 36
w = int(sys.argv[4]) if len(sys.argv) > 4 else 1280
h = int(sys.argv[5]) if len(sys.argv) > 5 else 800
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": w, "height": h})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{url}?frame={frame}", wait_until="networkidle")
    pg.wait_for_timeout(2500)
    pg.screenshot(path=out)
    print("saved", out, "errors:", errs if errs else "none")
    b.close()
