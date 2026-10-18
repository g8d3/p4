#!/usr/bin/env python3
"""Build landing.html — one self-contained, deployable sales page.

  python3 build_landing.py

Sources are the same files we edit (landing.md, pricing.md, objections.md), so the
page cannot drift from the offer. No external requests, no analytics, no fonts.
NOTHING IS DEPLOYED by this script; it writes one file for a human to publish.

The contact line is a placeholder on purpose: we do not invent an address.
"""

from __future__ import annotations

from pathlib import Path
import re

import markdown

HERE = Path(__file__).parent
OUT = HERE / "landing.html"
ROI_JS = HERE / "roi.js"
CONTACT = "hello@focalis.cc"  # live Cloudflare Email Routing rule -> forwards to the owner (site primary; hola@ also routes)
REPORT_URL = "https://focalis.cc/tps/"
REPO_URL = "https://github.com/g8d3/transcript-tax"

# The calculator form. Its defaults must equal DEFAULTS in roi.js (the parity test
# checks that), and the model-class presets must equal the sweep classes in
# tools/roi.py.
CALC = """
  <section id="calc">
    <h2>Price it on your own numbers</h2>
    <p>The same arithmetic as <code>tools/roi.py --sweep</code> in the repo, running in
    your browser — the calculator makes no request of its own (on the hosted copy
    Cloudflare's page-view beacon is the only network call). If this page and the script ever
    disagree, our own test fails — so we would rather you check the numbers than trust
    the copy.</p>
    <form id="roiForm">
      <div class="grid">
        <label>Agent loops
          <input type="number" id="agents" value="10" min="1" step="1"></label>
        <label>Turns per loop per working day
          <input type="number" id="turns" value="100" min="1" step="1"></label>
        <label>Input tokens carried per turn
          <input type="number" id="inTok" value="40000" min="0" step="1000"></label>
        <label>Share of input served from cache (%)
          <input type="number" id="cacheHitPct" value="70" min="0" max="100" step="5"></label>
        <label>Model class
          <select id="klass">
            <option value="cheap" selected>cheap (DeepSeek-class)</option>
            <option value="mid">mid (Sonnet-class)</option>
            <option value="premium">premium (Opus-class)</option>
            <option value="custom">custom prices below</option>
          </select></label>
        <label>Operator time ($/h, 0 = do not price wall-clock)
          <input type="number" id="hourly" value="0" min="0" step="5"></label>
      </div>
      <label class="check"><input type="checkbox" id="warm">
        the loop keeps a process warm (it does not pay process boot every turn)</label>
      <details>
        <summary>Advanced — every value here is ours and is an assumption you should replace</summary>
        <div class="grid">
          <label>Output tokens per turn <input type="number" id="outTok" value="400" min="0" step="50"></label>
          <label>Working days per year <input type="number" id="days" value="250" min="1" step="10"></label>
          <label>Input $/1M tokens <input type="number" id="priceIn" value="0.27" min="0" step="0.01"></label>
          <label>Cached input $/1M <input type="number" id="priceCache" value="0.07" min="0" step="0.01"></label>
          <label>Output $/1M tokens <input type="number" id="priceOut" value="1.10" min="0" step="0.01"></label>
          <label>Steady-state floor per turn (s) <input type="number" id="floorS" value="3.0" min="0" step="0.1"></label>
          <label>Process boot per turn (s, measured 0.93) <input type="number" id="bootS" value="0.93" min="0" step="0.01"></label>
          <label>Share of turns that miss the cache (%) <input type="number" id="missRatePct" value="30" min="0" max="100" step="5"></label>
          <label>Extra seconds on a miss <input type="number" id="missPenaltyS" value="5" min="0" step="1"></label>
          <label>Share of turns that fail or return nothing (%) <input type="number" id="wastedPct" value="10" min="0" max="100" step="5"></label>
          <label>Input tokens the audit removes (%) <input type="number" id="cutInputPct" value="35" min="0" max="100" step="5"></label>
          <label>Wall the audit removes (%) <input type="number" id="cutWallPct" value="20" min="0" max="100" step="5"></label>
          <label>Audit fee to compare against ($) <input type="number" id="tier" value="1400" min="0" step="100"></label>
        </div>
      </details>
      <output id="roiOut" aria-live="polite"></output>
    </form>
  </section>
"""

