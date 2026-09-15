#!/usr/bin/env python3
"""e059 build-time first-paint injection (static SSR, $0).

The card is a static file server: every headline div renders "…" until JS
+ JSON arrive. On slow phone signal the owner sees a blank card. This script
rebuilds output/index.html from page.html with the verdict, data-pulse and
score lines pre-rendered, so first paint already answers. JS overwrites the
same divs with live values on load — no duplication, just no blank paint.

Idempotent; runs last in bin/refresh.sh.
"""
import json, os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "output")

TREND_WORDS = {-1: "getting cheaper", 1: "getting pricier"}


def main():
    d = json.load(open(os.path.join(OUT, "multiples.json")))
    try:
        cc = json.load(open(os.path.join(OUT, "cheap_calls.json")))
    except Exception:
        cc = {}
    try:
        ver = json.load(open(os.path.join(OUT, "version.json")))
        commit = ver.get("commit", "?")
    except Exception:
        commit = "?"

    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "e068-tablelib"))
    from tablelib.render import render_table as _tl_render
    from tablelib.stats import auto_presets as _tl_presets, suggest as _tl_suggest
    import shutil as _shutil
    meds = d.get("category_medians", {})
    rows = []
    for p in d["protocols"]:
        m = meds.get(p.get("category", ""), {})
        mp = m.get("median_p_fees")
        if p.get("p_fees") and mp:
            rows.append((p["p_fees"] / mp, p))
    rows.sort(key=lambda t: t[0])
    from collections import Counter as _Counter
    _thrus = sorted(p.get('data_through', '?') for p in d['protocols'] if p.get('data_through'))
    mode_thru = _Counter(_thrus).most_common(1)[0][0] if _thrus else '?'
    if rows:
        r, p = rows[0]
        tw = TREND_WORDS.get(p.get("trend_dir"), "steady")
        stale_v = " (stale data)" if p.get("data_through") != mode_thru else ""
        verdict = f"Cheapest vs its group: {p['symbol']} at {r:.1f}x {p.get('category')} median, {tw}{stale_v}."
    else:
        verdict = f"{len(d['protocols'])} coins priced vs sales — tap below for what the columns mean."

    try:
        as_of = datetime.fromisoformat(d["as_of"].replace("Z", "+00:00"))
        age_h = (datetime.now(timezone.utc) - as_of).total_seconds() / 3600
        stale = age_h > 49
        badge = f"{'STALE' if stale else 'LIVE'} {as_of.month:02d}/{as_of.day:02d} {as_of.hour:02d}:{as_of.minute:02d}"
    except Exception:
        badge, stale = "LIVE ?", False
    thrus = sorted(p.get('data_through', '?') for p in d['protocols'] if p.get('data_through'))
    n_lag = sum(1 for t in thrus if t != mode_thru)
    if n_lag:
        thru_txt = (f"{len(thrus) - n_lag} current thru {mode_thru}, "
                    f"{n_lag} lagging \u2014 marked stale")
    else:
        thru_txt = f"data through {mode_thru}"
    pulse = (f"Sampling {len(d['protocols'])} coins daily from 2 free feeds "
             f"({thru_txt}).")

    bt = (cc.get("backtest") or {})
    pp = (cc.get("paper") or {})
    if bt.get("precision") is not None:
        score = (f"Cheap-vs-group calls stayed cheap {bt['precision']:.0%} "
                 f"({bt['hits']}/{bt['n']} backtested)")
        dp = (bt.get("deep") or {})
        if dp.get("precision") is not None:
            score += f" \u2014 \u2605 deep {dp['precision']:.0%} ({dp['hits']}/{dp['n']})"
        if pp.get("n_pending"):
            ds = sorted((x.get("date") or "") for x in (cc.get("pending") or []) if x.get("date"))
            due = ""
            if ds:
                try:
                    from datetime import date as _d, timedelta as _t
                    g = _d.fromisoformat(ds[0]) + _t(days=int(cc.get("resolve_days", 30)))
                    due = f", first grades {g.month:02d}-{g.day:02d}"
                except Exception:
                    due = ""
            score += f", {pp.get('n_pending', 0)} open now{due}."
        else:
            score += "."
    else:
        score = "Cheap-call scorecard building — first grade after the next refresh."

    cheap = [(r, p) for r, p in rows if r <= 0.8][:5]
    ALERT_COLS = [
        {"key": "i", "label": "#", "cls": "", "kind": "num"},
        {"key": "token", "label": "token", "cls": "", "kind": "text"},
        {"key": "p_fees", "label": "P/Fees", "cls": "", "kind": "num", "fmt": "{:.2f}"},
        {"key": "vs", "label": "vs cat", "cls": "", "kind": "pill",
         "fmt": "{:.1f}", "pill_key": "n"},
        {"key": "trend", "label": "trend", "cls": "", "kind": "text"},
        {"key": "thru", "label": "thru", "cls": "", "kind": "text"},
    ]
    alert_rows = []
    for i, (r, p) in enumerate(cheap, 1):
        m = meds.get(p.get("category", ""), {})
        n = m.get("n")
        star = "\u2605 " if r <= 0.5 else ""
        tw = TREND_WORDS.get(p.get("trend_dir"), "steady")
        stale = " (stale)" if p.get('data_through') != mode_thru else ""
        alert_rows.append({
            "i": i, "token": f"{star}{p['symbol']}", "p_fees": p.get("p_fees"),
            "vs": r, "n": (n if (n is not None and n < 20) else None),
            "trend": f"{tw}{stale}", "thru": p.get("data_through", "?")})
    deep = any(r <= 0.5 for r, _ in cheap)
    ahead = ("<b>cheap-vs-peers alerts (\u22640.8\u00d7 group, \u2605\u22640.5\u00d7 deep):</b>"
             if deep else "<b>cheap-vs-peers alerts (\u22640.8\u00d7 group):</b>")
    if len(cheap) >= 5:
        alerts = ahead + _tl_render(alert_rows, ALERT_COLS, total=len(alert_rows),
                                    page=1, per=10, sort_key="vs", sort_dir=1,
                                    ns="alerts", bare=True)
    else:
        alerts = (f"<b>cheap-vs-peers alerts:</b> only {len(cheap)}/5 qualifiers \u22640.8\u00d7 "
                  "(thin coverage \u2014 widening next).")
    MED_COLS = [
        {"key": "cat", "label": "category", "cls": "", "kind": "text"},
        {"key": "n", "label": "n", "cls": "", "kind": "num"},
        {"key": "mpf", "label": "median P/Fees", "cls": "", "kind": "num", "fmt": "{:.2f}"},
        {"key": "mpr", "label": "median P/Rev", "cls": "", "kind": "num", "fmt": "{:.2f}"},
    ]
    med_rows = [{"cat": c, "n": m["n"], "mpf": m["median_p_fees"],
                 "mpr": m["median_p_revenue"]} for c, m in sorted(meds.items())]
    med_table = _tl_render(med_rows, MED_COLS, total=len(med_rows), page=1,
                           per=10, sort_key="mpf", sort_dir=1, ns="meds", bare=True)

    for _asset, _dest in (("table.css", "tablelib.css"), ("table.js", "tablelib.js")):
        _shutil.copy(os.path.join(os.path.dirname(ROOT), "e068-tablelib", "tablelib", _asset),
                     os.path.join(OUT, _dest))

    TL_COLUMNS = [
        {"key": "token", "label": "token", "cls": "", "kind": "text", "ph": "token"},
        {"key": "name", "label": "name", "cls": "c-name", "kind": "text", "ph": "name"},
        {"key": "cat", "label": "cat", "cls": "c-cat", "kind": "text", "ph": "cat"},
        {"key": "mcap", "label": "mcap $B", "cls": "c-mcap", "kind": "num", "fmt": "{:.1f}"},
        {"key": "p_fees", "label": "P/Fees 30d", "cls": "c-pf", "kind": "num",
         "fmt": "{:.2f}", "ph": "\u2264 max"},
        {"key": "vs", "label": "vs cat", "cls": "c-vs", "kind": "pill",
         "fmt": "{:.1f}", "ph": "\u2264 max", "pill_key": "n"},
        {"key": "trend", "label": "sales 6wk", "cls": "c-tr", "kind": "spark"},
        {"key": "vol", "label": "vol 24h", "cls": "c-vol", "kind": "text"},
        {"key": "chg", "label": "24h %", "cls": "c-chg", "kind": "num", "fmt": "{:+.1f}"},
        {"key": "chg7", "label": "7d %", "cls": "c-chg7", "kind": "num", "fmt": "{:+.1f}"},
        {"key": "p7", "label": "P/Fees 7d", "cls": "c-7d", "kind": "num", "fmt": "{:.2f}"},
        {"key": "mom", "label": "momentum 7d/30d", "cls": "c-mom", "kind": "num", "fmt": "{:.2f}"},
        {"key": "prev", "label": "P/Revenue", "cls": "c-rev", "kind": "num", "fmt": "{:.2f}"},
        {"key": "thru", "label": "through", "cls": "c-thru tl-nw", "kind": "text"},
    ]

    def _tl_vol(v):
        if v is None:
            return None
        if v >= 1e9:
            return f"{v / 1e9:.1f}B"
        if v >= 1e6:
            return f"{round(v / 1e6)}M"
        return f"{round(v / 1e3)}k"

    tl_rows = []
    for p in d["protocols"]:
        m = meds.get(p.get("category", ""), {})
        mp = m.get("median_p_fees")
        r = (p["p_fees"] / mp) if (p.get("p_fees") and mp) else None
        n = m.get("n")
        tl_rows.append({
            "token": p["symbol"], "name": p["name"],
            "cat": p.get("category", ""),
            "mcap": (p["market_cap_usd"] / 1e9 if p.get("market_cap_usd") is not None else None),
            "p_fees": p.get("p_fees"), "vs": r,
            "n": (n if (n is not None and n < 20) else None),
            "trend": p.get("p_fees_trend"),
            "vol": _tl_vol(p.get("volume_24h_usd")),
            "chg": p.get("price_change_24h_pct"),
            "chg7": p.get("price_change_7d_pct"),
            "p7": p.get("p_fees_7d"), "mom": p.get("fees_momentum"),
            "prev": p.get("p_revenue"), "thru": p.get("data_through"),
        })
    tl_rows.sort(key=lambda r: (r["p_fees"] is None, r["p_fees"] or 0))
    presets = ([{"name": "cheap first", "state": {"sortKey": "vs",
                "sortDir": 1, "per": 10, "filters": {}}}] +
               _tl_presets(tl_rows, TL_COLUMNS))
    tl_html = _tl_render(tl_rows, TL_COLUMNS, total=len(tl_rows), page=1,
                         per=10, sort_key="p_fees", sort_dir=1, ns="e59",
                         presets=presets,
                         suggestions=_tl_suggest(tl_rows, TL_COLUMNS, derived={
                             "p7": "p_fees", "mom": "p_fees", "vs": "p_fees"}),
                         derived={"p7": "p_fees", "mom": "p_fees", "vs": "p_fees"})

    SCORE_COLS = [
        {"key": "k", "label": "metric", "cls": "", "kind": "text"},
        {"key": "v", "label": "value", "cls": "", "kind": "text"},
    ]
    _bt = (cc.get("backtest") or {})
    _pp = (cc.get("paper") or {})
    _dp = (_bt.get("deep") or {})
    score_rows = []
    if _bt.get("precision") is not None:
        score_rows.append({"k": "cheap-vs-group stayed cheap",
                           "v": "{:.0%}".format(_bt["precision"])})
        score_rows.append({"k": "backtested",
                           "v": "{}/{}".format(_bt.get("hits"), _bt.get("n"))})
        if _dp.get("precision") is not None:
            score_rows.append({"k": "deep stayed cheap",
                               "v": "{:.0%} ({}/{})".format(_dp["precision"], _dp.get("hits"), _dp.get("n"))})
        if _pp.get("n_pending"):
            ds = sorted((x.get("date") or "") for x in (cc.get("pending") or []) if x.get("date"))
            due = ""
            if ds:
                try:
                    from datetime import date as _d, timedelta as _t
                    g = _d.fromisoformat(ds[0]) + _t(days=int(cc.get("resolve_days", 30)))
                    due = "{:02d}-{:02d}".format(g.month, g.day)
                except Exception:
                    due = ""
            score_rows.append({"k": "open now", "v": str(_pp.get("n_pending", 0))})
            if due:
                score_rows.append({"k": "first grades", "v": due})
    score_table = _tl_render(score_rows, SCORE_COLS, total=len(score_rows),
                             page=1, per=10, ns="score", bare=True)
    GLOSS_COLS = [
        {"key": "k", "label": "column", "cls": "", "kind": "text"},
        {"key": "v", "label": "means", "cls": "", "kind": "text"},
    ]
    gloss_rows = [
        {"k": "vs cat", "v": "coin price vs its category median (<1x = cheaper)"},
        {"k": "sales 6wk", "v": "price-vs-sales each week, down = getting cheaper"},
        {"k": "vol", "v": "24h coin volume (full view)"},
        {"k": "24h% / 7d%", "v": "price move; compare vs momentum: price up + sales flat = multiple expanding"},
        {"k": "sources", "v": "; ".join(d.get("sources", []))},
    ]
    gloss_table = _tl_render(gloss_rows, GLOSS_COLS, total=len(gloss_rows),
                             page=1, per=10, ns="gloss", bare=True)

    html = open(os.path.join(ROOT, "page.html")).read()
    stale_cls = ' class="badge stale"' if stale else ' class="badge"'
    html = html.replace('<span class="badge" id="fresh">…</span>',
                        f'<span{stale_cls} id="fresh">{badge}</span>')
    html = html.replace('<small id="ver" style="font-weight:normal"></small>',
                        f'<small id="ver" style="font-weight:normal">v{commit}</small>')
    html = html.replace('<div id="verdict" class="cav" style="font-size:14px;margin:.4em 0">…</div>',
                        f'<div id="verdict" class="cav" style="font-size:14px;margin:.4em 0">{verdict}</div>')
    html = html.replace('<div id="pulse" class="cav">…</div>',
                        f'<div id="pulse" class="cav">{pulse}</div>')
    html = html.replace('<div id="score" class="cav" style="font-size:14px;margin:.4em 0">…</div>',
                        f'<div id="score" class="cav" style="font-size:14px;margin:.4em 0"><b>scorecard</b>{score_table}</div>')
    html = html.replace('<div id="alerts" class="cav" style="font-size:13px;margin:.4em 0">…</div>',
                        f'<div id="alerts" class="cav" style="font-size:13px;margin:.4em 0">{alerts}</div>')
    html = html.replace('<summary id="metasum">…</summary>',
                        f'<summary id="metasum">{len(d["protocols"])} coins priced vs sales — tap for what the columns mean.</summary>')
    html = html.replace('<div id="metadetail"></div>',
                        f'<div id="metadetail">{gloss_table}</div>')
    html = html.replace('<div id="table-slot">…</div>', tl_html)
    html = html.replace('<div id="medians" class="cav">…</div>',
                        f'<div id="medians" class="cav"><b>category medians</b>{med_table}</div>')
    open(os.path.join(OUT, "index.html"), "w").write(html)
    print(f"inject ok: verdict={verdict!r} pulse={pulse!r} score={score!r} alerts_n={len(cheap)}")


if __name__ == "__main__":
    main()
