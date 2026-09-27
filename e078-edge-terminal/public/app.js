/* Edge Terminal — app logic: board, decision engine, paper portfolio, LP. */
'use strict';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

/* ------------------------------------------------------------ state */
const S = {
  cfg: null,
  board: null,
  yields: null,
  tab: 'markets',
  coin: 'BTC',
  interval: '1h',
  tier: 'balanced',
  sort: { key: 'volume24hUsd', dir: -1 },
  filter: '',
  onlySignals: false,
  candles: [],
  chart: null,
  selectedPool: null,
  lpOnlyStables: false,
  pf: null,
  lastTicker: 0,
};

const LS = {
  pf: 'e078.portfolio',
  tier: 'e078.tier',
  coin: 'e078.coin',
};

/* ---------------------------------------------------------- helpers */
const fmt = {
  price(v, coin) {
    if (v == null || isNaN(v)) return '—';
    const d = v >= 1000 ? 2 : v >= 100 ? 3 : v >= 1 ? 4 : v >= 0.01 ? 5 : 7;
    return v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  },
  usd(v, d = 2) {
    if (v == null || isNaN(v)) return '—';
    return (v < 0 ? '-$' : '$') + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  },
  compact(v) {
    if (v == null || isNaN(v)) return '—';
    const a = Math.abs(v);
    const s = v < 0 ? '-' : '';
    if (a >= 1e9) return s + '$' + (a / 1e9).toFixed(2) + 'B';
    if (a >= 1e6) return s + '$' + (a / 1e6).toFixed(1) + 'M';
    if (a >= 1e3) return s + '$' + (a / 1e3).toFixed(1) + 'K';
    return s + '$' + a.toFixed(0);
  },
  pct(v, sign = true) {
    if (v == null || isNaN(v)) return '—';
    return (sign && v > 0 ? '+' : '') + v.toFixed(2) + '%';
  },
  cls(v) { return v == null ? 'neutral' : v > 0 ? 'up' : v < 0 ? 'down' : 'neutral'; },
  time(ts) {
    return new Date(ts).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  },
  hour(ts) {
    return new Date(ts).toLocaleString('en-US', { hour: '2-digit', minute: '2-digit' });
  },
};

function toast(msg, kind = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + kind;
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; }, 3200);
  setTimeout(() => el.remove(), 3600);
}

async function api(path) {
  const res = await fetch(path, { cache: 'no-store' });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

/* ------------------------------------------------------- portfolio */
function defaultPF() {
  return { cash: 10000, open: [], lp: [], hist: [], ts: Date.now() };
}
function loadPF() {
  try {
    const raw = localStorage.getItem(LS.pf);
    if (raw) { const p = JSON.parse(raw); if (p && typeof p.cash === 'number') return p; }
  } catch (e) { /* corrupted -> reset */ }
  return defaultPF();
}
function savePF() { localStorage.setItem(LS.pf, JSON.stringify(S.pf)); }
function equity() {
  let e = S.pf.cash;
  for (const p of S.pf.open) e += p.margin + unrealized(p);
  for (const p of S.pf.lp) e += lpValue(p);
  return e;
}
function markOf(coin) {
  const m = S.board && S.board.markets.find((x) => x.coin === coin);
  return m ? m.price : null;
}
function unrealized(p) {
  const mark = markOf(p.coin);
  if (mark == null) return 0;
  const dir = p.side === 'long' ? 1 : -1;
  return ((mark - p.entry) / p.entry) * p.notional * dir;
}
function lpValue(p) {
  const hours = (Date.now() - p.ts) / 3600e3;
  return p.principal * (1 + (p.apy / 100) * (hours / 8760));
}
function ledgerPost(event, payload) {
  // fire-and-forget: the server keeps the durable copy so the gate is auditable
  try {
    fetch('/api/ledger', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify(Object.assign({ event }, payload)),
    }).catch(() => {});
  } catch (e) { /* offline */ }
}

function openPosition({ coin, side, price, stopDist, targetDist, lev, notional, tier }) {
  const P = S.cfg.paper;
  const eq = equity();
  // portfolio-level risk rails (config, not code)
  if (S.pf.open.length >= P.maxOpenPositions)
    return { error: `Risk rail: max ${P.maxOpenPositions} open positions` };
  const totalNotional = S.pf.open.reduce((a, p) => a + p.notional, 0) + S.pf.lp.reduce((a, p) => a + p.principal, 0);
  if (totalNotional + notional > eq * (P.maxTotalNotionalPct / 100))
    return { error: `Risk rail: total exposure capped at ${P.maxTotalNotionalPct}% of equity` };
  const perCoin = S.pf.open.filter((p) => p.coin === coin).reduce((a, p) => a + p.notional, 0);
  if (perCoin + notional > eq * (P.maxPerCoinNotionalPct / 100))
    return { error: `Risk rail: ${coin} exposure capped at ${P.maxPerCoinNotionalPct}% of equity` };

  // fills pay slippage against you; stop/target distances stay anchored to the fill
  const dir = side === 'long' ? 1 : -1;
  const slip = (P.slippagePct || 0) / 100;
  const entry = price * (1 + slip * dir);
  const stop = entry - dir * stopDist;
  const target = entry + dir * targetDist;
  const fees = notional * ((P.feePctPerSide || 0) / 100);
  const margin = notional / lev;
  if (margin + fees > S.pf.cash) return { error: 'Not enough paper cash (need ' + fmt.usd(margin + fees) + ')' };

  S.pf.cash -= margin + fees;
  S.pf.open.push({
    id: 'p' + Date.now().toString(36), coin, side, entry, notional, lev, size: notional / entry,
    stop, target, tier, ts: Date.now(), fees, margin, mark0: price,
  });
  savePF();
  ledgerPost('open', { coin, side, entry: round(entry), notional, lev, tier, fees: round(fees), equity: round(equity()) });
  return { ok: true, entry };
}
function round(v) { return Math.round(v * 100) / 100; }
function closePosition(id, reason = 'manual') {
  const i = S.pf.open.findIndex((p) => p.id === id);
  if (i < 0) return;
  const p = S.pf.open[i];
  const P = S.cfg.paper;
  const mark = markOf(p.coin) != null ? markOf(p.coin) : p.entry;
  const dir = p.side === 'long' ? 1 : -1;
  const slip = (P.slippagePct || 0) / 100;
  const exit = mark * (1 - slip * dir); // close pays slippage too
  const pnl = ((exit - p.entry) / p.entry) * p.notional * dir;
  const feeClose = p.notional * ((P.feePctPerSide || 0) / 100);
  const net = pnl - feeClose;
  S.pf.cash += p.margin + net;
  const risk = Math.abs(p.entry - p.stop);
  const riskUsd = (risk / p.entry) * p.notional;
  const r = riskUsd > 0 ? net / riskUsd : 0;
  S.pf.hist.unshift({
    ts: Date.now(), coin: p.coin, side: p.side, entry: p.entry, exit: round(exit),
    pnl: round(net), r: Math.round(r * 100) / 100, reason, tier: p.tier,
  });
  S.pf.open.splice(i, 1);
  savePF();
  ledgerPost('close', { coin: p.coin, side: p.side, entry: round(p.entry), exit: round(exit), pnl: round(net), r: Math.round(r * 100) / 100, reason, equity: round(equity()) });
  return net;
}
function checkLiquidations() {
  const cushion = S.cfg.paper.liqCushion != null ? S.cfg.paper.liqCushion : 0.95;
  for (const p of [...S.pf.open]) {
    const u = unrealized(p);
    if (u <= -p.margin * cushion) {
      closePosition(p.id, 'liquidation');
      toast(`☠ Liquidated ${p.coin} ${p.side} at ${fmt.price(markOf(p.coin), p.coin)}`, 'err');
    } else if (u > 0 && ((p.side === 'long' && markOf(p.coin) >= p.target) ||
                         (p.side === 'short' && markOf(p.coin) <= p.target))) {
      closePosition(p.id, 'take-profit');
      toast(`✓ ${p.coin} ${p.side} closed at target`, 'ok');
    } else if (u < 0 && ((p.side === 'long' && markOf(p.coin) <= p.stop) ||
                         (p.side === 'short' && markOf(p.coin) >= p.stop))) {
      closePosition(p.id, 'stop-loss');
      toast(`✕ ${p.coin} ${p.side} stopped out`, 'err');
    }
  }
}

