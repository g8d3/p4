#!/usr/bin/env python3
"""e071 inject: SSR output/index.html via tablelib (real <tr> rows, counter+pager)."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "output")
sys.path.insert(0, "/home/vuos/code/p4/e068-tablelib")
from tablelib.render import render_table

COLUMNS = [
    {"key": "symbol", "label": "token", "kind": "text", "ph": "token"},
    {"key": "tier", "label": "tier", "kind": "text", "ph": "S/A/B/C"},
    {"key": "chain", "label": "chain", "kind": "text", "ph": "chain", "cls": "c-hid"},
    {"key": "price_usd", "label": "price $", "kind": "num", "fmt": "{:.6g}"},
    {"key": "mcap_usd", "label": "mcap $", "kind": "num", "fmt": "{:.3g}"},
    {"key": "fdv_usd", "label": "FDV $", "kind": "num", "fmt": "{:.3g}", "cls": "c-hid"},
    {"key": "p_sales", "label": "P/S", "kind": "num", "fmt": "{:.2f}", "ph": "<= max", "cls": "c-hid"},
    {"key": "fdv_to_sales", "label": "FDV/S", "kind": "num", "fmt": "{:.2f}", "cls": "c-hid"},
    {"key": "peg_proxy", "label": "PEGpx", "kind": "num", "fmt": "{:.2f}", "cls": "c-hid"},
    {"key": "mcap_share_pct", "label": "mcapshr %", "kind": "bar", "fmt": "{:.3f}"},
    {"key": "volume_share_pct", "label": "volshr %", "kind": "num", "fmt": "{:.2f}", "cls": "c-hid"},
    {"key": "liquidity_share_pct", "label": "liqshr %", "kind": "num", "fmt": "{:.2f}", "cls": "c-hid"},
    {"key": "sales_share_pct", "label": "salesshr %", "kind": "num", "fmt": "{:.2f}", "cls": "c-hid"},
    {"key": "usage_share_pct", "label": "usgshr %", "kind": "num", "fmt": "{:.2f}", "cls": "c-hid"},
    {"key": "drop_from_ath_pct", "label": "vs ATH %", "kind": "num", "fmt": "{:+.1f}"},
    {"key": "rise_from_atl_pct", "label": "vs ATL %", "kind": "num", "fmt": "{:+.0f}", "cls": "c-hid"},
    {"key": "rise_from_siglow_pct", "label": "vs siglow %", "kind": "num", "fmt": "{:+.0f}", "cls": "c-hid"},
    {"key": "mcap_to_vol_24h", "label": "P/Vol", "kind": "num", "fmt": "{:.1f}", "cls": "c-hid"},
    {"key": "liq_to_mcap_pct", "label": "liq/mcap %", "kind": "num", "fmt": "{:.3f}", "cls": "c-hid"},
    {"key": "vol_to_liq_turnover", "label": "turnovr", "kind": "bar", "fmt": "{:.2f}", "cls": "c-hid"},
    {"key": "chg_24h_pct", "label": "24h %", "kind": "num", "fmt": "{:+.1f}"},
    {"key": "supply_net_pct", "label": "sup net%", "kind": "num", "fmt": "{:+.1f}", "cls": "c-hid"},
    {"key": "age_days", "label": "age d", "kind": "num", "fmt": "{:.0f}"},
    {"key": "gmgn_url", "label": "gmgn", "kind": "link", "link_text": "gmgn"},
    {"key": "dex_url", "label": "dex", "kind": "link", "link_text": "dex"},
    {"key": "coingecko_url", "label": "cg", "kind": "link", "link_text": "cg"},
    {"key": "cmc_url", "label": "cmc", "kind": "link", "link_text": "cmc"},
    {"key": "site_url", "label": "website", "kind": "link", "link_text": "open"},
    {"key": "x_url", "label": "X", "kind": "link", "link_text": "open"},
    {"key": "tg_url", "label": "telegram", "kind": "link", "link_text": "open"},
    {"key": "discord_url", "label": "discord", "kind": "link", "link_text": "open"},
    {"key": "stale", "label": "stale", "kind": "num", "fmt": "{:.0f}", "cls": "c-hid"},
    {"key": "through", "label": "latest sync", "kind": "date", "cls": "c-hid"},
]

VENUES_COLUMNS = [
    {"key": "symbol", "label": "token", "kind": "text", "ph": "token"},
    {"key": "venue", "label": "venue", "kind": "text", "ph": "venue"},
    {"key": "venue_type", "label": "type", "kind": "text", "ph": "amm/clob"},
    {"key": "chain", "label": "chain", "kind": "text", "ph": "chain", "cls": "c-hid"},
    {"key": "price_usd", "label": "price $", "kind": "num", "fmt": "{:.6g}"},
    {"key": "volume_24h_usd", "label": "vol24 $", "kind": "num", "fmt": "{:.3g}"},
    {"key": "liquidity_usd", "label": "liq $", "kind": "num", "fmt": "{:.3g}"},
    {"key": "trades_24h", "label": "trades", "kind": "num", "fmt": "{:.0f}", "cls": "c-hid"},
    {"key": "taker_fee_bps", "label": "taker bps", "kind": "num", "fmt": "{:.0f}", "cls": "c-hid"},
    {"key": "fee_variable", "label": "feVar", "kind": "num", "fmt": "{:.0f}", "cls": "c-hid"},
    {"key": "slip_1k_bps", "label": "slip1k", "kind": "num", "fmt": "{:.1f}"},
    {"key": "slip_10k_bps", "label": "slip10k", "kind": "num", "fmt": "{:.0f}", "cls": "c-hid"},
    {"key": "lp_apr_proxy_pct", "label": "lpAPR %", "kind": "num", "fmt": "{:.1f}"},
    {"key": "lp_turnover", "label": "turnovr", "kind": "num", "fmt": "{:.2f}", "cls": "c-hid"},
    {"key": "trader_depth", "label": "depth $", "kind": "num", "fmt": "{:.3g}", "cls": "c-hid"},
]

SOURCES_COLUMNS = [
    {"key": "source", "label": "source", "kind": "text", "ph": "source"},
    {"key": "kind", "label": "kind", "kind": "text", "ph": "kind"},
    {"key": "covers", "label": "covers", "kind": "text", "ph": "covers"},
    {"key": "access", "label": "access", "kind": "text", "ph": "access", "cls": "c-hid"},
    {"key": "cadence", "label": "cadence", "kind": "text", "ph": "cadence", "cls": "c-hid"},
    {"key": "status", "label": "status", "kind": "text", "ph": "live/planned"},
    {"key": "url", "label": "link", "kind": "link", "link_text": "open"},
]

def main():
    d = json.load(open(os.path.join(OUT, "comps.json")))
    rows = d["tokens_rows"]
    rows = sorted(rows, key=lambda r: (r.get("mcap_usd") or 0), reverse=True)
    table = render_table(rows, COLUMNS, total=len(rows), page=1, per=10,
                         sort_key="mcap_usd", sort_dir=-1, ns="inf",
                         share=False, insights=False, compute=False)
    vd = json.load(open(os.path.join(OUT, "venues.json")))
    sd = json.load(open(os.path.join(OUT, "sources.json")))
    vtable = render_table(vd["rows"], VENUES_COLUMNS, total=vd["n"], page=1, per=25,
                          sort_key="volume_24h_usd", sort_dir=-1, ns="ven",
                          share=False, insights=False, compute=False)
    stable = render_table(sd["rows"], SOURCES_COLUMNS, total=sd["n"], page=1, per=25,
                          sort_key="source", sort_dir=1, ns="src",
                          share=False, insights=False, compute=False)
    if os.path.exists(os.path.join(OUT, "version.json")):
        v = json.load(open(os.path.join(OUT, "version.json")))
    else:
        v = {}
    asof = d["as_of"]
    ntok = d["tokens"]
    oldest = d["through_oldest"]
    top_sym = rows[0]["symbol"] if rows else "?"
    top_shr = rows[0].get("mcap_share_pct") if rows else "?"
    commit = v.get("commit", "?")
    head = "<!doctype html>\n<html><head><meta charset=\"utf-8\">"
    head += "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
    head += "<title>e071 AI inference comps</title>\n"
    head += "<link rel=\"stylesheet\" href=\"tablelib.css\">\n"
    head += "<style>body{font-family:system-ui,sans-serif;max-width:1100px;margin:2em auto;padding:0 1em 84px}"
    head += "h1{font-size:1.4em;margin:.2em 0}#meta,#verdict{font-size:13px;color:#444}#fresh{font-variant-numeric:tabular-nums}"
    head += "html.dark #meta,html.dark #verdict{color:#aaa}details.src{font-size:12px;color:#666;margin:.3em 0}body.simple th.c-hid,body.simple td.c-hid,body.simple .tl-f.c-hid{display:none}"
    head += "#net{font-size:13px;margin:.3em 0}#clock{font-variant-numeric:tabular-nums;background:#111;color:#0f0;padding:2px 8px;border-radius:6px;font-family:monospace}"
    head += "#conn.live{color:#0a0;font-weight:bold}#conn.off{color:#c00;font-weight:bold}"
    head += "#upd{color:#555;font-size:12px}"
    head += "@media(max-width:600px){#clock{font-size:12px;padding:2px 6px}#upd{display:block;margin-top:2px}}"
    head += ".tl-fu{animation:fU 1.8s}.tl-fd{animation:fD 1.8s}.tl-fn{animation:fN 1.8s}"
    head += "@keyframes fU{0%{background:rgba(0,180,0,.5)}100%{background:transparent}}"
    head += "@keyframes fD{0%{background:rgba(220,0,0,.45)}100%{background:transparent}}"
    head += "@keyframes fN{0%{background:rgba(0,120,255,.4)}100%{background:transparent}}</style>\n"
    head += "<style>.tabs{display:flex;gap:6px;margin:.6em 0}.tabs button{font:inherit;font-size:13px;padding:4px 14px;border:1px solid #999;border-radius:8px 8px 0 0;background:#eee;cursor:pointer}html.dark .tabs button{background:#222;color:#ddd;border-color:#555}.tabs button.on{background:#fff;font-weight:bold;border-bottom-color:#fff}html.dark .tabs button.on{background:#111;border-bottom-color:#111}</style>\n"
    head += "</head><body class=\"simple\">\n"
    try:
        shr1 = round(float(top_shr), 1)
    except (TypeError, ValueError):
        shr1 = top_shr
    short_date = asof[:10]
    body1 = "<h1>AI inference comps</h1>\n"
    body1 += "<div id=\"net\"><span id=\"clock\">--:--:--</span> <span id=\"conn\">connecting</span> <span id=\"upd\"></span></div>\n"
    body1 += "<div id=\"meta\">" + str(ntok) + " tokens \u00B7 data <span id=\"fresh\" title=\"" + asof + "\">" + short_date + "</span></div>\n"
    body2 = "<div id=\"verdict\">Biggest capital share: " + str(top_sym) + " \u00B7 " + str(shr1) + "%.</div>\n"
    body3 = "<details class=\"src\"><summary>API for agents & sources</summary>"
    body3 += "This page is a client of its own API: it renders from these files and re-polls <b>comps.json</b> every 30s. "
    body3 += "Agents: <b>comps.csv</b> is the flat table (one row per token, least redundant); <b>comps.json</b> adds history arrays + methodology. "
    body3 += "Endpoints: <a href=\"comps.json\">comps.json</a> <a href=\"venues.json\">venues.json</a> "
    body3 += "<a href=\"unlocks.json\">unlocks.json</a> <a href=\"sources.json\">sources.json</a> <a href=\"comps.csv\">comps.csv</a> "
    body3 += "<a href=\"version.json\">version.json</a>. "
    body3 += "Feeds: DexScreener (sol/base/robinhood) + CoinGecko (majors) + GeckoTerminal candles + public-RPC supply. "
    body3 += "Refresh: fast loop every 15 min (prices), full loop twice daily (history/supply). Oldest-through " + oldest + ".</details>\n"
    js = "<script src=\"tablelib.js\"></script>\n"
    js += "<script>var PRICE_POLL_S=30,srvOff=0,curAsOf='" + asof + "';"
    js += "function fmt2(n){return (n<10?'0':'')+n;}"
    js += "function fmtL(ms){var d=new Date(ms);return fmt2(d.getHours())+':'+fmt2(d.getMinutes())+':'+fmt2(d.getSeconds());}"
    js += "function tzN(){try{return Intl.DateTimeFormat().resolvedOptions().timeZone;}catch(e){return 'local';}}"
    js += "function tickClock(){try{var ms=Date.now()+srvOff,d=new Date(ms);"
    js += "var el=document.getElementById('clock');"
    js += "el.textContent='server '+fmtL(ms)+' '+tzN();"
    js += "el.title='UTC '+fmt2(d.getUTCHours())+':'+fmt2(d.getUTCMinutes())+':'+fmt2(d.getUTCSeconds());}catch(e){}}"
    js += "setInterval(tickClock,1000);"
    js += "function cellFlash(td,a,b){td.classList.remove('tl-fu','tl-fd','tl-fn');void td.offsetWidth;"
    js += "var c='tl-fn';if(typeof a==='number'&&typeof b==='number'){c=b>a?'tl-fu':'tl-fd';}td.classList.add(c);}"
    js += "function patchTable(nrows){var s=TL.inf;if(!s)return 0;"
    js += "var bySym={};nrows.forEach(function(r){bySym[r.symbol]=r;});"
    js += "var tb=document.querySelector('#tl-inf tbody');if(!tb)return 0;var n=0;"
    js += "Array.prototype.forEach.call(tb.rows,function(tr){"
    js += "var sym=tr.cells[0].textContent.trim(),nr=bySym[sym];if(!nr)return;"
    js += "var oi=-1;for(var i=0;i<s.all.length;i++){if(s.all[i].symbol===sym){oi=i;break;}}if(oi<0)return;"
    js += "var orow=s.all[oi];"
    js += "s.cols.forEach(function(col,ci){var a=orow[col.key],b=nr[col.key];"
    js += "if(a===b||(a==null&&b==null))return;var td=tr.cells[ci];if(!td)return;"
    js += "try{td.innerHTML=tlCell('inf',nr,col);}catch(e){td.textContent=(b==null?'\u2014':String(b));}"
    js += "cellFlash(td,a,b);n++;});s.all[oi]=nr;});s.total=nrows.length;return n;}"
    js += "async function poll(){var c=document.getElementById('conn'),t0=Date.now(),j=null;"
    js += "try{var r=await fetch('comps.json',{cache:'no-store'});j=await r.json();"
    js += "var rtt=Date.now()-t0,dh=r.headers.get('Date'),st=dh?Date.parse(dh):NaN;"
    js += "if(!isNaN(st)){srvOff=(st+rtt/2)-Date.now();}"
    js += "else if(j.server_ts&&Date.now()-j.server_ts*1000<600000){srvOff=(j.server_ts*1000+rtt/2)-Date.now();}}catch(e){}"
    js += "if(!j){c.textContent='\u25CF OFFLINE';c.className='off';return;}"
    js += "c.textContent='\u25CF LIVE';c.className='live';tickClock();"
    js += "if(j.as_of===curAsOf){document.getElementById('upd').textContent='\u00B7 up to date';return;}"
    js += "curAsOf=j.as_of;var n=0;try{n=patchTable(j.tokens_rows);}catch(e){}"
    js += "var f=document.getElementById('fresh');f.textContent=j.as_of.slice(0,10);f.title=j.as_of;"
    js += "document.getElementById('upd').textContent='\u00B7 '+n+' cells updated';}"
    js += "document.addEventListener('DOMContentLoaded',function(){try{tlRender('inf');}catch(e){}try{tlRender('ven');}catch(e){}try{tlRender('src');}catch(e){}"
    js += "tickClock();poll();setInterval(poll,PRICE_POLL_S*1000);});</script>\n"
    tabs = "<nav class=\"tabs\"><button data-t=\"comps\" class=\"on\">Comps</button><button data-t=\"ven\">Venues</button><button data-t=\"src\">Sources</button></nav>\n"
    sec1 = "<section id=\"tab-comps\">" + table + "</section>\n"
    sec2 = "<section id=\"tab-ven\" hidden>" + vtable + "</section>\n"
    sec3 = "<section id=\"tab-src\" hidden>" + stable + "</section>\n"
    tabjs = "<script>function showTab(n){['comps','ven','src'].forEach(function(k){document.getElementById('tab-'+k).hidden=(k!==n);});"
    tabjs += "Array.prototype.forEach.call(document.querySelectorAll('.tabs button'),function(b){b.classList.toggle('on',b.dataset.t===n);});"
    tabjs += "try{tlRender(n==='comps'?'inf':n);}catch(e){}}"
    tabjs += "Array.prototype.forEach.call(document.querySelectorAll('.tabs button'),function(b){b.addEventListener('click',function(){showTab(b.dataset.t);});});</script>\n"
    foot = "<!-- commit " + str(commit) + " -->\n</body></html>\n"
    page = head + body1 + body2 + tabs + sec1 + sec2 + sec3 + body3 + js + tabjs + foot
    tmp = os.path.join(OUT, "index.html.tmp")
    open(tmp, "w").write(page)
    os.replace(tmp, os.path.join(OUT, "index.html"))
    print("inject ok: %d rows" % len(rows))

if __name__ == "__main__":
    main()
