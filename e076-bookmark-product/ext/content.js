// BookmarkVault content script — dual capture (XHR primary + DOM fallback).
// Human-piggyback only: observes while the user browses bookmarks. No auto-scroll.
(function () {
  'use strict';
  var SEEN = new Map(); // id -> record
  var backoffUntil = 0;

  function send(records) {
    if (!records.length) return;
    try { chrome.runtime.sendMessage({ type: 'bv-capture', records: records }); } catch (e) {}
  }

  function upsert(rec) {
    if (!rec || !rec.id) return null;
    var prev = SEEN.get(rec.id);
    if (prev && prev.source === 'xhr' && rec.source === 'dom') return null; // XHR wins
    if (prev && prev.source === rec.source && prev.text === rec.text) return null; // dupe
    SEEN.set(rec.id, rec);
    return rec;
  }

  // --- XHR hook: page-context script observes fetch/XHR bookmark payloads ---
  function injectHook() {
    var s = document.createElement('script');
    s.textContent = '(' + hookFn.toString() + ')();';
    (document.head || document.documentElement).appendChild(s);
    s.remove();
  }
  function hookFn() {
    function pick(obj, out) {
      if (!obj || typeof obj !== 'object') return;
      if (Array.isArray(obj)) { for (var i = 0; i < obj.length; i++) pick(obj[i], out); return; }
      // GraphQL tweet shape: legacy.full_text + core.user_results.legacy.screen_name
      if (obj.legacy && typeof obj.legacy.full_text === 'string' &&
          (obj.rest_id || obj.legacy.id_str)) {
        var user = '';
        try { user = obj.core.user_results.result.legacy.screen_name || ''; } catch (e) {}
        out.push({
          id: String(obj.rest_id || obj.legacy.id_str),
          text: obj.legacy.full_text.slice(0, 2000),
          author: user,
          created_at: obj.legacy.created_at || '',
          source: 'xhr'
        });
        return;
      }
      for (var k in obj) { if (Object.prototype.hasOwnProperty.call(obj, k)) pick(obj[k], out); }
    }
    function emit(payload) {
      try {
        var out = [];
        var data = typeof payload === 'string' ? JSON.parse(payload) : payload;
        pick(data, out);
        if (out.length) window.postMessage({ __bv: true, records: out.slice(0, 100) }, '*');
      } catch (e) {}
    }
    var of = window.fetch;
    var historyPage = /\/i\/history/.test(location.pathname);
    window.fetch = function () {
      return of.apply(this, arguments).then(function (res) {
        var url = '';
        try { url = (typeof arguments[0] === 'string' ? arguments[0] : arguments[0].url) || ''; } catch (e) {}
        if (/Bookmark|bookmark/i.test(url) || (historyPage && /graphql/i.test(url))) {
          try {
            res.clone().text().then(emit).catch(function () {});
          } catch (e) {}
        }
        return res;
      });
    };
    var ox = window.XMLHttpRequest.prototype.open;
    window.XMLHttpRequest.prototype.open = function (m, u) {
      try { this.__bvUrl = String(u || ''); } catch (e) {}
      return ox.apply(this, arguments);
    };
    var os = window.XMLHttpRequest.prototype.send;
    window.XMLHttpRequest.prototype.send = function () {
      var self = this;
      self.addEventListener('load', function () {
        if (/Bookmark|bookmark/i.test(self.__bvUrl || '') || (historyPage && /graphql/i.test(self.__bvUrl || ''))) {
          try { emit(self.responseText || ''); } catch (e) {}
        }
      });
      return os.apply(this, arguments);
    };
  }

  window.addEventListener('message', function (ev) {
    if (!ev.data || !ev.data.__bv || !Array.isArray(ev.data.records)) return;
    var fresh = [];
    ev.data.records.forEach(function (r) { var u = upsert(r); if (u) fresh.push(u); });
    send(fresh);
  });

  // --- DOM fallback: parse article[data-testid=tweet] ---
  function domScrape() {
    if (Date.now() < backoffUntil) return;
    var fresh = [];
    document.querySelectorAll('article[data-testid="tweet"]').forEach(function (el) {
      var link = el.querySelector('a[href*="/status/"]');
      var m = link ? /\/status\/(\d+)/.exec(link.getAttribute('href') || '') : null;
      if (!m) return;
      var textEl = el.querySelector('[data-testid="tweetText"]');
      var timeEl = el.querySelector('time');
      var userEl = el.querySelector('[data-testid="User-Name"]');
      var r = {
        id: m[1],
        text: textEl ? (textEl.innerText || '').slice(0, 2000) : '',
        author: userEl ? (userEl.innerText || '').split('\n')[0].replace(/^@/, '').slice(0, 80) : '',
        created_at: timeEl ? (timeEl.getAttribute('datetime') || '') : '',
        source: 'dom'
      };
      var u = upsert(r);
      if (u) fresh.push(u);
    });
    send(fresh);
  }

  // --- Full-history import: human-paced auto-scroll, user-started only ---
  // Never runs on its own: sidepanel sets bv.import.v1.wish='run' when YOU tap
  // Start. Scrolls ~650px every ~3s (like a person), keeps its place so you
  // can pause/resume, and stops by itself if X shows a login/captcha/rate wall.
  var IMPORT_KEY = 'bv.import.v1';
  var impTimer = null, impBottomHits = 0, impLastY = 0;
  function importGet() {
    try {
      return chrome.storage.local.get(IMPORT_KEY).then(function (o) { return o[IMPORT_KEY] || null; });
    } catch (e) { return Promise.resolve(null); }
  }
  function importSet(patch) {
    try {
      return importGet().then(function (cur) {
        var nxt = Object.assign({}, cur || {}, patch, { updated_at: new Date().toISOString() });
        var obj = {}; obj[IMPORT_KEY] = nxt;
        return chrome.storage.local.set(obj).then(function () { return nxt; });
      });
    } catch (e) { return Promise.resolve(null); }
  }
  function challengeReason() {
    try {
      var body = document.body ? document.body.innerText.slice(0, 4000) : '';
      var hasLoginForm = !!document.querySelector('input[type="password"]');
      if (hasLoginForm && /log in|sign in/i.test(body)) return 'X shows a login wall';
      if (/captcha|verify you are (a )?human|unusual activity/i.test(body)) return 'X shows a check';
      if (/rate limit|too many requests|something went wrong.*retry/i.test(body)) return 'X asked us to slow down';
      if (/429/.test(body) && /retry/i.test(body)) return 'X asked us to slow down';
    } catch (e) {}
    return '';
  }
  function importStop(timerOnly) {
    if (impTimer) { clearInterval(impTimer); impTimer = null; }
    if (!timerOnly) impBottomHits = 0;
  }
  function importTick() {
    if (document.hidden) return; // only while you watch this tab
    var why = challengeReason();
    if (why) {
      importStop();
      importSet({ wish: 'pause', state: 'challenge', reason: why,
        checkpointY: window.scrollY || 0, cooldownUntil: Date.now() + 10 * 60 * 1000 });
      try { chrome.runtime.sendMessage({ type: 'bv-import-challenge', reason: why }); } catch (e) {}
      try { window.dispatchEvent(new CustomEvent('bv-backoff')); } catch (e) {}
      return;
    }
    try { window.scrollBy({ top: 650, behavior: 'smooth' }); } catch (e) { try { window.scrollBy(0, 650); } catch (e2) {} }
    var y = window.scrollY || 0;
    var bottom = false;
    try { bottom = (window.innerHeight + y) >= (document.documentElement.scrollHeight - 300); } catch (e) {}
    impBottomHits = bottom ? impBottomHits + 1 : 0;
    var lastId = '';
    try { SEEN.forEach(function (_v, k) { lastId = k; }); } catch (e) {}
    // increment scrolls + captured via read-modify-write
    importGet().then(function (cur) {
      var n = ((cur && cur.scrolls) || 0) + 1;
      var upd = { state: 'running', scrolls: n, checkpointY: y, checkpointId: lastId, captured: SEEN.size };
      if (n >= 1500 || impBottomHits >= 4) { upd.state = 'done'; upd.wish = 'idle'; importStop(); }
      return importSet(upd);
    });
    impLastY = y;
  }
  function importMaybeStart(st) {
    if (!st || st.wish !== 'run') { importStop(); return; }
    if (st.cooldownUntil && Date.now() < st.cooldownUntil && st.state === 'challenge') return; // wait out the 10 min
    if (st.state === 'done') { importStop(); return; }
    if (impTimer) return;
    impBottomHits = 0;
    importSet({ state: 'running' });
    impTimer = setInterval(importTick, 2800 + Math.floor(Math.random() * 900));
  }
  try {
    if (chrome.storage && chrome.storage.onChanged) {
      chrome.storage.onChanged.addListener(function (chg) {
        if (chg[IMPORT_KEY] && chg[IMPORT_KEY].newValue) importMaybeStart(chg[IMPORT_KEY].newValue);
      });
    }
  } catch (e) {}

  var mo = new MutationObserver(function () { domScrape(); });
  function beat() {
    try { chrome.runtime.sendMessage({ type: 'bv-heartbeat', page: location.href }); } catch (e) {}
  }
  function start() {
    injectHook();
    domScrape();
    importGet().then(importMaybeStart);
    beat();
    try { setInterval(beat, 20000); } catch (e) {}
    try { mo.observe(document.body, { childList: true, subtree: true }); } catch (e) {}
    window.addEventListener('bv-backoff', function () { backoffUntil = Date.now() + 10 * 60 * 1000; });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