/* --------------------------------------------------- decision engine */
function decide(row, tierKey) {
  const t = S.cfg.tiers[tierKey];
  // all arithmetic lives in engine.js (shared with the server and the test suite)
  const d = EdgeMath.decide(row, {
    tiers: S.cfg.tiers, paper: S.cfg.paper, equityUsd: equity(), tierKey, signal: S.cfg.signal,
  });
  const price = row.price;

  const reasons = [];
  if (row.sma20 && row.sma50) {
    if (price > row.sma20 && row.sma20 > row.sma50) reasons.push('uptrend (price > SMA20 > SMA50)');
    else if (price < row.sma20 && row.sma20 < row.sma50) reasons.push('downtrend (price < SMA20 < SMA50)');
    else reasons.push('mixed trend — MAs not aligned');
  }
  if (row.rsi != null) reasons.push(`RSI ${row.rsi}${row.rsi >= 70 ? ' (overbought)' : row.rsi <= 30 ? ' (oversold)' : ''}`);
  if (row.ret7dPct != null) reasons.push(`7d ${fmt.pct(row.ret7dPct)}`);
  reasons.push(`funding ${fmt.pct(row.fundingAprPct)} APR` + (row.fundingZ != null ? ` (z ${row.fundingZ.toFixed(1)})` : ''));

  d.row = row;
  d.price = price;
  d.reasons = reasons;
  d.hist = histFor(row.coin);
  d.lpBest = bestPool(tierKey);
  return d;
}

function histFor(coin) {
  if (!S.backtest) return null;
  const c = (S.backtest.coins || []).find((x) => x.coin === coin);
  return c && c.n ? c : null;
}

function poolsFor(tierKey) {
  if (!S.yields) return [];
  const pools = S.yields.pools.slice();
  if (tierKey === 'conservative') {
    const st = pools.filter((p) => p.stablecoin && p.tvlUsd >= 20e6);
    return (st.length ? st : pools.filter((p) => p.stablecoin)).sort((a, b) => b.apy - a.apy);
  }
  if (tierKey === 'balanced') return pools.filter((p) => p.tvlUsd >= 20e6).sort((a, b) => b.apy - a.apy);
  return pools.sort((a, b) => b.apy - a.apy);
}
function bestPool(tierKey) { return poolsFor(tierKey)[0] || null; }

