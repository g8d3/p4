// BookmarkVault resilience scorer (shared by background worker + sidepanel).
// 0-100 risk: <40 sync, 40-70 slow mode, >70 pause.
var BVResilience = (function () {
  'use strict';
  function score(plan) {
    var reasons = [];
    var s = 0;
    var meta = (plan && plan.meta) || {};
    var q = (plan && plan.queue) || [];
    if (meta.last429 && Date.now() - meta.last429 < 24 * 3600 * 1000) { s += 30; reasons.push('429 seen in last 24h'); }
    if (meta.schemaDrift) { s += 25; reasons.push('XHR schema drift'); }
    if (typeof meta.mismatchRate === 'number' && meta.mismatchRate > 0.1) { s += 20; reasons.push('DOM/XHR mismatch >10%'); }
    var oldest = 0;
    q.forEach(function (r) {
      var t = Date.parse(r.queued_at || '');
      if (t && (!oldest || t < oldest)) oldest = t;
    });
    if (oldest && Date.now() - oldest > 24 * 3600 * 1000) { s += 15; reasons.push('queue older than 24h'); }
    var fails = meta.fails || 0;
    s += Math.min(fails * 10, 30);
    if (fails) reasons.push(fails + ' consecutive failure(s)');
    if (s > 100) s = 100;
    return { score: s, reasons: reasons, action: s < 40 ? 'sync' : s <= 70 ? 'slow' : 'pause' };
  }
  return { score: score };
})();
if (typeof self !== 'undefined') self.BVResilience = BVResilience;
