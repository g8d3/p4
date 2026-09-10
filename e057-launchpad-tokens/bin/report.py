#!/usr/bin/env python3
"""Offline: data/ → output/report.md + output/stats.csv + output/site/index.html + charts.

One row per launchpad combining: token market (price/mcap/vol/social) + platform
activity (fees, revenue, buybacks, liquidity, DEX volume). Site is static and
self-contained → publishable anywhere (GitHub Pages, Cloudflare Pages, nginx).
"""
import csv, json, os, shutil, time
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE if os.path.exists(os.path.join(HERE, "config.json")) else os.path.dirname(HERE)
DATA, OUT = os.path.join(ROOT, "data"), os.path.join(ROOT, "output")
CHARTS = os.path.join(OUT, "charts")
SITE = os.path.join(OUT, "site")
os.makedirs(CHARTS, exist_ok=True)
os.makedirs(SITE, exist_ok=True)

GROUP_COLOR = {"memecoin-launchpad": "#e4572e", "platform-aligned": "#1789c9", "classic-launchpad": "#8d86c9"}
GROUP_LABEL = {"memecoin-launchpad": "Memecoin launchpad", "platform-aligned": "Platform-aligned", "classic-launchpad": "Classic (ICO-era)"}


def load(name):
    p = os.path.join(DATA, name)
    return json.load(open(p)) if os.path.exists(p) else None


def caps_series(coin_id):
    h = load(f"mcap__{coin_id}.json") or {}
    return [(ts / 1000, v) for ts, v in (h.get("market_caps") or []) if v]


def sec(ts):
    return ts / 1000 if ts > 1e12 else ts  # CG uses ms; llama uses seconds


def fee_stats(slugs):
    """Aggregate fees/revenue/holders over a list of DefiLlama slugs."""
    out = {"fees_1d": None, "fees_7d": None, "fees_30d": None, "fees_90d": None, "fees_365d": None,
           "rev_30d": None, "holders_30d": None, "growth_30v30": None, "daily": None}
    day = 86400
    now = time.time()
    fee_charts, rev_charts, hold_charts = [], [], []
    for slug in slugs:
        d = load(f"llama__{slug}.json") or {}
        for key, chart in (("dailyFees", fee_charts), ("dailyRevenue", rev_charts), ("dailyHoldersRevenue", hold_charts)):
            if d.get(key):
                chart.append(d[key])
    if not fee_charts:
        return None

    def window_sum(charts, lo, hi):
        return sum(v for ch in charts for t, v in ch if lo <= (now - sec(t)) < hi)

    out["fees_7d"] = window_sum(fee_charts, 0, 7 * day)
    out["fees_30d"] = window_sum(fee_charts, 0, 30 * day)
    out["fees_90d"] = window_sum(fee_charts, 0, 90 * day)
    out["fees_365d"] = window_sum(fee_charts, 0, 365 * day)
    out["rev_30d"] = window_sum(rev_charts, 0, 30 * day)
    out["holders_30d"] = window_sum(hold_charts, 0, 30 * day)
    prev30 = window_sum(fee_charts, 30 * day, 60 * day)
    out["growth_30v30"] = (out["fees_30d"] / prev30 - 1) if prev30 > 0 else None

    acc = {}
    for ch in fee_charts:
        for t, v in ch:
            acc[sec(t)] = acc.get(sec(t), 0) + v
    out["daily"] = sorted(acc.items())
    out["fees_1d"] = out["daily"][-1][1] if out["daily"] else 0
    return out


def plat_metrics(slugs):
    """TVL (liquidity) + DEX/aggregator volume from data/platform.json."""
    plat = load("platform.json") or {}
    out = {"tvl": None, "vol24h": None, "vol30d": None}
    t, v24, v30 = 0.0, 0.0, 0.0
    for s in slugs:
        m = plat.get(s) or {}
        t += m.get("tvl") or 0
        v24 += m.get("vol24h") or 0
        v30 += m.get("vol30d") or 0
    if t: out["tvl"] = t
    if v24: out["vol24h"] = v24
    if v30: out["vol30d"] = v30
    return out


def pct(a, b):
    return (a / b - 1) * 100 if (a and b) else None