/* ------------------------------------------------------ tabs & routing */
function setTab(tab) {
  S.tab = tab;
  $$('.tab').forEach((el) => el.classList.toggle('active', el.dataset.tab === tab));
  $$('.tb').forEach((el) => {
    const on = el.dataset.tab === tab;
    el.classList.toggle('active', on);
    el.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  if (tab === 'trade') { loadCandles(); }
  if (tab === 'portfolio') renderPortfolio();
  if (tab === 'lp') renderLP();
  if (tab === 'launch') renderLaunch();
  syncURL();
}
function syncURL() {
  const u = new URL(location.href);
  u.searchParams.set('tab', S.tab);
  u.searchParams.set('coin', S.coin);
  u.searchParams.set('tier', S.tier);
  history.replaceState(null, '', u);
}
function readURL() {
  const u = new URL(location.href);
  const tab = u.searchParams.get('tab');
  const coin = u.searchParams.get('coin');
  const tier = u.searchParams.get('tier');
  if (tier && S.cfg.tiers[tier]) S.tier = tier;
  if (coin && S.cfg.universe.includes(coin)) S.coin = coin;
  if (['markets', 'trade', 'lp', 'portfolio', 'launch'].includes(tab)) S.tab = tab;
}

/* --------------------------------------------------------- markets */
function sortedRows() {
  let rows = (S.board && S.board.markets ? S.board.markets : []).slice();
  const f = S.filter.trim().toUpperCase();
  if (f) rows = rows.filter((r) => r.coin.includes(f));
  if (S.onlySignals) rows = rows.filter((r) => r.label !== 'NEUTRAL');
  const { key, dir } = S.sort;
  rows.sort((a, b) => {
    const av = a[key], bv = b[key];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === 'string') return av.localeCompare(bv) * dir;
    return (av - bv) * dir;
  });
  return rows;
}

function renderMarkets() {
  const rows = sortedRows();
  const body = $('#m-body');
  body.innerHTML = rows.map((r) => `
    <tr data-coin="${r.coin}" class="${r.coin === S.coin ? 'sel' : ''}">
      <td><div class="coincell"><span class="coin-dot" style="background:${r.label === 'LONG' ? 'var(--up)' : r.label === 'SHORT' ? 'var(--down)' : 'var(--dim)'}"></span>${r.coin}<span class="muted" style="font-weight:400">×${r.maxLeverage}</span></div></td>
      <td class="num">${fmt.price(r.price, r.coin)}</td>
      <td class="num ${fmt.cls(r.change24hPct)}">${fmt.pct(r.change24hPct)}</td>
      <td class="num ${r.fundingAprPct > 25 ? 'down' : r.fundingAprPct < -5 ? 'up' : 'neutral'}">${fmt.pct(r.fundingAprPct)}</td>
      <td class="num">${fmt.compact(r.oiUsd)}</td>
      <td class="num ${r.rsi >= 70 ? 'down' : r.rsi <= 30 ? 'up' : ''}">${r.rsi ?? '—'}</td>
      <td class="num ${fmt.cls(r.ret7dPct)}">${fmt.pct(r.ret7dPct)}</td>
      <td class="num"><span class="sig ${r.label}">${r.label}</span></td>
      <td class="num"><div class="conf"><div class="bar"><i style="width:${r.confidence}%"></i></div><span>${r.confidence}</span></div></td>
    </tr>`).join('');

  $$('#m-body tr').forEach((tr) => {
    tr.addEventListener('click', () => {
      S.coin = tr.dataset.coin;
      localStorage.setItem(LS.coin, S.coin);
      renderMarkets();
      renderTrade();
      setTab('trade');
      toast(`${S.coin} loaded into Trade`);
    });
  });

  const sigs = (S.board.markets || []).filter((r) => r.label !== 'NEUTRAL').length;
  const stale = (S.board.markets || []).filter((r) => r.stale).map((r) => r.coin);
  $('#m-foot').textContent =
    `${rows.length}/${S.board.markets.length} markets · ${sigs} actionable signals · data ${new Date(S.board.generatedAt).toLocaleTimeString()} · source Hyperliquid perps` +
    (stale.length ? ` · stale indicators (cached): ${stale.join(', ')}` : '');
}

/* ----------------------------------------------------------- chart */
async function loadCandles() {
  $('#chart-loading').style.display = 'grid';
  try {
    const data = await api(`/api/candles?coin=${S.coin}&interval=${S.interval}&limit=400`);
    S.candles = data.candles;
    const closes = S.candles.map((c) => c.c);
    const ma20 = smaSeries(closes, 20), ma50 = smaSeries(closes, 50);
    S.chart.setData(S.candles, [
      { rgb: [0.3, 0.64, 1], values: ma20 },
      { rgb: [1, 0.71, 0.33], values: ma50 },
    ]);
    $('#chart-loading').style.display = 'none';
    renderChartStats();
  } catch (e) {
    $('#chart-loading').textContent = 'chart error: ' + e.message;
  }
}
function smaSeries(vals, p) {
  const out = new Array(vals.length).fill(null);
  let sum = 0;
  for (let i = 0; i < vals.length; i++) {
    sum += vals[i];
    if (i >= p) sum -= vals[i - p];
    if (i >= p - 1) out[i] = sum / p;
  }
  return out;
}
function renderChartStats() {
  const row = marketRow();
  if (!row || !S.candles.length) return;
  const last = S.candles[S.candles.length - 1];
  $('#chart-stats').innerHTML = `
    <span>O <b>${fmt.price(last.o, S.coin)}</b></span>
    <span>H <b class="up">${fmt.price(last.h, S.coin)}</b></span>
    <span>L <b class="down">${fmt.price(last.l, S.coin)}</b></span>
    <span>C <b>${fmt.price(last.c, S.coin)}</b></span>
    <span>ATR <b>${row.atrPct ? row.atrPct.toFixed(2) + '%' : '—'}</b></span>
    <span>SMA20 <b>${row.sma20 ? fmt.price(row.sma20, S.coin) : '—'}</b></span>
    <span>SMA50 <b>${row.sma50 ? fmt.price(row.sma50, S.coin) : '—'}</b></span>
    <span class="muted">wheel / pinch = zoom · drag = pan</span>`;
}
function marketRow() {
  return S.board && S.board.markets.find((m) => m.coin === S.coin);
}

/* ----------------------------------------------------------- trade */
function renderTrade() {
  const row = marketRow();
  $('#t-coin').textContent = S.coin;

  // tier selector
  $('#t-tiers').innerHTML = Object.entries(S.cfg.tiers).map(([key, t]) => `
    <div class="tier ${key === S.tier ? 'on' : ''}" data-tier="${key}">
      <div class="t-name">${t.label}</div>
      <div class="t-sub">${t.riskPct}% · ${t.maxLeverage}x</div>
    </div>`).join('');
  $$('#t-tiers .tier').forEach((el) => el.addEventListener('click', () => {
    S.tier = el.dataset.tier;
    localStorage.setItem(LS.tier, S.tier);
    renderTrade(); renderLP(); syncURL();
    toast(`Risk tier: ${S.cfg.tiers[S.tier].label} — ${S.cfg.tiers[S.tier].blurb}`);
  }));

  if (!row) { $('#t-decision').innerHTML = '<p class="empty">No market data yet.</p>'; return; }
  const d = decide(row, S.tier);
  const t = d.tier;

  let head, body;
  if (d.actionable) {
    const p = d.plan;
    const long = d.side === 'long';
    head = `<div class="dec-act ${long ? 'up' : 'down'}">${long ? '▲ LONG' : '▼ SHORT'} ${S.coin}</div>
            <div class="dec-head-right">
              ${d.actionable ? `<span class="sig ${long ? 'LONG' : 'SHORT'}">conf ${d.row.confidence}</span>` : ''}
              <button class="btn ghost sm" id="t-sharecard" title="Export a shareable PNG of this call">share card</button>
            </div>
            <div class="conf full"><div class="bar"><i style="width:${d.row.confidence}%"></i></div>
              <span>conviction ${d.row.confidence}/100 · score ${d.score.toFixed(2)}</span></div>`;
    body = `<div class="kv">
      <div class="k">Entry (market, incl. slippage)</div><div class="v">${fmt.price(p.entry, S.coin)}</div>
      <div class="k">Stop ${t.stopAtr}×ATR</div><div class="v down">${fmt.price(p.stop, S.coin)}</div>
      <div class="k">Target ${t.targetAtr}×ATR</div><div class="v up">${fmt.price(p.target, S.coin)}</div>
      <div class="k">Position size</div><div class="v">${fmt.usd(p.notional, 0)}</div>
      <div class="k">Leverage / margin</div><div class="v">${p.lev}× / ${fmt.usd(p.margin, 0)}</div>
      <div class="k">Liquidation buffer</div><div class="v">≈ ${p.liqPct.toFixed(1)}% adverse</div>
      <div class="k">Risk per trade</div><div class="v">${fmt.usd(p.riskUsd, 0)} (${t.riskPct}%)</div>
      <div class="k">Reward : risk</div><div class="v">${d.rr.toFixed(2)} : 1</div>
      <div class="k">Round-trip fee + slippage</div><div class="v ${p.feeShareOfRisk > 0.1 ? 'down' : ''}">${fmt.usd(p.fees * 2, 2)}${p.feeShareOfRisk != null ? ` · ${(p.feeShareOfRisk * 100).toFixed(0)}% of risk` : ''}</div>
    </div>`;
  } else {
    head = `<div class="dec-act neutral">⏳ WAIT</div>
            <span class="sig NEUTRAL">no setup at ${t.label}</span>
            <div class="dec-head-right"><button class="btn ghost sm" id="t-sharecard" title="Export a shareable PNG">share card</button></div>`;
    body = `<div class="kv">
      <div class="k">Signal score</div><div class="v">${d.score.toFixed(2)}</div>
      <div class="k">Needs |score| ≥</div><div class="v">${t.minScore.toFixed(2)}</div>
      <div class="k">Current ATR</div><div class="v">${row.atrPct ? row.atrPct.toFixed(2) + '%' : '—'}</div>
    </div>`;
  }

  const histLine = d.hist
    ? `<b>Receipt:</b> ${d.hist.winRate}% hit rate over ${d.hist.n} ${S.coin} calls in the ${S.cfg.backtest.days}d daily backtest (avg ${d.hist.avgR}R).`
    : (S.backtest ? `<b>Receipt:</b> no ${S.coin} calls in the ${S.cfg.backtest.days}d backtest window.` : '');
  const why = `<div class="dec-why"><b>Why:</b> ${d.reasons.join(' · ')}.
    Break-even win rate at RR ${d.rr.toFixed(2)}: <b>${(d.breakEvenWin * 100).toFixed(1)}%</b>.
    ${histLine}
    <b>Invalidate:</b> a daily close back through the ${d.side === 'long' ? 'stop' : 'target'} side of the range kills the thesis early; the stop is the hard floor.
    ${S.yields ? `<br>LP alternative for this tier: <b>${d.lpBest ? d.lpBest.symbol + ' @ ' + d.lpBest.apy + '%' : 'none found'}</b>` : ''}</div>`;

  $('#t-decision').innerHTML = `<div class="dec-head">${head}</div>${body}${why}`;

  // ticket
  const eq = equity();
  const presetNotional = d.actionable ? Math.round(d.plan.notional / 10) * 10 : 500;
  const fee = S.cfg.paper.feePctPerSide;
  $('#t-ticket').innerHTML = `
    <div class="row"><label>Size (USD notional)</label>
      <input class="input" id="tk-size" type="number" min="10" step="10" value="${presetNotional}"></div>
    <div class="preset">
      <button data-pct="25">25% risk cap</button>
      <button data-pct="100">tier size</button>
      <button data-usd="500">$500</button>
      <button data-usd="5000">$5k</button>
    </div>
    <div class="row"><label>Leverage</label>
      <select class="input" id="tk-lev">${Array.from({ length: Math.min(10, Math.max(1, row.maxLeverage)) }, (_, i) => i + 1)
        .map((l) => `<option value="${l}" ${d.actionable && l === d.plan.lev ? 'selected' : ''}>${l}×</option>`).join('')}</select></div>
    <div class="row"><label>Est. margin / liq. distance</label>
      <span class="v" id="tk-derived" style="font-family:var(--mono)">—</span></div>
    <div class="actions">
      <button class="btn up" id="tk-long">▲ Long (paper)</button>
      <button class="btn down" id="tk-short">▼ Short (paper)</button>
    </div>
    <div class="hint" style="margin:0">Paper only — cash ${fmt.usd(eq, 0)} · fee ${fee}%/side · your stop & target come from the ${t.label} tier.</div>`;

  const sizeEl = $('#tk-size'), levEl = $('#tk-lev'), derived = $('#tk-derived');
  const cushion = S.cfg.paper.liqCushion != null ? S.cfg.paper.liqCushion : 0.95;
  const updDerived = () => {
    const n = Number(sizeEl.value) || 0;
    const lev = Number(levEl.value) || 1;
    const liqDist = (1 / lev) * 100 * cushion;
    derived.textContent = `${fmt.usd(n / lev, 0)} · liq ≈ ${liqDist.toFixed(1)}% adverse`;
  };
  sizeEl.addEventListener('input', updDerived);
  levEl.addEventListener('change', updDerived);
  updDerived();
  $$('#t-ticket .preset button').forEach((b) => b.addEventListener('click', () => {
    if (b.dataset.usd) sizeEl.value = b.dataset.usd;
    else if (d.actionable) sizeEl.value = Math.round((eq * (t.riskPct / 100)) / ((d.row.atr * t.stopAtr) / d.row.price) / 10) * 10;
    else sizeEl.value = 500;
    updDerived();
  }));

  const doOpen = async (side) => {
    const n = Number(sizeEl.value);
    if (!n || n < 10) return toast('Size must be ≥ $10', 'err');
    const lev = Number(levEl.value);
    const atr = row.atr || row.price * 0.01;
    const stopDist = t.stopAtr * atr, targetDist = t.targetAtr * atr;
    const slip = (S.cfg.paper.slippagePct || 0) / 100;
    const estEntry = row.price * (1 + slip * (side === 'long' ? 1 : -1));
    const ok = await confirmDialog(
      `${side === 'long' ? '▲ Long' : '▼ Short'} ${S.coin} (paper)`,
      `<div class="kv">
        <div class="k">Notional</div><div class="v">${fmt.usd(n, 0)} at ${lev}×</div>
        <div class="k">Est. fill (with ${(S.cfg.paper.slippagePct || 0)}% slippage)</div><div class="v">${fmt.price(estEntry, S.coin)}</div>
        <div class="k">Stop / target</div><div class="v">${fmt.price(estEntry * (side === 'long' ? 1 : -1) - (side === 'long' ? stopDist : -stopDist), S.coin)} → ${fmt.price(estEntry * (side === 'long' ? 1 : -1) + (side === 'long' ? targetDist : -targetDist), S.coin)}</div>
        <div class="k">Margin + fee taken now</div><div class="v">${fmt.usd(n / lev + n * (S.cfg.paper.feePctPerSide / 100), 2)}</div>
      </div><p class="hint" style="margin:8px 0 0">Tier ${t.label}: risk ${fmt.usd(equity() * t.riskPct / 100, 0)} (${t.riskPct}% of equity). This is paper money.</p>`);
    if (!ok) return;
    const res = openPosition({
      coin: S.coin, side, price: row.price, stopDist, targetDist,
      lev, notional: n, tier: S.tier,
    });
    if (res.error) return toast(res.error, 'err');
    toast(`Paper ${side} ${S.coin}: ${fmt.usd(n, 0)} @ ${fmt.price(res.entry, S.coin)} (${lev}×)`, 'ok');
    renderPortfolio(); renderTrade();
  };
  $('#tk-long').addEventListener('click', () => doOpen('long'));
  $('#tk-short').addEventListener('click', () => doOpen('short'));
  const shareBtn = $('#t-sharecard');
  if (shareBtn) shareBtn.addEventListener('click', () => shareCard(d));
}

/* -------------------------------------------------------------- LP */
function renderLP() {
  if (!S.yields) { $('#lp-body').innerHTML = '<tr><td colspan="8" class="empty">loading yields…</td></tr>'; return; }
  let pools = S.yields.pools;
  if (S.lpOnlyStables) pools = pools.filter((p) => p.stablecoin);
  const tierPools = poolsFor(S.tier);
  const best = bestPool(S.tier);

  // compare card: trade EV vs LP APY, same weekly scale on both sides
  const row = marketRow();
  let tradeCard = '', lpCard = '';
  let tradeWeekly = null;
  if (row) {
    const d = decide(row, S.tier);
    const { winProb, evR } = EdgeMath.weeklyEvPct(d);
    const tier = d.tier;
    const tradesPerWeek = Math.max(1, Math.round(7 / Math.max(1, (d.row.atrPct || 5) * 1.6)));
    tradeWeekly = evR * tier.riskPct * tradesPerWeek;
    tradeCard = `<div class="cmp">
      <h4>Trade — ${S.coin} @ ${tier.label}</h4>
      <div class="big ${fmt.cls(evR)}">${evR > 0 ? '+' : ''}${evR.toFixed(2)}R</div>
      <p><b>Model</b> (assumption, not data): win ${(winProb * 100).toFixed(0)}% derived from score ${d.score.toFixed(2)} × RR ${d.rr.toFixed(2)} →
      <b>${tradeWeekly > 0 ? '+' : ''}${tradeWeekly.toFixed(1)}%/week</b> at ${tier.riskPct}% risk, ~${tradesPerWeek} setups/week.
      ${d.actionable ? 'Setup is <b class="up">active</b> right now.' : 'No active setup — the tier says WAIT.'}
      ${d.hist ? `Receipt for ${S.coin}: <b>${d.hist.winRate}% hit over ${d.hist.n} calls</b> in the ${S.cfg.backtest.days}d backtest.` : ''}</p></div>`;
  }
  const lpWeekly = best ? best.apy / 52 : null;
  const tradeWins = tradeWeekly != null && lpWeekly != null && tradeWeekly > lpWeekly;
  if (row) tradeCard = tradeCard.replace('class="cmp"', `class="cmp ${tradeWins ? 'best' : ''}"`);
  lpCard = `<div class="cmp ${lpWeekly != null && !tradeWins ? 'best' : ''}">
      <h4>LP — best for ${S.cfg.tiers[S.tier].label}</h4>
      <div class="big up">${best ? best.apy.toFixed(2) + '%' : '—'}</div>
      <p><b>Live data</b> (DefiLlama): ${best ? `${best.symbol} on ${best.chain} (${best.project}) · TVL ${fmt.compact(best.tvlUsd)} · IL risk ${best.ilRisk || 'n/a'}.` : 'No pool matches this tier.'}
      ≈ <b>${lpWeekly != null ? '+' + lpWeekly.toFixed(2) : '—'}%</b>/week, no directional risk (impermanent loss still applies on volatile pairs).</p></div>`;
  $('#lp-compare').innerHTML = tradeCard + lpCard;

  $('#lp-body').innerHTML = pools.map((p) => {
    const inTier = tierPools.some((x) => x.pool === p.pool);
    return `<tr data-pool="${p.pool}" class="${S.selectedPool === p.pool ? 'sel' : ''}" style="${inTier ? '' : 'opacity:.55'}">
      <td><div class="coincell">${p.symbol}<span class="muted" style="font-weight:400">${p.project}</span></div></td>
      <td>${p.chain}</td>
      <td class="num up">${p.apy.toFixed(2)}%</td>
      <td class="num">${p.apyBase == null ? '—' : p.apyBase.toFixed(2) + '%'}</td>
      <td class="num">${p.apyReward == null ? '—' : p.apyReward.toFixed(2) + '%'}</td>
      <td class="num">${fmt.compact(p.tvlUsd)}</td>
      <td>${p.stablecoin ? '<span class="sig NEUTRAL">stable</span>' : (p.ilRisk === 'yes' ? '<span class="sig SHORT">IL</span>' : '<span class="sig LONG">low</span>')}</td>
      <td class="num"><button class="btn sm ghost" data-add="${p.pool}">add paper</button></td>
    </tr>`;
  }).join('');

  $$('#lp-body tr').forEach((tr) => tr.addEventListener('click', (e) => {
    if (e.target.dataset.add) return;
    S.selectedPool = tr.dataset.pool;
    renderLP();
    const p = S.yields.pools.find((x) => x.pool === S.selectedPool);
    if (p) toast(`Selected ${p.symbol} on ${p.chain} — ${p.apy}% APY`);
  }));
  $$('#lp-body [data-add]').forEach((b) => b.addEventListener('click', async (e) => {
    e.stopPropagation();
    const p = S.yields.pools.find((x) => x.pool === b.dataset.add);
    if (!p) return;
    const principal = 250;
    const ok = await confirmDialog('Add paper LP position',
      `<div class="kv">
        <div class="k">Pool</div><div class="v">${p.symbol} · ${p.chain}</div>
        <div class="k">Protocol</div><div class="v">${p.project}</div>
        <div class="k">APY (live)</div><div class="v up">${p.apy}%</div>
        <div class="k">TVL / IL risk</div><div class="v">${fmt.compact(p.tvlUsd)} / ${p.ilRisk || 'n/a'}</div>
        <div class="k">Principal</div><div class="v">${fmt.usd(principal, 0)}</div>
      </div><p class="hint" style="margin:8px 0 0">Paper accrual compounds hourly from now. Impermanent loss is NOT modelled — treat the number as a gross yield estimate.</p>`);
    if (!ok) return;
    if (principal > S.pf.cash) return toast('Not enough paper cash', 'err');
    S.pf.cash -= principal;
    S.pf.lp.push({ id: 'l' + Date.now().toString(36), pool: p.pool, symbol: p.symbol, chain: p.chain, project: p.project, apy: p.apy, principal, ts: Date.now() });
    savePF();
    ledgerPost('lp-open', { pool: p.pool, symbol: p.symbol, chain: p.chain, apy: p.apy, principal });
    toast(`Paper LP: ${fmt.usd(principal, 0)} into ${p.symbol} @ ${p.apy}% APY`, 'ok');
    renderPortfolio();
  }));
}
/* ------------------------------------------------- modal + share card */
function confirmDialog(title, html) {
  return new Promise((resolve) => {
    const m = $('#modal');
    $('#modal-title').textContent = title;
    $('#modal-body').innerHTML = html;
    m.hidden = false;
    const done = (v) => {
      m.hidden = true;
      $('#modal-ok').onclick = null; $('#modal-cancel').onclick = null;
      document.removeEventListener('keydown', onKey);
      resolve(v);
    };
    const onKey = (e) => { if (e.key === 'Escape') done(false); if (e.key === 'Enter') done(true); };
    $('#modal-ok').onclick = () => done(true);
    $('#modal-cancel').onclick = () => done(false);
    m.onclick = (e) => { if (e.target === m) done(false); };
    document.addEventListener('keydown', onKey);
    $('#modal-ok').focus();
  });
}

/* Renders the current decision as a 1200x630 PNG — the crypto-Twitter share motion. */
async function shareCard(d) {
  const W = 1200, H = 630;
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const g = cv.getContext('2d');
  const long = d.side === 'long';
  const accent = long ? '#3ddc97' : '#ff5f6d';

  g.fillStyle = '#0a0e14'; g.fillRect(0, 0, W, H);
  g.strokeStyle = '#1f2b3a'; g.lineWidth = 2; g.strokeRect(1, 1, W - 2, H - 2);
  g.fillStyle = '#4da3ff'; g.font = '700 30px system-ui, sans-serif';
  g.fillText('▲ EDGE TERMINAL', 48, 66);
  g.fillStyle = '#7d8fa6'; g.font = '400 22px system-ui, sans-serif';
  g.fillText(S.cfg.product.tagline + ' · paper signal card', 300, 66);

  g.fillStyle = accent; g.font = '900 76px system-ui, sans-serif';
  g.fillText(d.actionable ? `${long ? 'LONG' : 'SHORT'} ${d.row.coin}` : `WAIT ${d.row.coin}`, 48, 176);
  g.fillStyle = '#dbe6f2'; g.font = '700 34px system-ui, sans-serif';
  g.fillText(`${d.tier.label} tier · conviction ${d.row.confidence}/100 · score ${d.score.toFixed(2)}`, 48, 232);

  const p = d.plan;
  const lines = p ? [
    ['Entry', fmt.price(p.entry, d.row.coin)],
    ['Stop', fmt.price(p.stop, d.row.coin)],
    ['Target', fmt.price(p.target, d.row.coin)],
    ['Size', fmt.usd(p.notional, 0) + ' @ ' + p.lev + 'x'],
    ['R : R', d.rr.toFixed(2) + ' : 1'],
    ['Risk', fmt.usd(p.riskUsd, 0) + ' (' + d.tier.riskPct + '% equity)'],
  ] : [['Signal score', d.score.toFixed(2)], ['Needs |score| >=', d.tier.minScore.toFixed(2)], ['Status', 'WAIT']];
  g.font = '600 26px ui-monospace, monospace';
  lines.forEach((ln, i) => {
    const col = i % 2, rowI = Math.floor(i / 2);
    const x = 48 + col * 560, y = 316 + rowI * 58;
    g.fillStyle = '#7d8fa6'; g.fillText(ln[0], x, y);
    g.fillStyle = ln[0] === 'Stop' ? '#ff5f6d' : ln[0] === 'Target' ? '#3ddc97' : '#dbe6f2';
    g.fillText(ln[1], x + 230, y);
  });

  g.fillStyle = '#5a6b80'; g.font = '400 19px system-ui, sans-serif';
  const bt = d.hist;
  g.fillText(
    `${S.cfg.backtest.days}d backtest: ${S.backtest ? S.backtest.summary.winRate + '% win, ' + S.backtest.summary.avgR + 'R avg over ' + S.backtest.summary.total + ' calls' : 'n/a'}` +
    (bt ? ` · ${d.row.coin} alone: ${bt.winRate}% over ${bt.n} calls` : ''), 48, 546);
  g.fillText('Paper trading · not financial advice · edge-terminal', 48, 578);

  const url = cv.toDataURL('image/png');
  const a = document.createElement('a');
  a.href = url;
  a.download = `edge-${d.row.coin}-${d.side || 'wait'}-${Date.now()}.png`;
  a.click();
  const text = d.actionable
    ? `${long ? 'LONG' : 'SHORT'} ${d.row.coin} — ${d.tier.label} tier | entry ${fmt.price(p.entry, d.row.coin)} · stop ${fmt.price(p.stop, d.row.coin)} · target ${fmt.price(p.target, d.row.coin)} · RR ${d.rr.toFixed(2)}:1 | conviction ${d.row.confidence}/100 | edge-terminal`
    : `${d.row.coin}: WAIT at ${d.tier.label} tier (score ${d.score.toFixed(2)} needs ${d.tier.minScore}) | edge-terminal`;
  try { await navigator.clipboard.writeText(text); toast('Card downloaded + call copied to clipboard', 'ok'); }
  catch (e) { toast('Card downloaded', 'ok'); }
}

/* ------------------------------------------------- track record panel */
async function refreshTrack() {
  const [bt, tr] = await Promise.allSettled([api('/api/backtest'), api('/api/track')]);
  if (bt.status === 'fulfilled') {
    S.backtest = bt.value;
    const s = bt.value.summary;
    $('#bt-line').innerHTML = s.total
      ? `<b class="${s.winRate >= 50 ? 'up' : 'down'}">${s.winRate}% hit</b> · ${s.avgR > 0 ? '+' : ''}${s.avgR}R avg · ${s.total} calls · ${s.totalR > 0 ? '+' : ''}${s.totalR}R total · maxDD ${s.maxDD_R}R`
      : 'no calls in window';
    $('#bt-body').innerHTML = (bt.value.coins || []).map((c) => `
      <tr><td>${c.coin}</td><td class="num">${c.n}</td>
      <td class="num ${c.winRate >= 50 ? 'up' : 'down'}">${c.winRate == null ? '—' : c.winRate + '%'}</td>
      <td class="num ${fmt.cls(c.avgR)}">${c.avgR == null ? '—' : c.avgR + 'R'}</td></tr>`).join('');
    $('#bt-foot').textContent =
      `${bt.value.cfg.days}d daily candles, ${bt.value.cfg.forwardDays}d forward horizon, ${bt.value.cfg.tier} tier stops ` +
      `(${bt.value.cfg.stopAtr}×ATR stop / ${bt.value.cfg.targetAtr}×ATR target), funding ${bt.value.fundingIncluded ? 'included' : 'UNAVAILABLE (excluded)'}. ` +
      `In-sample parameters — a receipt, not a walk-forward guarantee.`;
  } else {
    $('#bt-line').textContent = 'backtest unavailable (' + bt.reason + ')';
  }
  // numbers just landed — repaint the cards that quote them
  if (S.board) { renderTrade(); if (S.tab === 'lp') renderLP(); }
  if (S.tab === 'markets') renderMarkets();
  if (tr.status === 'fulfilled') {
    const s = tr.value.summary;
    $('#tr-line').innerHTML = !s.logged
      ? `<span class="muted">no live calls yet — every signal the board prints lands here and resolves at the ${tr.value.horizonHours}h horizon</span>`
      : s.resolved
        ? `<b class="${s.winRate >= 50 ? 'up' : 'down'}">${s.winRate}% win</b> · ${s.avgRetPct > 0 ? '+' : ''}${s.avgRetPct}% avg · ${s.resolved} resolved · ${s.pending} pending`
        : `<span class="muted">${s.pending} live calls waiting for the ${tr.value.horizonHours}h horizon</span>`;
  } else {
    $('#tr-line').textContent = 'live log unavailable';
  }
}

/* ------------------------------------------------------- portfolio */
function renderPortfolio() {
  const eq = equity();
  const openPnl = S.pf.open.reduce((a, p) => a + unrealized(p), 0);
  const lpUnreal = S.pf.lp.reduce((a, p) => a + (lpValue(p) - p.principal), 0);
  const realized = S.pf.hist.reduce((a, h) => a + h.pnl, 0);
  const wins = S.pf.hist.filter((h) => h.pnl > 0).length;
  const wr = S.pf.hist.length ? (wins / S.pf.hist.length) * 100 : null;
  const start = S.cfg.paper.startingEquityUsd;

  $('#pf-stats').innerHTML = `
    <div class="stat"><div class="s-k">Equity</div><div class="s-v ${fmt.cls(eq - start)}">${fmt.usd(eq, 0)}</div></div>
    <div class="stat"><div class="s-k">Open PnL</div><div class="s-v ${fmt.cls(openPnl)}">${fmt.usd(openPnl, 0)}</div></div>
    <div class="stat"><div class="s-k">Realized</div><div class="s-v ${fmt.cls(realized)}">${fmt.usd(realized, 0)}</div></div>
    <div class="stat"><div class="s-k">Win rate</div><div class="s-v">${wr == null ? '—' : wr.toFixed(0) + '%'}</div></div>`;

  const open = S.pf.open;
  $('#pf-body').innerHTML = open.length ? open.map((p) => {
    const mark = markOf(p.coin);
    const u = unrealized(p);
    const riskUsd = Math.abs(p.entry - p.stop) / p.entry * p.notional;
    return `<tr data-id="${p.id}">
      <td><div class="coincell">${p.coin}<span class="muted" style="font-weight:400">${p.tier}</span></div></td>
      <td><span class="sig ${p.side === 'long' ? 'LONG' : 'SHORT'}">${p.side.toUpperCase()} ${p.lev}×</span></td>
      <td class="num">${fmt.usd(p.notional, 0)}</td>
      <td class="num">${fmt.price(p.entry, p.coin)}</td>
      <td class="num">${mark == null ? '—' : fmt.price(mark, p.coin)}</td>
      <td class="num ${fmt.cls(u)}">${fmt.usd(u, 2)}</td>
      <td class="num ${fmt.cls(u)}">${riskUsd ? (u / riskUsd).toFixed(2) + 'R' : '—'}</td>
      <td class="num"><button class="btn sm ghost" data-close="${p.id}">close</button></td>
    </tr>`;
  }).join('') + S.pf.lp.map((p) => `
    <tr>
      <td><div class="coincell">${p.symbol}<span class="muted" style="font-weight:400">${p.chain}</span></div></td>
      <td><span class="sig NEUTRAL">LP ${p.apy}%</span></td>
      <td class="num">${fmt.usd(p.principal, 0)}</td>
      <td class="num">${fmt.hour(p.ts)}</td>
      <td class="num">${fmt.usd(lpValue(p), 2)}</td>
      <td class="num up">${fmt.usd(lpValue(p) - p.principal, 2)}</td>
      <td class="num muted">yield</td>
      <td class="num"><button class="btn sm ghost" data-closelp="${p.id}">withdraw</button></td>
    </tr>`).join('')
    : '<tr><td colspan="8" class="empty">No open positions. Pick a signal on Markets → Trade, or add a pool on LP.</td></tr>';

  $$('#pf-body [data-close]').forEach((b) => b.addEventListener('click', () => {
    const p = S.pf.open.find((x) => x.id === b.dataset.close);
    const net = closePosition(b.dataset.close);
    if (net != null) toast(`Closed ${p.coin} ${p.side}: ${fmt.usd(net, 2)}`, net >= 0 ? 'ok' : 'err');
    renderPortfolio(); renderTrade();
  }));
  $$('#pf-body [data-closelp]').forEach((b) => b.addEventListener('click', () => {
    const i = S.pf.lp.findIndex((x) => x.id === b.dataset.closelp);
    if (i < 0) return;
    const p = S.pf.lp[i];
    const val = lpValue(p);
    S.pf.cash += val;
    S.pf.lp.splice(i, 1);
    savePF();
    toast(`Withdrew ${p.symbol}: ${fmt.usd(val, 2)} (+${fmt.usd(val - p.principal, 2)} yield)`, 'ok');
    renderPortfolio();
  }));

  $('#pf-hist').innerHTML = S.pf.hist.length ? S.pf.hist.slice(0, 50).map((h) => `
    <tr>
      <td>${fmt.time(h.ts)}</td>
      <td><div class="coincell">${h.coin}<span class="muted" style="font-weight:400">${h.tier}</span></div></td>
      <td><span class="sig ${h.side === 'long' ? 'LONG' : 'SHORT'}">${h.side.toUpperCase()}</span></td>
      <td class="num">${fmt.price(h.entry, h.coin)}</td>
      <td class="num">${fmt.price(h.exit, h.coin)}</td>
      <td class="num ${fmt.cls(h.pnl)}">${fmt.usd(h.pnl, 2)}</td>
      <td class="num ${fmt.cls(h.r)}">${h.r.toFixed(2)}R</td>
    </tr>`).join('')
    : `<tr><td colspan="7" class="empty">Nothing closed yet — 50 closed trades with positive expectancy unlock the live-money gate.</td></tr>`;

  $('#pf-note').textContent =
    `Cash ${fmt.usd(S.pf.cash, 0)} · LP deployed ${fmt.usd(S.pf.lp.reduce((a, p) => a + p.principal, 0), 0)} · ` +
    `${S.pf.hist.length}/50 closed trades toward the live gate · everything lives in this browser (localStorage).`;
}

/* ----------------------------------------------------------- launch */
function initLaunch() {
  const L = S.cfg.launch;
  S.launch = {
    symbol: 'EDGE',
    feePct: L.defaultTotalFeePct,
    volumeUsd: L.monthlyVolumeUsd,
    shares: Object.fromEntries(L.destinations.map((d) => [d.id, d.share])),
  };
  $('#ln-sym').addEventListener('input', (e) => { S.launch.symbol = e.target.value.toUpperCase() || 'TOKEN'; renderLaunch(); });
  $('#ln-fee').addEventListener('input', (e) => { S.launch.feePct = Number(e.target.value); renderLaunch(); });
  $('#ln-vol').addEventListener('input', (e) => { S.launch.volumeUsd = Number(e.target.value); renderLaunch(); });
  $('#ln-copy').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText($('#ln-json').textContent); toast('Router config copied', 'ok'); }
    catch (e) { toast('Copy failed: ' + e.message, 'err'); }
  });
  renderLaunch();
}

