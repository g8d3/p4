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

    meds = d.get("category_medians", {})
    rows = []
    for p in d["protocols"]:
        m = meds.get(p.get("category", ""), {})
        mp = m.get("median_p_fees")
        if p.get("p_fees") and mp:
            rows.append((p["p_fees"] / mp, p))
    rows.sort(key=lambda t: t[0])
    if rows:
        r, p = rows[0]
        tw = TREND_WORDS.get(p.get("trend_dir"), "steady")
        verdict = f"Cheapest vs its group: {p['symbol']} at {r:.1f}x {p.get('category')} median, {tw}."
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
    if len(thrus) > 1 and thrus[0] != thrus[-1]:
        thru_txt = f"data mixed {thrus[0]}\u2192{thrus[-1]}"
    else:
        thru_txt = f"data through {(thrus[0] if thrus else '?')}"
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
    if len(cheap) >= 5:
        lines = []
        for i, (r, p) in enumerate(cheap, 1):
            m = meds.get(p.get("category", ""), {})
            n = m.get("n")
            thin = f' <span class="thin">thin n={n}</span>' if (n is not None and n < 20) else ""
            tw = TREND_WORDS.get(p.get("trend_dir"), "steady")
            star = "★ " if r <= 0.5 else ""
            lines.append(f"{i}. {star}<b>{p['symbol']}</b> — P/Fees {p.get('p_fees', '—')}, "
                           f"{r:.1f}× {p.get('category')} median, {tw}, thru {p.get('data_through', '?')}{thin}")
        head = ("<b>cheap-vs-peers alerts (≤0.8× group, ★≤0.5× deep):</b>"
                if any(r <= 0.5 for r, _ in cheap) else
                "<b>cheap-vs-peers alerts (≤0.8× group):</b>")
        alerts = head + "<br>" + "<br>".join(lines)
    else:
        alerts = (f"<b>cheap-vs-peers alerts:</b> only {len(cheap)}/5 qualifiers ≤0.8× "
                  "(thin coverage — widening next).")

    PER = 10
    by_fee = sorted(d["protocols"],
                    key=lambda p: (p.get("p_fees") is None, p.get("p_fees") or 0))
    total, pages = len(by_fee), max(1, (len(by_fee) + PER - 1) // PER)

    def _fmt_vol(v):
        if v is None:
            return "\u2014"
        if v >= 1e9:
            return f"{v / 1e9:.1f}B"
        if v >= 1e6:
            return f"{round(v / 1e6)}M"
        return f"{round(v / 1e3)}k"

    def _pct(v):
        if v is None:
            return "\u2014"
        return f"{'+' if v >= 0 else ''}{v:.1f}%"

    thead = ("<thead><tr><th>token</th><th class=\"c-name\">name</th>"
             "<th class=\"c-cat\">cat</th><th class=\"c-mcap\">mcap $B</th>"
             "<th class=\"c-pf\">P/Fees 30d</th><th class=\"c-vs\">vs cat</th>"
             "<th class=\"c-tr\">sales 6wk</th><th class=\"c-vol\">vol 24h</th>"
             "<th class=\"c-chg\">24h %</th><th class=\"c-chg7\">7d %</th>"
             "<th class=\"c-7d\">P/Fees 7d</th>"
             "<th class=\"c-mom\">momentum 7d/30d</th>"
             "<th class=\"c-rev\">P/Revenue</th>"
             "<th class=\"c-thru\">through</th></tr></thead><tbody>")
    ssr_rows = []
    for p in by_fee[:PER]:
        m = meds.get(p.get("category", ""), {})
        mp = m.get("median_p_fees")
        r = (p["p_fees"] / mp) if (p.get("p_fees") and mp) else None
        thin = (f' <span class="thin">thin n={m.get("n")}</span>'
                if m.get("n") is not None and m["n"] < 20 else "")
        vs = (f"{r:.1f}{thin}" if r is not None else "\u2014")
        mcap = "\u2014" if p.get("market_cap_usd") is None else f"{p['market_cap_usd'] / 1e9:.1f}"
        mom = "\u2014" if p.get("fees_momentum") is None else f"{p['fees_momentum']:.2f}\u00d7"
        ssr_rows.append(
            f"<tr><td>{p['symbol']}</td><td class=\"c-name\">{p['name']}</td>"
            f"<td class=\"c-cat\">{p.get('category', '')}</td>"
            f"<td class=\"c-mcap\">{mcap}</td>"
            f"<td class=\"c-pf\">{p.get('p_fees', '\u2014')}</td>"
            f"<td class=\"c-vs\">{vs}</td>"
            f"<td class=\"c-tr\">{p.get('trend_spark') or '\u2014'}</td>"
            f"<td class=\"c-vol\">{_fmt_vol(p.get('volume_24h_usd'))}</td>"
            f"<td class=\"c-chg\">{_pct(p.get('price_change_24h_pct'))}</td>"
            f"<td class=\"c-chg7\">{_pct(p.get('price_change_7d_pct'))}</td>"
            f"<td class=\"c-7d\">{p.get('p_fees_7d', '\u2014')}</td>"
            f"<td class=\"c-mom\">{mom}</td>"
            f"<td class=\"c-rev\">{p.get('p_revenue', '\u2014')}</td>"
            f"<td class=\"c-thru\">{p.get('data_through', '?')}</td></tr>")
    ssr_table = f'<table id="t">{thead}' + "".join(ssr_rows) + "</tbody></table>"
    ssr_pager = (f'Page 1/{pages} \u00b7 {total} rows \u00b7 {PER} per page '
                 f'<button onclick="chgPage(-1)">\u2190 Prev</button> '
                 f'<button onclick="chgPage(1)">Next \u2192</button>')

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
                        f'<div id="score" class="cav" style="font-size:14px;margin:.4em 0">{score}</div>')
    html = html.replace('<div id="alerts" class="cav" style="font-size:13px;margin:.4em 0">…</div>',
                        f'<div id="alerts" class="cav" style="font-size:13px;margin:.4em 0">{alerts}</div>')
    html = html.replace('<summary id="metasum">…</summary>',
                        f'<summary id="metasum">{len(d["protocols"])} coins priced vs sales — tap for what the columns mean.</summary>')
    html = html.replace('<table id="t"></table>', ssr_table)
    html = html.replace('<div id="pager" class="cav">…</div>',
                        f'<div id="pager" class="cav">{ssr_pager}</div>')
    open(os.path.join(OUT, "index.html"), "w").write(html)
    print(f"inject ok: verdict={verdict!r} pulse={pulse!r} score={score!r} alerts_n={len(cheap)}")


if __name__ == "__main__":
    main()