CALC_JS = """
(function () {
  var R = window.TPS_ROI;
  var form = document.getElementById("roiForm");
  if (!R || !form) return;
  var out = document.getElementById("roiOut");
  var PRESETS = {
    cheap: { priceIn: 0.27, priceCache: 0.07, priceOut: 1.1 },
    mid: { priceIn: 3.0, priceCache: 0.3, priceOut: 15.0 },
    premium: { priceIn: 15.0, priceCache: 1.5, priceOut: 75.0 }
  };
  function val(id) { var e = document.getElementById(id); return e ? Number(e.value) : NaN; }
  function set(id, v) { var e = document.getElementById(id); if (e && e.value === "") e.value = v; }
  function read() {
    var o = {
      agents: val("agents"), turns: val("turns"), days: val("days"),
      inTok: val("inTok"), outTok: val("outTok"),
      cacheHit: val("cacheHitPct") / 100,
      priceIn: val("priceIn"), priceCache: val("priceCache"), priceOut: val("priceOut"),
      floorS: val("floorS"), bootS: val("bootS"),
      warm: document.getElementById("warm").checked,
      missRate: val("missRatePct") / 100, missPenaltyS: val("missPenaltyS"),
      wasted: val("wastedPct") / 100,
      cutInput: val("cutInputPct") / 100, cutWall: val("cutWallPct") / 100,
      hourly: val("hourly"), tier: val("tier")
    };
    var k = document.getElementById("klass").value;
    if (PRESETS[k]) { o.priceIn = PRESETS[k].priceIn; o.priceCache = PRESETS[k].priceCache; o.priceOut = PRESETS[k].priceOut; }
    return o;
  }
  function render() {
    var o = read();
    var r = R.computeROI(o);
    var p = r.params;
    var rows = [];
    rows.push(["Turns per year", R.num(r.turnsYear)]);
    rows.push(["Token bill", R.money(r.yearTokens) + "/year (" + R.money(r.perTurn) + " per turn)"]);
    rows.push(["Wall-clock on the tax", R.num(r.yearHours) + " h/year (" + r.wallPerTurn.toFixed(2) + " s per turn, before any work)"]);
    rows.push(["— boot", p.warm ? "warm loop: 0" : R.num(r.bootHours) + " h/year (" + p.bootS.toFixed(2) + " s x every turn)"]);
    rows.push(["— floor", R.num(r.floorHours) + " h/year (" + p.floorS.toFixed(1) + " s x every turn)"]);
    rows.push(["— cache miss", R.num(r.missHours) + " h/year (" + Math.round(p.missRate * 100) + "% miss, +" + p.missPenaltyS + " s each)"]);
    rows.push(["Burned on failed/empty turns", R.money(r.wasteTokens) + "/year"]);
    rows.push(["Token saving at " + Math.round(p.cutInput * 100) + "% input cut", R.money(r.inSaved) + "/year"]);
    rows.push(["Wall saving at " + Math.round(p.cutWall * 100) + "% wall cut", R.num(r.wallSaved) + " h/year"]);
    if (p.hourly > 0) rows.push(["That wall priced at " + R.money(p.hourly) + "/h", R.money(r.timeValue) + "/year"]);
    rows.push(["Total saving", R.money(r.saved) + "/year"]);
    rows.push(["Audit fee " + R.money(p.tier) + " — payback", isFinite(r.paybackDays) ? R.num(r.paybackDays) + " working days" : "never at these numbers"]);
    var v = R.verdict(r, p.tier);
    var html = '<table class="roi-table">';
    for (var i = 0; i < rows.length; i++) html += "<tr><th>" + rows[i][0] + "</th><td>" + rows[i][1] + "</td></tr>";
    html += '</table><p class="verdict ' + v.key + '">' + v.label + '.</p>';
    if (p.hourly === 0) html += '<p class="note">Token saving only. A cheap-model fleet with a small token line does not pay for an audit on tokens alone — put a price on operator time above to see the other half.</p>';
    out.innerHTML = html;
  }
  form.addEventListener("input", render);
  form.addEventListener("change", render);
  render();
})();
"""

