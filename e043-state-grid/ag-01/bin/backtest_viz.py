#!/usr/bin/env python3
"""e043 — educational backtest visualizer.

Reads the outputs of sim.py / run_grid.py (metrics.json, equity_curve.csv,
fills_report.csv) plus the OHLCV data file, and produces a self-contained,
offline, mobile-first HTML page that explains the backtest to a beginner:

  - Equity curve, price + fills, and a trade-by-trade PnL chart with the
    RUNNING profit factor (so "does PF change per trade?" is visible).
  - A plain-language Profit Factor explainer (whole-backtest, $-based ratio,
    why it ignores compounding) with a tiny interactive calculator.
  - A metric glossary in simple words.
  - An auto verdict line ("this config makes money / loses after fees").

Run:
  python3 ag-01/bin/backtest_viz.py --data <ohlcv.csv> \
      --dir output/viz_1h --title "1h grid, flatten threshold 10k" --out output/viz.html
"""

import argparse, json, math, os
import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# Fill normalization + FIFO lot ledger (net-of-fees per-trade PnL)
# --------------------------------------------------------------------------- #
def normalize_fills(path):
    """Accept sim.py (bar,side,action,price,notional,fee) and run_grid.py
    (bar,side,px,notional,fee,kind) formats → (bar, side_sign, price, notional,
    fee, kind)."""
    rows = []
    df = pd.read_csv(path)
    cols = list(df.columns)
    for _, r in df.iterrows():
        bar = int(r["bar"])
        side = r.get("side")
        action = str(r.get("action", ""))
        if isinstance(side, str):
            side_sign = 1 if side.upper().startswith("B") else -1
        else:
            side_sign = 1 if float(side) > 0 else -1
        # sim.py: a CLOSE fill carries the POSITION side (+1 long). The actual
        # sell direction is the opposite.
        if action == "CLOSE":
            side_sign = -side_sign
        price = float(r.get("price", r.get("px")))
        notional = float(r["notional"])
        fee = float(r.get("fee", 0.0) or 0.0)
        kind = str(r.get("kind", "TAKE"))
        if action == "CLOSE":
            kind = "TAKE"
        rows.append(dict(bar=bar, side=side_sign, price=price, notional=notional,
                         fee=fee, kind=kind))
    rows.sort(key=lambda x: x["bar"])
    return rows


def reconstruct_trades(fills):
    """Return per-trade records with NET pnl (fees included) via a FIFO lot
    ledger, plus running profit factor stats."""
    lots = []           # FIFO of open inventory: {side, qty, px, fee}
    trades = []
    for f in fills:
        qty = f["notional"] / f["price"]
        if f["side"] > 0:                       # buy / open long
            lots.append(dict(side=1, qty=qty, px=f["price"], fee=f["fee"]))
        else:                                   # sell / open short
            lots.append(dict(side=-1, qty=qty, px=f["price"], fee=f["fee"]))
        # reduce against opposite-sign lots FIFO
        need = qty
        while need > 1e-9 and lots:
            l = lots[0]
            opp = -l["side"]
            if opp != f["side"]:
                break
            take = min(need, l["qty"])
            pnl = -(f["price"] - l["px"]) * take * f["side"]  # + when favorable
            # allocate fees: entry fee share + exit fee share
            fee_in = l["fee"] * (take / l["qty"])
            fee_out = f["fee"] * (take / qty)
            net = pnl - fee_in - fee_out
            trades.append(dict(bar=f["bar"], kind=f["kind"],
                               closed_qty=round(take, 8),
                               entry_px=round(l["px"], 2),
                               exit_px=round(f["price"], 2),
                               pnl=round(net, 2),
                               pnl_pct=round(net / (take * l["px"]) * 100, 3)))
            l["qty"] -= take
            l["fee"] -= fee_in
            if l["qty"] <= 1e-9:
                lots.pop(0)
            need -= take
        if need > 1e-9:
            # leftover reduction against late-shorts: rare; keep it simple
            pass
    # running profit factor
    wins = losses = 0.0
    run_pf = []
    for t in trades:
        if t["pnl"] > 0: wins += t["pnl"]
        else: losses -= t["pnl"]
        run_pf.append(round((wins / losses) if losses > 0 else (float("inf") if wins > 0 else 1.0), 3))
    gross_win = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = gross_win / gross_loss if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    # percentage-based PF (the same trades measured as % of their notional)
    pwin = sum(t["pnl_pct"] for t in trades if t["pnl"] > 0)
    ploss = -sum(t["pnl_pct"] for t in trades if t["pnl"] < 0)
    pf_pct = pwin / ploss if ploss > 0 else (float("inf") if pwin > 0 else 0.0)
    return trades, dict(pf=pf, pf_pct=pf_pct, gross_win=round(gross_win, 2),
                        gross_loss=round(gross_loss, 2), n_trades=len(trades),
                        n_wins=sum(1 for t in trades if t["pnl"] > 0),
                        n_losses=sum(1 for t in trades if t["pnl"] < 0))


