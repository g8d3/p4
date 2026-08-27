/* Pulse — GMGN-style Hyperliquid terminal (e045). No frameworks. */
"use strict";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const fmt = (n) => {
  if (n == null || isNaN(n)) return "—";
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (a >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (a >= 1e3) return (n / 1e3).toFixed(2) + "K";
  return Number(n).toPrecision(4);
};
const fmtPx = (n) => {
  if (n == null || isNaN(n)) return "—";
  const a = Math.abs(n);
  let d = a >= 1000 ? 2 : a >= 1 ? 4 : a >= 0.01 ? 5 : a >= 0.0001 ? 6 : 8;
  return Number(n).toLocaleString("en-US", {
    minimumFractionDigits: d, maximumFractionDigits: d,
  });
};
const pct = (n) => (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
const timeStr = (ms) => new Date(ms).toLocaleTimeString("en-GB", { hour12: false });
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

const state = { venue: "meme", market: "perp", sort: "volume", order: "desc", tab: "trending", q: "", rows: [], memeRows: [], memeLoaded: false };

async function api(path) {
  const r = await fetch(path);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
  return j;
}
function toast(msg) {
  const el = $("#toast");
  el.textContent = msg; el.classList.add("show");
  clearTimeout(toast._t); toast._t = setTimeout(() => el.classList.remove("show"), 1800);
}

/* ---------- router ---------- */
function go(h) { location.hash = h; }
function updateMarketToggle() {
  $$("#marketToggle button").forEach((x) => x.classList.toggle("active", x.dataset.m === state.market));
}
function updateVenue() {
  $$("#venueToggle button").forEach((x) => x.classList.toggle("active", x.dataset.v === state.venue));
  $("#marketToggle").classList.toggle("hidden", state.venue !== "hl");
  updateMarketToggle();
}
function route() {
  const h = location.hash || "#/";
  const mm = h.match(/^#\/meme\/(.+)$/);
  if (mm) { state.venue = "meme"; updateVenue(); showMemecoin(decodeURIComponent(mm[1])); return; }
  const ml = h.match(/^#\/token\/(perp|spot)\/(.+)$/);
  if (ml) {
    state.venue = "hl";
    state.market = ml[1];
    updateVenue();
    showToken(decodeURIComponent(ml[2]));
    return;
  }
  const m = h.match(/^#\/token\/(.+)$/);
  if (m) { state.venue = "hl"; updateVenue(); showToken(decodeURIComponent(m[1])); }
  else { showScreener(); }
}
window.addEventListener("hashchange", route);

/* ---------- screener ---------- */
let loadedMarket = null;
async function showScreener() {
  $("#token").classList.add("hidden");
  $("#screener").classList.remove("hidden");
  updateVenue();
  if (state.venue === "meme") {
    if (!state.memeLoaded || !state.memeRows.length) await loadMemecoinScreener();
    else renderMemecoinScreener();
  } else {
    if (loadedMarket !== state.market || !state.rows.length) {
      loadedMarket = state.market;
      await loadScreener();
    } else {
      renderScreener();
    }
  }
}

async function loadScreener() {
  $("#screener").innerHTML = '<div class="spinner">Loading markets…</div>';
  try {
    const j = await api(`/api/screener?market=${state.market}&sort=volume&order=desc&limit=400`);
    state.rows = j.rows || [];
  } catch (e) {
    $("#screener").innerHTML = `<div class="error">Could not load markets.<br>${esc(e.message)}</div>`;
    return;
  }
  renderScreener();
  scheduleRefresh();
}

async function reloadScreener() {
  try {
    const j = await api(`/api/screener?market=${state.market}&sort=volume&order=desc&limit=400`);
    state.rows = j.rows || [];
  } catch (e) { return; }
  renderScreener();
}

function visibleRows() {
  let rows = [...state.rows];
  if (state.q) rows = rows.filter((r) => r.name.toLowerCase().includes(state.q));
  if (state.tab === "trending") {
    rows = rows.map((r) => ({ ...r, _score: (r.volume_24h || 0) * (1 + Math.abs(r.change_24h || 0) / 100 * 3) }))
      .sort((a, b) => b._score - a._score);
  } else if (state.tab === "gainers") {
    rows = rows.filter((r) => r.change_24h > 0).sort((a, b) => b.change_24h - a.change_24h);
  } else if (state.tab === "losers") {
    rows = rows.filter((r) => r.change_24h < 0).sort((a, b) => a.change_24h - b.change_24h);
  } else if (state.tab === "volume") {
    rows = rows.sort((a, b) => b.volume_24h - a.volume_24h);
  } else if (state.tab === "new") {
    rows = rows.sort((a, b) => (b.market === "spot" ? 1 : 0) - (a.market === "spot" ? 1 : 0));
  }
  const k = state.sort, o = state.order === "desc" ? -1 : 1;
  const key = (r) => {
    if (k === "name") return r.name;
    if (k === "price") return r.price;
    if (k === "change") return r.change_24h;
    if (k === "volume") return r.volume_24h;
    if (k === "mc") return r.market_cap || 0;
    if (k === "fdv") return r.fully_diluted_cap || 0;
    if (k === "oi") return r.open_interest || 0;
    return r.volume_24h;
  };
  rows = rows.sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0) * o);
  // trending + search already imply a view; for tabs use natural order unless sorted by user
  return rows.slice(0, 60);
}

function renderScreener() {
  const rows = visibleRows();
  const cols = state.market === "perp"
    ? [["name", "Coin"], ["price", "Price", "num"], ["change", "24h %"], ["volume", "Volume(24h)"], ["oi", "Open Interest"]]
    : [["name", "Coin"], ["price", "Price", "num"], ["change", "24h %"], ["volume", "Volume(24h)"], ["mc", "Market Cap"]];

  const head = cols.map(([k, l, cls]) => {
    const ar = state.sort === k ? `<span class="arrow">${state.order === "desc" ? "▼" : "▲"}</span>` : "";
    return `<div class="head ${cls || ""}" data-sort="${k}">${l}${ar}</div>`;
  }).join("");

  let body = rows.map((r) => arrow(r)).join("");
  if (!body) body = `<div class="spinner" style="grid-column:1/-1">No tokens match.</div>`;

  $("#screener").innerHTML = `
    <h1>${state.market === "perp" ? "Perpetuals" : "Spot Tokens"}</h1>
    <p class="sub"><span class="pill"><span class="dot"></span>live · Hyperliquid</span>
      <span class="pill">${rows.length} shown</span></p>
    <div class="tabs">
      <button class="tab ${state.tab==="trending"?"active":""}" data-tab="trending">🔥 Trending</button>
      <button class="tab ${state.tab==="gainers"?"active":""}" data-tab="gainers">Gainers</button>
      <button class="tab ${state.tab==="losers"?"active":""}" data-tab="losers">Losers</button>
      <button class="tab ${state.tab==="volume"?"active":""}" data-tab="volume">Volume</button>
      <button class="tab ${state.tab==="new"?"active":""}" data-tab="new">New</button>
    </div>
    <div class="tbl">
      <div class="row head">${head}</div>
      ${body}
    </div>`;

  $$(".tabs .tab", $("#screener")).forEach((b) => (b.onclick = () => { state.tab = b.dataset.tab; renderScreener(); }));
  $$(".head[data-sort]", $("#screener")).forEach((h) => (h.onclick = () => {
    const s = h.dataset.sort;
    if (state.sort === s) state.order = state.order === "desc" ? "asc" : "desc";
    else { state.sort = s; state.order = "desc"; }
    renderScreener();
  }));
  $$(".row", $("#screener")).forEach((r) => (r.onclick = () => {
    if (r.classList.contains("head")) return;
    location.hash = `#/token/${state.market}/${encodeURIComponent(r.dataset.name)}`;
  }));
}

function arrow(r) {
  const c = r.change_24h, up = c >= 0;
  const icon = r.name[0] || "•";
  const meta = state.market === "perp"
    ? `OI ${fmt(r.open_interest)}`
    : `MC ${fmt(r.market_cap)}`;
  const extra = state.market === "perp" ? fmt(r.open_interest) : fmt(r.market_cap);
  const maxVol = Math.max(1, ...state.rows.map((x) => x.volume_24h || 0));
  const vw = Math.max(4, ((r.volume_24h || 0) / maxVol) * 100);
  return `
    <div class="row" data-name="${esc(r.name)}">
      <div class="coin">
        <div class="icon">${esc(icon)}</div>
        <div style="min-width:0">
          <div class="c-name">${esc(r.name)}</div>
          <div class="c-meta">${esc(meta)}</div>
        </div>
      </div>
      <div class="num c-price">${fmtPx(r.price)}</div>
      <div class="chg ${up ? "up" : "down"}">${pct(c)}</div>
      <div>
        <div class="num c-vol">$${fmt(r.volume_24h)}</div>
        <div class="bar"><span style="width:${vw}%"></span></div>
      </div>
      <div class="num c-extra">${esc(extra)}</div>
    </div>`;
}

/* ---------- memecoin screener ---------- */
async function loadMemecoinScreener() {
  $("#screener").innerHTML = '<div class="spinner">Loading memecoins…</div>';
  try {
    const j = await api(`/api/memecoins/screener?sort=volume&order=desc`);
    state.memeRows = j.rows || [];
    state.memeLoaded = true;
  } catch (e) {
    $("#screener").innerHTML = `<div class="error">Could not load memecoins.<br>${esc(e.message)}</div>`;
    return;
  }
  renderMemecoinScreener();
}

function memeVisible() {
  let rows = [...state.memeRows];
  if (state.q) rows = rows.filter((r) => ((r.symbol || "") + (r.name || "")).toLowerCase().includes(state.q));
  const k = state.memeSort || "volume", o = state.memeOrder === "asc" ? 1 : -1;
  const key = (r) => {
    if (k === "name") return r.name || "";
    if (k === "price") return r.price || 0;
    if (k === "change") return r.change_24h || 0;
    if (k === "mc") return r.market_cap || 0;
    if (k === "liquidity") return r.liquidity || 0;
    if (k === "buys") return r.buys_24h || 0;
    if (k === "sells") return r.sells_24h || 0;
    return r.volume_24h || 0;
  };
  rows = rows.sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0) * o);
  if (state.memeTab === "watchlist") {
    const wl = watchlist().map((x) => x.mint);
    rows = rows.filter((r) => wl.includes(r.mint)).sort((a, b) => (b.volume_24h || 0) - (a.volume_24h || 0));
  }
  if (state.memeTab === "gainers") rows = rows.filter((r) => (r.change_24h || 0) > 0).sort((a, b) => (b.change_24h || 0) - (a.change_24h || 0));
  if (state.memeTab === "losers") rows = rows.filter((r) => (r.change_24h || 0) < 0).sort((a, b) => (a.change_24h || 0) - (b.change_24h || 0));
  if (state.memeTab === "new") rows = rows.filter((r) => r.flag).sort((a, b) => (b.volume_24h || 0) - (a.volume_24h || 0));
  if (state.memeTab === "trending") rows = rows.sort((a, b) => (b.buys_24h || 0) - (a.buys_24h || 0));
  return rows.slice(0, 60);
}

function watchlist() { try { return JSON.parse(localStorage.getItem("gmgn_watch") || "[]"); } catch (e) { return []; } }
function wlSave(arr) { localStorage.setItem("gmgn_watch", JSON.stringify(arr)); }
function inWatch(mint) { return watchlist().some((x) => x.mint === mint); }
function toggleWatch(mint, symbol) {
  const arr = watchlist();
  const i = arr.findIndex((x) => x.mint === mint);
  if (i >= 0) arr.splice(i, 1); else arr.push({ mint, symbol });
  wlSave(arr);
  if (state.venue === "meme") renderMemecoinScreener();
}

function renderMemecoinScreener() {
  const rows = memeVisible();
  const cols = [
    ["name", "Token"], ["price", "Price", "num"], ["change", "24h %"],
    ["volume", "Vol(24h)"], ["mc", "Mkt Cap"], ["buys", "Buy/Sell"],
  ];
  const head = cols.map(([k, l]) => {
    const ar = (state.memeSort === k) ? `<span class="arrow">${state.memeOrder === "desc" ? "▼" : "▲"}</span>` : "";
    return `<th class="head ${k === "name" ? "" : "num"}" data-sort="${k}">${l}${ar}</th>`;
  }).join("");
  const tabs = [["trending", "🔥 Hot"], ["volume", "Vol"], ["gainers", "Gainers"], ["losers", "Losers"], ["new", "New"], ["watchlist", "★ Watchlist"]];
  const tabhtml = tabs.map(([t, l]) => `<button class="tab ${state.memeTab === t ? "active" : ""}" data-tab="${t}">${l}</button>`).join("");

  const body = rows.map((r) => {
    const chg = r.change_24h;
    const up = chg != null && chg >= 0;
    const buy = r.buys_24h, sell = r.sells_24h;
    const hasFlow = buy != null && sell != null;
    const img = `<img src="${esc(r.img || "")}" style="width:34px;height:34px;border-radius:50%;object-fit:cover;border:1px solid var(--line)" onerror="this.style.display='none'">`;
    const mn = r.mint || "";
    const star = inWatch(mn) ? "★" : "☆";
    const chip = (r.flag && r.price == null) ? `<span class="newchip ${r.flag}">${r.flag === "boost" ? "BOOST" : "NEW"}</span>` : "";
    const sym = r.symbol || r.name || "—";
    return `<tr class="row" data-mint="${esc(mn)}">
      <td><div class="coin"><div class="icon" style="overflow:hidden">${img}<span style="display:none">${esc((r.symbol || "•")[0])}</span></div>
        <div><div class="c-name">${esc(sym)}${chip} <span class="star ${inWatch(mn) ? "on" : ""}" data-mint="${esc(mn)}" data-sym="${esc(sym)}" title="Watchlist">${star}</span></div><div class="c-meta">${esc((r.name || "").slice(0, 16))}</div></div></div></td>
      <td class="num">${fmtPx(r.price)}</td>
      <td class="chg ${chg == null ? "" : (up ? "up" : "down")}">${chg == null ? "—" : pct(chg)}</td>
      <td class="num">${r.volume_24h == null ? "—" : "$" + fmt(r.volume_24h)}</td>
      <td class="num">${r.market_cap ? "$" + fmt(r.market_cap) : "—"}</td>
      <td class="num">${hasFlow ? `<span style="color:var(--green)">${buy}</span>/<span style="color:var(--red)">${sell}</span>` : "—"}</td>
    </tr>`;
  }).join("");

  $("#screener").innerHTML = `
    <h1>${state.venue === "meme" ? "Solana Memecoins" : ""}</h1>
    <p class="sub"><span class="pill"><span class="dot"></span>live · on-chain</span><span class="pill">${rows.length} shown</span></p>
    <div class="tabs">${tabhtml}</div>
    <div class="tbl meme"><table><thead><tr class="head">${head}</tr></thead><tbody>${body || `<tr class="row"><td colspan="6" class="spinner" style="grid-column:1/-1">No tokens</td></tr>`}</tbody></table></div>`;

  $$(".tabs .tab", $("#screener")).forEach((b) => (b.onclick = () => { state.memeTab = b.dataset.tab; renderMemecoinScreener(); }));
  $$(".head[data-sort]", $("#screener")).forEach((h) => (h.onclick = () => {
    const s = h.dataset.sort;
    if (state.memeSort === s) state.memeOrder = state.memeOrder === "desc" ? "asc" : "desc";
    else { state.memeSort = s; state.memeOrder = "desc"; }
    renderMemecoinScreener();
  }));
  $$(".star", $("#screener")).forEach((s) => (s.onclick = (e) => {
    e.stopPropagation();
    toggleWatch(s.dataset.mint, s.dataset.sym);
  }));
  $$(".row", $("#screener")).forEach((r) => (r.onclick = (e) => {
    if (r.classList.contains("head")) return;
    if (e.target.classList.contains("star")) return;
    const mint = r.dataset.mint; if (mint) location.hash = `#/meme/${encodeURIComponent(mint)}`;
  }));
}

/* ---------- memecoin token detail ---------- */
async function showMemecoin(mint) {
  $("#screener").classList.add("hidden");
  $("#token").classList.remove("hidden");
  $("#token").innerHTML = '<div class="spinner">Loading token…</div>';
  try {
    const detail = await api(`/api/memecoins/token?addr=${encodeURIComponent(mint)}`);
    const pool = detail.pool;
    const [candles] = await Promise.all([
      pool ? api(`/api/memecoins/candles?pool=${encodeURIComponent(pool)}&interval=15m`) : Promise.resolve({ candles: [] }),
    ]);
    renderMemecoin(detail, candles);
  } catch (e) {
    $("#token").innerHTML = `<div class="error">Could not load ${esc(mint.slice(0, 10))}.<br>${esc(e.message)}</div>`;
  }
}

function flowTimeline(txns) {
  if (!txns) return "";
  const labels = { m5: "5m", m15: "15m", m30: "30m", h1: "1h", h6: "6h", h24: "24h" };
  const tfs = ["m15", "h1", "h6", "h24"].filter((t) => txns[t]);
  if (!tfs.length) return "";
  const rows = tfs.map((t) => {
    const tr = txns[t]; const tot = ((tr.buys || 0) + (tr.sells || 0)) || 1;
    const b = Math.round((tr.buys || 0) / tot * 100);
    return `<div class="tline"><span class="tf">${labels[t]}</span><div class="split"><div class="buys" style="width:${b}%"></div><div class="sells" style="width:${100 - b}%"></div></div><span class="n" style="min-width:74px;text-align:right"><span style="color:var(--green)">${tr.buys || 0}</span>/<span style="color:var(--red)">${tr.sells || 0}</span></span></div>`;
  }).join("");
  return `<div class="timeline"><div class="tl-h">Buy / Sell by timeframe</div>${rows}</div>`;
}

function renderMemecoin(d, candlesJson) {
  const candles = candlesJson.candles || [];
  const buy = d.buys_24h, sell = d.sells_24h;
  const hasFlow = buy != null && sell != null && (buy + sell) > 0;
  const buyPct = hasFlow ? Math.round(buy / (buy + sell) * 100) : 50;
  const fmt$ = (x) => (x == null || isNaN(x)) ? "—" : "$" + fmt(x);
  const soc = (d.socials || []).map((s) => `<a href="${esc(s.url || "#")}" target="_blank" rel="noopener" class="pill">${esc(s.type || "link")}</a>`).join(" ");
  const holders = (d.holders || []).slice(0, 12);
  const holderRows = holders.length
    ? holders.map((h) => `<div class="bp"><span class="p">${esc(h.owner.slice(0, 8))}…</span><span class="num">${fmt(h.amount)}</span><div class="lvl"><span style="left:0;width:${Math.min(100, h.pct)}%;background:var(--accent)"></span></div><span class="num">${h.pct}%</span></div>`).join("")
    : '<div class="spinner" style="padding:14px">Holders no disponible (RPC rate-limited)</div>';

  const stat = (k, v) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`;
  const stats = [
    stat("Market Cap", fmt$(d.market_cap)),
    stat("FDV", fmt$(d.fdv)),
    stat("Volume 24h", fmt$(d.volume_24h)),
    stat("Liquidity", fmt$(d.liquidity)),
    stat("Supply", d.supply ? fmt(parseFloat(d.supply)) : "—"),
    stat("24h Change", d.change_24h == null ? "—" : pct(d.change_24h)),
  ];

  $("#token").innerHTML = `
    <div class="tok-head">
      <div class="tok-title">
        <div class="tok-icon">${d.img ? `<img src="${esc(d.img)}" style="width:100%;height:100%;border-radius:50%;object-fit:cover" onerror="this.style.display='none'">` : esc((d.symbol || "•")[0])}</div>
        <div>
          <div class="tok-name">${esc(d.symbol || d.name)}</div>
          <div class="tok-mtrl">
            <span class="pill">Solana</span><span class="pill">${esc(d.dex || "dex")}</span>
            <span class="pill" onclick="go('#/')">← back</span>
          </div>
        </div>
      </div>
      <div class="tok-price"><div class="px-big">${d.price == null ? "—" : "$" + fmtPx(d.price)}</div><div class="px-chg ${d.change_24h == null ? "" : (d.change_24h >= 0 ? "up" : "down")}">${d.change_24h == null ? "—" : pct(d.change_24h)}</div></div>
    </div>

    <div class="stat-grid">${stats}</div>

    <div class="chart-panel">
      <div class="chart-head"><div class="tf" id="tf">${["5m", "15m", "1h", "4h", "1d"].map((i) => `<button data-i="${i}" class="${i === "15m" ? "active" : ""}">${i}</button>`).join("")}</div><div class="legend" id="lg"></div></div>
      <canvas id="chart"></canvas>
    </div>

    <div class="flow">
      <div class="flow-top"><span class="t">Buy / Sell Flow (24h)</span><span class="n">${hasFlow ? (buy + sell) + " trades" : "no data"}</span></div>
      <div class="split"><div class="buys" style="width:${buyPct}%"></div><div class="sells" style="width:${100 - buyPct}%"></div></div>
      <div class="flow-nums"><span class="b">${hasFlow ? `▲ ${buy} buys · ${d.buyers_24h || 0} buyers` : "▲ —"}</span><span class="s">${hasFlow ? `▼ ${sell} sells · ${d.sellers_24h || 0} sellers` : "▼ —"}</span></div>
      ${flowTimeline(d.txns)}
    </div>

    <div class="two">
      <div class="panel"><div class="t">Top Holders</div><div class="bucket">${holderRows}</div></div>
      <div class="panel"><div class="t">About</div>
        <p style="color:var(--muted);font-size:12.5px">${esc(d.description || "No description.")}</p>
        <div class="tok-mtrl">${soc}${(d.websites || []).map((w) => `<a href="${esc(w)}" target="_blank" rel="noopener" class="pill">site</a>`).join(" ")}</div>
        <div class="c-meta" style="margin-top:8px">${esc(d.mint)}</div>
      </div>
    </div>`;

  bindMemecoinTf(d.pool);
  drawChart($("#chart"), candles);
  state.tokenCoin = d.pool;
  state.tokenName = d.symbol;
}

function bindMemecoinTf(pool) {
  $$("#tf button").forEach((b) => (b.onclick = async () => {
    $$("#tf button").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    if (!pool) return;
    try {
      const c = await api(`/api/memecoins/candles?pool=${encodeURIComponent(pool)}&interval=${b.dataset.i}`);
      drawChart($("#chart"), c.candles || []);
    } catch (e) { toast(e.message); }
  }));
}

/* ---------- token detail ---------- */
async function showToken(name) {
  $("#screener").classList.add("hidden");
  $("#token").classList.remove("hidden");
  $("#token").innerHTML = '<div class="spinner">Loading token…</div>';
  try {
    // resolve the exact API coin (pair name for spot) first, then fetch the rest
    const detail = await api(`/api/token?name=${encodeURIComponent(name)}&market=${state.market}`);
    const coin = detail.coin || name;
    const [candles, flow, trades, book] = await Promise.all([
      api(`/api/candles?name=${encodeURIComponent(coin)}&market=${state.market}&interval=1m&limit=150`),
      api(`/api/flow?name=${encodeURIComponent(coin)}&market=${state.market}`),
      api(`/api/trades?name=${encodeURIComponent(coin)}&market=${state.market}&limit=50`),
      api(`/api/orderbook?name=${encodeURIComponent(coin)}`),
    ]);
    renderToken(detail, candles, flow, trades, book);
    scheduleRefresh();
  } catch (e) {
    $("#token").innerHTML = `<div class="error">Could not load ${esc(name)}.<br>${esc(e.message)}</div>`;
  }
}

function renderToken(d, candlesJson, flowJson, tradesJson, bookJson) {
  const candles = candlesJson.candles || [];
  const flow = flowJson.flow || {};
  const trades = tradesJson.trades || [];
  const bids = (bookJson && bookJson.bids) || [];
  const asks = (bookJson && bookJson.asks) || [];

  const bookRow = (arr, isAsk) => {
    if (!arr.length) return '<div class="spinner" style="padding:12px">No book</div>';
    const max = Math.max(...arr.map((a) => parseFloat(a.sz)), 0.000001);
    const rows = arr.map((a) => {
      const sz = parseFloat(a.sz);
      return `<div class="bp"><span class="p ${isAsk ? "ask" : ""}">${fmtPx(parseFloat(a.px))}</span><span class="num">${fmt(sz)}</span><div class="lvl"><span style="left:${isAsk ? 100 - (sz / max) * 100 : 0}%;width:${(sz / max) * 100}%;background:${isAsk ? "#ef4444" : "#22c55e"}"></span></div></div>`;
    }).join("");
    return rows;
  };
  const f = flow;
  const buyPct = Math.round((f.buy_ratio ?? 0.5) * 100);

  const statCards = state.market === "perp" ? [
    ["Volume 24h", "$" + fmt(d.volume_24h)],
    ["Open Interest", fmt(d.open_interest)],
    ["Funding", (d.funding * 100).toFixed(4) + "%"],
    ["Oracle Price", fmtPx(d.oracle_px)],
    ["Max Leverage", (d.max_leverage ?? "—") + "x"],
    ["24h Change", pct(d.change_24h)],
  ] : [
    ["Volume 24h", "$" + fmt(d.volume_24h)],
    ["Market Cap", "$" + fmt(d.market_cap)],
    ["FDV", "$" + fmt(d.fully_diluted_cap)],
    ["Circulating", fmt(d.circulating_supply)],
    ["Total Supply", fmt(d.total_supply)],
    ["24h Change", pct(d.change_24h)],
  ];

  const tradeRows = trades.map((t) => {
    const side = t.side === "B" ? "BUY" : "SELL";
    return `<div class="trade">
      <span class="t-side ${side}">${side}</span>
      <span class="num">${fmtPx(parseFloat(t.px))}</span>
      <span class="t-time">${timeStr(t.time)}</span>
    </div>`;
  }).join("");

  const whales = (flowJson.whales || []).map((w) => {
    const side = w.side === "B" ? "BUY" : "SELL";
    return `<div class="trade">
      <span class="t-side ${side}">${side}</span>
      <span class="num">$${fmt(w.notional)}</span>
      <span class="t-time">${fmtPx(w.price)}</span>
    </div>`;
  }).join("");

  $("#token").innerHTML = `
    <div class="tok-head">
      <div class="tok-title">
        <div class="tok-icon">${esc(d.name[0])}</div>
        <div>
          <div class="tok-name">${esc(d.name)}</div>
          <div class="tok-mtrl">
            <span class="pill">${state.market === "perp" ? "Perp" : "Spot"}</span>
            ${state.market === "spot" ? `<span class="pill">${esc(d.base_symbol)}</span>` : ""}
            <span class="pill" onclick="go('#/')">← back</span>
          </div>
        </div>
      </div>
      <div class="tok-price">
        <div class="px-big">$${fmtPx(d.price)}</div>
        <div class="px-chg ${d.change_24h >= 0 ? "up" : "down"}">${pct(d.change_24h)}</div>
      </div>
    </div>

    <div class="stat-grid">${statCards.map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("")}</div>

    <div class="chart-panel">
      <div class="chart-head">
        <div class="tf" id="tf">
          ${["1m","5m","15m","1h","4h","1d"].map((i) => `<button data-i="${i}" class="${i==="1m"?"active":""}">${i}</button>`).join("")}
        </div>
        <div class="legend" id="lg"></div>
      </div>
      <canvas id="chart"></canvas>
    </div>

    <div class="flow">
      <div class="flow-top"><span class="t">Buy / Sell Flow</span><span class="n">recent trades</span></div>
      <div class="split"><div class="buys" id="flowBuys" style="width:${buyPct}%"></div><div class="sells" id="flowSells" style="width:${100 - buyPct}%"></div></div>
      <div class="flow-nums">
        <span class="b" id="flowBuyNum">▲ Buy $${fmt(f.buy_volume)} · ${f.buy_count}</span>
        <span class="s" id="flowSellNum">▼ Sell $${fmt(f.sell_volume)} · ${f.sell_count}</span>
      </div>
    </div>

    <div class="panel book">
      <div class="t">Order Book</div>
      <div class="book-cols">
        <div><div class="bk-h">Bids</div>${bookRow(bids, false)}</div>
        <div><div class="bk-h">Asks</div>${bookRow(asks, true)}</div>
      </div>
    </div>

    <div class="two">
      <div class="panel">
        <div class="t">Recent Trades</div>
        <div class="feed" id="tradeFeed">${tradeRows || '<div class="spinner">No trades</div>'}</div>
      </div>
      <div class="panel">
        <div class="t">Whale Moves <span style="color:var(--muted2);font-weight:400;font-size:11px">— largest notional</span></div>
        <div class="feed" id="whaleFeed">${whales || '<div class="spinner">No whales</div>'}</div>
      </div>
    </div>`;

  bindToken(d.coin || d.name);
  drawChart($("#chart"), candles);
  state.tokenName = d.name;
  state.tokenCoin = d.coin || d.name;
}