CSS = """
:root { color-scheme: light dark; --fg: #14161a; --bg: #fff; --muted: #5b6270;
  --line: #e3e6ec; --accent: #1c5fd4; --card: #f7f8fa; }
@media (prefers-color-scheme: dark) { :root { --fg:#e8eaed; --bg:#101215; --muted:#9aa2b1;
  --line:#282c33; --accent:#79aaff; --card:#171a1f; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
header { border-bottom:1px solid var(--line); padding:1rem 1.2rem; position:sticky; top:0;
  background:color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter:blur(6px); }
header nav a { color:var(--muted); text-decoration:none; margin-right:1rem; font-size:.92rem; }
header nav a:hover { color:var(--accent); }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(16rem,1fr)); gap:.8rem 1.2rem; margin:1rem 0; }
.grid label, form label { display:flex; flex-direction:column; gap:.25rem; font-size:.9rem; color:var(--muted); }
.grid input, .grid select { padding:.6rem .55rem; min-height:2.75rem; border:1px solid var(--line); border-radius:.4rem;
  background:var(--bg); color:var(--fg); font:inherit; }
label.check { flex-direction:row; align-items:center; gap:.5rem; margin:.6rem 0; }
details { border:1px solid var(--line); border-radius:.5rem; padding:.6rem .8rem; margin:1rem 0; }
details summary { cursor:pointer; color:var(--muted); font-size:.9rem; }
.roi-table { width:100%; border-collapse:collapse; margin:1rem 0; }
.roi-table th { text-align:left; font-weight:500; color:var(--muted); padding:.4rem .6rem .4rem 0; width:55%; }
.roi-table td { text-align:right; padding:.4rem 0; font-variant-numeric:tabular-nums; }
.roi-table tr { border-bottom:1px solid var(--line); }
.verdict { font-weight:600; margin-top:.6rem; }
.verdict.pays { color:#1a7f37; } .verdict.marginal { color:#9a6700; } .verdict.no { color:#b42318; }
.note { color:var(--muted); font-size:.9rem; }
@media (prefers-color-scheme: dark) { .verdict.pays { color:#57d07a; } .verdict.marginal { color:#e3b341; } .verdict.no { color:#f97066; } }
main { max-width:52rem; margin:0 auto; padding:0 1.2rem 4rem; }
h1 { font-size:2.05rem; line-height:1.2; margin:2.2rem 0 .4rem; }
h2 { font-size:1.35rem; margin-top:2.8rem; border-top:1px solid var(--line); padding-top:1.4rem; }
h3 { font-size:1.1rem; margin-top:1.8rem; }
table { border-collapse:collapse; width:100%; margin:1.2rem 0; font-size:.93rem; display:block; overflow-x:auto; }
th,td { border:1px solid var(--line); padding:.45rem .6rem; text-align:left; }
th { background:var(--card); }
code,pre { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.9em; }
pre { background:var(--card); padding:.8rem; overflow-x:auto; border-radius:6px; }
blockquote { border-left:3px solid var(--line); margin:1.3rem 0; padding:.2rem 0 .2rem 1rem; color:var(--muted); }
ul { padding-left:1.2rem; }
.cta { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:1.2rem 1.3rem; margin:2rem 0; }
.cta a { color:var(--accent); font-weight:600; text-decoration:none; }
.banner { background:var(--card); border:1px dashed var(--line); color:var(--muted);
  font-size:.85rem; padding:.5rem .8rem; border-radius:6px; margin:1.2rem 0; }
footer { border-top:1px solid var(--line); color:var(--muted); font-size:.85rem;
  padding:1.4rem 1.2rem; max-width:52rem; margin:0 auto; }
"""