# --------------------------------------------------------------------------- #
# HTML template
# --------------------------------------------------------------------------- #
GLOSSARY = [
    ("Return %", "How much the 100,000 start money grew or shrank at the end, in percent. Growth compounds here, so it already includes everything that happened in between."),
    ("Profit factor", "Gross dollars won ÷ gross dollars lost, for ALL trades of this test. 1.0 = breakeven. It does NOT know about order, time, or compounding — that's why it is read next to the other metrics."),
    ("Max drawdown %", "The worst dip from a high point to a low point of the account, in percent. It answers: \"how painful was the worst moment?\" A -50% dip needs +100% to recover."),
    ("Sharpe", "Average return per unit of risk (how wobbly the equity was). Above ~1 is decent; negative means the ride was bumpy and losing. Not a guarantee — history only."),
    ("Win rate %", "Share of trades that ended in profit. A low win rate is NOT automatically bad: big wins can beat many small losses. Always read it next to Profit factor."),
    ("Commissions", "Money paid to the exchange for every fill, summed (maker/taker fees). Grids trade a lot, so fees are often the difference between profit and loss."),
    ("Fills", "How many times orders actually got filled (bought or sold). More fills = more fees; fewer fills = the grid may not be doing much."),
    ("Regime flips", "How many times the filter switched between 'range' and 'trend'. Each switch can cost a flatten fee, so a nervous filter bleeds money."),
    ("Exposure time", "How much of the time the account actually held a position (as % of starting capital). Low = the strategy sits in cash most of the time."),
]

PF_HTML = """
<div class="card">
  <h2>📖 Profit factor, explained for a beginner</h2>
  <p><b>Profit factor = money won ÷ money lost</b> (in dollars / USDT), counting
  <b>every</b> trade of the <b>whole test</b> — not each single trade.</p>
  <table class="mini">
    <tr><td>Example trades</td><td>Won</td><td>Lost</td></tr>
    <tr><td>Trade 1: +$40</td><td>$40</td><td>—</td></tr>
    <tr><td>Trade 2: -$10</td><td>—</td><td>$10</td></tr>
    <tr><td>Trade 3: +$30</td><td>$30</td><td>—</td></tr>
    <tr><td><b>Totals</b></td><td><b>$70</b></td><td><b>$10</b></td></tr>
  </table>
  <p><b>Profit factor = 70 / 10 = 7.0</b> — you won 7 dollars for every 1 you lost.</p>
  <ul>
    <li><b>Is it per backtest or per trade?</b> One number PER TEST. It changes
        only when you change the strategy parameters and run again. The chart
        below shows how it <i>builds up</i> trade by trade to that final number.</li>
    <li><b>Dollars or percentages?</b> <b>Dollars.</b> Because it's a ratio
        (won ÷ lost, same currency), it has no units and it ignores the size of
        the account: if every trade doubles, the ratio stays the same. A
        percentage version would change with account size — the page shows both
        (Profit factor vs %-based) so you can see they differ.</li>
    <li><b>Does it care that the account grows or shrinks?</b> <b>No — on
        purpose.</b> It just adds dollars. It forgets the order of trades,
        compounding, and time. That's why it's NEVER read alone: Return % knows
        compounding, Sharpe knows time, Max drawdown knows the risky path.</li>
  </ul>
  <div class="calc">
    <h3>Try it yourself</h3>
    <label>Money won: <input type="number" id="cw" value="70" step="1"></label>
    <label>Money lost: <input type="number" id="cl" value="10" step="1"></label>
    <p>Profit factor = <span id="cpf" class="big">7.00</span></p>
  </div>
</div>
"""


