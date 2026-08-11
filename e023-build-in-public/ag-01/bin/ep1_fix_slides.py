#!/usr/bin/env python3
"""Regenerate missing data-slide HTMLs + render all data PNGs robustly."""
import os, subprocess, glob

OUT = "/home/vuos/code/p4/e023-build-in-public/ag-01/output/slides/v3"

BEATS = [
    ("d11_oosseed", "ONE SEED LOST", "-50.5%", "the champion, out of sample", "#f85149"),
    ("d12_hold", "THE OTHER HELD", "+23.8%", "single parameter = overfit", "#3fb950"),
    ("d13_real", "STEP 6 · REAL TEST", "105,122", "real Binance BTC 5m bars · 1 year", "#58a6ff"),
    ("d14_v1", "v1 ON REAL BTC", "-20.6%", "max drawdown -48%", "#f85149"),
    ("d15_fees", "BLED TO DEATH", "13,424", "fills → 25,235 USDT in fees", "#f85149"),
    ("d16_v2", "STEP 7 · THE REDESIGN", "v2", "ATR-spaced levels · EMA trend filter\nhonest leverage · maker fees", "#58a6ff"),
    ("d17_v2_5m", "v2 ON REAL BTC 5m", "+3.6%", "2,158 fills · fees 25,235 → 2,393", "#3fb950"),
    ("d18_v2_1h", "v2 ON REAL BTC 1h", "+1.7%", "was -79.4%", "#3fb950"),
    ("d19_pf", "THE HONEST TRUTH", "PF 1.14", "a modest fee-controlled edge,\nnot a money printer", "#f0c674"),
    ("d20_ridge", "REBALANCE RIDGE", "+8.4% → -5.6%", "16 bars apart on the same edge", "#f85149"),
    ("d21_verdict", "THE VERDICT", "BACKTESTS LIE", "Synthetic → 'not broken'.\nReal money → the truth.", "#f0c674"),
    ("d22_thanks", "THANKS", "E01", "code & data in the description", "#58a6ff"),
]

TABLE_SLIDES = {
    "t01_v1v2_5m": ("v1 vs v2 · REAL BTC 5m · 1 YEAR", [
        ("v1 robust", "-20.6%", "-48.5%", "13,424", "25,235"),
        ("v2 redesign", "+3.6%", "-7.2%", "2,158", "2,393"),
    ]),
    "t02_v1v2_1h": ("v1 vs v2 · REAL BTC 1h · 4 YEARS", [
        ("v1 robust", "-79.4%", "-94.3%", "6,918", "7,183"),
        ("v2 redesign", "+1.7%", "-7.6%", "1,103", "1,975"),
    ]),
}

TPL = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#0d1117;color:#e6edf3;font-family:'DejaVu Sans',system-ui,sans-serif;
display:flex;align-items:center;justify-content:center;height:1080px;overflow:hidden;}
.card{text-align:center;max-width:1750px;}
.label{font-size:40px;color:#8b949e;letter-spacing:1px;margin-bottom:20px;}
.num{font-size:190px;font-weight:800;color:%s;line-height:1.05;text-shadow:0 0 50px rgba(88,166,255,.2);}
.sub{font-size:48px;color:#e6edf3;margin-top:26px;line-height:1.4;white-space:pre-line;}
</style></head><body><div class="card">
<div class="label">%s</div><div class="num">%s</div><div class="sub">%s</div>
</div></body></html>"""

TBL_TPL = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#0d1117;color:#e6edf3;font-family:'DejaVu Sans',system-ui,sans-serif;
display:flex;align-items:center;justify-content:center;height:1080px;overflow:hidden;}
.wrap{text-align:center;}
.h1{font-size:52px;color:#58a6ff;margin-bottom:40px;font-weight:700;}
table{border-collapse:collapse;margin:0 auto;font-size:36px;}
th{background:#161b22;color:#8b949e;padding:16px 26px;border-bottom:2px solid #30363d;}
td{padding:14px 26px;border-bottom:1px solid #30363d;text-align:center;}
.pos{color:#3fb950;font-weight:700;} .neg{color:#f85149;font-weight:700;}
</style></head><body><div class="wrap">
<div class="h1">%s</div>
<table><tr><th>run</th><th>return</th><th>max DD</th><th>fills</th><th>fees</th></tr>
%s</table></div></body></html>"""

def write_and_render(fname, html):
    open(f"{OUT}/{fname}.html", "w").write(html)
    png = f"{OUT}/{fname}.png"
    if os.path.exists(png):
        try:
            from PIL import Image
            import numpy as np
            if np.array(Image.open(png).convert("RGB")).mean() < 200:
                print(f"  {fname}: ya bueno")
                return
        except Exception:
            pass
    cmd = ["timeout", "45", "google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
           f"--user-data-dir=/tmp/opencode/cv3d-{fname}-{os.getpid()}",
           f"--screenshot={png}", "--window-size=1920,1080",
           "--ozone-platform=headless", "--use-gl=swiftshader",
           "--force-device-scale-factor=1", f"file://{OUT}/{fname}.html"]
    subprocess.run(cmd, capture_output=True)
    ok = os.path.exists(png) and os.path.getsize(png) > 10000
    print(f"  {fname}: {'OK' if ok else 'FAIL'}")

for fname, label, big, sub, accent in BEATS:
    write_and_render(fname, TPL % (accent, label, big, sub))

for fname, (title, rows) in TABLE_SLIDES.items():
    trs = ""
    for name, ret, dd, fills, fees in rows:
        rcls = "pos" if ret.startswith("+") else "neg"
        trs += f"<tr><td>{name}</td><td class='{rcls}'>{ret}</td><td class='neg'>{dd}</td><td>{fills}</td><td>{fees}</td></tr>"
    write_and_render(fname, TBL_TPL % (title, trs))

print("done")