def fmt(v, dec=1, dollar=True, na="—"):
    if v is None:
        return na
    sign = "$" if dollar else ""
    a = abs(v)
    if a >= 1e9:
        return f"{sign}{v/1e9:.{dec}f}B"
    if a >= 1e6:
        return f"{sign}{v/1e6:.{dec}f}M"
    if a >= 1e3:
        return f"{sign}{v/1e3:,.0f}k"
    return f"{sign}{v:,.0f}" if dollar else f"{sign}{v:.{dec}f}"


def fmt_price(v, na="—"):
    if v is None:
        return na
    if v >= 1000:
        return f"${v:,.0f}"
    if v >= 1:
        return f"${v:.2f}"
    if v >= 0.01:
        return f"${v:.4f}"
    return f"${v:.2e}"


def fmt_pct(v, na="—"):
    return na if v is None else f"{v:+.0f}%"


def fmt_int(v, na="—"):
    return na if v is None else f"{v:,}"


def build_rows():
    cfg = json.load(open(os.path.join(ROOT, "config.json")))
    markets = {m["id"]: m for m in load("markets.json") or []}
    rows = []
    for c in cfg["coins"]:
        cid = c["cg_id"]
        r = {"symbol": c["symbol"], "name": c["name"], "group": c["group"], "cg_id": cid}
        if cid:
            mk = markets.get(cid, {})
            cd = load(f"coin__{cid}.json") or {}
            md = cd.get("market_data", {})
            comm = cd.get("community_data", {}) or {}
            ser = caps_series(cid)
            r.update({
                "price": mk.get("current_price"), "mcap": mk.get("market_cap"),
                "rank": cd.get("market_cap_rank"),
                "vol24h_token": mk.get("total_volume"),
                "ath": md.get("ath", {}).get("usd"),
                "ath_date": (md.get("ath_date", {}).get("usd") or "")[:10],
                "ath_off": md.get("ath_change_percentage", {}).get("usd"),
                "tw": comm.get("twitter_followers"),
                "reddit": comm.get("reddit_subscribers"),
            })
            if ser:
                mcaps = [v for _, v in ser]
                times = [t for t, _ in ser]

                def chg_days(d):
                    cutoff = times[-1] - d * 86400
                    base = next((v for t, v in ser if t >= cutoff), mcaps[0])
                    return pct(mcaps[-1], base)
                r["chg_30d"], r["chg_90d"], r["chg_1y"] = chg_days(30), chg_days(90), pct(mcaps[-1], mcaps[0])
        fees = fee_stats(c["llama"])
        if fees:
            r.update({k: fees[k] for k in ("fees_1d", "fees_7d", "fees_30d", "fees_90d",
                                           "fees_365d", "rev_30d", "holders_30d", "growth_30v30")})
            annual = (fees["fees_30d"] or 0) * 12
            r["pf"] = (r.get("mcap") / annual) if r.get("mcap") and annual else None
        r["daily_fees"] = fees["daily"] if fees else None
        r.update(plat_metrics(c["llama"]))
        rows.append(r)
    return rows


# ---------------- charts ----------------

