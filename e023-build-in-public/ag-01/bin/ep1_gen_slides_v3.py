#!/usr/bin/env python3
"""E01 v3 slide deck: real-data slides (HTML->PNG) + grid-image cells.
No Ken Burns — static, big, one idea per slide. Slides generated for 16:9."""
import os, subprocess, glob

OUT = "/home/vuos/code/p4/e023-build-in-public/ag-01/output/slides/v3"
CELLS = "/home/vuos/code/p4/e023-build-in-public/ag-01/output/slides/grid_cells"
EXP = "/home/vuos/code/p4/e022-nautilus-sr-grid/ag-01/output"
os.makedirs(OUT, exist_ok=True)

# --- 1. Real-data slides as HTML -> PNG (big, readable, honest numbers) ---

def render_png(fname):
    hpath = f"{OUT}/{fname}.html"
    png = f"{OUT}/{fname}.png"
    cmd = ["timeout", "40", "google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
           f"--user-data-dir=/tmp/opencode/cv3-{fname}-{os.getpid()}",
           f"--screenshot={png}", "--window-size=1920,1080",
           "--ozone-platform=headless", "--use-gl=swiftshader",
           "--force-device-scale-factor=1", f"file://{hpath}"]
    subprocess.run(cmd, capture_output=True)
    return png

def html_slide(fname, title, big, sub, accent="#3fb950"):
    tpl = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#0d1117;color:#e6edf3;font-family:'DejaVu Sans',system-ui,sans-serif;
display:flex;align-items:center;justify-content:center;height:1080px;overflow:hidden;}
.card{text-align:center;max-width:1750px;}
.label{font-size:40px;color:#8b949e;letter-spacing:1px;margin-bottom:20px;}
.num{font-size:190px;font-weight:800;color:%s;line-height:1.05;text-shadow:0 0 50px rgba(88,166,255,.2);}
.sub{font-size:48px;color:#e6edf3;margin-top:26px;line-height:1.4;white-space:pre-line;}
table{border-collapse:collapse;margin:0 auto;font-size:38px;}
th{background:#161b22;color:#8b949e;padding:14px 22px;border-bottom:2px solid #30363d;}
td{padding:12px 22px;border-bottom:1px solid #30363d;}
.pos{color:#3fb950;font-weight:700;} .neg{color:#f85149;font-weight:700;}
</style></head><body><div class="card">
<div class="label">%s</div><div class="num">%s</div><div class="sub">%s</div>
</div></body></html>""" % (accent, title, big, sub)
    hpath = f"{OUT}/{fname}.html"
    open(hpath, "w").write(tpl)
    return render_png(fname)

# story beats: (fname, label, big, sub, accent)
BEATS = [
    ("d00_title", "EPISODE 1", "+50%", "The trading bot that lost everything\non real data", "#f0c674"),
    ("d01_strategy", "THE STRATEGY", "GRID", "buy/sell on support & resistance\nfreed capital → redistributed by volume profile", "#58a6ff"),
    ("d02_synth", "STEP 1 · FAKE MARKET", "20,000", "synthetic 5-min bars · seed 42", "#58a6ff"),
    ("d03_range", "STEP 2 · RANGE BACKTEST", "+20.9%", "profit factor 2.70", "#3fb950"),
    ("d04_golive", "THIS IS WHERE", "TUTORIALS STOP", "green number → go live", "#3fb950"),
    ("d05_regimes", "STEP 3 · ALL 4 REGIMES", "RANGE +21%", "trend +15% · downtrend +6% · mixed -16%", "#3fb950"),
    ("d06_mixed", "ONE REGIME IS LOSING", "-16%", "mixed market · same strategy", "#f85149"),
    ("d07_search", "STEP 4 · GRID SEARCH", "486", "configurations searched", "#58a6ff"),
    ("d08_reb48", "CONFIG A", "+54.8%", "rebalance 48 bars (train)", "#f0c674"),
    ("d09_reb96", "CONFIG B", "+50%", "rebalance 96 bars (train)", "#f0c674"),
    ("d10_oos", "STEP 5 · OUT-OF-SAMPLE", "-1.9%", "best config collapses (3 unseen seeds)", "#f85149"),
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

# table slides (real numbers, verified)
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

def table_html(fname, title, rows):
    tpl = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
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
    trs = ""
    for name, ret, dd, fills, fees in rows:
        rcls = "pos" if ret.startswith("+") else "neg"
        trs += f"<tr><td>{name}</td><td class='{rcls}'>{ret}</td><td class='neg'>{dd}</td><td>{fills}</td><td>{fees}</td></tr>"
    html = tpl % (title, trs)
    hpath = f"{OUT}/{fname}.html"
    open(hpath, "w").write(html)
    return render_png(fname)

print("== generando diapositivas de datos ==")
for fname, label, big, sub, accent in BEATS:
    png = html_slide(fname, label, big, sub, accent)
    ok = os.path.exists(png) and os.path.getsize(png) > 10000
    print(f"  {fname}: {'OK' if ok else 'FAIL'} ({os.path.getsize(png) if os.path.exists(png) else 0}B)")
for fname, (title, rows) in TABLE_SLIDES.items():
    png = table_html(fname, title, rows)
    ok = os.path.exists(png) and os.path.getsize(png) > 10000
    print(f"  {fname}: {'OK' if ok else 'FAIL'}")

# --- 2. Copy grid-image cells as thematic slides ---
print("== celdas de la grilla (imágenes IA) ==")
for i in range(12):
    src = f"{CELLS}/cell_{i:02d}.png"
    dst = f"{OUT}/img_{i:02d}.png"
    if os.path.exists(src):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src,
                        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0d1117",
                        "-frames:v", "1", dst], capture_output=True)
        print(f"  img_{i:02d}: {'OK' if os.path.exists(dst) else 'FAIL'}")
    else:
        print(f"  img_{i:02d}: FALTA cell")

# --- 3. Real equity curves ---
print("== equity curves reales ==")
equity_map = {
    "eq_v1_5m": f"{EXP}/real_robust/equity_curve.png",
    "eq_v2_5m": f"{EXP}/v2_5m/equity_curve.png",
    "eq_v2_1h": f"{EXP}/v2_1h/equity_curve.png",
}
for name, src in equity_map.items():
    dst = f"{OUT}/{name}.png"
    if os.path.exists(src):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src,
                        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0d1117",
                        "-frames:v", "1", dst], capture_output=True)
        print(f"  {name}: {'OK' if os.path.exists(dst) else 'FAIL'}")
    else:
        print(f"  {name}: FALTA")

print("DONE")