function bindToken(coin) {
  $$("#tf button").forEach((b) => (b.onclick = async () => {
    $$("#tf button").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    try {
      const c = await api(`/api/candles?name=${encodeURIComponent(coin)}&market=${state.market}&interval=${b.dataset.i}&limit=150`);
      drawChart($("#chart"), c.candles || []);
    } catch (e) { toast(e.message); }
  }));
}

/* ---------- candlestick chart ---------- */
function drawChart(canvas, candles) {
  if (!canvas) return;
  const light = document.documentElement.dataset.theme === "light";
  const GRID = light ? "rgba(0,0,0,.07)" : "rgba(255,255,255,.05)";
  const AXIS = light ? "#64748b" : "#5b6272";
  const BASE = light ? "rgba(0,0,0,.12)" : "rgba(255,255,255,.08)";
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.clientWidth, H = canvas.clientHeight || 360;
  canvas.width = W * dpr; canvas.height = H * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);

  if (!candles || candles.length < 2) {
    ctx.fillStyle = AXIS; ctx.font = "13px sans-serif"; ctx.textAlign = "center";
    ctx.fillText("No candle data", W / 2, H / 2);
    return;
  }
  const mine = Math.min(...candles.map((c) => parseFloat(c.l)));
  const maxe = Math.max(...candles.map((c) => parseFloat(c.h)));
  const pad = (maxe - mine) * 0.04 || 0.0001;
  let lo = mine - pad, hi = maxe + pad;
  const R = 58, B = 22, L = 8, T = 8;
  const plotW = W - L - R, plotH = H - T - B;
  const n = candles.length;
  const step = plotW / n;
  const bw = Math.max(1, Math.min(10, step * 0.62));
  const x = (i) => L + step * i + step / 2;
  const y = (p) => T + (hi - p) / (hi - lo) * plotH;

  // grid + price labels
  ctx.strokeStyle = GRID; ctx.fillStyle = AXIS;
  ctx.font = "10px sans-serif"; ctx.textAlign = "left";
  const steps = 5;
  for (let g = 0; g <= steps; g++) {
    const p = lo + (hi - lo) * (g / steps);
    const gy = y(p);
    ctx.beginPath(); ctx.moveTo(L, gy); ctx.lineTo(W - R, gy); ctx.stroke();
    ctx.fillText(fmtPx(p), W - R + 4, gy + 3);
  }
  // time labels
  ctx.textAlign = "center";
  const tstep = Math.max(1, Math.floor(n / 4));
  for (let i = 0; i < n; i += tstep) {
    const t = candles[i].t;
    ctx.fillText(new Date(t).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }), x(i), H - 6);
  }

  // volume zone
  const vh = plotH * 0.16;
  const vBase = T + plotH;
  const vmax = Math.max(...candles.map((c) => parseFloat(c.v)), 1);

  // candles
  for (let i = 0; i < n; i++) {
    const c = candles[i];
    const o = parseFloat(c.o), h = parseFloat(c.h), l = parseFloat(c.l), cl = parseFloat(c.c);
    const up = cl >= o;
    ctx.strokeStyle = up ? "#22c55e" : "#ef4444";
    ctx.fillStyle = up ? "#22c55e" : "#ef4444";
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x(i), y(l)); ctx.lineTo(x(i), y(h)); ctx.stroke();
    const yo = y(o), yc = y(cl);
    const top = Math.min(yo, yc), hh = Math.max(1, Math.abs(yo - yc));
    ctx.fillRect(x(i) - bw / 2, top, bw, hh);
    // volume
    const vhgt = (parseFloat(c.v) / vmax) * vh;
    ctx.globalAlpha = 0.35;
    ctx.fillRect(x(i) - bw / 2, vBase - vhgt, bw, vhgt);
    ctx.globalAlpha = 1;
  }
  ctx.strokeStyle = BASE;
  ctx.beginPath(); ctx.moveTo(L, vBase); ctx.lineTo(W - R, vBase); ctx.stroke();

  // legend
  const last = candles[n - 1], first = candles[0];
  const lg = $("#lg");
  if (lg) lg.innerHTML = `
    <span>O <b>${fmtPx(last.o)}</b></span><span>H <b>${fmtPx(last.h)}</b></span>
    <span>L <b>${fmtPx(last.l)}</b></span><span>C <b>${fmtPx(last.c)}</b></span>
    <span>Vol <b>${fmt(last.v)}</b></span><span style="opacity:.6">${n} bars</span>`;

  // crosshair
  canvas._state = { candles, x, y, W, H, lo, hi, R, L, T };
}