def make_charts(rows):
    plt.rcParams.update({"font.size": 11, "figure.facecolor": "#11141c", "axes.facecolor": "#11141c",
                         "axes.edgecolor": "#444", "axes.labelcolor": "#ddd", "text.color": "#ddd",
                         "xtick.color": "#aaa", "ytick.color": "#aaa", "grid.color": "#2a2f3a",
                         "legend.facecolor": "#11141c", "legend.edgecolor": "#444"})
    fee_rows = [r for r in rows if r.get("daily_fees")]

    def style(ax, title):
        ax.set_title(title, fontsize=13)
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8.5, ncol=2)

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(f"{CHARTS}/{name}")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=110)
    for r in rows:
        ser = caps_series(r["cg_id"]) if r["cg_id"] else None
        if not ser:
            continue
        ax.plot([datetime.fromtimestamp(t) for t, _ in ser], [v for _, v in ser],
                label=f"{r['symbol']} ({fmt(r.get('mcap'))})", color=GROUP_COLOR[r["group"]], lw=1.4, alpha=0.9)
    ax.set_yscale("log")
    style(ax, "Launchpad platform tokens — market cap, trailing 365d (log)")
    save(fig, "mcap_365d.png")

    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=110)
    for r in rows:
        ser = caps_series(r["cg_id"]) if r["cg_id"] else None
        if not ser:
            continue
        peak = max(v for _, v in ser)
        ax.plot([datetime.fromtimestamp(t) for t, _ in ser], [100 * v / peak for _, v in ser],
                label=r["symbol"], color=GROUP_COLOR[r["group"]], lw=1.3, alpha=0.9)
    style(ax, "Position within its own 365d range (100 = window high)")
    save(fig, "range_position_365d.png")

    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=110)
    for r in fee_rows:
        ch = r["daily_fees"]
        vals = [v for _, v in ch]
        roll = [sum(vals[max(0, i - 6):i + 1]) / len(vals[max(0, i - 6):i + 1]) for i in range(len(vals))]
        ax.plot([datetime.fromtimestamp(t) for t, _ in ch], roll, label=r["symbol"],
                color=GROUP_COLOR[r["group"]], lw=1.5, alpha=0.9)
    ax.set_yscale("log")
    style(ax, "Launchpad platform fees — 7d-rolling daily, trailing 365d (log)")
    save(fig, "fees_365d.png")

    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=110)
    for r in rows:
        ser = caps_series(r["cg_id"]) if r["cg_id"] else None
        if not ser:
            continue
        base = ser[0][1]
        ax.plot([datetime.fromtimestamp(t) for t, _ in ser], [100 * v / base for _, v in ser],
                label=r["symbol"], color=GROUP_COLOR[r["group"]], lw=1.3, alpha=0.9)
    style(ax, "Growth comparison — mcap indexed to 100 at window start (365d ago)")
    save(fig, "mcap_indexed_365d.png")

    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=110)
    for r in fee_rows:
        ch = r["daily_fees"]
        ts = [datetime.fromtimestamp(t) for t, _ in ch]
        cum, s = [], 0.0
        for _, v in ch:
            s += v
            cum.append(s)
        ax.plot(ts, cum, label=f"{r['symbol']} (365d total {fmt(s)})", color=GROUP_COLOR[r["group"]], lw=1.6, alpha=0.9)
    style(ax, "Cumulative platform fees per launchpad — trailing 365d")
    save(fig, "fees_cum_365d.png")


# ---------------- report.md ----------------

NOTES = {
    "PUMP": "Fees = pump.fun launch fees + PumpSwap (own AMM) trading fees. Treasury buybacks of PUMP are ongoing.",
    "VIRTUAL": "Agent-launch platform; protocol revenue with buyback/burn of VIRTUAL announced 2025.",
    "CLANKER": "Farcaster/Base token launcher; fees from per-deploy + trading.",
    "BOOP": "boop.fun Solana/BSC launchpad; fee share to BOOP stakers.",
    "RAY": "LaunchLab (launchpad, fees→RAY buybacks) + Raydium AMM (LP-dominated fees; small protocol cut).",
    "JUP": "Aggregator + perps + Studio; 50% of protocol fees routed to JUP buybacks (announced policy).",
    "BONK": "bonk.fun/LetsBonk fees; a fixed share buys & burns BONK. Token benefits indirectly (no direct claim).",
    "LAUNCHCOIN": "Believe app fees; platform activity ~0 → effectively dead revenue.",
    "FOUR.MEME": "BNB-chain pump.fun clone; fees tracked but NO token exists yet (fee-only row).",
}


def md_table(headers, rows_md):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(cells) + " |" for cells in rows_md]
    return "\n".join(out)


