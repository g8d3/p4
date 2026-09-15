#!/usr/bin/env python3
"""e059 build-time first-paint injection (static SSR, $0).

The card is a static file server: every headline div renders "…" until JS
+ JSON arrive. On slow phone signal the owner sees a blank card. This script
rebuilds output/index.html from page.html with the verdict, data-pulse and
score lines pre-rendered, so first paint already answers. JS overwrites the
same divs with live values on load — no duplication, just no blank paint.

Table-first rule: no multi-variable prose in cells. Every timestamp is a
tablelib date column ({"kind": "date"}, value = epoch seconds); packed
cells are split (thru date + stale flag, trend words + stale flag,
token + deep flag, vol as numeric $M). Verdict/pulse stay one short
sentence each; the variables live in tables.

Idempotent; runs last in bin/refresh.sh.
"""
import json
import os
import re
from calendar import timegm
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "output")

TREND_WORDS = {-1: "getting cheaper", 1: "getting pricier"}


def epoch_day(s):
    """'YYYY-MM-DD' -> UTC-midnight epoch seconds (int). None if unparseable."""
    try:
        dt = datetime.strptime(str(s).strip()[:10], "%Y-%m-%d")
        return int(timegm(dt.replace(tzinfo=timezone.utc).timetuple()))
    except (ValueError, TypeError):
        return None


def epoch_iso(s):
    """ISO-8601 datetime -> epoch seconds (int). None if unparseable."""
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return int(dt.timestamp())
    except (ValueError, TypeError):
        return None


def fmt_ts(ep):
    """Epoch seconds -> short 'MM/DD HH:MM' (UTC, matches tablelib date contract)."""
    dt = datetime.fromtimestamp(int(ep), tz=timezone.utc)
    return f"{dt.month:02d}/{dt.day:02d} {dt.hour:02d}:{dt.minute:02d}"


def datize(html, label, epochs):
    """Give tablelib SSR date cells their contract display + data-ts.

    render.py has no date kind yet (lands in parallel), so date columns
    render as raw epochs. This post-pass rewrites only
    <td data-l="LABEL">EPOCH</td> cells -> data-ts + 'MM/DD HH:MM'.
    Same epoch always maps to the same display, so merged maps are safe.
    """
    for ep in sorted({e for e in epochs if e is not None}):
        pat = re.compile(r'(<td data-l="%s"[^>]*?)>\s*%d\s*</td>'
                         % (re.escape(label), ep))
        html = pat.sub(lambda m: f'{m.group(1)} data-ts="{ep}">{fmt_ts(ep)}</td>',
                       html)
    return html


