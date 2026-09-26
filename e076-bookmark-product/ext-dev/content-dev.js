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

  // --- XHR hook: runs in MAIN world via background (CSP-safe, no inline script) ---
  function injectHook() {
    try { chrome.runtime.sendMessage({ type: 'bv-exec-main' }); } catch (e) {}
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
  var mo = new MutationObserver(function () { domScrape(); });
  var hudEl = null;
  function hud() {
    try {
      if (hudEl) return hudEl;
      hudEl = document.createElement('div');
      hudEl.id = 'bv-hud';
      hudEl.setAttribute('style', 'position:fixed;left:8px;right:8px;bottom:12px;z-index:999999;background:#111;color:#fff;border-radius:10px;padding:8px 12px;font:13px/1.4 system-ui;display:flex;gap:8px;align-items:center;box-shadow:0 2px 12px rgba(0,0,0,.4)');
      hudEl.innerHTML = '<span id="bv-hud-t" style="flex:1">BookmarkVault: starting…</span><button id="bv-hud-b" style="background:#fff;color:#111;border:0;border-radius:6px;padding:8px 12px;font-size:13px">Pause</button>';
      (document.body || document.documentElement).appendChild(hudEl);
      hudEl.querySelector('#bv-hud-b').addEventListener('click', function () {
        importGet().then(function (cur) {
          var running = cur && cur.wish === 'run' && cur.state !== 'done' && cur.state !== 'challenge';
          importSet(running ? { wish: 'pause', state: 'paused' } : { wish: 'run', state: 'running', reason: '', cooldownUntil: 0 });
        });
      });
      return hudEl;
    } catch (e) { return null; }
  }
  function hudPaint() {
    var el = hud();
    if (!el) return;
    Promise.all([importGet(), new Promise(function (res) {
      try { chrome.runtime.sendMessage({ type: 'bv-stats' }, function (s) { res(s || {}); }); }
      catch (e) { res({}); }
    })]).then(function (parts) {
      var st = parts[0] || {}, s = parts[1] || {};
      var running = st.wish === 'run' && st.state !== 'done' && st.state !== 'challenge';
      var n = st.scrolls || 0, c = (typeof s.queued === 'number') ? s.queued : SEEN.size;
      var t = el.querySelector('#bv-hud-t'), b = el.querySelector('#bv-hud-b');
      if (t) t.textContent = st.state === 'done' ? 'BookmarkVault: done — ' + c + ' saved here.' :
        st.state === 'challenge' ? 'BookmarkVault: paused — ' + (st.reason || 'X asked us to slow down') + '.' :
        running ? 'BookmarkVault: importing… ' + n + ' scrolled · ' + c + ' saved.' :
        'BookmarkVault: watching · ' + c + ' saved here.';
      if (b) b.textContent = running ? 'Pause' : 'Import';
    });
  }
  try {
    if (chrome.storage && chrome.storage.onChanged) {
      chrome.storage.onChanged.addListener(function (chg) {
        if (chg[IMPORT_KEY] && chg[IMPORT_KEY].newValue) importMaybeStart(chg[IMPORT_KEY].newValue);
        if (chg['bv.tuning']) pushTuning();
        hudPaint();
      });
    }
  } catch (e) {}

  // --- In-page HUD: status + pause/resume right on x.com, no tab-hopping ---
  function pushTuning() {
    try {
      chrome.storage.local.get('bv.tuning', function (o) {
        try { window.postMessage({ __bvTuning: o['bv.tuning'] || null }, '*'); } catch (e) {}
      });
    } catch (e) {}
  }
  function beat() {
    try { chrome.runtime.sendMessage({ type: 'bv-heartbeat', page: location.href }); } catch (e) {}
  }
  function start() {
    injectHook();
    domScrape();
    importGet().then(importMaybeStart);
    pushTuning();
    hudPaint();
    try { setInterval(hudPaint, 5000); } catch (e) {}
    beat();
    try { setInterval(beat, 20000); } catch (e) {}
    try { mo.observe(document.body, { childList: true, subtree: true }); } catch (e) {}
    window.addEventListener('bv-backoff', function () { backoffUntil = Date.now() + 10 * 60 * 1000; });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