def write_report(rows, now):
    rep = [f"# Launchpad platform tokens — stats for {now.date()}\n",
           "Data: CoinGecko (price/mcap/volume/social) + DefiLlama (fees, revenue, liquidity/TVL, DEX volume). "
           f"Generated {now.isoformat(timespec='seconds')}.\n"]

    master = []
    for r in rows:
        master.append([
            f"**{r['symbol']}** {r['name']}",
            fmt_price(r.get("price")), fmt(r.get("mcap")), fmt_pct(r.get("ath_off")),
            fmt(r.get("vol24h_token")), fmt(r.get("fees_30d")),
            fmt_pct(r.get("growth_30v30") and r["growth_30v30"] * 100),
            fmt(r.get("rev_30d")), fmt(r.get("holders_30d")),
            fmt(r.get("tvl")), fmt(r.get("vol24h")),
            fmt(r.get("pf"), dec=1, dollar=False),
        ])
    rep.append("\n## Master table — one row per launchpad\n")
    rep.append(md_table(
        ["Launchpad", "Price", "MCap", "vs ATH", "Token vol 24h", "Fees 30d", "Fee growth 30v30",
         "Rev 30d", "Holders rev 30d", "Liquidity (TVL)", "Platform vol 24h", "P/F"], master))
    rep.append("\n\\* RAY/JUP platform volume + TVL are gross AMM/aggregator/perp figures — most flows belong to LPs/users; the protocol cut is `Rev`.\n")

    by_group = {}
    for r in rows:
        by_group.setdefault(r["group"], []).append(r)

    for g, title in (("memecoin-launchpad", "Memecoin launchpads"),
                     ("platform-aligned", "Platform-aligned (exchange/launchpad rails)"),
                     ("classic-launchpad", "Classic ICO-era launchpads (comparison)")):
        grp = by_group.get(g, [])
        rep.append(f"\n## {title}\n")
        rep.append(md_table(["Token", "Price", "MCap", "30d", "90d", "1y", "ATH mcap→date", "vs ATH", "P/F"],
                            [[f"**{r['symbol']}** {r['name']}", fmt_price(r.get("price")), fmt(r.get("mcap")),
                              fmt_pct(r.get("chg_30d")), fmt_pct(r.get("chg_90d")), fmt_pct(r.get("chg_1y")),
                              (f"{fmt_price(r['ath'])}→{r['ath_date']}" if r.get("ath") else "—"),
                              fmt_pct(r.get("ath_off")),
                              fmt(r.get("pf"), dec=1, dollar=False)] for r in grp]))
        fee_rows = [r for r in grp if r.get("fees_30d") is not None]
        if fee_rows:
            rep.append("\n" + md_table(["Platform", "Fees 1d", "7d", "30d", "90d", "365d", "Growth 30v30", "Rev 30d", "Holders 30d", "Liquidity", "Plat. vol 24h"],
                                       [[f"**{r['symbol']}**", fmt(r.get("fees_1d")), fmt(r.get("fees_7d")), fmt(r.get("fees_30d")),
                                         fmt(r.get("fees_90d")), fmt(r.get("fees_365d")),
                                         fmt_pct(r.get("growth_30v30") and r["growth_30v30"] * 100),
                                         fmt(r.get("rev_30d")), fmt(r.get("holders_30d")), fmt(r.get("tvl")), fmt(r.get("vol24h"))]
                                        for r in fee_rows]))

    rep.append("\n## Charts\n")
    rep.append("Time series per token:\n\n![mcap](charts/mcap_365d.png)\n\n![range](charts/range_position_365d.png)\n\n![fees](charts/fees_365d.png)")
    rep.append("\nCross-launchpad comparison:\n\n![indexed](charts/mcap_indexed_365d.png)\n\n![cumfees](charts/fees_cum_365d.png)")

    rep.append("\n## Per-token context (mechanics, not advice)\n")
    for r in rows:
        if r["symbol"] in NOTES:
            extra = f" Fees 30d {fmt(r.get('fees_30d'))}, growth 30v30 {fmt_pct(r.get('growth_30v30') and r['growth_30v30']*100)}." if r.get("fees_30d") else ""
            rep.append(f"- **{r['symbol']}** — {NOTES[r['symbol']]}{extra}")

    frontier = load("pumpfun_frontier.json")
    rep.append("\n## Coverage gaps\n")
    rep.append("- **Tokens created**: no free aggregate API for per-launchpad creation counts. pump.fun frontier signal: newest coin minted "
               + (f"{datetime.fromtimestamp(frontier['newest_created'], tz=timezone.utc):%Y-%m-%d %H:%M} UTC" if frontier else "n/a")
               + " (sampled on every refresh — rate accumulates in data/).")
    rep.append("- **Social volume**: no free source survives (CoinGecko community_data is paid-only now; X syndication + Reddit public JSON blocked). Needs LunarCrush/X API once monetized — table columns reserved.")
    rep.append("- **boot.fun (BOOT), belive.fun (BEL)**: not listed on CoinGecko/DefiLlama → no reliable history.")
    rep.append("- **DAO Maker / Polkastarter / Seedify**: fee flows not tracked; token price only. Structurally declining (ICO-era).")
    rep.append("- History window is 365d (CoinGecko public tier); all-time ATH from per-coin metadata.\n")

    with open(f"{OUT}/report.md", "w") as f:
        f.write("\n".join(rep))


