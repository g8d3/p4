// BookmarkVault content script — dual capture (XHR primary + DOM fallback).
// Human-piggyback only: observes while the user browses X (bookmarks, likes,
// history). No auto-scroll except the user-started full-history import.
(function () {
  'use strict';
  var SEEN = new Map(); // id -> record
  var backoffUntil = 0;

  function pageType() {
    try {
      var p = location.pathname || '';
      if (/\/i\/bookmarks/.test(p)) return 'bookmarks';
      if (/\/likes/.test(p)) return 'likes';
      if (/\/i\/history/.test(p)) return 'history';
    } catch (e) {}
    return 'other';
  }

  function send(records) {
    if (!records.length) return;
    try { chrome.runtime.sendMessage({ type: 'bv-capture', records: records }); } catch (e) {}
  }

  var PAGE_OK = { bookmarks: 1, likes: 1, history: 1, other: 1 };
  function normPagesLocal(rec) {
    var out = [];
    var list = Array.isArray(rec.pages) ? rec.pages : [rec.page];
    list.forEach(function (p) { if (PAGE_OK[p] && out.indexOf(p) < 0) out.push(p); });
    if (!out.length) out.push('bookmarks');
    return out;
  }
  function upsert(rec) {
    if (!rec || !rec.id) return null;
    rec.pages = normPagesLocal(rec);
    // Button states upgrade tags: a liked tweet seen on the bookmarks page
    // counts as both without visiting the likes page (and vice versa).
    if (rec.liked === true && rec.pages.indexOf('likes') < 0) rec.pages.push('likes');
    if (rec.saved === true && rec.pages.indexOf('bookmarks') < 0) rec.pages.push('bookmarks');
    rec.page = rec.pages[0];
    var prev = SEEN.get(rec.id);
    if (!prev) { SEEN.set(rec.id, rec); return rec; }
    prev.pages = normPagesLocal(prev);
    // Same tweet on another page (bookmark + like): merge tags so it
    // counts as both instead of being dropped as a dupe.
    var changed = false;
    rec.pages.forEach(function (p) {
      if (prev.pages.indexOf(p) < 0) { prev.pages.push(p); changed = true; }
    });
    // Button states ride BOTH paths: merge them even when XHR wins the text,
    // or DOM-only knowledge (liked/saved buttons) dies in dedupe. True is
    // sticky; false only fills unknowns (an unlike needs an XHR round-trip).
    if ((rec.liked === true || rec.liked === false) && prev.liked !== rec.liked) {
      if (prev.liked == null || rec.liked === true) { prev.liked = rec.liked; changed = true; }
    }
    if ((rec.saved === true || rec.saved === false) && prev.saved !== rec.saved) {
      if (prev.saved == null || rec.saved === true) { prev.saved = rec.saved; changed = true; }
    }
    if (prev.kind === 'tweet' && rec.kind && rec.kind !== 'tweet') { prev.kind = rec.kind; changed = true; }
    if (!prev.saveOrder && rec.saveOrder) { prev.saveOrder = rec.saveOrder; changed = true; }
    if (changed) {
      if (prev.liked === true && prev.pages.indexOf('likes') < 0) prev.pages.push('likes');
      if (prev.saved === true && prev.pages.indexOf('bookmarks') < 0) prev.pages.push('bookmarks');
      prev.page = prev.pages[0];
    }
    if (prev.source === 'xhr' && rec.source === 'dom') return changed ? prev : null; // XHR wins
    if (prev.source === 'dom' && rec.source === 'xhr') {
      prev.text = rec.text; prev.author = rec.author || prev.author;
      prev.created_at = rec.created_at || prev.created_at; prev.source = 'xhr';
      SEEN.set(rec.id, prev);
      return prev;
    }
    if (prev.source === rec.source && prev.text === rec.text) return changed ? prev : null; // dupe
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
    var pg = pageType();
    ev.data.records.forEach(function (r) { if (r && !r.page) r.page = pg; var u = upsert(r); if (u) fresh.push(u); });
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
      // Articles / cards / media render extra preview nodes outside tweetText —
      // grab them so those posts are not saved empty.
      var cardEl = el.querySelector('[data-testid="card.wrapper"]');
      var cardText = cardEl ? (cardEl.innerText || '').slice(0, 1000) : '';
      var base = textEl ? (textEl.innerText || '') : '';
      var kind = el.querySelector('a[href*="/i/article/"]') ? 'article'
        : el.querySelector('video') ? 'media'
        : cardEl ? 'card' : 'tweet';
      // Like/save button states: the single-page source of truth for the
      // user's two levels (liked vs liked+saved). X swaps like->unlike when
      // liked; bookmark reports via aria-pressed / aria-label.
      function btnState(btn, posRe) {
        if (!btn) return null;
        var tid = btn.getAttribute('data-testid') || '';
        var lab = btn.getAttribute('aria-label') || '';
        var pressed = btn.getAttribute('aria-pressed');
        if (/^un/.test(tid)) return true;
        if (pressed === 'true') return true;
        if (pressed === 'false') return false;
        if (posRe.test(lab) || posRe.test(tid)) return true;
        return false;
      }
      var liked = btnState(el.querySelector('[data-testid="like"], [data-testid="unlike"]'), /liked/i);
      var saved = btnState(el.querySelector('[data-testid="bookmark"]'), /bookmarked|saved/i);
      var r = {
        id: m[1],
        text: (base + ((cardText && (!base || cardText.indexOf(base.slice(0, 40)) < 0))
          ? '\n\u2014 \u2014 \u2014\n' + cardText : '')).slice(0, 3000),
        author: userEl ? (userEl.innerText || '').split('\n')[0].replace(/^@/, '').slice(0, 80) : '',
        created_at: timeEl ? (timeEl.getAttribute('datetime') || '') : '',
        source: 'dom',
        page: pageType(),
        kind: kind,
        context: 'seen',
        liked: liked,
        saved: saved,
        saveOrder: null
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
  // Minimized pill (never covers X UI for long: it is DRAGGABLE — hold and
  // move it anywhere; position persists. Tap (no move) opens the full panel.
  var pillEl = null, pillPos = null, pillDrag = null, pillSuppressClick = false;
  function pillApplyPos() {
    try {
      if (!pillEl || !pillPos) return;
      pillEl.style.left = pillPos.left + 'px';
      pillEl.style.top = pillPos.top + 'px';
      pillEl.style.bottom = 'auto';
      pillEl.style.right = 'auto';
    } catch (e) {}
  }
  function pillEndDrag(save) {
    if (!pillDrag) return false;
    var wasDrag = pillDrag.moved;
    pillDrag = null;
    if (wasDrag) {
      pillSuppressClick = true;
      if (save && pillPos) { try { chrome.storage.local.set({ 'bv.pillPos': pillPos }); } catch (e) {} }
    }
    return wasDrag;
  }
  function pill() {
    try {
      if (pillEl) return pillEl;
      pillEl = document.createElement('button');
      pillEl.id = 'bv-pill';
      pillEl.setAttribute('style', 'position:fixed;left:8px;bottom:12px;z-index:999999;background:#111;color:#fff;border:0;border-radius:20px;padding:8px 12px;font:12px system-ui;box-shadow:0 2px 12px rgba(0,0,0,.4);touch-action:none;user-select:none;-webkit-user-select:none;cursor:grab');
      pillEl.textContent = 'BV…';
      try {
        chrome.storage.local.get('bv.pillPos', function (o) {
          if (o && o['bv.pillPos'] && typeof o['bv.pillPos'].left === 'number') {
            pillPos = o['bv.pillPos'];
            pillApplyPos();
          }
        });
      } catch (e) {}
      // No click handler: mobile tap jitter + pointer capture make click
      // unreliable — taps open directly from pointerup below.
      pillEl.addEventListener('pointerdown', function (ev) {
        try {
          pillDrag = { x0: ev.clientX, y0: ev.clientY, moved: false, t0: Date.now() };
          pillEl.setPointerCapture(ev.pointerId);
        } catch (e) { pillDrag = null; }
      });
      pillEl.addEventListener('pointermove', function (ev) {
        if (!pillDrag) return;
        var dx = ev.clientX - pillDrag.x0, dy = ev.clientY - pillDrag.y0;
        if (!pillDrag.moved && Math.abs(dx) + Math.abs(dy) < 24) return;
        pillDrag.moved = true;
        try {
          var r = pillEl.getBoundingClientRect();
          pillPos = {
            left: Math.max(0, Math.min(window.innerWidth - r.width, r.left + dx)),
            top: Math.max(0, Math.min(window.innerHeight - r.height, r.top + dy))
          };
          pillDrag.x0 = ev.clientX; pillDrag.y0 = ev.clientY;
          pillApplyPos();
        } catch (e) {}
      });
      pillEl.addEventListener('pointerup', function (ev) {
        var dt = 9999;
        try { dt = Date.now() - (pillDrag ? pillDrag.t0 : 0); } catch (e) {}
        var wasDrag = pillEndDrag(true);
        if (!wasDrag && dt < 800) {
          try { ev.preventDefault(); } catch (e) {}
          try {
            if (window.BVAPP.isOpen()) window.BVAPP.close();
            else window.BVAPP.open();
          } catch (e2) {}
        }
      });
      pillEl.addEventListener('pointercancel', function () { pillEndDrag(false); });
      (document.body || document.documentElement).appendChild(pillEl);
      return pillEl;
    } catch (e) { return null; }
  }
  function pillPaint() {
    var el = pill();
    if (!el) return;
    Promise.all([importGet(), new Promise(function (res) {
      try { chrome.runtime.sendMessage({ type: 'bv-stats' }, function (s) { res(s || {}); }); }
      catch (e) { res({}); }
    })]).then(function (parts) {
      var st = parts[0] || {}, s = parts[1] || {};
      var running = st.wish === 'run' && st.state !== 'done' && st.state !== 'challenge';
      var n = st.scrolls || 0, c = (typeof s.queued === 'number') ? s.queued : SEEN.size;
      var pg = pageType();
      var where = pg === 'other' ? '' : pg + ' ';
      try {
        el.textContent = st.state === 'done' ? 'BV done ' + c :
          st.state === 'challenge' ? 'BV paused' :
          running ? 'BV ' + where + n + '·' + c : 'BV ' + where + c;
        try { el.style.background = running ? '#0b5f2a' : '#111'; } catch (e2) {}
      } catch (e) {}
    });
  }
  try {
    if (chrome.storage && chrome.storage.onChanged) {
      chrome.storage.onChanged.addListener(function (chg) {
        if (chg[IMPORT_KEY] && chg[IMPORT_KEY].newValue) importMaybeStart(chg[IMPORT_KEY].newValue);
        if (chg['bv.tuning']) pushTuning();
        pillPaint();
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
    pillPaint();
    try { setInterval(pillPaint, 5000); } catch (e) {}
    beat();
    try { setInterval(beat, 20000); } catch (e) {}
    try { mo.observe(document.body, { childList: true, subtree: true }); } catch (e) {}
    window.addEventListener('bv-backoff', function () { backoffUntil = Date.now() + 10 * 60 * 1000; });
  }
  window.__bvEngineStart = start; // boot is coordinated (see prelude below)
})();

  // Boot: static manifest delivery only. Remote eval is CSP-blocked on
  // x.com, so there is nothing to wait for (docs/extension-devtooling.md).
  window.__bvStandDown = true; // engine never self-starts
  (function bvCoordinate() {
    function go() {
      try {
        if (window.__bvUIBooted) return;
        window.__bvUIBooted = true;
        window.__bvEngineStart();
      } catch (e) {}
      try { chrome.runtime.sendMessage({ type: 'bv-devnote', note: 'panel-ui-boot' }); } catch (e2) {}
    }
    try { go(); } catch (e) {}
  })();

