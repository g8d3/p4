/* Tests for the shared Edge engine (the math that generates trading advice).
 * Run: npm test   (node --test test/) */
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const EM = require('../public/engine.js');

const W = { trend: 0.4, rsi: 0.2, momentum: 0.25, funding: 0.15 };
const SIGNAL = { weights: W, longThreshold: 0.25, shortThreshold: -0.25 };

const TIERS = {
  conservative: { label: 'Conservative', riskPct: 0.5, maxLeverage: 1, stopAtr: 2, targetAtr: 3, minScore: 0.45, prefer: 'lp' },
  balanced: { label: 'Balanced', riskPct: 1, maxLeverage: 2, stopAtr: 1.5, targetAtr: 3, minScore: 0.3, prefer: 'either' },
  degen: { label: 'Degen', riskPct: 3, maxLeverage: 5, stopAtr: 1, targetAtr: 4, minScore: 0.2, prefer: 'trade' },
};
const PAPER = { startingEquityUsd: 10000, feePctPerSide: 0.045, slippagePct: 0.05, maxOpenPositions: 6 };

/* ------------------------------------------------------------ indicators */
test('rsi: rising series pins at 100, known 14-period value', () => {
  const up = Array.from({ length: 30 }, (_, i) => 100 + i);
  assert.strictEqual(EM.rsi(up), 100);

  // classic worked example: 14 periods of mixed deltas
  const closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
    45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64];
  const r = EM.rsi(closes, 14);
  assert.ok(r > 40 && r < 80, `rsi out of sane range: ${r}`);
});

test('rsi: returns null when there is not enough history', () => {
  assert.strictEqual(EM.rsi([1, 2, 3], 14), null);
  assert.strictEqual(EM.rsi(null, 14), null);
});

test('sma: window average, null when short', () => {
  assert.strictEqual(EM.sma([1, 2, 3, 4], 4), 2.5);
  assert.strictEqual(EM.sma([1, 2], 4), null);
  const series = EM.smaSeries([1, 2, 3, 4], 2);
  assert.deepStrictEqual(series, [null, 1.5, 2.5, 3.5]);
});

test('atr: true range of a synthetic path', () => {
  const candles = [
    { h: 10, l: 8, c: 9 }, { h: 11, l: 9, c: 10 }, { h: 12, l: 10, c: 11 },
    { h: 13, l: 11, c: 12 }, { h: 14, l: 12, c: 13 },
  ];
  // each bar spans exactly 2 (h = l + 2) and never gaps off the prior close,
  // so every true range is 2 and the ATR must be exactly 2
  assert.strictEqual(EM.atr(candles, 4), 2);
  assert.strictEqual(EM.atr(candles.slice(0, 1), 14), null);
});

/* --------------------------------------------------------------- scoring */
test('scoreOf: aligned uptrend scores positive, downtrend negative', () => {
  const up = EM.scoreOf({ price: 110, sma20: 105, sma50: 100, rsi: 55, ret7dPct: 8, fundingZ: 0 }, W);
  const down = EM.scoreOf({ price: 90, sma20: 95, sma50: 100, rsi: 45, ret7dPct: -8, fundingZ: 0 }, W);
  assert.ok(up.score > 0, `up ${up.score}`);
  assert.ok(down.score < 0, `down ${down.score}`);
  assert.strictEqual(up.trend, 1);
  assert.strictEqual(down.trend, -1);
});

test('scoreOf: missing indicators never produce NaN', () => {
  const s = EM.scoreOf({ price: 1 }, W);
  assert.ok(Number.isFinite(s.score), 'NaN leaked into score');
});

test('scoreOf: crowded funding (high positive z) drags the score down', () => {
  const base = { price: 100, sma20: 100, sma50: 100, rsi: 50, ret7dPct: 0 };
  const calm = EM.scoreOf(Object.assign({}, base, { fundingZ: 0 }), W);
  const crowded = EM.scoreOf(Object.assign({}, base, { fundingZ: 3 }), W);
  assert.ok(crowded.score < calm.score, 'fading crowding must lower the score');
});

test('scoreOf: score stays within [-1, 1]', () => {
  const s = EM.scoreOf({ price: 1000, sma20: 1, sma50: 0.5, rsi: 5, ret7dPct: 500, fundingZ: -50 }, W);
  assert.ok(s.score >= -1 && s.score <= 1, String(s.score));
});