# ---------------- site ----------------

def write_site(rows, now):
    if os.path.isdir(f"{SITE}/charts"):
        shutil.rmtree(f"{SITE}/charts")
    shutil.copytree(CHARTS, f"{SITE}/charts")

    def tr(cells, tag="td"):
        return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"

    master_head = ["Launchpad", "Price", "MCap", "vs ATH", "Token vol 24h", "Fees 30d", "Fee growth 30v30",
                   "Rev 30d", "Holders rev 30d", "Liquidity (TVL)", "Platform vol 24h", "Twitter", "P/F"]
    master_rows = []
    for r in rows:
        cls = GROUP_COLOR[r["group"]].replace("#", "g-")
        master_rows.append(f"<tr class='{cls}'><td><b>{r['symbol']}</b><br><span class='sub'>{r['name']}</span></td>"
                           + "".join(f"<td>{c}</td>" for c in [
                               fmt_price(r.get("price")), fmt(r.get("mcap")), fmt_pct(r.get("ath_off")),
                               fmt(r.get("vol24h_token")), fmt(r.get("fees_30d")),
                               fmt_pct(r.get("growth_30v30") and r["growth_30v30"] * 100),
                               fmt(r.get("rev_30d")), fmt(r.get("holders_30d")), fmt(r.get("tvl")),
                               fmt(r.get("vol24h")), fmt(r.get("pf"), dec=1, dollar=False)]) + "</tr>")

    sections = ""
    for g in ("memecoin-launchpad", "platform-aligned", "classic-launchpad"):
        grp = [r for r in rows if r["group"] == g]
        trs = "".join(tr([f"<b>{r['symbol']}</b> {r['name']}", fmt_price(r.get("price")), fmt(r.get("mcap")),
                          fmt_pct(r.get("chg_30d")), fmt_pct(r.get("chg_90d")), fmt_pct(r.get("chg_1y")),
                          (f"{fmt_price(r['ath'])}→{r['ath_date']}" if r.get("ath") else "—"),
                          fmt_pct(r.get("ath_off")),
                          fmt(r.get("pf"), dec=1, dollar=False)]) for r in grp)
        sections += f"<h2>{GROUP_LABEL[g]}</h2><div class='scroll'><table>" + tr(
            ["Token", "Price", "MCap", "30d", "90d", "1y", "ATH mcap→date", "vs ATH", "P/F"], "th") + trs + "</table></div>"

    frontier = load("pumpfun_frontier.json")
    frontier_line = (f"Newest pump.fun token minted {datetime.fromtimestamp(frontier['newest_created'], tz=timezone.utc):%Y-%m-%d %H:%M} UTC"
                     if frontier else "pump.fun creation frontier: n/a")

    SORT_JS = """
    document.querySelectorAll('th').forEach(th=>th.addEventListener('click',()=>{
 const tb=th.closest('table').querySelector('tbody'),i=[...th.parentNode.children].indexOf(th);
 [...tb.rows].sort((a,b)=>{const x=a.cells[i].innerText.replace(/[$,%+,]/g,''),y=b.cells[i].innerText.replace(/[$,%+,]/g,'');
 const nx=parseFloat(x),ny=parseFloat(y);const c=(isNaN(nx)||isNaN(ny))?x.localeCompare(y):nx-ny;return th.asc?-c:c;})
 .forEach(r=>tb.appendChild(r));th.asc=!th.asc;}));
    """

    html = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Launchpad Radar — launchpad tokens: price, fees, liquidity, social</title>
