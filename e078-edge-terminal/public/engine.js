/* Edge engine — single source of truth for indicators, signal scoring and
 * position sizing. Loaded by the browser (window.EdgeMath) and required by the
 * Node server / tests (module.exports). Pure functions only, no I/O. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.EdgeMath = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  function rsi(closes, period = 14) {
    if (!Array.isArray(closes) || closes.length < period + 1) return null;
    let gain = 0, loss = 0;
    for (let i = closes.length - period; i < closes.length; i++) {
      const d = closes[i] - closes[i - 1];
      if (d >= 0) gain += d; else loss -= d;
    }
    if (loss === 0) return 100;
    const rs = gain / period / (loss / period);
    return 100 - 100 / (1 + rs);
  }

  function sma(values, period) {
    if (!Array.isArray(values) || values.length < period) return null;
    const slice = values.slice(-period);
    return slice.reduce((a, b) => a + b, 0) / period;
  }

  function smaSeries(values, period) {
    const out = new Array(values.length).fill(null);
    let sum = 0;
    for (let i = 0; i < values.length; i++) {
      sum += values[i];
      if (i >= period) sum -= values[i - period];
      if (i >= period - 1) out[i] = sum / period;
    }
    return out;
  }

  function atr(candles, period = 14) {
    if (!Array.isArray(candles) || candles.length < period + 1) return null;
    const trs = [];
    for (let i = candles.length - period; i < candles.length; i++) {
      const c = candles[i], p = candles[i - 1];
      trs.push(Math.max(c.h - c.l, Math.abs(c.h - p.c), Math.abs(c.l - p.c)));
    }
    return trs.reduce((a, b) => a + b, 0) / trs.length;
  }

  /* Signal score in [-1, 1]. Trend/momentum say WHERE, RSI and funding say WHEN. */
  function scoreOf(row, weights) {
    const w = weights || { trend: 0.4, rsi: 0.2, momentum: 0.25, funding: 0.15 };
    let trend = 0;
    if (row.price && row.sma20 && row.sma50) {
      if (row.price > row.sma20 && row.sma20 > row.sma50) trend = 1;
      else if (row.price < row.sma20 && row.sma20 < row.sma50) trend = -1;
    }
    const r = row.rsi == null ? 50 : row.rsi;
    const rsiScore = r < 30 ? 1 : r > 70 ? -1 : clamp((50 - r) / 20, -1, 1);
    const momScore = row.ret7dPct == null ? 0 : clamp(row.ret7dPct / 15, -1, 1);

    let fundScore = 0;
    if (row.fundingZ != null && row.fundingZ !== 0) fundScore = clamp(-row.fundingZ / 1.5, -1, 1);
    else if (row.fundingAprPct != null) fundScore = clamp(-row.fundingAprPct / 40, -1, 1);

    const score =
      w.trend * trend + w.rsi * rsiScore + w.momentum * momScore + w.funding * fundScore;
    return { score: Math.round(clamp(score, -1, 1) * 1000) / 1000, trend };
  }

  function labelOf(score, signalCfg) {
    if (score >= signalCfg.longThreshold) return 'LONG';
    if (score <= signalCfg.shortThreshold) return 'SHORT';
    return 'NEUTRAL';
  }

  /* Full decision: side, entry/stop/target, size, leverage, fees, R:R.
   * ctx = { tiers, paper, equityUsd, tierKey, signal } */
  function decide(row, ctx) {
    const t = ctx.tiers[ctx.tierKey];
    if (!t) throw new Error('unknown tier: ' + ctx.tierKey);
    const score = row.score || 0;
    const price = row.price;
    const atrVal = row.atr || price * 0.01;
    const equity = ctx.equityUsd;

    let side = null;
    if (score >= t.minScore) side = 'long';
    else if (score <= -t.minScore) side = 'short';

    const stopDist = t.stopAtr * atrVal;
    const targetDist = t.targetAtr * atrVal;
    const rr = t.targetAtr / t.stopAtr;

    const out = {
      tierKey: ctx.tierKey, tier: t, side, score, rr,
      breakEvenWin: 1 / (1 + rr),
      actionable: !!side,
      stopDist, targetDist, atr: atrVal, price,
    };

    if (side) {
      const entry = price;
      const stop = side === 'long' ? entry - stopDist : entry + stopDist;
      const target = side === 'long' ? entry + targetDist : entry - targetDist;
      const lev = Math.max(1, Math.min(t.maxLeverage, row.maxLeverage || t.maxLeverage));
      const riskUsd = equity * (t.riskPct / 100);
      let notional = riskUsd / (stopDist / entry);
      notional = Math.min(notional, equity * lev);
      notional = Math.max(notional, 10);
      const fees = notional * ((ctx.paper && ctx.paper.feePctPerSide || 0) / 100);
      out.plan = {
        entry, stop, target, lev,
        notional, margin: notional / lev, fees, riskUsd,
        liqPct: (1 / lev) * 100 * 0.95,
        feeShareOfRisk: riskUsd > 0 ? (fees * 2) / riskUsd : null,
      };
    }
    return out;
  }

  /* Weekly % estimate used by the Trade-vs-LP comparison card. */
  function weeklyEvPct(d) {
    const winProb = clamp(0.5 + d.score * 0.3, 0.2, 0.8);
    const evR = winProb * d.rr - (1 - winProb);
    return { winProb, evR };
  }

  return { clamp, rsi, sma, smaSeries, atr, scoreOf, labelOf, decide, weeklyEvPct };
});