async function refreshTokenLive(name) {
  const coin = state.tokenCoin || name;
  try {
    const [flow, trades] = await Promise.all([
      api(`/api/flow?name=${encodeURIComponent(coin)}&market=${state.market}`),
      api(`/api/trades?name=${encodeURIComponent(coin)}&market=${state.market}&limit=50`),
    ]);
    const f = flow.flow || {};
    const buyPct = Math.round((f.buy_ratio ?? 0.5) * 100);
    const b = $("#flowBuys"), s = $("#flowSells");
    if (b) b.style.width = buyPct + "%";
    if (s) s.style.width = (100 - buyPct) + "%";
    const bn = $("#flowBuyNum"); if (bn) bn.textContent = `▲ Buy $${fmt(f.buy_volume)} · ${f.buy_count}`;
    const sn = $("#flowSellNum"); if (sn) sn.textContent = `▼ Sell $${fmt(f.sell_volume)} · ${f.sell_count}`;
    const ff = $("#tradeFeed");
    if (ff) ff.innerHTML = (trades.trades || []).map((t) => {
      const side = t.side === "B" ? "BUY" : "SELL";
      return `<div class="trade"><span class="t-side ${side}">${side}</span><span class="num">${fmtPx(parseFloat(t.px))}</span><span class="t-time">${timeStr(t.time)}</span></div>`;
    }).join("");
    const wf = $("#whaleFeed");
    if (wf) wf.innerHTML = (flow.whales || []).map((w) => {
      const side = w.side === "B" ? "BUY" : "SELL";
      return `<div class="trade"><span class="t-side ${side}">${side}</span><span class="num">$${fmt(w.notional)}</span><span class="t-time">${fmtPx(w.price)}</span></div>`;
    }).join("");
  } catch (e) { /* silent live fail */ }
}