def main():
    d = json.load(open(os.path.join(OUT, "multiples.json")))
    try:
        _tvl = json.load(open(os.path.join(OUT, "tvl.json")))
        _tvlmap = {r.get("symbol"): r.get("p_tvl") for r in (_tvl.get("rows") or [])}
        _tvlcov = _tvl.get("coverage", "?")
    except Exception:
        _tvlmap, _tvlcov = {}, "?"
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
    mode_ep = epoch_day(mode_thru)
    # Short verdict sentence only — ratio/trend/stale/thru live in the tables.
    if rows:
        verdict = f"Cheapest vs its group: {rows[0][1]['symbol']}."
    else:
        verdict = f"{len(d['protocols'])} coins priced vs sales — tap below for what the columns mean."

    try:
        as_of = datetime.fromisoformat(d["as_of"].replace("Z", "+00:00"))
        as_ep = int(as_of.timestamp())
        age_h = (datetime.now(timezone.utc) - as_of).total_seconds() / 3600
        stale = age_h > 49
        badge = f"{'STALE' if stale else 'LIVE'} {as_of.month:02d}/{as_of.day:02d} {as_of.hour:02d}:{as_of.minute:02d}"
    except Exception:
        badge, stale, as_ep = "LIVE ?", False, None
    n_lag = sum(1 for t in _thrus if t != mode_thru)
    n_cur = len(_thrus) - n_lag
    # Short pulse sentence only — counts/dates live in the freshness table.
    pulse = (f"Sampling {len(d['protocols'])} coins daily from 2 free feeds.")
    FRESH_COLS = [
        {"key": "cov", "label": "coverage", "cls": "", "kind": "text"},
        {"key": "n", "label": "coins", "cls": "", "kind": "num"},
        {"key": "thru", "label": "through", "cls": "", "kind": "date"},
    ]
    fresh_rows = [{"cov": "current", "n": n_cur, "thru": mode_ep},
                  {"cov": "lagging", "n": n_lag, "thru": None}]
    pulse_table = _tl_render(fresh_rows, FRESH_COLS, total=2, page=1,
                             per=10, ns="fresh", bare=True)
    pulse_table = datize(pulse_table, "through", [mode_ep])

    bt = (cc.get("backtest") or {})
    pp = (cc.get("paper") or {})
    dp = (bt.get("deep") or {})
    sh = (bt.get("shallow") or {})
    SCORE_COLS = [
        {"key": "scope", "label": "scope", "cls": "", "kind": "text"},
        {"key": "prec", "label": "precision", "cls": "", "kind": "num", "fmt": "{:.0%}"},
        {"key": "hits", "label": "hits", "cls": "", "kind": "num"},
        {"key": "n", "label": "n", "cls": "", "kind": "num"},
    ]
    score_rows = []
    if bt.get("precision") is not None:
        score_rows.append({"scope": "cheap stayed cheap",
                           "prec": bt["precision"], "hits": bt.get("hits"), "n": bt.get("n")})
        if dp.get("precision") is not None:
            score_rows.append({"scope": "deep stayed cheap",
                               "prec": dp["precision"], "hits": dp.get("hits"), "n": dp.get("n")})
        if sh.get("precision") is not None:
            score_rows.append({"scope": "shallow stayed cheap",
                               "prec": sh["precision"], "hits": sh.get("hits"), "n": sh.get("n")})
    score_table = _tl_render(score_rows, SCORE_COLS, total=len(score_rows),
                             page=1, per=10, sort_key="prec", sort_dir=-1,
                             ns="score", bare=True)
    PAPER_COLS = [
        {"key": "open", "label": "open now", "cls": "", "kind": "num"},
        {"key": "due", "label": "first grades", "cls": "", "kind": "date"},
        {"key": "res", "label": "resolve days", "cls": "", "kind": "num"},
    ]
    due_ep = None
    if pp.get("n_pending"):
        ds = sorted((x.get("date") or "") for x in (cc.get("pending") or []) if x.get("date"))
        if ds:
            try:
                g = datetime.strptime(ds[0][:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                from datetime import timedelta as _t
                due_ep = int((g + _t(days=int(cc.get("resolve_days", 30)))).timestamp())
            except (ValueError, TypeError):
                due_ep = None
    paper_rows = [{"open": pp.get("n_pending", 0), "due": due_ep,
                   "res": cc.get("resolve_days", 30)}]
    paper_table = _tl_render(paper_rows, PAPER_COLS, total=1, page=1,
                             per=10, ns="paper", bare=True)
    paper_table = datize(paper_table, "first grades", [due_ep])
    if bt.get("precision") is not None:
        score_txt = (f"stayed cheap {bt['precision']:.0%} "
                     f"({bt['hits']}/{bt['n']})")
    else:
        score_txt = "scorecard building"

    cheap = [(r, p) for r, p in rows if r <= 0.8][:5]
    ALERT_COLS = [
        {"key": "i", "label": "#", "cls": "", "kind": "num"},
        {"key": "token", "label": "token", "cls": "", "kind": "text"},
        {"key": "deep", "label": "deep", "cls": "", "kind": "text"},
        {"key": "p_fees", "label": "P/Fees", "cls": "", "kind": "num", "fmt": "{:.2f}"},
        {"key": "ptvl", "label": "P/TVL", "cls": "", "kind": "num", "fmt": "{:.2f}"},
        {"key": "vs", "label": "vs cat", "cls": "", "kind": "pill",
         "fmt": "{:.1f}", "pill_key": "n"},
        {"key": "trend", "label": "trend", "cls": "", "kind": "text"},
        {"key": "thru", "label": "thru", "cls": "", "kind": "date"},
        {"key": "stale", "label": "stale", "cls": "", "kind": "text"},
    ]
    alert_rows = []
    for i, (r, p) in enumerate(cheap, 1):
        m = meds.get(p.get("category", ""), {})
        n = m.get("n")
        tw = TREND_WORDS.get(p.get("trend_dir"), "steady")
        is_stale = p.get('data_through') != mode_thru
        alert_rows.append({
            "i": i, "token": p['symbol'],
            "deep": ("\u2605" if r <= 0.5 else "\u2014"),
            "p_fees": p.get("p_fees"),
            "ptvl": _tvlmap.get(p.get("symbol")),
            "vs": r, "n": (n if (n is not None and n < 20) else None),
            "trend": tw,
            "thru": epoch_day(p.get("data_through", "?")),
            "stale": ("stale" if is_stale else "ok")})
    ahead = "<b>cheap-vs-peers alerts (\u22640.8\u00d7 group, \u2605 deep):</b>"
    if len(cheap) >= 5:
        alerts = ahead + _tl_render(alert_rows, ALERT_COLS, total=len(alert_rows),
                                    page=1, per=10, sort_key="vs", sort_dir=1,
                                    ns="alerts", bare=True)
        alerts = datize(alerts, "thru", [r["thru"] for r in alert_rows])
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
        {"key": "vol", "label": "vol 24h $M", "cls": "c-vol", "kind": "num",
         "fmt": "{:,.0f}", "ph": "\u2264 max"},
        {"key": "chg", "label": "24h %", "cls": "c-chg", "kind": "num", "fmt": "{:+.1f}"},
        {"key": "chg7", "label": "7d %", "cls": "c-chg7", "kind": "num", "fmt": "{:+.1f}"},
        {"key": "p7", "label": "P/Fees 7d", "cls": "c-7d", "kind": "num", "fmt": "{:.2f}"},
        {"key": "mom", "label": "momentum 7d/30d", "cls": "c-mom", "kind": "num", "fmt": "{:.2f}"},
        {"key": "prev", "label": "P/Revenue", "cls": "c-rev", "kind": "num", "fmt": "{:.2f}"},
        {"key": "ptvl", "label": "P/TVL", "cls": "c-ptvl", "kind": "num",
         "fmt": "{:.2f}", "ph": "\u2264 max"},
        {"key": "thru", "label": "through", "cls": "c-thru tl-nw", "kind": "date"},
        {"key": "stale", "label": "stale", "cls": "c-stale", "kind": "text", "ph": "stale?"},
    ]

    tl_rows = []
    for p in d["protocols"]:
        m = meds.get(p.get("category", ""), {})
        mp = m.get("median_p_fees")
        r = (p["p_fees"] / mp) if (p.get("p_fees") and mp) else None
        n = m.get("n")
        v24 = p.get("volume_24h_usd")
        tl_rows.append({
            "token": p["symbol"], "name": p["name"],
            "cat": p.get("category", ""),
            "mcap": (p["market_cap_usd"] / 1e9 if p.get("market_cap_usd") is not None else None),
            "p_fees": p.get("p_fees"), "vs": r,
            "n": (n if (n is not None and n < 20) else None),
            "trend": p.get("p_fees_trend"),
            "vol": (v24 / 1e6 if v24 is not None else None),
            "chg": p.get("price_change_24h_pct"),
            "chg7": p.get("price_change_7d_pct"),
            "p7": p.get("p_fees_7d"), "mom": p.get("fees_momentum"),
            "prev": p.get("p_revenue"),
            "ptvl": _tvlmap.get(p.get("symbol")),
            "thru": epoch_day(p.get("data_through")),
            "stale": ("stale" if p.get("data_through") != mode_thru else "ok"),
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
    tl_html = datize(tl_html, "through", [r["thru"] for r in tl_rows])

    GLOSS_COLS = [
        {"key": "k", "label": "column", "cls": "", "kind": "text"},
        {"key": "v", "label": "means", "cls": "", "kind": "text"},
    ]
    gloss_rows = [
        {"k": "vs cat", "v": "coin price / its category median (<1x = cheaper)"},
        {"k": "sales 6wk", "v": "weekly price-vs-sales, falling = getting cheaper"},
        {"k": "vol 24h $M", "v": "24h coin volume in millions of USD"},
        {"k": "24h %", "v": "daily price move"},
        {"k": "7d %", "v": "weekly price move"},
        {"k": "momentum", "v": "7d fees / 30d fees pace (>1 = accelerating)"},
        {"k": "P/Fees 7d", "v": "price / 7d-annualised fees"},
        {"k": "P/Revenue", "v": "price / annualised protocol revenue"},
        {"k": "P/TVL", "v": "price / locked value (free TVL " + str(_tvlcov) + "); lower = cheaper vs deposits"},
        {"k": "through", "v": "data date of that coin row"},
        {"k": "stale", "v": "ok = current, stale = lagging the mode date"},
        {"k": "deep", "v": "star = 0.5x group or cheaper"},
        {"k": "trend", "v": "6-week sales direction in words"},
        {"k": "source: DefiLlama", "v": "/summary/fees, free and keyless"},
        {"k": "source: CoinGecko", "v": "/coins/markets, public"},
    ]
    gloss_table = _tl_render(gloss_rows, GLOSS_COLS, total=len(gloss_rows),
                             page=1, per=20, ns="gloss", bare=True)

    html = open(os.path.join(ROOT, "page.html")).read()
    stale_cls = ' class="badge stale"' if stale else ' class="badge"'
    fresh_ts = f' data-ts="{as_ep}"' if as_ep is not None else ""
    html = html.replace('<span class="badge" id="fresh">…</span>',
                        f'<span{stale_cls} id="fresh"{fresh_ts}>{badge}</span>')
    html = html.replace('<small id="ver" style="font-weight:normal"></small>',
                        f'<small id="ver" style="font-weight:normal">v{commit}</small>')
    html = html.replace('<div id="verdict" class="cav" style="font-size:14px;margin:.4em 0">…</div>',
                        f'<div id="verdict" class="cav" style="font-size:14px;margin:.4em 0">{verdict}</div>')
    html = html.replace('<div id="pulse" class="cav">…</div>',
                        f'<div id="pulse" class="cav">{pulse}{pulse_table}</div>')
    html = html.replace('<div id="score" class="cav" style="font-size:14px;margin:.4em 0">…</div>',
                        f'<div id="score" class="cav" style="font-size:14px;margin:.4em 0">'
                        f'<b>scorecard</b>{score_table}{paper_table}</div>')
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
    print(f"inject ok: verdict={verdict!r} pulse={pulse!r} score={score_txt!r} alerts_n={len(cheap)}")


if __name__ == "__main__":
    main()