function renderLaunch() {
  if (!S.launch) return;
  const L = S.cfg.launch, ls = S.launch;
  const colors = ['#4da3ff', '#3ddc97', '#ffb454', '#c792ea', '#ff5f6d', '#7d8fa6', '#56b6c2', '#e5c07b'];

  $('#ln-feelabel').textContent = ls.feePct.toFixed(2) + '%';
  $('#ln-vol').textContent = fmt.usd(ls.volumeUsd, 0);

  // inputs are built ONCE — re-rendering them on every keystroke would steal focus
  if (!$('#ln-dests').children.length) {
    $('#ln-dests').innerHTML = L.destinations.map((d) => `
      <div class="dest" data-id="${d.id}">
        <div class="d-name">${d.label}</div>
        <input class="input" type="number" min="0" max="100" step="1" value="${ls.shares[d.id]}" data-share="${d.id}" aria-label="share percent for ${d.label}">
        <div class="d-note">${d.note}</div>
      </div>`).join('');
    $$('#ln-dests [data-share]').forEach((inp) => inp.addEventListener('input', (e) => {
      const v = Math.max(0, Math.min(100, Number(e.target.value) || 0));
      S.launch.shares[e.target.dataset.share] = v;
      renderLaunch();
    }));
  }

  const sum = L.destinations.reduce((a, d) => a + (ls.shares[d.id] || 0), 0);
  const revenue = ls.volumeUsd * (ls.feePct / 100);
  $('#ln-sum').innerHTML = Math.abs(sum - 100) < 0.01
    ? `<span class="up">Allocations sum to 100% — router is valid.</span> ${fmt.usd(revenue, 0)}/month in fees at ${ls.feePct.toFixed(2)}% on ${fmt.usd(ls.volumeUsd, 0)} volume.`
    : `<span class="down">Allocations sum to ${sum.toFixed(0)}% — must be exactly 100% before deploy.</span>`;

  $('#ln-bar').innerHTML = L.destinations.filter((d) => ls.shares[d.id] > 0)
    .map((d, i) => {
      // normalise so the bar always fills exactly, even while the split is invalid
      const w = sum > 0 ? (ls.shares[d.id] / sum) * 100 : 0;
      return `<i style="width:${w}%;background:${colors[i % colors.length]}" title="${d.label}: ${ls.shares[d.id]}%"></i>`;
    }).join('');

  const kindLabel = { lp: 'depth · LP yield', sink: 'sink · supply cut', yield: 'yield · market risk', strategy: 'leveraged · directional' };
  $('#ln-body').innerHTML = L.destinations.map((d, i) => {
    const share = ls.shares[d.id] || 0;
    return `<tr>
      <td><div class="coincell"><span class="coin-dot" style="background:${colors[i % colors.length]}"></span>${d.label}</div></td>
      <td class="num">${share}%</td>
      <td class="num">${fmt.usd(revenue * share / 100, 0)}</td>
      <td class="${d.kind === 'strategy' ? 'down' : d.kind === 'lp' ? 'up' : 'neutral'}">${kindLabel[d.kind] || d.kind}</td>
    </tr>`;
  }).join('');

  const cfg = {
    token: ls.symbol,
    swapFeePct: Number(ls.feePct.toFixed(2)),
    splitTotal: sum,
    monthlyVolumeUsd: ls.volumeUsd,
    monthlyFeeUsd: Math.round(revenue),
    routes: L.destinations.map((d) => ({
      dest: d.id, kind: d.kind, sharePct: ls.shares[d.id] || 0,
      usdPerMonth: Math.round(revenue * (ls.shares[d.id] || 0) / 100),
    })),
    note: 'sum of routes must equal 100; router reverts otherwise',
  };
  $('#ln-json').textContent = JSON.stringify(cfg, null, 2);
}

