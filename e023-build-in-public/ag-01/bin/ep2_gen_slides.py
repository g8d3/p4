#!/usr/bin/env python3
"""E02 slide deck: data/concept slides (HTML->PNG, 16:9, big, one idea each).
Styled after the E01 v3 deck. Numbers verified against e025 outputs."""
import os, subprocess

OUT = "/home/vuos/code/p4/e023-build-in-public/ag-01/output/ep2_slides"
EXP = "/home/vuos/code/p4/e025-hyperliquid-candle-tails"
os.makedirs(OUT, exist_ok=True)


def render_png(fname):
    hpath = f"{OUT}/{fname}.html"
    png = f"{OUT}/{fname}.png"
    cmd = ["timeout", "40", "google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
           f"--user-data-dir=/tmp/opencode/cv2-{fname}-{os.getpid()}",
           f"--screenshot={png}", "--window-size=1920,1080",
           "--ozone-platform=headless", "--use-gl=swiftshader",
           "--force-device-scale-factor=1", f"file://{hpath}"]
    subprocess.run(cmd, capture_output=True)
    return png


TPL = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#0d1117;color:#e6edf3;font-family:'DejaVu Sans',system-ui,sans-serif;
display:flex;align-items:center;justify-content:center;height:1080px;overflow:hidden;}
.card{text-align:center;max-width:1760px;}
.label{font-size:40px;color:#8b949e;letter-spacing:1px;margin-bottom:24px;}
.num{font-size:200px;font-weight:800;color:%s;line-height:1.05;text-shadow:0 0 60px rgba(88,166,255,.25);}
.sub{font-size:50px;color:#e6edf3;margin-top:28px;line-height:1.45;white-space:pre-line;}
ul{list-style:none;padding:0;font-size:46px;line-height:1.75;}
li{margin:14px 0;}
li .k{color:#8b949e;}
li .n{color:#f85149;font-weight:700;}
li .y{color:#3fb950;font-weight:700;}
table{border-collapse:collapse;margin:0 auto;font-size:38px;}
th{background:#161b22;color:#8b949e;padding:15px 24px;border-bottom:2px solid #30363d;}
td{padding:13px 24px;border-bottom:1px solid #30363d;text-align:center;}
.pos{color:#3fb950;font-weight:700;} .neg{color:#f85149;font-weight:700;}
.warn{color:#f0c674;font-weight:700;}
</style></head><body><div class="card">%s</div></body></html>"""


def big(fname, label, num, sub, accent="#58a6ff"):
    html = TPL % (accent, f'<div class="label">{label}</div>'
                  f'<div class="num">{num}</div>'
                  f'<div class="sub">{sub}</div>')
    write_render(fname, html)


def list_slide(fname, title, items):
    lis = "".join(f"<li><span class='k'>{k}</span><span class='{cls}'>{v}</span></li>"
                  for k, v, cls in items)
    html = TPL % ("#8b949e", f'<div class="label">{title}</div><ul>{lis}</ul>')
    write_render(fname, html)


def table_slide(fname, title, headers, rows):
    trs = ""
    for row in rows:
        tds = ""
        for cell in row:
            cls = ""
            s = cell
            if s.startswith("+") and "%" in s:
                cls = "pos"
            elif s.startswith("-"):
                cls = "neg"
            tds += f"<td class='{cls}'>{s}</td>"
        trs += f"<tr>{tds}</tr>"
    ths = "".join(f"<th>{h}</th>" for h in headers)
    html = TPL % ("#58a6ff", f'<div class="label">{title}</div>'
                  f'<table><tr>{ths}</tr>{trs}</table>')
    write_render(fname, html)


def write_render(fname, html):
    hpath = f"{OUT}/{fname}.html"
    with open(hpath, "w") as f:
        f.write(html)
    png = render_png(fname)
    ok = os.path.exists(png) and os.path.getsize(png) > 10000
    print(f"  {fname}: {'OK' if ok else 'FAIL'} ({os.path.getsize(png) if os.path.exists(png) else 0}B)")


print("== E02 slides ==")
# title + intro
big("d00_title", "EPISODE 2 · THE EDGE HUNT", "135,232", "candles · 15 agents · one survivor",
    "#f0c674")
big("d01_question", "THE QUESTION", "CAN AI FIND AN EDGE\nIN CRYPTO CANDLES?",
    "not a vibe — a number that survives\nout-of-sample AND after fees", "#58a6ff")
big("d02_setup", "THE SETUP", "12 PERPS × 4 TIMEFRAMES",
    "5m · 1h · 1d · 1w\n135,232 candles · max available history", "#58a6ff")
big("d03_candle", "BEGINNER REFRESHER · WHAT'S A CANDLE?", "OPEN · HIGH · LOW · CLOSE",
    "one bar = one period of trading\n'the question: does the past predict the next move?'", "#8b949e")
# fat tails
big("d05_fattails", "FINDING 1 · FAT TAILS", "KURTOSIS 9–14",
    "a normal bell curve = kurtosis 3\ncrypto candles: 9 · 10 · 14", "#3fb950")
big("d06_fattail_mean", "WHAT FAT TAILS MEAN", "1-in-1000 MOVES\nHAPPEN ALL THE TIME",
    "extreme events are routine, not black swans\nrisk models that assume normal = blow-ups", "#f0c674")
# vol clustering
big("d07_volcluster", "FINDING 2 · VOLATILITY CLUSTERING", "~2×",
    "after an extreme candle, swings stay 2–2.5× normal\nfor several candles, then decay slowly", "#3fb950")
big("d08_volinput", "BUT IT'S NOT A TRADE", "SIZING INPUT, NOT DIRECTION",
    "clustering predicts the SIZE of the next move\nnot its direction — use it to size, not to buy", "#8b949e")
# nulls
list_slide("d09_nulls", "THE HONEST NULLS — DIRECTION", [
    ("hour of day", "  null", "k"),
    ("day of month", "  null", "k"),
    ("VWAP distance", "  null", "k"),
    ("funding rates", "  persistent, blind", "k"),
    ("weekday effect", "  real pattern · loses OOS", "n"),
    ("OBV divergence", "  dies at fees", "n"),
])
# event study
big("d10_eventstudy", "THE EVENT STUDY — HOW IT WORKS", "LINE UP THE RARE ONES",
    "pick every 3σ daily crash\nline them up · average the path after", "#58a6ff")
big("d11_eventresult", "WHAT HAPPENS AFTER A DAILY CRASH?", "+2.5%",
    "mean return over the next 5 days\n6/6 coins · both halves of the data", "#3fb950")
# out of sample
big("d12_oos", "THE TEST THAT CATCHES MIRAGES", "OUT-OF-SAMPLE",
    "thresholds built on the FIRST half only\ntrades taken in the SECOND half — never seen", "#f0c674")
big("d13_overfit", "THE CLASSIC OVERFIT", "TRAINING CHAMPION\n→ COLLAPSES OOS",
    "the rule that fits training noise best\nis usually the one that fails live", "#f85149")
# fees
big("d14_fees", "THE SECOND KILLER · FEES", "0.09%",
    "round-trip cost on EVERY trade\nmost statistical edges are smaller than the fee", "#f85149")
table_slide("d15_ledger", "THE EDGE LEDGER · HYPE FILTER (net of 0.09% RT)",
    ["edge", "gross", "net", "verdict"], [
        ("daily crash reversion", "+2.47%", "+2.38%", "REAL"),
        ("1h post-crash bounce", "+0.21%", "+0.12%", "not robust"),
        ("5m post-crash bounce", "+0.05%", "-0.04%", "dies at fees"),
        ("body-position reversion", "+0.04%", "-0.05%", "sub-fee"),
        ("weekday tilt", "-0.34%", "-0.43%", "not tradeable"),
        ("OBV divergence", "-0.10%", "+0.01%", "dies at fees"),
        ("vol clustering", "—", "—", "sizing only"),
    ])
# combined
big("d16_small", "THE PROBLEM WITH THE CRASH SIGNAL", "28 TRADES",
    "a statistical edge with 28 trades\ncan be luck", "#f0c674")
big("d17_t2", "THE SECOND, INDEPENDENT SIGNAL", "LOW-VOLUME DOWN",
    "a down day on unusually LOW volume\nfor the size of the move — an unconfirmed decline", "#58a6ff")
big("d18_overlap", "THE SURPRISE", "4% OVERLAP",
    "only 4% of low-volume days were also crashes\ntwo independent signals → combine them", "#3fb950")
big("d19_combined", "COMBINED: CRASH OR LOW-VOLUME DOWN", "+0.55%/trade",
    "312 out-of-sample trades · net of fees\nSharpe 0.44 · +16.3% total", "#3fb950")
big("d20_baseline", "THE BASELINE", "-67%",
    "just being long every day, same window\nlost sixty-seven percent", "#f85149")
# honest
big("d21_honest", "THE HONEST PART", "NOT A MONEY PRINTER",
    "Sharpe 0.44 · -32% drawdown\n12 correlated coins · one market regime\nresearch, not advice", "#f0c674")
big("d22_monitor", "THE FORWARD TEST", "LIVE PAPER MONITOR",
    "reads live Hyperliquid candles daily\ncrash or low-volume-down → 5d paper long\nP&L net of fees → phone push", "#58a6ff")
big("d23_verdict", "THE VERDICT", "ONE EDGE SURVIVED",
    "daily crashes mean-revert\nnow being paper-traded live, in public\nlosses included", "#3fb950")
big("d24_thanks", "THANKS FOR WATCHING · E02", "LINKS BELOW",
    "all 15 agent reports + the live monitor\nin the description", "#8b949e")

print("== charts ==")
chart_map = {
    "ch_hist": f"{EXP}/ag-02-dist/output/charts/hist_5m.png",
    "ch_paths": f"{EXP}/ag-07-event-study/output/charts/paths_1d.png",
    "ch_equity": f"{EXP}/ag-15-combined/output/equity.png",
}
for name, src in chart_map.items():
    dst = f"{OUT}/{name}.png"
    if os.path.exists(src):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src,
                        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0d1117",
                        "-frames:v", "1", dst], capture_output=True)
        print(f"  {name}: {'OK' if os.path.exists(dst) else 'FAIL'}")
    else:
        print(f"  {name}: FALTA")

print("DONE")
