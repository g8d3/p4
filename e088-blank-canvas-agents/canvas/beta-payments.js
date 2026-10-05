// beta-payments.js — fiat MoR stub + direct-crypto stub + refunds/guarantee.
// Plain JS, no deps. Browser (<script src>) and node (module.exports) compatible.
// RULE: revenue-share pays out ONLY from real settled payments. Test, pending,
// or refunded payments contribute zero. Zero revenue = zero payout.
(function (root) {
  var S = {
    token: "OSS",
    mor: "stub-mor", // fiat merchant-of-record placeholder (Stripe/Paddle wired later)
    cryptoAddress: "STUB-PLACEHOLDER", // direct-crypto receiving address placeholder
    guaranteeDays: 14, // full-refund window, no questions asked
    repos: [ // token's OSS repos + revenue weights (must sum to 1)
      { repo: "oss/core", weight: 0.6 },
      { repo: "oss/docs", weight: 0.25 },
      { repo: "oss/tooling", weight: 0.15 }
    ],
    ledger: [], // payment events; {id,method,amountCents,live,status,ts,tx,refunded}
    refunds: [], // {id,paymentId,reason,status,ts}
    seq: 0
  };
  function now() { return Date.now(); }
  function real(p) { // the ONLY money that counts toward revenue-share
    return !!p.live && p.status === "settled" && !p.refunded;
  }
  function splitCents(amountCents) { // fixed-weight split preview for any amount
    var out = [], acc = 0;
    S.repos.forEach(function (r, i) {
      var c = i < S.repos.length - 1 ? Math.floor(amountCents * r.weight) : amountCents - acc;
      acc += c; out.push({ repo: r.repo, cents: c });
    });
    return out;
  }
  function configure(o) { // machine values come from caller/settings, never hardcoded
    if (o.token) S.token = o.token;
    if (o.mor) S.mor = o.mor;
    if (o.cryptoAddress) S.cryptoAddress = o.cryptoAddress;
    if (o.guaranteeDays != null) S.guaranteeDays = o.guaranteeDays;
    if (o.repos) S.repos = o.repos;
    return snapshot();
  }
  function mk(method, amountCents, live) {
    var p = { id: "pay_" + (++S.seq), method: method, amountCents: amountCents,
      live: !!live, status: "pending", ts: now(), tx: null, refunded: false };
    S.ledger.push(p); return p;
  }
  // --- fiat via merchant-of-record (stub: no network, explicit live/test flag)
  function fiatCheckout(amountCents, opts) {
    opts = opts || {};
    return mk("fiat-mor:" + S.mor, amountCents, opts.live);
  }
  function fiatConfirm(id) { // stub webhook: live settles real, test settles as test (worth $0)
    var p = find(id); if (!p || p.method.indexOf("fiat") !== 0) return null;
    p.status = p.live ? "settled" : "settled-test"; return p;
  }
  // --- direct crypto (stub: invoice + tx-hash placeholder, manual confirm = chain watch later)
  function cryptoInvoice(amountCents, opts) {
    var p = mk("crypto-direct", amountCents, true);
    p.address = (opts && opts.address) || S.cryptoAddress;
    return p;
  }
  function cryptoSubmitTx(id, txHash) { // wallet broadcasts, we store the placeholder hash
    var p = find(id); if (!p || p.method !== "crypto-direct") return null;
    p.tx = txHash || "TX-PLACEHOLDER"; p.status = "submitted"; return p;
  }
  function cryptoConfirm(id) { // stub for N-confirmation watcher: only real tx counts
    var p = find(id); if (!p || p.method !== "crypto-direct") return null;
    if (!p.tx) return null; p.status = "settled"; return p;
  }
  // --- revenue-share: ONLY real settled non-refunded payments
  function revenueCents() {
    return S.ledger.reduce(function (a, p) { return a + (real(p) ? p.amountCents : 0); }, 0);
  }
  function payouts() { // zero revenue => every repo gets 0. No advances, no estimates.
    var total = revenueCents(), out = [], acc = 0;
    S.repos.forEach(function (r, i) {
      var c = total ? (i < S.repos.length - 1 ? Math.floor(total * r.weight) : total - acc) : 0;
      acc += c; out.push({ repo: r.repo, cents: c });
    });
    return { totalCents: total, payouts: out };
  }
  // --- refunds / guarantee: full refund within window, only against real payments
  function requestRefund(paymentId, reason) {
    var p = find(paymentId); if (!p) return null;
    var r = { id: "ref_" + (++S.seq), paymentId: paymentId,
      reason: reason || "guarantee", status: "pending", ts: now() };
    S.refunds.push(r); return r;
  }
  function decideRefund(refundId, approve) {
    var r = S.refunds.filter(function (x) { return x.id === refundId; })[0];
    if (!r || r.status !== "pending") return null;
    var p = find(r.paymentId);
    var ageDays = (now() - p.ts) / 864e5;
    if (!approve || !real(p) || ageDays > S.guaranteeDays) { r.status = "denied"; return r; }
    r.status = "approved"; p.refunded = true; p.status = "refunded"; return r;
  }
  function find(id) { return S.ledger.filter(function (p) { return p.id === id; })[0] || null; }
  function snapshot() {
    return { token: S.token, guaranteeDays: S.guaranteeDays, payments: S.ledger.length,
      refunds: S.refunds.length, revenueCents: revenueCents(), payouts: payouts() };
  }
  var API = { configure: configure, fiatCheckout: fiatCheckout, fiatConfirm: fiatConfirm,
    cryptoInvoice: cryptoInvoice, cryptoSubmitTx: cryptoSubmitTx, cryptoConfirm: cryptoConfirm,
    splitCents: splitCents, revenueCents: revenueCents, payouts: payouts,
    requestRefund: requestRefund, decideRefund: decideRefund, snapshot: snapshot, _state: S };
  if (typeof module !== "undefined") module.exports = API;
  root.BetaPay = API;
})(typeof window !== "undefined" ? window : globalThis);