/* --------------------------------------------------------- help */
function showHelp() {
  confirmDialog('Keyboard shortcuts',
    `<div class="kv">
      <div class="k">1 – 4</div><div class="v">switch tab</div>
      <div class="k">/</div><div class="v">focus the coin filter</div>
      <div class="k">r</div><div class="v">refresh board + track record</div>
      <div class="k">?</div><div class="v">this dialog</div>
      <div class="k">Esc</div><div class="v">close any dialog</div>
      <div class="k">wheel / pinch</div><div class="v">zoom the chart</div>
      <div class="k">drag</div><div class="v">pan the chart</div>
    </div><p class="hint" style="margin:8px 0 0">Admin surface lives at <code>/admin.html</code> — upstream health, cache, ledger, kill switch.</p>`)
    .then(() => {});
}

/* --------------------------------------------------------- refresh */
async function refreshBoard(first = false) {
  try {
    S.board = await api('/api/board');
    setKill(false);
    if (S.board.errors && S.board.errors.length && first) {
      const hard = S.board.errors.filter((e) => /hyperliquid|defillama|fng|timeout/i.test(e));
      if (hard.length) toast('upstream warning: ' + hard[0], 'err');
    }
    renderTicker();
    if (S.tab === 'markets') renderMarkets();
    renderTrade();
    if (S.tab === 'portfolio') renderPortfolio();
    if (S.tab === 'lp') renderLP();
    checkLiquidations();
    savePF();
  } catch (e) {
    if (/503|kill switch/i.test(String(e.message))) setKill(true);
    else toast('board failed: ' + e.message, 'err');
    if (first) $('#m-body').innerHTML = '<tr><td colspan="9" class="empty">Board unavailable: ' + e.message + '</td></tr>';
  }
}
function setKill(on) {
  const b = $('#killbanner');
  if (!b) return;
  b.hidden = !on;
  if (on) $('#killnote').textContent = 'Remove data/STOP (or use the Admin page) to resume.';
}
async function refreshTicker() {
  try {
    const t = await api('/api/ticker');
    S.lastTicker = Date.now();
    if (!S.board) return;
    // splice fresh prices into the board without recomputing indicators
    for (const row of S.board.markets) {
      const fresh = t.prices[row.coin];
      if (!fresh) continue;
      row.price = fresh.mark;
      row.change24hPct = fresh.prev ? ((fresh.mark - fresh.prev) / fresh.prev) * 100 : row.change24hPct;
      // keep the 7d mean (board) as the ranking number; the live rate is the now-view
      row.fundingNowAprPct = fresh.funding * 24 * 365 * 100;
      row.oiUsd = fresh.oi * fresh.mark;
    }
    renderTicker();
    if (S.tab === 'markets') renderMarkets();
    if (S.tab === 'trade') renderTrade();
    if (S.tab === 'portfolio') renderPortfolio();
    checkLiquidations();
  } catch (e) { /* silent: ticker is best-effort */ }
}
async function refreshYields() {
  try { S.yields = await api('/api/yields'); if (S.tab === 'lp') renderLP(); renderTrade(); }
  catch (e) { toast('yields failed: ' + e.message, 'err'); }
}
function renderTicker() {
  const byCoin = (c) => (S.board.markets.find((m) => m.coin === c) || {});
  const btc = byCoin('BTC'), eth = byCoin('ETH');
  if (btc.price) $('#tk-btc').innerHTML = `BTC <b>${fmt.price(btc.price, 'BTC')}</b> <span class="${fmt.cls(btc.change24hPct)}">${fmt.pct(btc.change24hPct)}</span>`;
  if (eth.price) $('#tk-eth').innerHTML = `ETH <b>${fmt.price(eth.price, 'ETH')}</b> <span class="${fmt.cls(eth.change24hPct)}">${fmt.pct(eth.change24hPct)}</span>`;
  const fng = S.board.sentiment && S.board.sentiment.now;
  if (fng) $('#tk-fng').innerHTML = `F&G <b>${fng.value}</b> <span class="${fng.value >= 75 ? 'down' : fng.value <= 25 ? 'up' : ''}">${fng.label}</span>`;
  $('#tk-mode').textContent = S.cfg.mode === 'paper' ? 'PAPER MODE' : S.cfg.mode.toUpperCase();
}

