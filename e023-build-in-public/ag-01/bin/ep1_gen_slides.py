#!/usr/bin/env python3
"""Generate 23 big-readability slides for E01, timed to the existing narration."""
import os, subprocess, time

OUT = "/home/vuos/code/p4/e023-build-in-public/ag-01/output/slides/big"
os.makedirs(OUT, exist_ok=True)

# (label, big_number, subline, bg, accent) — ONE idea per slide
SLIDES = [
    ("EPISODE 1", "+50%", "The trading bot that lost everything\non real data", "#0d1117", "#f0c674"),
    ("THE STRATEGY", "GRID", "Buy & sell on support/resistance levels.\nFreed capital → redistributed by volume profile.", "#0d1117", "#58a6ff"),
    ("STEP 1 · FAKE MARKET", "20,000", "synthetic 5-min bars, seed 42", "#0d1117", "#58a6ff"),
    ("STEP 2 · RANGE BACKTEST", "+20.9%", "profit factor 2.70\nbudget 30k · start 100k", "#0d1117", "#3fb950"),
    ("THIS IS WHERE", "TUTORIALS STOP", "green number → 'go live'", "#0d1117", "#3fb950"),
    ("STEP 3 · ALL 4 REGIMES", "RANGE +21%", "trend +15% · downtrend +6% · mixed -16%", "#0d1117", "#3fb950"),
    ("ONE REGIME IS LOSING", "-16%", "mixed market · same strategy", "#0d1117", "#f85149"),
    ("STEP 4 · GRID SEARCH", "486", "configurations searched", "#0d1117", "#58a6ff"),
    ("TWO CONFIGS · ONE DIFFERENCE", "+54.8%", "rebalance 48 bars (train)", "#0d1117", "#f0c674"),
    ("THE OTHER", "+50%", "rebalance 96 bars (train)", "#0d1117", "#f0c674"),
    ("STEP 5 · OUT-OF-SAMPLE", "-1.9%", "best config collapses (3 unseen seeds)", "#0d1117", "#f85149"),
    ("ONE SEED LOST", "-50.5%", "the champion, out of sample", "#0d1117", "#f85149"),
    ("THE OTHER HELD", "+23.8%", "single parameter difference = overfit", "#0d1117", "#3fb950"),
    ("STEP 6 · REAL TEST", "105,122", "real Binance BTC 5m bars · 1 year", "#0d1117", "#58a6ff"),
    ("v1 ON REAL BTC", "-20.6%", "max drawdown -48%", "#0d1117", "#f85149"),
    ("BLED TO DEATH", "13,424", "fills → 25,235 USDT in fees", "#0d1117", "#f85149"),
    ("STEP 7 · THE REDESIGN", "v2", "ATR-spaced levels · EMA trend filter\nhonest leverage · maker fees", "#0d1117", "#58a6ff"),
    ("v2 ON REAL BTC", "+3.6%", "2,158 fills · fees 25,235 → 2,393", "#0d1117", "#3fb950"),
    ("BTC 1h · 4 YEARS", "+1.7%", "was -79.4%", "#0d1117", "#3fb950"),
    ("THE HONEST TRUTH", "PF 1.14", "a modest fee-controlled edge,\nnot a money printer", "#0d1117", "#f0c674"),
    ("REBALANCE RIDGE", "+8.4% → -5.6%", "16 bars apart on the same edge", "#0d1117", "#f85149"),
    ("THE VERDICT", "BACKTESTS LIE", "Synthetic data → 'not broken'.\nReal money → the truth.", "#0d1117", "#f0c674"),
    ("THANKS", "E01", "link to the code & data in the description", "#0d1117", "#58a6ff"),
]

TPL = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body {{ margin:0; background:{bg}; color:#e6edf3; font-family:'DejaVu Sans',system-ui,sans-serif;
         display:flex; align-items:center; justify-content:center; height:1080px; overflow:hidden; }}
  .card {{ text-align:center; max-width:1700px; }}
  .label {{ font-size:44px; color:#8b949e; letter-spacing:2px; margin-bottom:28px; }}
  .num {{ font-size:250px; font-weight:800; color:{accent}; line-height:1.05; text-shadow:0 0 60px rgba(88,166,255,.25); }}
  .sub {{ font-size:52px; color:#e6edf3; margin-top:34px; line-height:1.45; white-space:pre-line; }}
</style></head><body>
  <div class="card">
    <div class="label">{label}</div>
    <div class="num">{num}</div>
    <div class="sub">{sub}</div>
  </div>
</body></html>"""

# Write all HTMLs first (fast, no chrome)
for i, (label, num, sub, bg, accent) in enumerate(SLIDES):
    html = TPL.format(label=label, num=num, sub=sub, bg=bg, accent=accent)
    with open(f"{OUT}/slide_{i:02d}.html", "w") as f:
        f.write(html)
print(f"wrote {len(SLIDES)} html files")

# Then screenshot each with a unique temp profile (avoids profile locks) + hard timeout
for i in range(len(SLIDES)):
    png = f"{OUT}/slide_{i:02d}.png"
    if os.path.exists(png) and os.path.getsize(png) > 10000:
        print(f"slide {i:02d} exists, skip", flush=True)
        continue
    prof = f"/tmp/opencode/chrome-slide-{i}-{os.getpid()}"
    cmd = ["timeout", "25", "google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
           f"--user-data-dir={prof}",
           f"--screenshot={png}", "--window-size=1920,1080",
           "--ozone-platform=headless", "--use-gl=swiftshader",
           "--force-device-scale-factor=1", f"file://{OUT}/slide_{i:02d}.html"]
    r = subprocess.run(cmd, capture_output=True)
    ok = os.path.exists(png) and os.path.getsize(png) > 10000
    print(f"slide {i:02d} -> {'OK' if ok else 'FAIL'} ({os.path.getsize(png) if os.path.exists(png) else 0})", flush=True)
    time.sleep(0.5)

print(f"done: {len(SLIDES)} slides")