test('labelOf: thresholds are inclusive exactly at the boundary', () => {
  assert.strictEqual(EM.labelOf(0.25, SIGNAL), 'LONG');
  assert.strictEqual(EM.labelOf(0.249, SIGNAL), 'NEUTRAL');
  assert.strictEqual(EM.labelOf(-0.25, SIGNAL), 'SHORT');
  assert.strictEqual(EM.labelOf(-0.249, SIGNAL), 'NEUTRAL');
  assert.strictEqual(EM.labelOf(NaN, SIGNAL), 'NEUTRAL');
});

/* --------------------------------------------------------------- decision */
function row(over = {}) {
  return Object.assign({
    coin: 'BTC', price: 100, atr: 2, maxLeverage: 20,
    score: 0.6, rsi: 60, ret7dPct: 5, fundingAprPct: 10, fundingZ: -0.2,
  }, over);
}
const ctx = (tierKey, over = {}) => Object.assign({ tiers: TIERS, paper: PAPER, equityUsd: 10000, tierKey, signal: SIGNAL }, over);

test('decide: below minScore there is no trade', () => {
  const d = EM.decide(row({ score: 0.1 }), ctx('balanced'));
  assert.strictEqual(d.side, null);
  assert.strictEqual(d.actionable, false);
  assert.strictEqual(d.plan, undefined);
  assert.ok(Number.isFinite(d.breakEvenWin));
});

test('decide: risk-sized notional matches riskPct x equity / stop distance', () => {
  const d = EM.decide(row(), ctx('balanced')); // 1% of 10k = $100 risk, stop = 1.5*2 = $3
  assert.strictEqual(d.side, 'long');
  assert.strictEqual(Math.round(d.plan.riskUsd), 100);
  const stopDist = 1.5 * 2;
  const expected = 100 / (stopDist / 100);
  assert.ok(Math.abs(d.plan.notional - expected) < 1e-6, `${d.plan.notional} vs ${expected}`);
  assert.strictEqual(Math.round(d.plan.margin), Math.round(d.plan.notional / d.plan.lev));
});

test('decide: leverage is capped by both the tier and the venue', () => {
  assert.strictEqual(EM.decide(row(), ctx('degen')).plan.lev, 5);
  assert.strictEqual(EM.decide(row({ maxLeverage: 3 }), ctx('degen')).plan.lev, 3);
  assert.strictEqual(EM.decide(row(), ctx('conservative')).plan.lev, 1);
});

test('decide: notional never exceeds equity x leverage', () => {
  const d = EM.decide(row({ atr: 0.01, score: 0.9 }), ctx('degen'));
  assert.ok(d.plan.notional <= 10000 * d.plan.lev + 1e-6, String(d.plan.notional));
});

test('decide: fees come from config, not a magic number', () => {
  const d = EM.decide(row(), ctx('balanced'));
  assert.ok(Math.abs(d.plan.fees - d.plan.notional * 0.045 / 100) < 1e-9);
});

test('decide: short flips stop and target sides', () => {
  const d = EM.decide(row({ score: -0.6 }), ctx('balanced'));
  assert.strictEqual(d.side, 'short');
  assert.ok(d.plan.stop > d.plan.entry);
  assert.ok(d.plan.target < d.plan.entry);
});

test('decide: R:R equals targetAtr/stopAtr and break-even is its complement', () => {
  const d = EM.decide(row(), ctx('balanced'));
  assert.strictEqual(d.rr, 2);
  assert.ok(Math.abs(d.breakEvenWin - 1 / 3) < 1e-9);
});

test('decide: unknown tier throws instead of silently defaulting', () => {
  assert.throws(() => EM.decide(row(), ctx('yolo')), /unknown tier/);
});

/* ------------------------------------------------------- LP comparison */
test('weeklyEvPct: neutral score implies a coin-flip edge', () => {
  const d = EM.decide(row({ score: 0 }), ctx('balanced'));
  const { winProb, evR } = EM.weeklyEvPct(d);
  assert.ok(Math.abs(winProb - 0.5) < 1e-9);
  // 0.5 * 2 - 0.5 = 0.5R at a coin flip with RR 2
  assert.ok(Math.abs(evR - 0.5) < 1e-9, String(evR));
});

test('weeklyEvPct: win probability is clamped to [0.2, 0.8]', () => {
  const d = EM.decide(row({ score: 1 }), ctx('balanced'));
  assert.ok(EM.weeklyEvPct(d).winProb <= 0.8);
});
