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
    pulse = (f"Sampling {len(d['protocols'])} coins daily from 2 free feeds "
             f"(data through {d['protocols'][0].get('data_through', '?') if d['protocols'] else '?'}).")

    bt = (cc.get("backtest") or {})
    pp = (cc.get("paper") or {})
    if bt.get("precision") is not None:
        score = (f"Cheap-vs-group calls stayed cheap {bt['precision']:.0%} "
                 f"({bt['hits']}/{bt['n']} backtested)")
        score += f", {pp.get('n_pending', 0)} open now." if pp.get("n_pending") else "."
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
            lines.append(f"{i}. <b>{p['symbol']}</b> — P/Fees {p.get('p_fees', '—')}, "
                           f"{r:.1f}× {p.get('category')} median, {tw}, thru {p.get('data_through', '?')}{thin}")
        alerts = "<b>cheap-vs-peers alerts (≤0.8× group):</b><br>" + "<br>".join(lines)
    else:
        alerts = (f"<b>cheap-vs-peers alerts:</b> only {len(cheap)}/5 qualifiers ≤0.8× "
                  "(thin coverage — widening next).")

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
    open(os.path.join(OUT, "index.html"), "w").write(html)
    print(f"inject ok: verdict={verdict!r} pulse={pulse!r} score={score!r} alerts_n={len(cheap)}")


if __name__ == "__main__":
    main()
