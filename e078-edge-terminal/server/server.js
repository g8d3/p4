#!/usr/bin/env node
/* Edge Terminal — zero-dependency Node server.
 * Static SPA + cached /api/* proxies to keyless public crypto data sources.
 * Every machine value (port, upstream URLs, universe, tiers) comes from config.json. */

'use strict';
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const CONFIG_PATH = path.join(__dirname, 'config.json');
const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
const EM = require(path.join(ROOT, 'public', 'engine.js')); // shared math (browser + server + tests)
const PORT = Number(process.env[config.server.envPortOverride || 'EDGE_PORT'] || config.server.port);
const BIND = config.server.bind || '0.0.0.0';
const PUB = path.join(ROOT, 'public');

/* ---------------------------------------------------------------- cache */
const cache = new Map(); // key -> { ts, ttl, promise }
const stats = { started: Date.now(), hits: 0, misses: 0, upstreamOk: 0, upstreamErr: 0, lastUpstreamErr: null, requests: 0 };
function cached(key, ttlSec, producer) {
  const hit = cache.get(key);
  const now = Date.now();
  if (hit && hit.promise && now - hit.ts < ttlSec * 1000) { stats.hits++; return hit.promise; }
  stats.misses++;
  const entry = { ts: now, ttl: ttlSec, promise: null };
  entry.promise = Promise.resolve()
    .then(producer)
    .then((v) => { stats.upstreamOk++; return v; })
    .catch((err) => {
      stats.upstreamErr++;
      stats.lastUpstreamErr = { ts: new Date().toISOString(), error: String(err && err.message || err), key };
      cache.delete(key); // do not pin failures
      throw err;
    });
  cache.set(key, entry);
  return entry.promise;
}