/* ----------------------------------------------------------- init */
function bindUI() {
  $$('.tb').forEach((b) => b.addEventListener('click', () => setTab(b.dataset.tab)));

  $$('#m-table thead th[data-sort]').forEach((th) => th.addEventListener('click', () => {
    const key = th.dataset.sort;
    S.sort = { key, dir: S.sort.key === key ? -S.sort.dir : (key === 'coin' ? 1 : -1) };
    $$('#m-table thead th').forEach((x) => x.classList.remove('sorted', 'asc'));
    th.classList.add('sorted');
    if (S.sort.dir === 1) th.classList.add('asc');
    renderMarkets();
  }));
  $('#m-filter').addEventListener('input', (e) => { S.filter = e.target.value; renderMarkets(); });
  $('#m-onlysignals').addEventListener('change', (e) => { S.onlySignals = e.target.checked; renderMarkets(); });

  $('#t-interval').addEventListener('change', (e) => { S.interval = e.target.value; loadCandles(); });
  $('#t-share').addEventListener('click', async () => {
    syncURL();
    try { await navigator.clipboard.writeText(location.href); toast('Link copied — coin, tier and tab travel with it', 'ok'); }
    catch (e) { toast('Copy failed: ' + e.message, 'err'); }
  });
  $('#lp-stables').addEventListener('change', (e) => { S.lpOnlyStables = e.target.checked; renderLP(); });

  $('#btn-refresh').addEventListener('click', () => { refreshBoard(); refreshYields(); toast('Refreshing…'); });
  $('#pf-reset').addEventListener('click', () => {
    if (!confirm('Reset paper account to $10,000?')) return;
    S.pf = defaultPF(); savePF(); renderPortfolio(); renderTrade();
    toast('Paper account reset', 'ok');
  });

  document.addEventListener('keydown', (e) => {
    if (/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName)) return;
    const map = { 1: 'markets', 2: 'trade', 3: 'lp', 4: 'portfolio', 5: 'launch' };
    if (map[e.key]) setTab(map[e.key]);
    if (e.key === 'r') { refreshBoard(); refreshYields(); refreshTrack().catch(() => {}); }
    if (e.key === '/') { e.preventDefault(); setTab('markets'); $('#m-filter').focus(); }
    if (e.key === '?') showHelp();
  });

  $('#btn-help').addEventListener('click', showHelp);

  setInterval(() => { $('#clock').textContent = new Date().toLocaleTimeString(); }, 1000);
}