<meta name="description" content="Auto-updating stats for launchpad platform tokens (PUMP, RAY, JUP, VIRTUAL, CLANKER, BONK…): market cap, platform fees, revenue, buybacks, liquidity, volume and social reach.">
<style>
:root{{color-scheme:dark}}
body{{background:#11141c;color:#ddd;font:14px/1.45 system-ui,-apple-system,sans-serif;margin:0;padding:1rem;max-width:1200px;margin-inline:auto}}
h1{{font-size:1.5rem;margin:.2em 0}} h2{{font-size:1.1rem;margin:1.6em 0 .4em;color:#fff}}
.sub{{color:#888;font-size:.78em}}
.updated{{color:#888;font-size:.85rem;margin-bottom:1rem}}
.scroll{{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid #2a2f3a;border-radius:8px}}
table{{border-collapse:collapse;width:100%;font-size:.82rem;white-space:nowrap}}
th,td{{padding:.45rem .6rem;border-bottom:1px solid #2a2f3a;text-align:right}}
th:first-child,td:first-child{{text-align:left;position:sticky;left:0;background:#11141c}}
th{{color:#9ab;cursor:pointer;user-select:none;background:#151926;position:sticky;top:0}}
tr.g-e4572e td:first-child{{border-left:3px solid #e4572e}} tr.g-1789c9 td:first-child{{border-left:3px solid #1789c9}} tr.g-8d86c9 td:first-child{{border-left:3px solid #8d86c9}}
tr:hover td{{background:#1a1f2e}}
img{{max-width:100%;border-radius:8px;border:1px solid #2a2f3a;margin:.4rem 0}}
.note{{color:#888;font-size:.8rem}}
.legend span{{display:inline-block;padding:.15rem .5rem;margin-right:.5rem;border-radius:4px;font-size:.75rem}}
footer{{margin:2rem 0;color:#666;font-size:.78rem}}
</style></head><body>
<h1>🚀 Launchpad Radar</h1>
<p class="updated">Updated {now:%Y-%m-%d %H:%M} UTC · {frontier_line}</p>
<p class="legend"><span style="background:#e4572e">memecoin launchpad</span><span style="background:#1789c9">platform-aligned</span><span style="background:#8d86c9">classic</span></p>
<h2>Master table — one row per launchpad</h2>
<div class="scroll"><table id="master">
<thead>{tr(master_head, "th")}</thead><tbody>{''.join(master_rows)}</tbody></table></div>
<p class="note">RAY/JUP platform volume + liquidity are gross AMM/aggregator/perp figures — most flows belong to LPs/users; the protocol cut is <i>Rev 30d</i>. P/F = mcap ÷ annualized (30d×12) fees. Click a column header to sort.</p>
{sections}
<h2>Charts</h2>
<img src="charts/mcap_indexed_365d.png" alt="growth comparison">
<img src="charts/fees_cum_365d.png" alt="cumulative fees">
<img src="charts/mcap_365d.png" alt="market cap">
<img src="charts/fees_365d.png" alt="daily fees">
<img src="charts/range_position_365d.png" alt="range position">
<footer>Data: CoinGecko + DefiLlama · rebuilt automatically {now:%Y-%m-%d %H:%M} UTC · not financial advice</footer>
<script>{SORT_JS}</script>
</body></html>"""
    with open(f"{SITE}/index.html", "w") as f:
        f.write(html)


def main():
    now = datetime.now(timezone.utc)
    rows = build_rows()
    make_charts(rows)

    cols = ["symbol", "group", "price", "mcap", "vol24h_token", "chg_30d", "chg_90d", "chg_1y",
            "ath", "ath_date", "ath_off", "tw", "reddit",
            "fees_1d", "fees_7d", "fees_30d", "fees_90d", "fees_365d", "rev_30d", "holders_30d",
            "growth_30v30", "tvl", "vol24h", "vol30d", "pf"]
    with open(f"{OUT}/stats.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    write_report(rows, now)
    write_site(rows, now)

    print(f"report → {OUT}/report.md\nsite   → {SITE}/index.html")
    for r in rows:
        print(f"  {r['symbol']:10s} mcap={fmt(r.get('mcap')):>9s} fees30d={fmt(r.get('fees_30d')):>8s} "
              f"liq={fmt(r.get('tvl')):>9s} vol24h={fmt(r.get('vol24h')):>9s} tw={fmt_int(r.get('tw'), '-'):>10s} "
              f"P/F={fmt(r.get('pf'), dec=1, dollar=False) if r.get('pf') else '—'}")


if __name__ == "__main__":
    main()
