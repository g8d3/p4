#!/usr/bin/env python3
"""Build the tablelib demo page (deterministic sample data, no network)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from tablelib.render import render_table

COLUMNS = [
    {"key": "token", "label": "token", "cls": "", "kind": "text", "ph": "token"},
    {"key": "name", "label": "name", "cls": "c-name", "kind": "text", "ph": "name"},
    {"key": "cat", "label": "cat", "cls": "c-cat", "kind": "text", "ph": "cat"},
    {"key": "mcap", "label": "mcap $B", "cls": "c-mcap", "kind": "num", "fmt": "{:.1f}"},
    {"key": "p_fees", "label": "P/Fees 30d", "cls": "c-pf", "kind": "bar",
     "fmt": "{:.2f}", "ph": "\u2264 max"},
    {"key": "trend", "label": "sales 6wk", "cls": "c-tr", "kind": "spark"},
    {"key": "curve", "label": "curve", "cls": "c-cu", "kind": "poly"},
    {"key": "vs", "label": "vs cat", "cls": "c-vs", "kind": "pill",
     "fmt": "{:.1f}", "ph": "\u2264 max", "pill_key": "n"},
    {"key": "chg", "label": "24h %", "cls": "c-chg", "kind": "num", "fmt": "{:+.1f}"},
    {"key": "thru", "label": "through", "cls": "c-thru tl-nw", "kind": "text"},
]

NAMES = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta",
         "Theta", "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron",
         "Pi", "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi",
         "Omega", "Prime"]


def main():
    rows = []
    for i, nm in enumerate(NAMES):
        rows.append({
            "token": f"T{i:02d}", "name": f"Token {nm}",
            "cat": ["L1", "DEX", "Lending"][i % 3],
            "mcap": round(60 + ((i * 53) % 23) * 22.5, 1),
            "p_fees": (180.0 if nm == "Omega" else
                       round(0.5 + ((i * 29) % 19) * 2.1, 2)),
            "vs": round(0.1 + ((i * 41) % 20) * 0.1, 1),
            "n": [10, 6, 5][i % 3],
            "chg": round(-13.1 + ((i * 37) % 21) * 1.3, 1),
            "thru": "2026-09-15",
            "trend": [round(1 + ((i * 7 + j * 13) % 10) + j * (0.5 if i % 2 else -0.3), 1)
                      for j in range(6)],
            "curve": [round(5 + 4 * (1 - abs(j - 2.5) / 2.5) + (i % 3), 1)
                      for j in range(6)],
        })
    rows.sort(key=lambda r: r["p_fees"])
    from tablelib.stats import auto_presets, suggest
    presets = auto_presets(rows, COLUMNS)
    presets += [
        {"name": "cheap L1",
         "state": {"sortKey": "p_fees", "sortDir": 1, "per": 10,
                    "filters": {"c": "L1", "vs": "0.5"},
                    "density": "simple", "cards": 0}},
        {"name": "biggest first",
         "state": {"sortKey": "mcap", "sortDir": -1, "per": 10,
                    "filters": {}, "density": "full", "cards": 0}},
    ]
    table = render_table(rows, COLUMNS, total=len(rows), page=1, per=10,
                         sort_key="p_fees", sort_dir=1, ns="demo",
                         presets=presets,
                         suggestions=suggest(rows, COLUMNS))
    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>tablelib demo</title>
<link rel="stylesheet" href="../tablelib/table.css">
<style>body{{font-family:system-ui,sans-serif;max-width:1000px;margin:2em auto;padding:0 1em}}</style>
</head><body>
<h1>tablelib demo</h1>
<div id="verdict" class="cav">Cheapest vs its group: T00 at 0.1x L1 median, steady.</div>
<div id="pulse" class="cav">Sampling 25 coins daily from 2 free feeds (data through 2026-09-15).</div>
{table}
<script src="../tablelib/table.js"></script>
<script>document.addEventListener('DOMContentLoaded',function(){{tlRender('demo')}});</script>
</body></html>"""
    out = os.path.join(HERE, "index.html")
    open(out, "w").write(page)
    print(f"demo ok: {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