async function init() {
  try { S.cfg = await api('/api/config'); }
  catch (e) { document.body.innerHTML = `<p style="padding:20px;font-family:monospace">config failed: ${e.message}</p>`; return; }

  S.pf = loadPF();
  S.tier = localStorage.getItem(LS.tier) || 'balanced';
  if (!S.cfg.tiers[S.tier]) S.tier = 'balanced';
  S.coin = localStorage.getItem(LS.coin) || S.cfg.universe[0];
  readURL();
  document.title = `${S.cfg.product.name} — ${S.cfg.product.tagline}`;
  $('#brand-tag').textContent = S.cfg.product.tagline.toLowerCase();

  bindUI();

  S.chart = new GLChart($('#glchart'), {
    axisY: $('#axis-y'),
    axisX: $('#axis-x'),
    fmtPrice: (p) => fmt.price(p, S.coin),
    fmtTime: (t) => S.interval === '1d'
      ? new Date(t).toLocaleString('en-US', { month: 'short', day: 'numeric' })
      : new Date(t).toLocaleString('en-GB', { hour: '2-digit', minute: '2-digit' }),
    onHover: (candle, pos) => {
      const tip = $('#chart-tip');
      if (!candle) { tip.hidden = true; return; }
      const geo = S.chart.geom(); if (!geo) return;
      const flip = pos.x > S.chart.w - 170;
      tip.hidden = false;
      tip.style.left = (flip ? pos.x - 158 : pos.x + 14) + 'px';
      tip.style.top = Math.min(pos.y + 12, S.chart.h - 92) + 'px';
      const chg = ((candle.c - candle.o) / candle.o) * 100;
      tip.innerHTML = `<b>${S.coin} · ${fmt.time(candle.t)}</b><br>
        <i>O</i> ${fmt.price(candle.o)} <i>H</i> ${fmt.price(candle.h)}<br>
        <i>L</i> ${fmt.price(candle.l)} <i>C</i> <span class="${fmt.cls(chg)}">${fmt.price(candle.c)}</span><br>
        <i>vol</i> ${fmt.compact(candle.v * candle.c)}`;
    },
  });

  // GPU proof badge — debug artifact, hidden unless ?debug=1 (a trader does not
  // care about ANGLE strings) but ALWAYS visible when the renderer is software.
  try {
    const gl = $('#glchart').getContext('webgl2') || $('#glchart').getContext('webgl');
    const dbg = gl && gl.getExtension('WEBGL_debug_renderer_info');
    const renderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : (gl ? gl.getParameter(gl.RENDERER) : 'none');
    window.__glRenderer = renderer;
    const badge = $('#gl-badge');
    const cpu = /swiftshader|llvmpipe|software/i.test(renderer || '');
    const wantDebug = new URL(location.href).searchParams.get('debug') === '1';
    badge.textContent = 'GPU: ' + (renderer || 'none').replace(/^ANGLE \(/, '').replace(/\)$/, '').slice(0, 46);
    badge.classList.toggle('cpu', cpu);
    badge.hidden = !cpu && !wantDebug;
    if (cpu) toast('Browser is on CPU rendering (SwiftShader) — relaunch with bin/gpu-browser.sh', 'err');
  } catch (e) { /* badge optional */ }

  renderTrade();
  if (S.cfg.launch) initLaunch();
  setTab(S.tab);
  await Promise.all([refreshBoard(true), refreshYields()]);
  refreshTrack().catch(() => {});

  setInterval(refreshTicker, 5000);
  setInterval(() => refreshBoard(), 60000);
  setInterval(() => refreshYields(), 300000);
  setInterval(() => refreshTrack().catch(() => {}), 180000);

  // DX: live reload — the agent edits a file, the page follows (config dev.liveReload)
  if (S.cfg.dev && S.cfg.dev.liveReload) {
    S.ver = (await api('/api/version').catch(() => null));
    setInterval(async () => {
      const v = await api('/api/version').catch(() => null);
      if (!v || !S.ver) return;
      if (v.killed !== S.ver.killed) setKill(v.killed);
      if (v.v !== S.ver.v) { location.reload(); return; }
      S.ver = v;
    }, S.cfg.dev.pollMs || 1500);
  }
}

document.addEventListener('DOMContentLoaded', init);