def section(path: str) -> str:
    text = (HERE / path).read_text()
    # drop the markdown H1: the page has its own header
    text = "\n".join(text.splitlines()[1:]) if text.startswith("# ") else text
    return markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])


def slug(title: str) -> str:
    keep = [c if c.isalnum() or c == " " else " " for c in title.lower()]
    return "-".join("".join(keep).split())


def add_heading_ids(html: str) -> tuple[str, list[str]]:
    """Give every h2 an id so in-page nav links actually resolve."""
    seen: list[str] = []

    def repl(m: re.Match) -> str:
        title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        sid = slug(title)
        if sid in seen or not sid:
            return m.group(0)
        seen.append(sid)
        return f'<h2 id="{sid}">{m.group(1)}</h2>'

    return re.sub(r"<h2>(.*?)</h2>", repl, html), seen


def main() -> None:
    ROI_JS_SRC = ROI_JS.read_text()
    landing, _ = add_heading_ids(section("landing.md"))
    pricing, _ = add_heading_ids(section("pricing.md"))
    faq, _ = add_heading_ids(section("objections.md"))
    cta = f"""
    <div class="cta">
      <p><strong>Start with one loop.</strong> Reply <code>TAX</code> or write to
      <a href="mailto:{CONTACT}">{CONTACT}</a> and we send the three questions we need.
      If the numbers do not show a tax worth cutting, you keep the data and we say so.</p>
    </div>"""
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Fleet Tax Audit — measure the tax, then cut it</title>
<meta name="description" content="A measured per-turn overhead tax on agent fleets: what it costs, how we find it, and what we cut.">
<meta property="og:type" content="website">
<meta property="og:title" content="Agent Fleet Tax Audit — measure the tax, then cut it">
<meta property="og:description" content="A measured per-turn overhead tax on agent fleets: what it costs, how we find it, and what we cut.">
<meta property="og:url" content="https://focalis.cc/audit/">
<meta name="twitter:card" content="summary">

<style>{CSS}</style></head>
<body>
<header><nav>
  <a href="#findings">The finding</a><a href="#what-we-do">What we do</a>
  <a href="#pricing">Pricing</a><a href="#calc">Calculator</a>
  <a href="#faq">Questions</a><a href="#start">Start</a>
</nav></header>
<main>
  <div class="banner">Published 2026-10-17. The full paper, the raw 65-run CSV and the
  analysis script are public: <a href="{REPORT_URL}">{REPORT_URL}</a> ·
  <a href="{REPO_URL}">repo (MIT / CC BY 4.0)</a>. We also publish the three
  mechanisms we retracted from our own pitch.</div>
  <section id="findings">{landing}</section>
  <section id="pricing">{pricing}</section>
  {CALC}
  <section id="faq">{faq}</section>
  <section id="start">{cta}</section>
</main>
<footer>Seller: Focalis S.A.S. (Bogotá, Colombia) · <a href="https://focalis.cc/company">Company</a> ·
<a href="https://focalis.cc/terms">Terms</a> · <a href="https://focalis.cc/privacy">Privacy</a> ·
<a href="https://focalis.cc/refunds">Refund policy</a>.<br>
No analytics of our own, no external fonts, no cookies. On the hosted copy Cloudflare adds
an email-obfuscation script and a cookieless page-view beacon; we keep no visitor data. Text CC BY 4.0.
Method and data: <code>bench.csv</code> + <code>analyze.py</code> + <code>tools/roi.py</code>.</footer>
<script>{ROI_JS_SRC}</script>
<script>{CALC_JS}</script>
</body></html>
"""
    OUT.write_text(html)
    print(f"wrote {OUT.name} ({len(html)/1024:.0f} KB) -- contact: {CONTACT}")


if __name__ == "__main__":
    main()