let refreshTimer = null;
function scheduleRefresh() {
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(() => {
    if (location.hash.startsWith("#/token") && state.tokenName) refreshTokenLive(state.tokenName);
    else if (location.hash.startsWith("#/meme")) { if (state.venue === "meme" && state.memeLoaded) loadMemecoinScreener(); }
    else if (state.venue === "meme") loadMemecoinScreener();
    else reloadScreener();
  }, 45000);
}

/* ---------- theme ---------- */
function applyTheme() {
  const t = localStorage.getItem("gmgn_theme") === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = t;
  const btn = $("#themeBtn");
  if (btn) btn.textContent = t === "light" ? "☀️" : "🌙";
}
function toggleTheme() {
  const t = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  localStorage.setItem("gmgn_theme", t);
  applyTheme();
  const c = $("#chart"); if (c && c._state) drawChart(c, c._state.candles);
}

/* ---------- events ---------- */
function bindGlobal() {
  $$("#themeBtn").forEach((b) => (b.onclick = toggleTheme));
  $$("#venueToggle button").forEach((b) => (b.onclick = () => {
    state.venue = b.dataset.v;
    updateVenue();
    state.q = "";
    const s = $("#search"); if (s) s.value = "";
    // jump to the screener of that venue
    location.hash = "#/";
    showScreener();
  }));
  $$("#marketToggle button").forEach((b) => (b.onclick = () => {
    $$("#marketToggle button").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    state.market = b.dataset.m;
    state.venue = "hl";
    showScreener();
  }));
  const s = $("#search");
  s.addEventListener("input", debounce(() => { state.q = s.value.trim(); if (state.venue === "meme") renderMemecoinScreener(); else renderScreener(); }, 250));
  s.addEventListener("keydown", (e) => { if (e.key === "Enter") { const q = s.value.trim(); if (!q) return; if (state.venue === "meme") { const m = state.memeRows.find((r) => (r.symbol || "").toLowerCase().includes(q.toLowerCase())); if (m && m.mint) location.hash = `#/meme/${encodeURIComponent(m.mint)}`; } else { if (/^\d+$/.test(q) === false) location.hash = `#/token/${state.market}/${encodeURIComponent(q)}`; } } });
  window.addEventListener("resize", debounce(() => { const c = $("#chart"); if (c && c._state) drawChart(c, c._state.candles); }, 200));
}

applyTheme();
bindGlobal();
route();