/* ---------------------------------------------------------------- http */
function fetchJSON(url, opts = {}, timeoutMs = 12000) {
  const lib = url.startsWith('https') ? https : http;
  const body = opts.body ? Buffer.from(opts.body) : null;
  const headers = Object.assign({ 'user-agent': 'edge-terminal/0.1' }, opts.headers || {});
  if (body) headers['content-type'] = 'application/json';
  return new Promise((resolve, reject) => {
    const req = lib.request(url, { method: opts.method || 'GET', headers }, (res) => {
      let data = '';
      res.setEncoding('utf8');
      res.on('data', (c) => (data += c));
      res.on('end', () => {
        if (res.statusCode >= 400) return reject(new Error(`${res.statusCode} ${url}`));
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error(`bad json from ${url}: ${e.message}`));
        }
      });
    });
    req.setTimeout(timeoutMs, () => req.destroy(new Error(`timeout ${url}`)));
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

const HL = () => config.upstreams.hyperliquid.replace(/\/$/, '');
const hlInfo = (payload) =>
  fetchJSON(`${HL()}/info`, { method: 'POST', body: JSON.stringify(payload) });

/* ------------------------------------------- indicators (shared engine) */
const clamp = EM.clamp, rsi = EM.rsi, sma = EM.sma, atr = EM.atr;
const scoreOf = EM.scoreOf, labelOf = EM.labelOf;

/* ---------------------------------------------------------------- board */
const lastGood = new Map(); // coin -> indicator fields from the last healthy build

async function buildBoard() {
  const b = config.board;
  const errors = [];
  const meta = await hlInfo({ type: 'metaAndAssetCtxs' }).catch((e) => {
    errors.push(`hyperliquid: ${e.message}`);
    return null;
  });

  let fng = null;
  fng = await fetchJSON(`${config.upstreams.fng}/fng/?limit=30`).catch((e) => {
    errors.push(`fng: ${e.message}`);
    return null;
  });

  const rows = [];
  if (meta) {
    const universe = meta[0].universe;
    const ctxs = meta[1];
    const byName = new Map();
    universe.forEach((u, i) => byName.set(u.name, { u, ctx: ctxs[i] }));

    const picks = b.universe.filter((c) => byName.has(c));

    // candles for indicators + funding history for the crowding read, bounded concurrency
    const queue = picks.slice();
    const results = new Map();
    const fundSeries = new Map();
    async function worker() {
      while (queue.length) {
        const coin = queue.shift();
        const now = Date.now();
        let candles = null, funding = null;
        for (let attempt = 0; attempt < 2 && candles == null; attempt++) {
          try {
            const res = await Promise.all([
              hlInfo({ type: 'candleSnapshot', req: { coin, interval: b.interval, startTime: now - b.lookbackMs, endTime: now } }),
              hlInfo({ type: 'fundingHistory', coin, startTime: now - 7 * 86400e3 }).catch(() => []),
            ]);
            candles = res[0] || [];
            funding = res[1] || [];
            if (!candles.length && attempt === 0) { candles = null; await new Promise((r) => setTimeout(r, 400)); }
          } catch (e) {
            if (attempt === 1) { errors.push(`candles ${coin}: ${e.message}`); candles = []; funding = []; }
            else await new Promise((r) => setTimeout(r, 400));
          }
        }
        results.set(coin, candles || []);
        fundSeries.set(coin, Array.isArray(funding) ? funding : []);
      }
    }
    await Promise.all(Array.from({ length: Math.max(1, b.concurrency) }, worker));

    for (const coin of picks) {
      const { u, ctx } = byName.get(coin);
      const price = Number(ctx.markPx || ctx.oraclePx || 0);
      const prev = Number(ctx.prevDayPx || 0);
      const candles = (results.get(coin) || []).map((c) => ({
        t: c.t, o: +c.o, h: +c.h, l: +c.l, c: +c.c, v: +c.v,
      }));
      const live = {
        coin,
        maxLeverage: u.maxLeverage || 1,
        price,
        change24hPct: prev ? ((price - prev) / prev) * 100 : null,
        volume24hUsd: Number(ctx.dayNtlVlm || 0),
        oiUsd: Number(ctx.openInterest || 0) * price,
      };

      // Not enough candles (new listing, delisted, or transient upstream hole):
      // reuse the last healthy indicators instead of publishing a hollow row.
      if (candles.length < 60) {
        const good = lastGood.get(coin);
        if (good) {
          rows.push(Object.assign({}, good, live, { candles: candles.length, stale: true }));
        } else {
          errors.push(`no usable candles for ${coin} (${candles.length})`);
        }
        continue;
      }

      const closes = candles.map((c) => c.c);
      const funding = Number(ctx.funding || 0);
      // HL funding settles HOURLY: APR = rate * 24 * 365
      const rates = (fundSeries.get(coin) || []).map((h) => Number(h.fundingRate)).filter((x) => isFinite(x));
      const mean = rates.length ? rates.reduce((a, x) => a + x, 0) / rates.length : funding;
      const last = rates.length ? rates[rates.length - 1] : funding;
      const std = rates.length > 2
        ? Math.sqrt(rates.reduce((a, x) => a + (x - mean) ** 2, 0) / rates.length)
        : 0;
      const row = {
        ...live,
        funding: last,
        fundingAprPct: mean * 24 * 365 * 100,
        fundingNowAprPct: last * 24 * 365 * 100,
        fundingZ: std > 0 ? (last - mean) / std : null,
        fundingSamples: rates.length,
        oiUsd: Number(ctx.openInterest || 0) * price,
        rsi: rsi(closes) == null ? null : Math.round(rsi(closes) * 10) / 10,
        sma20: sma(closes, 20),
        sma50: sma(closes, 50),
        atr: atr(candles),
        atrPct: null,
        ret7dPct: closes.length > 168 ? ((closes[closes.length - 1] / closes[closes.length - 169]) - 1) * 100 : null,
        candles: candles.length,
      };
      row.atrPct = row.atr && price ? (row.atr / price) * 100 : null;
      row.ret7dPct = row.ret7dPct == null ? null : Math.round(row.ret7dPct * 10) / 10;
      const s = scoreOf(row, config.signal.weights);
      row.trend = s.trend;
      row.score = s.score;
      row.label = labelOf(s.score, config.signal);
      row.confidence = Math.round(Math.abs(s.score) * 100);
      // round helper numbers for display
      for (const k of ['sma20', 'sma50', 'atr']) if (row[k] != null) row[k] = Math.round(row[k] * 1e6) / 1e6;
      lastGood.set(coin, Object.assign({}, row));
      rows.push(row);
    }
  }

  rows.sort((a, b2) => b2.volume24hUsd - a.volume24hUsd);

  const fngSeries = fng
    ? fng.data.map((d) => ({ ts: Number(d.timestamp), value: Number(d.value), label: d.value_classification }))
    : [];

  return {
    generatedAt: new Date().toISOString(),
    mode: config.product.mode,
    errors,
    sentiment: fngSeries.length ? { now: fngSeries[0], series: fngSeries } : null,
    markets: rows,
  };
}

async function buildTicker() {
  const meta = await hlInfo({ type: 'metaAndAssetCtxs' });
  const universe = meta[0].universe, ctxs = meta[1];
  const prices = {};
  universe.forEach((u, i) => {
    const c = ctxs[i];
    prices[u.name] = {
      mark: Number(c.markPx || c.oraclePx || 0),
      prev: Number(c.prevDayPx || 0),
      funding: Number(c.funding || 0),
      oi: Number(c.openInterest || 0),
      vol24h: Number(c.dayNtlVlm || 0),
    };
  });
  return { generatedAt: new Date().toISOString(), prices };
}

async function buildYields() {
  const y = config.yields;
  const raw = await fetchJSON(`${config.upstreams.defillama}/pools`);
  const pools = (raw.data || [])
    .filter((p) => p.tvlUsd >= y.minTvlUsd)
    .filter((p) => !p.outlier && !p.apyOverride) // outliers distort the ranking
    .filter((p) => p.apy != null && p.apy > 0 && p.apy <= y.maxApyPct)
    .filter((p) => p.chain === 'Ethereum' || p.chain === 'Arbitrum' || p.chain === 'Base' ||
                   p.chain === 'Solana' || p.chain === 'Optimism' || p.chain === 'Polygon' ||
                   p.chain === 'Avalanche' || p.chain === 'Hyperliquid')
    .sort((a, b) => (b.apy || 0) - (a.apy || 0))
    .slice(0, y.limit)
    .map((p) => ({
      pool: p.pool, chain: p.chain, project: p.project, symbol: p.symbol,
      apy: Math.round(p.apy * 100) / 100,
      apyBase: p.apyBase == null ? null : Math.round(p.apyBase * 100) / 100,
      apyReward: p.apyReward == null ? null : Math.round(p.apyReward * 100) / 100,
      tvlUsd: p.tvlUsd,
      stablecoin: !!p.stablecoin,
      ilRisk: p.ilRisk,
      exposure: p.exposure,
      outlier: !!p.outlier,
    }));
  return { generatedAt: new Date().toISOString(), pools };
}

async function buildCandles(coin, interval, limit) {
  const now = Date.now();
  const spanMap = { '1h': 3600e3, '4h': 14400e3, '1d': 86400e3, '15m': 900e3 };
  const span = spanMap[interval] || 3600e3;
  const candles = await hlInfo({
    type: 'candleSnapshot',
    req: { coin, interval, startTime: now - span * Math.min(limit, 1000), endTime: now },
  });
  return candles.map((c) => ({ t: c.t, o: +c.o, h: +c.h, l: +c.l, c: +c.c, v: +c.v }));
}

/* ------------------------------------------------- dev / ops / gates */
const PUB_FILES = ['index.html', 'app.js', 'chart.js', 'style.css', 'engine.js', 'admin.html', 'admin.js'];

function publicVersion() {
  let h = 0;
  for (const f of PUB_FILES) {
    try { h = (h * 31 + Math.floor(fs.statSync(path.join(PUB, f)).mtimeMs)) % 1e12; } catch (e) { /* optional file */ }
  }
  return String(h);
}
const killPath = () => path.resolve(ROOT, config.killSwitchFile);
const isKilled = () => fs.existsSync(killPath());

function appendJsonl(rel, obj) {
  const abs = path.resolve(ROOT, rel);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.appendFileSync(abs, JSON.stringify(obj) + '\n');
}
function readJsonlTail(rel, n) {
  try {
    const abs = path.resolve(ROOT, rel);
    const lines = fs.readFileSync(abs, 'utf8').trim().split('\n').filter(Boolean);
    return lines.slice(-n).map((l) => { try { return JSON.parse(l); } catch (e) { return null; } }).filter(Boolean);
  } catch (e) { return []; }
}

/* ------------------------------------------- signal track record (live) */
const trackLast = new Map(); // "COIN:LABEL" -> ts of last logged signal
function logSignals(board) {
  const t = config.track;
  const now = Date.now();
  for (const row of board.markets || []) {
    if (row.label === 'NEUTRAL') continue;
    const key = `${row.coin}:${row.label}`;
    const last = trackLast.get(key) || 0;
    if (now - last < t.gapMs) continue;
    trackLast.set(key, now);
    appendJsonl(t.file, {
      ts: now, coin: row.coin, label: row.label, score: row.score,
      confidence: row.confidence, price: row.price, atrPct: row.atrPct,
    });
  }
}
// warm trackLast from the existing log so restarts do not re-log everything
(function warmTrack() {
  for (const r of readJsonlTail(config.track.file, 5000)) {
    const key = `${r.coin}:${r.label}`;
    if (!trackLast.has(key) || trackLast.get(key) < r.ts) trackLast.set(key, r.ts);
  }
})();

/* --------------------------------------------------------- backtest */
async function backtestCoin(coin, rawCandles, funding, cfg, tier) {
  // HL returns numeric fields as strings — normalize once, arithmetic downstream
  const candles = (rawCandles || []).map((c) => ({ t: c.t, o: +c.o, h: +c.h, l: +c.l, c: +c.c, v: +c.v }));
  if (candles.length < cfg.warmupDays + 30) return { coin, skipped: candles.length };
  // hourly funding -> daily mean
  const dayMean = new Map();
  for (const f of funding || []) {
    const day = Math.floor(Number(f.time) / 86400e3) * 86400e3;
    const arr = dayMean.get(day) || [];
    arr.push(Number(f.fundingRate));
    dayMean.set(day, arr);
  }
  const dailyFunding = new Map();
  for (const [day, arr] of dayMean) dailyFunding.set(day, arr.reduce((a, b) => a + b, 0) / arr.length);

  const closes = candles.map((c) => c.c);
  const trades = [];
  const fwd = cfg.forwardDays;
  const stopAtr = tier.stopAtr, targetAtr = tier.targetAtr;

  for (let i = cfg.warmupDays; i < candles.length - fwd; i++) {
    const c = candles[i];
    const row = {
      price: c.c,
      sma20: EM.sma(closes.slice(0, i + 1), 20),
      sma50: EM.sma(closes.slice(0, i + 1), 50),
      rsi: EM.rsi(closes.slice(0, i + 1), 14),
      ret7dPct: closes[i - 7] ? (c.c / closes[i - 7] - 1) * 100 : null,
    };
    const day = Math.floor(c.t / 86400e3) * 86400e3;
    const dm = dailyFunding.get(day);
    row.fundingAprPct = dm != null ? dm * 24 * 365 * 100 : 0;
    if (dm != null) {
      const prev = [];
      for (let k = 1; k <= 7; k++) { const v = dailyFunding.get(day - k * 86400e3); if (v != null) prev.push(v); }
      if (prev.length >= 3) {
        const mean = prev.reduce((a, b) => a + b, 0) / prev.length;
        const std = Math.sqrt(prev.reduce((a, b) => a + (b - mean) ** 2, 0) / prev.length);
        row.fundingZ = std > 0 ? (dm - mean) / std : null;
      }
    }
    const { score } = EM.scoreOf(row, config.signal.weights);
    const label = EM.labelOf(score, config.signal);
    if (label === 'NEUTRAL') continue;

    const atrVal = EM.atr(candles.slice(0, i + 1), 14) || c.c * 0.01;
    const dir = label === 'LONG' ? 1 : -1;
    const entry = c.c;
    const stop = dir > 0 ? entry - stopAtr * atrVal : entry + stopAtr * atrVal;
    const target = dir > 0 ? entry + targetAtr * atrVal : entry - targetAtr * atrVal;
    const risk = Math.abs(entry - stop);

    let exit = candles[i + fwd].c, exitRule = 'horizon';
    for (let j = i + 1; j <= i + fwd; j++) {
      const k = candles[j];
      // conservative: on a bar that spans both levels, assume the stop filled first
      const stopHit = dir > 0 ? k.l <= stop : k.h >= stop;
      const tgtHit = dir > 0 ? k.h >= target : k.l <= target;
      if (stopHit) { exit = stop; exitRule = 'stop'; break; }
      if (tgtHit) { exit = target; exitRule = 'target'; break; }
    }
    const r = risk > 0 ? (dir * (exit - entry)) / risk : 0;
    trades.push({ ts: c.t, label, score, entry, exit, r: Math.round(r * 100) / 100, exitRule });
  }
  return { coin, trades };
}

async function runBacktest() {
  const cfg = config.backtest;
  const tier = config.tiers.balanced;
  const now = Date.now();
  const start = now - (cfg.days + cfg.warmupDays) * 86400e3;
  const perCoin = [];
  const queue = config.board.universe.slice();
  let fundingOk = true;
  async function worker() {
    while (queue.length) {
      const coin = queue.shift();
      try {
        const [candles, funding] = await Promise.all([
          hlInfo({ type: 'candleSnapshot', req: { coin, interval: cfg.interval, startTime: start, endTime: now } }),
          hlInfo({ type: 'fundingHistory', coin, startTime: start })
            .catch(() => hlInfo({ type: 'fundingHistory', coin, startTime: start }))
            .catch(() => { fundingOk = false; return []; }),
        ]);
        const res = await backtestCoin(coin, candles || [], funding || [], cfg, tier);
        if (res && !res.skipped) perCoin.push(res);
      } catch (e) {
        perCoin.push({ coin, error: String(e && e.message || e) });
      }
    }
  }
  await Promise.all(Array.from({ length: 5 }, worker));

  const all = perCoin.flatMap((p) => (p.trades || []).map((t) => Object.assign({ coin: p.coin }, t)));
  all.sort((a, b) => a.ts - b.ts);
  const wins = all.filter((t) => t.r > 0).length;
  let cum = 0, peak = 0, maxDD = 0;
  for (const t of all) { cum += t.r; peak = Math.max(peak, cum); maxDD = Math.min(maxDD, cum - peak); }
  const split = (arr) => ({
    n: arr.length,
    winRate: arr.length ? Math.round((arr.filter((t) => t.r > 0).length / arr.length) * 1000) / 10 : null,
    avgR: arr.length ? Math.round((arr.reduce((a, t) => a + t.r, 0) / arr.length) * 100) / 100 : null,
  });
  const stopOut = all.filter((t) => t.exitRule === 'stop').length;
  const targetOut = all.filter((t) => t.exitRule === 'target').length;

  return {
    generatedAt: new Date().toISOString(),
    cfg: { days: cfg.days, interval: cfg.interval, forwardDays: cfg.forwardDays, tier: config.tiers.balanced.label, stopAtr: tier.stopAtr, targetAtr: tier.targetAtr },
    fundingIncluded: fundingOk,
    summary: {
      total: all.length,
      winRate: all.length ? Math.round((wins / all.length) * 1000) / 10 : null,
      avgR: all.length ? Math.round((all.reduce((a, t) => a + t.r, 0) / all.length) * 100) / 100 : null,
      totalR: Math.round(cum * 10) / 10,
      maxDD_R: Math.round(maxDD * 10) / 10,
      long: split(all.filter((t) => t.label === 'LONG')),
      short: split(all.filter((t) => t.label === 'SHORT')),
      targetOut, stopOut,
      horizonOut: all.length - targetOut - stopOut,
    },
    coins: perCoin.map((p) => ({ coin: p.coin, error: p.error || null, ...split(p.trades || []) }))
      .sort((a, b) => (b.n || 0) - (a.n || 0)),
    recent: all.slice(-40).reverse(),
  };
}

/* ------------------------------------------------- live track record */
async function buildTrack() {
  const t = config.track;
  const now = Date.now();
  const rows = readJsonlTail(t.file, 500).reverse();
  const resolved = [], pending = [];
  const priceCache = new Map();
  for (const r of rows) {
    const age = now - r.ts;
    if (age < t.resolveHorizonMs) { pending.push(Object.assign({ status: 'pending' }, r)); continue; }
    const at = r.ts + t.resolveHorizonMs;
    try {
      if (!priceCache.has(r.coin)) {
        priceCache.set(r.coin, await hlInfo({
          type: 'candleSnapshot',
          req: { coin: r.coin, interval: '1h', startTime: r.ts - 3600e3, endTime: now },
        }));
      }
      const candles = priceCache.get(r.coin) || [];
      let target = null;
      for (const c of candles) if (c.t <= at) target = +c.c;
      if (target == null) target = r.price;
      const dir = r.label === 'LONG' ? 1 : -1;
      const retPct = Math.round(dir * (target / r.price - 1) * 10000) / 100;
      const stopDist = (r.atrPct || 1) / 100 * config.tiers.balanced.stopAtr;
      resolved.push(Object.assign({ status: retPct / (stopDist * 100) > 0 ? 'win' : 'loss', retPct, r: Math.round((dir * (target - r.price)) / (r.price * stopDist) * 100) / 100 }, r));
    } catch (e) {
      resolved.push(Object.assign({ status: 'error' }, r));
    }
  }
  const done = resolved.filter((r) => r.status === 'win' || r.status === 'loss');
  return {
    generatedAt: new Date().toISOString(),
    horizonHours: t.resolveHorizonMs / 3600e3,
    summary: {
      logged: rows.length,
      resolved: done.length,
      pending: pending.length,
      winRate: done.length ? Math.round((done.filter((r) => r.status === 'win').length / done.length) * 1000) / 10 : null,
      avgRetPct: done.length ? Math.round((done.reduce((a, r) => a + r.retPct, 0) / done.length) * 100) / 100 : null,
    },
    rows: [...resolved.slice(0, 60), ...pending].slice(0, 80),
  };
}

/* --------------------------------------------------------------- routing */
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

function sendJSON(res, code, obj) {
  let body = Buffer.from(JSON.stringify(obj));
  const accept = (res.req && res.req.headers && res.req.headers['accept-encoding']) || '';
  const headers = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' };
  if (body.length > 2048 && /gzip/.test(accept)) {
    body = require('zlib').gzipSync(body);
    headers['content-encoding'] = 'gzip';
  }
  headers['content-length'] = body.length;
  res.writeHead(code, headers);
  res.end(body);
}

function publicConfig() {
  return {
    product: config.product,
    tiers: config.tiers,
    paper: config.paper,
    signal: config.signal,
    universe: config.board.universe,
    intervals: ['1h', '4h', '1d'],
    mode: config.product.mode,
    dev: config.dev,
    launch: config.launch,
    backtest: { days: config.backtest.days, interval: config.backtest.interval, forwardDays: config.backtest.forwardDays },
  };
}

let configMtime = fs.statSync(CONFIG_PATH).mtimeMs;
function reloadConfig() {
  const next = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  Object.keys(config).forEach((k) => delete config[k]);
  Object.assign(config, next);
  configMtime = fs.statSync(CONFIG_PATH).mtimeMs;
  cache.delete('board'); cache.delete('yields');
  return config;
}

const ALLOWED_INTERVALS = new Set(['15m', '1h', '4h', '1d']);

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const p = url.pathname;
  stats.requests++;
  try {
    if (p === '/api/health') {
      return sendJSON(res, 200, { ok: true, uptime: process.uptime(), now: new Date().toISOString(), killed: isKilled(), version: publicVersion() });
    }
    if (p === '/api/version') return sendJSON(res, 200, { v: publicVersion(), killed: isKilled() });
    if (p === '/api/config') return sendJSON(res, 200, publicConfig());
    if (p === '/api/board') {
      if (isKilled()) return sendJSON(res, 503, { error: 'kill switch active', file: config.killSwitchFile });
      const data = await cached('board', config.board.cacheTtlSec, buildBoard);
      try { logSignals(data); } catch (e) { console.error('[track]', e.message); }
      return sendJSON(res, 200, data);
    }
    if (p === '/api/ticker') {
      const data = await cached('ticker', 5, buildTicker);
      return sendJSON(res, 200, data);
    }
    if (p === '/api/yields') {
      const data = await cached('yields', config.yields.cacheTtlSec, buildYields);
      return sendJSON(res, 200, data);
    }
    if (p === '/api/candles') {
      const coin = (url.searchParams.get('coin') || 'BTC').toUpperCase();
      const interval = url.searchParams.get('interval') || config.board.interval;
      const limit = Math.max(1, Math.min(1000, Number(url.searchParams.get('limit') || 300) || 300));
      if (!/^[A-Z0-9]{1,12}$/.test(coin)) return sendJSON(res, 400, { error: 'bad coin' });
      if (!ALLOWED_INTERVALS.has(interval)) return sendJSON(res, 400, { error: 'bad interval' });
      const key = `candles:${coin}:${interval}:${limit}`;
      const data = await cached(key, 30, () => buildCandles(coin, interval, limit));
      return sendJSON(res, 200, { coin, interval, candles: data });
    }
    if (p === '/api/backtest') {
      const data = await cached('backtest', config.backtest.cacheTtlSec, runBacktest);
      return sendJSON(res, 200, data);
    }
    if (p === '/api/track') return sendJSON(res, 200, await cached('track', 30, buildTrack));

    /* ------------------------------------------------- ledger + admin */
    if (p === '/api/ledger' && req.method === 'GET') {
      const limit = Math.max(1, Math.min(500, Number(url.searchParams.get('limit') || 100)));
      return sendJSON(res, 200, { rows: readJsonlTail(config.ledger.file, limit) });
    }
    if (p === '/api/ledger' && req.method === 'POST') {
      let raw = '';
      for await (const chunk of req) { raw += chunk; if (raw.length > 20000) { res.writeHead(413); return res.end('too large'); } }
      let body;
      try { body = JSON.parse(raw); } catch (e) { return sendJSON(res, 400, { error: 'bad json' }); }
      const row = Object.assign({ ts: Date.now(), id: 'e' + Date.now().toString(36) }, body);
      appendJsonl(config.ledger.file, row);
      return sendJSON(res, 200, { ok: true, row });
    }
    if (p === '/api/status') {
      const cacheRows = [...cache.entries()].map(([key, e]) => ({
        key, ageSec: Math.round((Date.now() - e.ts) / 1000), ttlSec: e.ttl,
      })).sort((a, b) => b.ageSec - a.ageSec);
      let needs = null;
      try { needs = JSON.parse(fs.readFileSync(path.resolve(ROOT, 'needs.json'), 'utf8')); } catch (e) { /* optional */ }
      return sendJSON(res, 200, {
        ok: true, killed: isKilled(), mode: config.product.mode,
        version: publicVersion(), configMtime: new Date(configMtime).toISOString(),
        uptimeSec: Math.round(process.uptime()), stats,
        cache: cacheRows,
        counts: {
          signals: readJsonlTail(config.track.file, 100000).length,
          ledger: readJsonlTail(config.ledger.file, 100000).length,
        },
        needs,
        humanGo: fs.existsSync(path.resolve(ROOT, 'data/human_go.txt')),
      });
    }
    if (p === '/api/admin/reload' && req.method === 'POST') {
      reloadConfig();
      return sendJSON(res, 200, { ok: true, config: publicConfig() });
    }
    if (p === '/api/admin/kill' && req.method === 'POST') {
      fs.writeFileSync(killPath(), 'killed ' + new Date().toISOString() + '\n');
      return sendJSON(res, 200, { ok: true, killed: true });
    }
    if (p === '/api/admin/unkill' && req.method === 'POST') {
      try { fs.unlinkSync(killPath()); } catch (e) { /* already gone */ }
      return sendJSON(res, 200, { ok: true, killed: false });
    }

    // static
    let file = p === '/' ? '/index.html' : p;
    file = path.normalize(file).replace(/^(\.\.[/\\])+/, '');
    const abs = path.join(PUB, file);
    if (!abs.startsWith(PUB)) { res.writeHead(403); return res.end('forbidden'); }
    fs.readFile(abs, (err, buf) => {
      if (err) { res.writeHead(404, { 'content-type': 'text/plain' }); return res.end('not found'); }
      res.writeHead(200, {
        'content-type': MIME[path.extname(abs)] || 'application/octet-stream',
        'cache-control': 'no-cache', // dev loop: the file you saved is the file you get
        'x-content-type-options': 'nosniff',
      });
      res.end(buf);
    });
  } catch (e) {
    console.error('[error]', p, String(e && e.stack || e));
    sendJSON(res, 500, { error: String(e && e.message || e) });
  }
});

server.listen(PORT, BIND, () => {
  console.log(`[edge-terminal] listening on http://${BIND}:${PORT} (mode=${config.product.mode})`);
});