def build_html(title, m, trades, pf, eq, fills, closes):
    n = len(trades)
    wins = pf["n_wins"]
    verdict = "✅ This config made money after fees." if (m.get("total_return_pct", 0) > 0 and pf["pf"] >= 1.02) else \
              ("🟡 Breakeven — it roughly paid its own fees, nothing more." if abs(m.get("total_return_pct", 0)) < 1.5 else
               "❌ Losing after fees. Study the equity curve: is it a slow bleed (fees/geometry) or one big drop (trend)?")
    max_rows = 400
    shown = trades if len(trades) <= max_rows else trades[: max_rows // 2] + trades[-max_rows // 2:]
    cap_note = f"<div class='legend'>Showing {len(shown)} of {len(trades)} trades (trimmed for mobile).</div>" if len(trades) > max_rows else ""
    trade_rows = "".join(
        f"<tr><td>{t['bar']}</td><td>{t['kind']}</td><td>{t['entry_px']} → {t['exit_px']}</td>"
        f"<td class=\"{'pos' if t['pnl'] >= 0 else 'neg'}\">{t['pnl']:+.2f}</td>"
        f"<td class=\"{'pos' if t['pnl'] >= 0 else 'neg'}\">{t['pnl_pct']:+.3f}%</td>"
        f"<td>{t['run_pf']:.2f}</td></tr>"
        for t in shown)
    chips = "".join(
        f"<div class=\"chip\"><div class=\"k\">{k}</div><div class=\"v\">{v}</div>"
        f"<div class=\"d\">{dict(GLOSSARY).get(k, '')}</div></div>"
        for k, v in [("Return %", f"{m.get('total_return_pct', 0):.2f}%"),
                     ("Profit factor", "∞" if pf["pf"] == float("inf") else f"{pf['pf']:.2f}"),
                     ("PF (% based)", "∞" if pf["pf_pct"] == float("inf") else f"{pf['pf_pct']:.2f}"),
                     ("Max drawdown", f"{m.get('max_drawdown_pct', 0):.2f}%"),
                     ("Sharpe", f"{m.get('sharpe', 0):.2f}"),
                     ("Win rate", f"{wins}/{n} = {100*wins/n if n else 0:.0f}%"),
                     ("Commissions", f"${m.get('total_commissions_usdt', m.get('commissions', 0)):,.0f}"),
                     ("Fills", f"{m.get('n_fills', 0):,}"),
                     ("Final equity", f"${m.get('final_equity_usdt', m.get('final_equity', 0)):,.0f}")])
    gloss = "".join(f"<tr><td><b>{k}</b></td><td>{v}</td></tr>" for k, v in GLOSSARY)
    data = {
        "title": title, "verdict": verdict, "n_end": len(eq) - 1,
        "equity": [round(float(x), 2) for x in eq[::max(1, len(eq) // 800)]],
        "price": [round(float(x), 2) for x in closes[::max(1, len(closes) // 1000)]],
        "fills": [[f["bar"], f["side"], round(f["price"], 2), round(f["notional"])] for f in fills[::max(1, len(fills) // 300)]],
        "trades": [[t["bar"], t["pnl"], t["run_pf"]] for t in trades],
        "pf": pf, "start_cash": 100_000,
    }
    return HTML_TPL.replace("//TITLE//", title).replace("//VERDICT//", verdict).replace(
        "/*CAP*/", cap_note).replace(
        "/*DATA*/", json.dumps(data)).replace(
        "/*CHIPS*/", chips).replace("/*TRADES*/", trade_rows).replace(
        "/*GLOSS*/", gloss).replace("/*PF*/", PF_HTML)


HTML_TPL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>e043 — backtest explainer</title>
<style>
  :root{--bg:#0d1117;--fg:#e6edf3;--mut:#8b949e;--card:#161b22;--line:#30363d;
        --pos:#3fb950;--neg:#f85149;--acc:#58a6ff;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
  .wrap{max-width:760px;margin:0 auto;padding:16px 12px 80px}
  h1{font-size:1.35rem;margin:10px 0 2px}
  h2{font-size:1.15rem;margin:26px 0 8px}
  .sub{color:var(--mut);font-size:.92rem}
  .verdict{background:#1f2937;border-left:4px solid var(--acc);padding:10px 14px;border-radius:8px;margin:12px 0}
  .chips{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:14px 0}
  .chip{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}
  .chip .k{font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}
  .chip .v{font-size:1.15rem;font-weight:700;margin:2px 0}
  .chip .d{font-size:.78rem;color:var(--mut)}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:14px 0}
  canvas{width:100%;height:auto;background:#0a0e14;border:1px solid var(--line);border-radius:8px}
  .legend{font-size:.8rem;color:var(--mut);margin:4px 0 12px}
  table{width:100%;border-collapse:collapse;font-size:.85rem}
  th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}
  th{color:var(--mut);font-weight:600}
  table.mini{max-width:360px}
  .pos{color:var(--pos)!important}.neg{color:var(--neg)!important}
  .calc{background:#0a0e14;border:1px solid var(--line);border-radius:8px;padding:12px;margin-top:10px}
  .calc label{margin-right:12px}
  .calc input{background:#161b22;color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:6px;width:110px}
  .big{font-size:1.5rem;font-weight:800;color:var(--acc)}
  ul li{margin:6px 0}
  .scroll{overflow-x:auto}
</style></head><body><div class="wrap">
  <h1>//TITLE// — backtest explainer</h1>
  <div class="sub">e043 · state grid · one self-contained page · open offline</div>
  <div class="verdict"><b>Verdict:</b> //VERDICT//</div>
  <div class="chips">/*CHIPS*/</div>

  <h2>1 · Equity (your account through time)</h2>
  <canvas id="eq"></canvas>
  <div class="legend">Start: $100,000. Flat line = the strategy did nothing.</div>

  <h2>2 · Price and fills</h2>
  <canvas id="px"></canvas>
  <div class="legend">🟢 = bought (&nbsp;/ opened long) &nbsp; 🔴 = sold (&nbsp;/ opened short).</div>

  <h2>3 · Each trade and the growing Profit factor</h2>
  <canvas id="tr"></canvas>
  <div class="legend">Bars: each finished trade (green = profit, red = loss).
  The line is the Profit factor <i>so far</i> — watch it change trade by trade;
  the last point is the final Profit factor of the whole test.</div>

  /*PF*/

  <h2>Trades list</h2>
  /*CAP*/
  <div class="scroll"><table>
    <tr><th>#</th><th>Bar</th><th>Exit kind</th><th>Path</th><th>PnL $</th><th>PnL %</th><th>PF so far</th></tr>
    /*TRADES*/
  </table></div>

  <h2>📚 Glossary (plain words)</h2>
  <div class="scroll"><table>/*GLOSS*/</table></div>
</div>
<script>
const D = /*DATA*/;
function mk(id){const c=document.getElementById(id);const r=c.getContext("2d");
  const dpr=window.devicePixelRatio||1;const W=c.clientWidth||600;const H=Math.max(180,Math.min(280,W*0.5));
  c.width=W*dpr;c.height=H*dpr;r.scale(dpr,dpr);return {c,r,W,H};}
function axes(r,W,H,ymin,ymax,ylabel){const padL=56,padR=10,padT=8,padB=20;
  const ax={x:padL,xw:W-padL-padR,y:padT,yh:H-padT-padB};
  r.strokeStyle="#30363d";r.lineWidth=1;
  r.beginPath();r.moveTo(ax.x,ax.y);r.lineTo(ax.x,ax.y+ax.yh);r.lineTo(ax.x+ax.xw,ax.y+ax.yh);r.stroke();
  const n=4;for(let i=0;i<=n;i++){const v=ymin+(ymax-ymin)*i/n;const y=ax.y+ax.yh-(ax.yh)*(i/n);
    r.fillStyle="#8b949e";r.font="10px monospace";r.textAlign="right";
    r.fillText(ylabel?v.toFixed(0):v.toFixed(2),ax.x-6,y+3);
    r.strokeStyle="#21262d";r.beginPath();r.moveTo(ax.x,y);r.lineTo(ax.x+ax.xw,y);r.stroke();}
  return ax;}
function line(o,vals,ymin,ymax,color,w){const ax=axes(o.r,o.W,o.H,ymin,ymax);
  o.r.strokeStyle=color;o.r.lineWidth=w||2;o.r.beginPath();
  for(let i=0;i<vals.length;i++){const x=ax.x+ax.xw*i/(vals.length-1),y=ax.y+ax.yh-(vals[i]-ymin)/(ymax-ymin)*ax.yh;
    i?o.r.lineTo(x,y):o.r.moveTo(x,y);}o.r.stroke();}
// 1 equity
(function(){const o=mk("eq");const v=D.equity;const lo=Math.min(...v),hi=Math.max(...v);
  const pad=(hi-lo)*0.1||1;line(o,v,lo-pad,hi+pad,"#58a6ff",2);
  o.r.fillStyle="#58a6ff";o.r.font="12px monospace";o.r.textAlign="left";
  o.r.fillText("$"+v[v.length-1].toLocaleString(),60,20);})();
// 2 price + fills
(function(){const o=mk("px");const v=D.price;const lo=Math.min(...v),hi=Math.max(...v);
  const pad=(hi-lo)*0.05||1;line(o,v,lo-pad,hi+pad,"#e6edf3",1.5);
  const ax={x:56,xw:o.W-66,y:8,yh:o.H-28};
  D.fills.forEach(f=>{const [bar,side,px]=f;const t=bar/D.n_end;
    if(t<0||t>1)return;const x=ax.x+ax.xw*t,y=ax.y+ax.yh-(px-lo+pad)/(hi-lo+2*pad)*ax.yh;
    o.r.fillStyle=side>0?"#3fb950":"#f85149";
    o.r.beginPath();o.r.arc(x,y,2.6,0,7);o.r.fill();});})();
// 3 trades + running PF
(function(){const o=mk("tr");const T=D.trades;
  if(!T.length){o.r.fillStyle="#8b949e";o.r.fillText("No completed trades to draw.",70,30);return;}
  const pnls=T.map(t=>t[1]);const pmin=Math.min(0,...pnls),pmax=Math.max(0,...pnls);
  const ax=axes(o.r,o.W,o.H,pmin||-1,pmax||1,"$");
  const W=Math.min(8,ax.xw/T.length);
  T.forEach((t,i)=>{const x=ax.x+ax.xw*(i+0.5)/T.length;
    const y0=ax.y+ax.yh*(pmin/(pmin-pmax)||0.5);  // zero line at pmin..pmax scale
    const y1=ax.y+ax.yh-(t[1]-pmin)/((pmax-pmin)||1)*ax.yh;
    o.r.fillStyle=t[1]>=0?"#3fb950":"#f85149";
    o.r.fillRect(x-W/2,Math.min(y0,y1),W,Math.max(1,Math.abs(y1-y0)));});
  // running PF line (log-ish, clamp)
  const pfs=T.map(t=>Math.min(10,t[2]));
  const pfmin=Math.min(...pfs),pfmax=Math.max(...pfs);
  const ax2={x:ax.x,xw:ax.xw,y:ax.y,yh:ax.yh};
  o.r.strokeStyle="#d29922";o.r.lineWidth=1.5;o.r.beginPath();
  T.forEach((t,i)=>{const x=ax2.x+ax2.xw*(i+0.5)/T.length;
    const y=ax2.y+ax2.yh-(Math.min(10,t[2])-pfmin)/((pfmax-pfmin)||1)*ax2.yh;
    i?o.r.lineTo(x,y):o.r.moveTo(x,y);});o.r.stroke();})();
// PF calculator
function upd(){const w=parseFloat(document.getElementById('cw').value)||0;
  const l=parseFloat(document.getElementById('cl').value)||0;
  document.getElementById('cpf').textContent=(l>0?(w/l).toFixed(2):(w>0?'∞':'—'));}
document.getElementById('cw').addEventListener('input',upd);
document.getElementById('cl').addEventListener('input',upd);
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="OHLCV csv (for price series)")
    ap.add_argument("--dir", required=True, help="output dir of a run (metrics.json, equity_curve.csv, fills_report.csv)")
    ap.add_argument("--title", default="Backtest")
    ap.add_argument("--out", default="output/viz.html")
    args = ap.parse_args()

    m = json.load(open(f"{args.dir}/metrics.json"))
    eq = pd.read_csv(f"{args.dir}/equity_curve.csv")["equity"].astype(float).tolist()
    fills = normalize_fills(f"{args.dir}/fills_report.csv")
    trades, pf = reconstruct_trades(fills)
    # attach running pf to trades
    wins = losses = 0.0
    for t in trades:
        if t["pnl"] > 0: wins += t["pnl"]
        else: losses -= t["pnl"]
        t["run_pf"] = round((wins / losses) if losses > 0 else 9.999, 2)

    price = pd.read_csv(args.data)
    closes = price["close"].astype(float).tolist()

    html = build_html(args.title, m, trades, pf, eq, fills, closes)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    open(args.out, "w").write(html)
    print(f"Wrote {args.out}  ({len(html)} bytes)")
    print(f"trades={pf['n_trades']} wins={pf['n_wins']} gross_win=${pf['gross_win']} "
          f"gross_loss=${pf['gross_loss']} PF={pf['pf']:.2f} PF%={pf['pf_pct']:.2f}")


if __name__ == "__main__":
    main()