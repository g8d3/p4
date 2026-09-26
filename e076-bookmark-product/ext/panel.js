// BookmarkVault in-page app (v0.3.0): capture engine + full panel UI.
// Delivered remotely (devMode) or as bundled snapshot; the whole UI
// rides the hot lane. Legacy sidepanel/ files remain as fallback.
(function () {
'use strict';
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



  // Backend calls are proxied through the background service worker:
  // content scripts must not fetch http endpoints from https pages.
  function bgFetch(url, opts) {
    opts = opts || {};
    var m = /^(https?:\/\/[^\/]+)(\/.*)$/.exec(String(url));
    var path = m ? m[2] : String(url);
    var body;
    try { body = opts.body ? JSON.parse(opts.body) : undefined; } catch (e) { body = undefined; }
    return new Promise(function (resolve) {
      function done(r) {
        r = r || {};
        resolve({ ok: !!r.ok, status: r.status || 0,
          json: function () { return Promise.resolve(r.data || {}); } });
      }
      try {
        chrome.runtime.sendMessage({ type: 'bv-api', method: opts.method || 'GET',
          path: path, body: body }, done);
      } catch (e) { done(null); }
    });
  }
  var BV_CSS = `
  :root { color-scheme: light dark; --pad: 72px; }
  * { box-sizing: border-box; }
  body { margin: 0; font: 15px/1.45 system-ui, sans-serif; padding-bottom: var(--pad); }
  header { padding: 12px 14px 4px; }
  header h1 { font-size: 17px; margin: 0; }
  header p { margin: 4px 0 8px; color: #666; font-size: 13px; }
  #status { margin: 0 14px 8px; padding: 8px 10px; border-radius: 8px; background: #f2f2f2; font-size: 13px; }
  #search { display: block; width: 100%; min-width: 0; padding: 10px; font-size: 15px; }
  .searchrow { display: flex; gap: 6px; margin: 0 14px 8px; }
  .searchrow input { flex: 1; min-width: 0; }
  #clearSearch { flex: 0 0 auto; padding: 10px 12px; font-size: 14px; white-space: nowrap; }
  #list li, #labList li, #whList li { min-width: 0; overflow-wrap: anywhere; word-break: break-word; }
  #list .txt { overflow-wrap: anywhere; white-space: pre-wrap; }
  #list .txt.collapsed { display: -webkit-box; -webkit-line-clamp: 5; -webkit-box-orient: vertical; overflow: hidden; }
  #list .morebtn { border: 0; background: none; color: #0b5fff; font-size: 12px; padding: 2px 0; cursor: pointer; }
  .kind { font-size: 11px; border: 1px solid #bbb; background: #f2f2f2; color: #333; border-radius: 4px; padding: 0 4px; margin-left: 6px; white-space: nowrap; }
  #list .meta { display: flex; flex-wrap: wrap; gap: 2px 6px; align-items: center; }
  #list .open { font-size: 12px; white-space: nowrap; }
  #list { list-style: none; margin: 0; padding: 0 14px; }
  #list li { border-bottom: 1px solid #ddd; padding: 8px 0; }
  #list .meta { font-size: 12px; color: #666; }
  #list .src { font-size: 11px; border: 1px solid #bbb; border-radius: 4px; padding: 0 4px; margin-left: 6px; }
  #list .dupe { font-size: 11px; border: 1px solid #c90; background: #fff8e1; color: #7a5b00; border-radius: 4px; padding: 0 4px; margin-left: 6px; white-space: nowrap; }
  nav.tabs { position: fixed; left: 0; right: 0; bottom: 0; display: flex; background: #fff; border-top: 1px solid #ddd; }
  nav.tabs button { flex: 1 1 0; min-width: 0; border: 0; background: none; padding: 10px 2px 12px; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  nav.tabs button[aria-selected="true"] { font-weight: 700; }
  .pane { display: none; padding: 0 0 8px; }
  .pane.active { display: block; }
  .row { padding: 8px 14px; }
  .row label { display: block; font-size: 13px; margin: 8px 0 4px; }
  .row input { width: 100%; padding: 9px; font-size: 14px; }
  .btn { display: inline-block; margin: 8px 14px; padding: 10px 16px; font-size: 14px; }
  #planRow #plan { font-size: 13px; background: #f2f2f2; border-radius: 8px; padding: 8px 10px; }
  #planHint { margin-top: 6px; }
  .hint { font-size: 12px; color: #666; padding: 0 14px; }
  #labelFilter { display: block; width: calc(100% - 28px); margin: 0 14px 8px; padding: 9px; font-size: 14px; }
  #typeFilter { display: block; width: calc(100% - 28px); margin: 0 14px 8px; padding: 9px; font-size: 14px; }
  #locFilter { display: block; width: calc(100% - 28px); margin: 0 14px 8px; padding: 9px; font-size: 14px; }
  .st { font-size: 11px; border-radius: 10px; padding: 0 7px; border: 1px solid; white-space: nowrap; margin-left: 6px; }
  .st-both { color: #7a5b00; border-color: #c90; background: #fff3c4; font-weight: 700; }
  .st-liked { color: #c2185b; border-color: #c2185b; background: #fdeef4; }
  .st-saved { color: #0b5fff; border-color: #0b5fff; background: #eef4ff; }
  .st-seen { color: #666; border-color: #bbb; }
  .st-quoted { color: #6a1b9a; border-color: #6a1b9a; background: #f3e8fd; }
  .ord { font-size: 11px; color: #333; background: #eee; border-radius: 4px; padding: 0 4px; margin-left: 6px; white-space: nowrap; }
  .verifyrow { display: block; margin: 0 14px 8px; font-size: 13px; }
  .verifyrow input { width: auto; }
  #verifyLine { margin: 0 14px 8px; font-size: 12px; color: #333; background: #f2f2f2; border-radius: 8px; padding: 8px 10px; }
  .impbarwrap { margin: 8px 14px 0; height: 8px; background: #e5e5e5; border-radius: 4px; overflow: hidden; }
  #impBar { height: 100%; width: 0; background: #111; }
  #impQueue { margin-top: 6px; }
  #buildBox { margin: 0 14px; font-size: 12px; color: #333; background: #f2f2f2; border-radius: 8px; padding: 8px 10px; white-space: pre-wrap; }
  .pg { font-size: 11px; border-radius: 10px; padding: 0 7px; border: 1px solid; white-space: nowrap; margin-left: 6px; }
  .pg-bookmarks { color: #0b5fff; border-color: #0b5fff; background: #eef4ff; }
  .pg-likes { color: #c2185b; border-color: #c2185b; background: #fdeef4; }
  .pg-history { color: #5d6d7e; border-color: #5d6d7e; background: #f2f4f6; }
  .pg-other { color: #666; border-color: #bbb; }
  .syncok { font-size: 11px; border-radius: 4px; padding: 0 4px; margin-left: 6px; white-space: nowrap; color: #1a7f37; border: 1px solid #1a7f37; background: #eaf7ee; }
  .syncpend { font-size: 11px; border-radius: 4px; padding: 0 4px; margin-left: 6px; white-space: nowrap; color: #7a5b00; border: 1px solid #c90; background: #fff8e1; }
  .chips { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px; }
  .chip { display: inline-block; font-size: 12px; background: #eef4ff; border: 1px solid #bcd; border-radius: 20px; padding: 1px 4px 1px 8px; }
  .chip button { border: 0; background: none; font-size: 12px; padding: 0 4px; cursor: pointer; }
  .attach { display: flex; gap: 6px; margin-top: 6px; }
  .attach select { flex: 1; min-width: 0; padding: 7px; font-size: 13px; }
  .attach button { padding: 7px 10px; font-size: 13px; white-space: nowrap; }
  #labList { list-style: none; margin: 8px 0 0; padding: 0 14px; }
  #labList li { display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #ddd; padding: 8px 0; font-size: 14px; }
  #labList .nm { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  #labList .ct { font-size: 12px; color: #666; white-space: nowrap; }
  #labList button { padding: 6px 10px; font-size: 13px; white-space: nowrap; }
  .labform { display: flex; gap: 6px; padding: 0 14px; }
  .labform input { flex: 1; min-width: 0; padding: 9px; font-size: 14px; }
  .labform button { padding: 9px 12px; font-size: 14px; white-space: nowrap; }
  #labStatus { margin: 8px 14px 0; font-size: 12px; color: #666; }
  .whform { display: flex; gap: 6px; padding: 0 14px; }
  .whform input { flex: 1; min-width: 0; padding: 9px; font-size: 14px; }
  .whform button { padding: 9px 12px; font-size: 14px; white-space: nowrap; }
  #whList { list-style: none; margin: 8px 0 0; padding: 0 14px; word-break: break-all; }
  #whList li { border-bottom: 1px solid #ddd; padding: 8px 0; font-size: 13px; }
  #whList .when { font-size: 12px; color: #666; }
  #whStatus { margin: 8px 14px 0; font-size: 12px; color: #666; }
  .apform { display: flex; gap: 6px; padding: 0 14px; }
  .apform input { flex: 1; min-width: 0; padding: 9px; font-size: 14px; }
  .apform button { padding: 9px 12px; font-size: 14px; white-space: nowrap; }
  #apList { list-style: none; margin: 8px 0 0; padding: 0 14px; }
  #apList li { border-bottom: 1px solid #ddd; padding: 8px 0; font-size: 13px; min-width: 0; overflow-wrap: anywhere; word-break: break-word; }
  #apList .t { font-weight: 600; }
  #apList .st { font-size: 11px; border: 1px solid #bbb; border-radius: 4px; padding: 0 4px; margin-left: 6px; white-space: nowrap; }
  #apList .row2 { display: flex; gap: 6px; margin-top: 6px; }
  #apList .row2 button { padding: 6px 12px; font-size: 13px; white-space: nowrap; }
  #apStatus { margin: 8px 14px 0; font-size: 12px; color: #666; }
  .impform { display: flex; gap: 6px; padding: 0 14px; align-items: center; flex-wrap: wrap; }
  .impform button { padding: 9px 12px; font-size: 14px; white-space: nowrap; }
  .impform a { font-size: 13px; white-space: nowrap; }
  #impStatus { margin: 8px 14px 0; font-size: 12px; color: #333; background: #f2f2f2; border-radius: 8px; padding: 8px 10px; }

#bv-app-host{position:fixed;inset:0;z-index:999999;display:none}#bv-app-host.open{display:block}#bv-app-host .scrim{position:absolute;inset:0;background:rgba(0,0,0,.35)}#bv-app{position:absolute;inset:0;margin:0 auto;max-width:800px;display:none;background:#fff;display:flex;flex-direction:column;box-shadow:0 0 40px rgba(0,0,0,.5);font:15px/1.45 system-ui,sans-serif;color:#111}#bv-app-bar{display:flex;gap:8px;align-items:center;padding:10px 12px;background:#111;color:#fff;font-size:14px;flex:0 0 auto}#bv-app-bar .t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}#bv-app-bar button{background:#222;color:#fff;border:1px solid #555;border-radius:6px;padding:6px 10px;font-size:13px}#bv-app-body{flex:1;min-width:0;overflow-y:auto}#bv-app-body .tabs{position:absolute;left:0;right:0;bottom:0}#bv-app-body .pane{padding-bottom:76px}#bv-pill{position:fixed;left:8px;bottom:12px;z-index:999999;background:#111;color:#fff;border:0;border-radius:20px;padding:8px 12px;font:12px system-ui;box-shadow:0 2px 12px rgba(0,0,0,.4);touch-action:none;user-select:none;-webkit-user-select:none;cursor:grab}#bv-pill.run{background:#0b5f2a}#bv-pill:active{cursor:grabbing}`;
  var BV_HTML = `<div id="bv-app-bar"><span class="t">BookmarkVault</span></div><div id="bv-app-body"><div id="status">Loading…</div>

<section class="pane active" id="pane-saved" aria-label="Saved">
  <div class="searchrow">
    <input id="search" type="search" placeholder="Search saved bookmarks…" autocomplete="off" aria-label="Search saved bookmarks">
    <button id="clearSearch" title="Clear search and label filter">Clear</button>
  </div>
  <select id="labelFilter" aria-label="Filter by label"><option value="">All labels</option></select>
  <select id="typeFilter" aria-label="Filter by type">
    <option value="">All types</option>
    <option value="likes">Liked</option>
    <option value="bookmarks">Bookmarked</option>
    <option value="both">Liked + bookmarked</option>
  </select>
  <label class="verifyrow"><input type="checkbox" id="verifyOrder"> Verify save order (newest/oldest)</label>
  <select id="locFilter" aria-label="Filter by location">
    <option value="">Everywhere (device + server)</option>
    <option value="device">This device only</option>
    <option value="server">On server only</option>
  </select>
  <div id="verifyLine" role="status" style="display:none"></div>
  <ul id="list"></ul>
</section>
<section class="pane" id="pane-labels" aria-label="Labels">
  <div class="row" style="padding-bottom:0"><strong>Labels</strong></div>
  <p class="hint">Group bookmarks with labels. Saved on this device; synced to the server when an API base + token is set.</p>
  <div class="labform">
    <input id="labName" placeholder="New label name" maxlength="40" autocomplete="off">
    <button id="labCreate">Create</button>
  </div>
  <div id="labStatus" role="status">Loading…</div>
  <ul id="labList"></ul>
</section>
<section class="pane" id="pane-sync" aria-label="Sync">
  <div class="row">
    <label for="apiBase">API base URL</label>
    <input id="apiBase" placeholder="https://…">
    <label for="token">Token</label>
    <input id="token" placeholder="Paste token" autocomplete="off">
  </div>
  <button class="btn" id="save">Save settings</button>
  <button class="btn" id="sync">Sync now</button>
  <a class="btn" id="viewServer" href="http://127.0.0.1:8899/view" target="_blank" rel="noopener" style="text-decoration:none;border:1px solid #111;border-radius:8px;">View on server</a>
  <div class="row" style="padding-bottom:0"><strong>This build</strong></div>
  <div id="buildBox" role="status">Checking…</div>
  <div><button class="btn" id="verCheck" style="margin:8px 14px">Check for updates</button></div>
  <p class="hint">Uploads only with a token. Test mode: stays local until you add one.</p>
  <div class="row" id="devRow">
    <label><input type="checkbox" id="devMode" style="width:auto"> Developer mode (tuning loads from server, no reinstall)</label>
    <div><button class="btn" id="tuneBtn" style="margin:8px 0 0">Refresh tuning</button></div>
    <div class="hint" id="tuneHint" style="padding:0">Off = store build (frozen). On = my latest tuning applies on next scroll.</div>
  </div>
  <div class="row" id="health"></div>
  <div class="row" id="planRow">
    <div id="plan" role="status">Plan: checking…</div>
    <div><button class="btn" id="planBtn" style="margin:8px 0 0">Check plan</button></div>
    <div class="hint" id="planHint" style="padding:0">Reads GET /v1/billing/me with your API base + token.</div>
  </div>
  <div class="row" style="padding-bottom:0"><strong>Full-history import</strong></div>
  <p class="hint">Brings in old bookmarks and likes below what is already saved. Start it on your X bookmarks or likes page — it scrolls slowly like you would, keeps its place, and pauses by itself if X asks to slow down.</p>
  <div class="impform">
    <button id="impStart">Start import</button>
    <button id="impPause">Pause</button>
    <a id="impOpen" href="https://x.com/i/bookmarks" target="_blank" rel="noopener">Open X bookmarks</a>
    <a id="impOpenLikes" href="https://x.com/" target="_blank" rel="noopener">Open X (your profile → Likes)</a>
  </div>
  <div id="impStatus" role="status">Not started yet. Your place is kept on this device.</div>
  <div class="impbarwrap"><div id="impBar"></div></div>
  <div id="impQueue" class="hint" style="padding-top:6px">Queue status loads here.</div>
  <div class="row" style="padding-bottom:0"><strong>Proposed actions</strong></div>
  <p class="hint">Risky steps wait here until you approve them. Nothing runs until you tap Approve.</p>
  <div class="apform">
    <input id="apTitle" placeholder="Propose an action, e.g. Resume paused sync" maxlength="120" autocomplete="off">
    <button id="apAdd">Propose</button>
  </div>
  <div id="apStatus" role="status">Loading…</div>
  <ul id="apList"></ul>
</section>
<section class="pane" id="pane-hooks" aria-label="Hooks">
  <div class="row" style="padding-bottom:0"><strong>Outbound webhooks</strong></div>
  <p class="hint">Get a POST on every new import. Saved on this device; registered with POST /v1/webhooks/bookmarks when an API base + token is set.</p>
  <div class="whform">
    <input id="whUrl" placeholder="https://…" inputmode="url" autocomplete="off">
    <button id="whAdd">Add</button>
  </div>
  <div id="whStatus" role="status">Loading…</div>
  <ul id="whList"></ul>
</section>
<section class="pane" id="pane-export" aria-label="Export">
  <button class="btn" id="dl">Download JSON</button>
  <p class="hint">Exports everything stored locally on this device.</p>
  <button class="btn" id="wipe">Erase everything (device + server)</button>
  <p class="hint">Wipes the local queue and all tweets on the server. Labels you created stay. Use for a clean re-capture, then Start import.</p>
</section>

<nav class="tabs" role="tablist" aria-label="BookmarkVault">
  <button role="tab" aria-selected="true" data-pane="pane-saved">Saved</button>
  <button role="tab" aria-selected="false" data-pane="pane-labels">Labels</button>
  <button role="tab" aria-selected="false" data-pane="pane-sync">Sync</button>
  <button role="tab" aria-selected="false" data-pane="pane-hooks">Hooks</button>
  <button role="tab" aria-selected="false" data-pane="pane-export">Export</button>
</nav>
<template id="t-item"><li><div class="txt collapsed"></div><button class="morebtn" data-act="more" hidden>Show all</button><div class="meta"><span class="ma"></span><span class="md"></span><a class="open" target="_blank" rel="noopener">Open</a></div><div class="meta m2"></div><div class="chips" hidden></div><div class="attach" hidden></div></li></template></div>`;
  var BV_SH = null, BV_MOUNTED = false, BV_OPEN = false;
  function bvShell() {
    if (BV_SH) return BV_SH;
    try {
      var host = document.createElement('div');
      host.id = 'bv-app-host';
      var sh = host.attachShadow({ mode: 'open' });
      var st = document.createElement('style');
      st.textContent = BV_CSS;
      sh.appendChild(st);
      var wrap = document.createElement('div');
      wrap.innerHTML = BV_HTML;
      var sheet0 = document.createElement('div');
      sheet0.id = 'bv-app';
      while (wrap.firstChild) sheet0.appendChild(wrap.firstChild);
      sheet0.style.display = 'none';
      sh.appendChild(sheet0);
      (document.body || document.documentElement).appendChild(host);
      /* nav has no Close cell: the pill toggles open/close */
      BV_SH = sh;
      return sh;
    } catch (e) { return null; }
  }
  window.BVAPP = window.BVAPP || {};
  window.BVAPP.open = function () {
    var sh = bvShell();
    if (!sh) { try { chrome.runtime.sendMessage({ type: 'bv-devnote', note: 'panel-open-noshell' }); } catch (e) {} return; }
    if (!BV_MOUNTED) { try { mountPanel(sh); BV_MOUNTED = true; } catch (e) { try { chrome.runtime.sendMessage({ type: 'bv-devnote', note: 'panel-mount-fail:' + String((e && e.message) || e).slice(0, 120) }); } catch (e2) {} } }
    try {
      var sheet = sh.getElementById('bv-app');
      if (sheet) sheet.style.display = 'flex';
      BV_OPEN = true;
    } catch (e) {}
    try { if (window.BVAPP.refresh) window.BVAPP.refresh(); } catch (e) {}
  };
  window.BVAPP.isOpen = function () { return BV_OPEN; };
  window.BVAPP.close = function () {
    try {
      var sh = BV_SH;
      var sheet = sh && sh.getElementById('bv-app');
      if (sheet) sheet.style.display = 'none';
      BV_OPEN = false;
    } catch (e) {}
  };
  try { chrome.runtime.sendMessage({ type: 'bv-devnote', note: 'panel-boot' }); } catch (e) {}


  function mountPanel(SH) {
    var fetch = bgFetch;

  'use strict';
  var QUEUE_KEY = 'bv.queue.v1';
  var LABELS_KEY = 'bv.labels.v1';
  var LABELDEFS_KEY = 'bv.labeldefs.v1';
  var WEBHOOKS_KEY = 'bv.webhooks.v1';
  var APPROVALS_KEY = 'bv.approvals.v1';
  var activeLabel = '';
  var activeType = ''; // '' | 'bookmarks' | 'likes' | 'both'
  var activeLoc = ''; // '' | 'device' | 'server'
  var verifyOn = false; // save-order verification overlay (Saved pane setting)

  var tabs = Array.prototype.slice.call(SH.querySelectorAll('nav.tabs button'));
  var panes = Array.prototype.slice.call(SH.querySelectorAll('.pane'));
  function showPane(id, pushHash) {
    tabs.forEach(function (x) { x.setAttribute('aria-selected', x.dataset.pane === id ? 'true' : 'false'); });
    panes.forEach(function (p) { p.classList.toggle('active', p.id === id); });
    // storage only in-page: never touch the page URL.
    // + storage: mobile panels reopen fresh on every icon tap (hash lost), storage survives.
    if (pushHash) { try { void 0(null, '', '#' + id.replace(/^pane-/, '')); } catch (e) {} }
    try { chrome.storage.local.set({ 'bv.pane': id }); } catch (e) {}
  }
  tabs.forEach(function (b) {
    b.addEventListener('click', function () { showPane(b.dataset.pane, false); });
  });
  try {
    chrome.storage.local.get('bv.pane').then(function (o) {
      if (o && o['bv.pane'] && SH.getElementById(o['bv.pane'])) showPane(o['bv.pane'], false);
    });
  } catch (e) {}

  function getQueue() {
    return chrome.storage.local.get(QUEUE_KEY).then(function (o) { return o[QUEUE_KEY] || []; });
  }
  function getLabelMap() {
    return chrome.storage.local.get(LABELS_KEY).then(function (o) { return o[LABELS_KEY] || {}; });
  }
  function getLabelDefs() {
    return chrome.storage.local.get(LABELDEFS_KEY).then(function (o) { return o[LABELDEFS_KEY] || []; });
  }
  function setLabelMap(m) { return chrome.storage.local.set({ [LABELS_KEY]: m }); }
  function setLabelDefs(d) { return chrome.storage.local.set({ [LABELDEFS_KEY]: d }); }
  function getWebhooks() {
    return chrome.storage.local.get(WEBHOOKS_KEY).then(function (o) { return o[WEBHOOKS_KEY] || []; });
  }
  function setWebhooks(w) { return chrome.storage.local.set({ [WEBHOOKS_KEY]: w }); }
  function getApprovals() {
    return chrome.storage.local.get(APPROVALS_KEY).then(function (o) { return o[APPROVALS_KEY] || []; });
  }
  function setApprovals(a) { return chrome.storage.local.set({ [APPROVALS_KEY]: a }); }
  var DEFAULT_BASE = 'http://vuos-hcar5000mi.tail6918b0.ts.net:8899';
  var OPS_BASE = 'http://vuos-hcar5000mi.tail6918b0.ts.net:8901'; // serves ext/manifest.json (update check)
  function getApi() {
    return chrome.storage.local.get(['bv.apiBase', 'bv.token']).then(function (o) {
      var base = (o['bv.apiBase'] || '').replace(/\/$/, '') || DEFAULT_BASE;
      var tok = o['bv.token'] || '';
      if (!tok) {
        // zero-config owner build: create a local random token once (stub accepts any)
        tok = 'local-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
        try { chrome.storage.local.set({ 'bv.token': tok, 'bv.apiBase': base }); } catch (e) {}
      }
      return { apiBase: base, token: tok };
    });
  }
  function esc(s) { return String(s || '').replace(/[&<>\"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmtBuild(iso) {
    // Stored UTC, shown in the viewer's own timezone (owner asked).
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso || '?');
      return d.toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) { return String(iso || '?'); }
  }
  function fmtDate(s) {
    if (!s) return '';
    var d = new Date(s);
    if (isNaN(d.getTime())) return String(s).slice(0, 16);
    try { return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }); }
    catch (e) { return d.toLocaleString(); }
  }
  // Relevance: newest-first sort key (created_at, then queued/imported, else 0).
  function tsOf(r) {
    var t = Date.parse(r.created_at || r.queued_at || r.imported_at || '');
    return isNaN(t) ? 0 : t;
  }
  function newestFirst(a, b) { return tsOf(b) - tsOf(a); }
  // Dupe signal: normalized text shared by 2+ ids (URLs stripped, case/space folded).
  function normText(r) {
    return String(r.text || '').toLowerCase().replace(/https?:\/\/\S+/g, '')
      .replace(/\s+/g, ' ').trim().slice(0, 160);
  }
  function dupeCounts(items) {
    var n = {};
    items.forEach(function (r) {
      var k = normText(r);
      if (k.length >= 20) n[k] = (n[k] || 0) + 1;
    });
    return n;
  }
  function pagesOf(r) {
    if (r && Array.isArray(r.pages) && r.pages.length) return r.pages;
    return [(r && r.page) || 'bookmarks'];
  }
  function typeMatch(r) {
    if (!activeType) return true;
    var st = statusOf(r);
    if (activeType === 'both') return st === 'both';
    if (activeType === 'likes') return st === 'liked' || st === 'both';
    if (activeType === 'bookmarks') return st === 'saved' || st === 'both';
    return pagesOf(r).indexOf(activeType) >= 0;
  }
  // Owner's two levels: liked (good to know) vs both liked+saved (important).
  // Quoted/thread context never counts as saved; DOM 'seen' records resolve
  // through observed button states, else stay 'seen'.
  function statusOf(r) {
    if (r && r.context === 'quoted') return 'quoted';
    var p = pagesOf(r);
    var liked = (r && r.liked === true) || (r && r.liked !== false && p.indexOf('likes') >= 0);
    var saved = (r && r.saved === true) || (r && r.saved !== false && p.indexOf('bookmarks') >= 0);
    if (liked && saved) return 'both';
    if (liked) return 'liked';
    if (saved) return 'saved';
    return 'seen';
  }
  var ST_LABEL = { both: 'liked + bookmarked', liked: 'liked', saved: 'bookmarked', seen: 'seen', quoted: 'quoted' };
  // DOM builders (no HTML strings): structure lives in panel.html <template>,
  // text goes through textContent (auto-escaped).
  function mk(tag, cls, text) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text != null) el.textContent = text;
    return el;
  }
  function cloneTpl(id) {
    var t = SH.getElementById(id);
    var n = t && t.content && t.content.firstElementChild;
    return n ? n.cloneNode(true) : null;
  }
  function statusEl(r) {
    var st = statusOf(r);
    return mk('span', 'st st-' + st, ST_LABEL[st]);
  }
  function pageBadges(r) {
    return pagesOf(r).map(function (p) {
      return '<span class="pg pg-' + esc(p) + '">' + esc(p) + '</span>';
    }).join('');
  }
  function labelsOf(r, map) {
    var fromRec = Array.isArray(r.labels) ? r.labels : [];
    var fromMap = map[r.id] || [];
    var seen = {};
    return fromRec.concat(fromMap).filter(function (l) {
      if (!l || seen[l]) return false;
      seen[l] = true;
      return true;
    });
  }

  // --- server mirror (best-effort; local always wins on failure) ---
  function serverLabels() {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return null;
      return fetch(a.apiBase + '/v1/labels', {
        headers: { Authorization: 'Bearer ' + a.token }
      }).then(function (res) {
        if (!res.ok) throw new Error('http-' + res.status);
        return res.json();
      }).then(function (p) {
        return (p.labels || []).map(function (l) { return l.name; }).filter(Boolean);
      }).catch(function () { return null; });
    });
  }
  function serverCreate(name) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return false;
      return fetch(a.apiBase + '/v1/labels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.token },
        body: JSON.stringify({ name: name })
      }).then(function (res) { return res.ok; }).catch(function () { return false; });
    });
  }
  function serverAttach(id, label) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return false;
      return fetch(a.apiBase + '/v1/bookmarks/' + encodeURIComponent(id) + '/labels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.token },
        body: JSON.stringify({ label: label })
      }).then(function (res) { return res.ok; }).catch(function () { return false; });
    });
  }
  function serverDetach(id, label) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return false;
      return fetch(a.apiBase + '/v1/bookmarks/' + encodeURIComponent(id) + '/labels', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.token },
        body: JSON.stringify({ label: label })
      }).then(function (res) { return res.ok; }).catch(function () { return false; });
    });
  }

  // --- server search (GET /v1/bookmarks?q=&label=); null = no creds, 'error' = offline ---
  function serverSearch(qstr, label) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return null;
      var url = a.apiBase + '/v1/bookmarks?q=' + encodeURIComponent(qstr || '') +
        '&label=' + encodeURIComponent(label || '') +
        '&page=' + encodeURIComponent(activeType || '');
      return fetch(url, { headers: { Authorization: 'Bearer ' + a.token } })
        .then(function (res) {
          if (!res.ok) throw new Error('http-' + res.status);
          return res.json();
        })
        .then(function (p) {
          return { tweets: p.tweets || [], total: (p.total != null ? p.total : (p.tweets || []).length) };
        })
        .catch(function () { return 'error'; });
    });
  }
  function render(q, map, qstr, serverData) {
    var list = SH.getElementById('list');
    qstr = (qstr || '').toLowerCase();
    var items, mode, all, syncedIds = {}, pendingCount = 0;
    function locMatch(r) {
      if (!activeLoc) return true;
      var onServer = (mode === 'server') && !!syncedIds[r.id];
      return activeLoc === 'server' ? onServer : !onServer;
    }
    if (serverData && Array.isArray(serverData.tweets)) {
      // Online: server already applied q + label + type filter. Merge local-only ids not yet synced.
      var seen = {};
      serverData.tweets.forEach(function (r) { seen[r.id] = true; syncedIds[r.id] = true; });
      var localOnly = q.filter(function (r) {
        if (seen[r.id]) return false;
        if (!locMatch(r)) return false;
        if (!typeMatch(r)) return false;
        if (activeLabel && labelsOf(r, map).indexOf(activeLabel) < 0) return false;
        if (!qstr) return true;
        return ((r.text || '') + ' ' + (r.author || '')).toLowerCase().indexOf(qstr) >= 0;
      });
      pendingCount = localOnly.length;
      all = serverData.tweets.filter(function (r) { return typeMatch(r) && locMatch(r); })
        .concat(localOnly).sort(newestFirst);
      items = all.slice(0, 100);
      mode = 'server';
    } else {
      all = q.filter(function (r) {
        if (!locMatch(r)) return false;
        if (!typeMatch(r)) return false;
        if (activeLabel && labelsOf(r, map).indexOf(activeLabel) < 0) return false;
        if (!qstr) return true;
        return ((r.text || '') + ' ' + (r.author || '')).toLowerCase().indexOf(qstr) >= 0;
      }).sort(newestFirst);
      pendingCount = all.length;
      items = all.slice(0, 100);
      mode = (serverData === 'error') ? 'offline' : 'local';
    }
    function syncEl(r) {
      if (mode !== 'server') return mk('span', 'syncpend', 'this device');
      return syncedIds[r.id] ? mk('span', 'syncok', 'on server') : mk('span', 'syncpend', 'upload pending');
    }
    var nLiked = 0, nSaved = 0, nBoth = 0, nQuoted = 0, nSeen = 0;
    all.forEach(function (r) {
      var st = statusOf(r);
      if (st === 'liked') nLiked++;
      else if (st === 'saved') nSaved++;
      else if (st === 'both') nBoth++;
      else if (st === 'quoted') nQuoted++;
      else nSeen++;
    });
    var typeLine = nBoth + ' liked+bookmarked · ' + nLiked + ' liked · ' + nSaved + ' bookmarked' +
      (nQuoted ? ' · ' + nQuoted + ' quoted' : '') + (nSeen ? ' · ' + nSeen + ' seen' : '');
    // Save-order rank from X sortIndex (larger = more recent bookmark; X sends
    // no bookmark creation date, so this ordering is the sync check).
    function ordVal(r) { return String((r && r.saveOrder) || ''); }
    var ranked = all.filter(function (r) { return ordVal(r); }).sort(function (a, b) {
      var x = ordVal(a), y = ordVal(b);
      if (x.length !== y.length) return y.length - x.length;
      return x < y ? 1 : (x > y ? -1 : 0);
    });
    var saveRank = {};
    ranked.forEach(function (r, i) { if (!saveRank[r.id]) saveRank[r.id] = i + 1; });
    var newestSaved = ranked[0] || null, oldestSaved = ranked[ranked.length - 1] || null;

    return getLabelDefs().then(function (defs) {
      var dupes = dupeCounts(items);
      var dupeShown = 0;
      function buildItem(r) {
        var li = cloneTpl('t-item');
        var dk = normText(r);
        var isDupe = dk.length >= 20 && dupes[dk] > 1;
        if (isDupe) dupeShown++;
        li.dataset.tid = r.id;
        li.querySelector('.txt').textContent = String(r.text || '');
        var more = li.querySelector('.morebtn');
        if (String(r.text || '').length > 220) { more.hidden = false; more.dataset.id = r.id; }
        else { more.remove(); }
        var metas = li.querySelectorAll('.meta');
        metas[0].querySelector('.ma').textContent = '@' + (r.author || '?');
        metas[0].querySelector('.md').textContent = fmtDate(r.created_at);
        metas[0].querySelector('.open').href = 'https://x.com/i/status/' + encodeURIComponent(r.id);
        if (isDupe) {
          var db = mk('span', 'dupe', 'Possible duplicate \u00d7' + dupes[dk]);
          db.title = 'Same text saved ' + dupes[dk] + ' times';
          metas[0].appendChild(db);
        }
        var m2 = metas[1];
        m2.appendChild(statusEl(r));
        var kind = (r && r.kind && r.kind !== 'tweet') ? r.kind : '';
        if (kind) m2.appendChild(mk('span', 'kind', kind));
        if (verifyOn && saveRank[r.id]) m2.appendChild(mk('span', 'ord', 'saved #' + saveRank[r.id]));
        m2.appendChild(syncEl(r));
        var labs = labelsOf(r, map);
        var chipsBox = li.querySelector('.chips');
        if (labs.length) {
          chipsBox.hidden = false;
          labs.forEach(function (l) {
            var chip = mk('span', 'chip', l);
            var x = mk('button', null, '\u00d7');
            x.dataset.act = 'detach'; x.dataset.id = r.id; x.dataset.label = l;
            x.title = 'Remove label'; x.setAttribute('aria-label', 'Remove ' + l);
            chip.appendChild(x);
            chipsBox.appendChild(chip);
          });
        } else { chipsBox.remove(); }
        var box = li.querySelector('.attach');
        var opts = defs.filter(function (d) { return labs.indexOf(d) < 0; });
        if (defs.length && opts.length) {
          box.hidden = false;
          var sel = document.createElement('select');
          sel.dataset.attachFor = r.id;
          sel.setAttribute('aria-label', 'Attach label');
          opts.forEach(function (d) {
            var o = document.createElement('option');
            o.value = d; o.textContent = d;
            sel.appendChild(o);
          });
          var add = mk('button', null, 'Add');
          add.dataset.act = 'attach'; add.dataset.id = r.id;
          box.appendChild(sel); box.appendChild(add);
        } else { box.remove(); }
        return li;
      }
      list.textContent = '';
      if (items.length) {
        items.forEach(function (r) { list.appendChild(buildItem(r)); });
      } else {
        var empty = mk('li', null, (qstr || activeLabel)
          ? 'No matches for this search. '
          : 'No saved bookmarks yet. Browse your X bookmarks and they appear here.');
        if (qstr || activeLabel) {
          var cb = mk('button', null, 'Clear search');
          cb.dataset.act = 'clear';
          empty.appendChild(cb);
        }
        list.appendChild(empty);
      }
      var st = SH.getElementById('status');
      var orderNote = items.length > 1 ? ' · newest first' : '';
      var dupeNote = dupeShown ? ' · ' + dupeShown + ' possible duplicate' + (dupeShown > 1 ? 's' : '') : '';
      var filterNote = (activeType ? ' · showing ' + activeType : '') +
        (activeLoc ? ' · ' + (activeLoc === 'server' ? 'on server' : 'this device') : '') +
        (activeLabel ? ' · label: ' + activeLabel : '') +
        (qstr ? ' · "' + qstr + '"' : '');
      if (mode === 'server') {
        st.textContent = serverData.total + ' on server · ' + pendingCount + ' upload pending' +
          ' · ' + items.length + ' shown (' + typeLine + ')' + filterNote + orderNote + dupeNote;
      } else if (mode === 'offline') {
        st.textContent = q.length + ' on this device (server unreachable, will retry)' +
          ' · ' + items.length + ' shown (' + typeLine + ')' + filterNote + orderNote + dupeNote;
      } else {
        st.textContent = q.length + ' on this device only (no sync yet — tap Sync now)' +
          ' · ' + items.length + ' shown (' + typeLine + ')' + filterNote + orderNote + dupeNote;
      }
      var vl = SH.getElementById('verifyLine');
      if (vl) {
        if (verifyOn && newestSaved) {
          vl.style.display = '';
          vl.textContent = 'Newest saved: @' + (newestSaved.author || '?') +
            ' (saved #1) · Oldest: @' + ((oldestSaved && oldestSaved.author) || '?') +
            ' (saved #' + ranked.length + '). Compare with X order, newest first.';
        } else { vl.style.display = 'none'; vl.textContent = ''; }
      }
    });
  }

  // --- outbound webhooks (local-first; POST /v1/webhooks/bookmarks + GET list) ---
  function serverWebhookList() {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return null;
      return fetch(a.apiBase + '/v1/webhooks/bookmarks', {
        headers: { Authorization: 'Bearer ' + a.token }
      }).then(function (res) {
        if (!res.ok) throw new Error('http-' + res.status);
        return res.json();
      }).then(function (p) {
        return (p.webhooks || []).map(function (w) {
          return typeof w === 'string' ? w : w.url;
        }).filter(Boolean);
      }).catch(function () { return 'error'; });
    });
  }
  function serverWebhookAdd(url) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return false;
      return fetch(a.apiBase + '/v1/webhooks/bookmarks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.token },
        body: JSON.stringify({ url: url })
      }).then(function (res) { return res.ok; }).catch(function () { return false; });
    });
  }
  function validWebhookUrl(s) {
    s = String(s || '').trim();
    return (/^https:\/\/\S+/.test(s) || /^http:\/\/localhost(:\d+)?\/\S*/.test(s) ||
      /^http:\/\/127\.0\.0\.1(:\d+)?\/\S*/.test(s)) && s.length <= 500;
  }
  function renderWebhooksPane(local, serverState) {
    var ul = SH.getElementById('whList');
    var status = SH.getElementById('whStatus');
    if (!ul || !status) return;
    var seen = {};
    var urls = (local || []).map(function (w) { return typeof w === 'string' ? w : w.url; })
      .filter(Boolean).filter(function (u) {
        if (seen[u]) return false;
        seen[u] = true;
        return true;
      });
    ul.textContent = '';
    if (urls.length) urls.forEach(function (u) { ul.appendChild(mk('li', null, u)); });
    else ul.appendChild(mk('li', null, 'No webhook URLs yet. Add one above.'));
    if (serverState === null) {
      status.textContent = urls.length
        ? urls.length + ' URL(s), saved on this device only (no API base + token in Sync tab).'
        : 'Local-only (no API base + token in Sync tab).';
    } else if (serverState === 'ok') {
      status.textContent = urls.length
        ? urls.length + ' URL(s), registered with server.'
        : 'No webhook URLs yet. Add one above.';
    } else {
      status.textContent = urls.length
        ? urls.length + ' URL(s), saved locally (server unreachable, will retry).'
        : 'Server unreachable. URLs you add stay on this device and retry later.';
    }
  }
  function refreshWebhooks() {
    return getWebhooks().then(function (local) {
      return serverWebhookList().then(function (names) {
        if (Array.isArray(names)) {
          var seen = {};
          var merged = local.slice();
          merged.forEach(function (w) { seen[typeof w === 'string' ? w : w.url] = true; });
          var changed = false;
          names.forEach(function (u) {
            if (!seen[u]) { merged.push({ url: u, created_at: '' }); changed = true; }
          });
          if (changed) setWebhooks(merged);
          renderWebhooksPane(changed ? merged : local, 'ok');
        } else {
          renderWebhooksPane(local, names === null ? null : 'error');
        }
      });
    });
  }
  function renderLabelsPane(defs, map, serverState) {
    var ul = SH.getElementById('labList');
    var status = SH.getElementById('labStatus');
    var counts = {};
    Object.keys(map).forEach(function (id) {
      (map[id] || []).forEach(function (l) { counts[l] = (counts[l] || 0) + 1; });
    });
    ul.textContent = '';
    if (!defs.length) { ul.appendChild(mk('li', null, 'No labels yet. Create one above.')); }
    defs.forEach(function (d) {
      var c = counts[d] || 0;
      var li = mk('li');
      li.appendChild(mk('span', 'nm', d));
      li.appendChild(mk('span', 'ct', c + ' saved' + (activeLabel === d ? ' · showing' : '')));
      var b = mk('button', null, activeLabel === d ? 'Clear' : 'Show');
      b.dataset.act = 'filter'; b.dataset.label = d;
      li.appendChild(b);
      ul.appendChild(li);
    });
    status.textContent = serverState === null
      ? 'Local-only (no API base + token in Sync tab).'
      : serverState === 'ok'
        ? defs.length + ' label(s), synced with server.'
        : defs.length + ' label(s), saved locally (server unreachable, will retry).';
    // filter dropdown in Saved pane
    var sel = SH.getElementById('labelFilter');
    var cur = activeLabel;
    sel.options.length = 0;
    sel.appendChild(new Option('All labels', ''));
    defs.forEach(function (d) {
      var o = new Option(d, d);
      if (d === cur) o.selected = true;
      sel.appendChild(o);
    });
  }

  // --- approvals: propose -> approve/reject (local-first; server mirror) ---
  // Risky steps (e.g. resuming a paused sync) wait as pending until the
  // user taps Approve. Nothing runs on propose; decide only flips status.
  function serverApprovalList() {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return null;
      return fetch(a.apiBase + '/v1/approvals', {
        headers: { Authorization: 'Bearer ' + a.token }
      }).then(function (res) {
        if (!res.ok) throw new Error('http-' + res.status);
        return res.json();
      }).then(function (p) {
        return (p.approvals || []).filter(Boolean);
      }).catch(function () { return 'error'; });
    });
  }
  function serverPropose(title) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return false;
      return fetch(a.apiBase + '/v1/approvals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.token },
        body: JSON.stringify({ kind: 'general', title: title })
      }).then(function (res) { return res.ok; }).catch(function () { return false; });
    });
  }
  function serverDecide(id, verdict) {
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) return false;
      return fetch(a.apiBase + '/v1/approvals/' + encodeURIComponent(id) + '/' + verdict, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.token },
        body: JSON.stringify({})
      }).then(function (res) { return res.ok; }).catch(function () { return false; });
    });
  }
  function renderApprovalsPane(local, serverState) {
    var ul = SH.getElementById('apList');
    var status = SH.getElementById('apStatus');
    if (!ul || !status) return;
    var items = (local || []).slice(-50).reverse();
    ul.textContent = '';
    if (items.length) items.forEach(function (p) {
      var st = p.status || 'pending';
      var li = mk('li');
      li.appendChild(mk('span', 't', p.title || '(untitled)'));
      li.appendChild(mk('span', 'st', st));
      if (st === 'pending') {
        var row = mk('div', 'row2');
        var ok = mk('button', null, 'Approve');
        ok.dataset.act = 'ap-approve'; ok.dataset.id = p.id;
        var no = mk('button', null, 'Reject');
        no.dataset.act = 'ap-reject'; no.dataset.id = p.id;
        row.appendChild(ok); row.appendChild(no);
        li.appendChild(row);
      }
      ul.appendChild(li);
    });
    else ul.appendChild(mk('li', null, 'No proposed actions. Propose one above to try the flow.'));
    var pending = (local || []).filter(function (p) { return (p.status || 'pending') === 'pending'; }).length;
    if (serverState === null) {
      status.textContent = pending
        ? pending + ' waiting, saved on this device only (no API base + token in Sync tab).'
        : 'Local-only (no API base + token in Sync tab).';
    } else if (serverState === 'ok') {
      status.textContent = pending
        ? pending + ' waiting your decision, synced with server.'
        : 'Nothing waiting. Propose an action to try the flow.';
    } else {
      status.textContent = pending
        ? pending + ' waiting, saved locally (server unreachable, will retry).'
        : 'Server unreachable. Proposals you add stay on this device and retry later.';
    }
  }
  function refreshApprovals() {
    return getApprovals().then(function (local) {
      return serverApprovalList().then(function (names) {
        if (Array.isArray(names)) {
          var seen = {};
          local.forEach(function (p) { seen[String(p.id)] = true; });
          var merged = local.slice();
          var changed = false;
          names.forEach(function (s) {
            if (!seen[String(s.id)]) { merged.push(s); changed = true; }
          });
          if (changed) setApprovals(merged);
          renderApprovalsPane(changed ? merged : local, 'ok');
        } else {
          renderApprovalsPane(local, names === null ? null : 'error');
        }
      });
    });
  }

  SH.getElementById('whAdd').addEventListener('click', function () {
    var inp = SH.getElementById('whUrl');
    var url = String(inp.value || '').trim();
    if (!validWebhookUrl(url)) {
      var st0 = SH.getElementById('whStatus');
      if (st0) st0.textContent = 'Enter an https:// URL (http://localhost allowed for testing).';
      inp.focus();
      return;
    }
    getWebhooks().then(function (local) {
      var urls = local.map(function (w) { return typeof w === 'string' ? w : w.url; });
      if (urls.indexOf(url) < 0) {
        local.push({ url: url, created_at: new Date().toISOString() });
        return setWebhooks(local);
      }
      return local;
    }).then(function () {
      inp.value = '';
      inp.focus();
      return serverWebhookAdd(url).then(refreshWebhooks);
    });
  });
  function refresh() {
    var qstr = SH.getElementById('search').value;
    return Promise.all([getQueue(), getLabelMap(), getLabelDefs(), serverSearch(qstr, activeLabel)]).then(function (parts) {
      var q = parts[0], map = parts[1], defs = parts[2], serverData = parts[3];
      return render(q, map, qstr, serverData).then(function () {
        chrome.runtime.sendMessage({ type: 'bv-stats' }, function (s) {
          var h = SH.getElementById('health');
          if (!h) return;
          if (!s) { h.textContent = ''; return; }
          // HTTP preview has no background worker: fall back to the local queue count.
          if (typeof s.queued !== 'number') { h.textContent = 'Queue ' + q.length + ' · never synced'; return; }
          var m = s.meta || {}, st = s.status || {};
          var live = st.watching ? 'watching X now' : 'open x.com bookmarks or your profile likes to capture';
          var sess = st.sessionAdded ? ' · +' + st.sessionAdded + ' this session' : '';
          var last = st.lastCaptureAt ? ' · last ' + st.lastCaptureAt.slice(11, 16) : '';
          h.textContent = live + sess + last + ' · Queue ' + s.queued +
            (m.lastSync ? ' · last sync ' + m.lastSync : ' · never synced') +
            (typeof m.lastScore === 'number' ? ' · risk ' + m.lastScore : '') +
            (m.lastReasons && m.lastReasons.length ? ' (' + m.lastReasons.join('; ') + ')' : '');
        });
      }).then(refreshWebhooks).then(function () {
        return serverLabels().then(function (names) {
          if (names) {
            var merged = defs.slice();
            names.forEach(function (n) { if (merged.indexOf(n) < 0) merged.push(n); });
            merged.sort();
            if (merged.join() !== defs.join()) {
              defs = merged;
              setLabelDefs(defs);
            }
            renderLabelsPane(defs, map, 'ok');
          } else {
            renderLabelsPane(defs, map, null);
          }
        });
      }).then(refreshApprovals);
    });
  }

  function cleanName(s) { return String(s || '').trim().replace(/\s+/g, ' ').slice(0, 40); }

  SH.getElementById('labCreate').addEventListener('click', function () {
    var inp = SH.getElementById('labName');
    var name = cleanName(inp.value);
    if (!name) { inp.focus(); return; }
    getLabelDefs().then(function (defs) {
      if (defs.indexOf(name) < 0) {
        defs.push(name);
        defs.sort();
        return setLabelDefs(defs).then(function () { return defs; });
      }
      return defs;
    }).then(function () {
      inp.value = '';
      inp.focus();
      return serverCreate(name).then(refresh);
    });
  });

  SH.getElementById('apAdd').addEventListener('click', function () {
    var inp = SH.getElementById('apTitle');
    var title = String(inp.value || '').trim().replace(/\s+/g, ' ').slice(0, 120);
    if (!title) { inp.focus(); return; }
    var item = { id: 'local-' + Date.now(), kind: 'general', title: title,
                 status: 'pending', created_at: new Date().toISOString() };
    getApprovals().then(function (local) {
      local.push(item);
      return setApprovals(local.slice(-200));
    }).then(function () {
      inp.value = '';
      inp.focus();
      return serverPropose(title).then(refreshApprovals);
    });
  });

  SH.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t || !t.dataset || !t.dataset.act) return;
    var id = t.dataset.id, label = t.dataset.label;
    if (t.dataset.act === 'clear') {
      activeLabel = '';
      activeType = '';
      activeLoc = '';
      var si = SH.getElementById('search');
      if (si) si.value = '';
      var lf = SH.getElementById('labelFilter');
      if (lf) lf.value = '';
      var tf = SH.getElementById('typeFilter');
      if (tf) tf.value = '';
      var lf2 = SH.getElementById('locFilter');
      if (lf2) lf2.value = '';
      refresh();
    } else if (t.dataset.act === 'detach') {
      getLabelMap().then(function (map) {
        map[id] = (map[id] || []).filter(function (l) { return l !== label; });
        if (!map[id].length) delete map[id];
        return setLabelMap(map);
      }).then(function () { return serverDetach(id, label); }).then(refresh);
    } else if (t.dataset.act === 'attach') {
      var sel = SH.querySelector('select[data-attach-for="' + CSS.escape(id) + '"]');
      var name = sel ? cleanName(sel.value) : '';
      if (!name) return;
      Promise.all([getLabelMap(), getLabelDefs()]).then(function (parts) {
        var map = parts[0], defs = parts[1];
        if (defs.indexOf(name) < 0) { defs.push(name); defs.sort(); }
        var cur = map[id] || [];
        if (cur.indexOf(name) < 0) cur.push(name);
        map[id] = cur;
        return Promise.all([setLabelMap(map), setLabelDefs(defs)]);
      }).then(function () { return serverAttach(id, name); }).then(refresh);
    } else if (t.dataset.act === 'ap-approve' || t.dataset.act === 'ap-reject') {
      var verdict = t.dataset.act === 'ap-approve' ? 'approve' : 'reject';
      var decided = verdict === 'approve' ? 'approved' : 'rejected';
      getApprovals().then(function (local) {
        var hit = null;
        local.forEach(function (p) {
          if (String(p.id) === String(id) && (p.status || 'pending') === 'pending') {
            p.status = decided;
            p.decided_at = new Date().toISOString();
            hit = p;
          }
        });
        return setApprovals(local).then(function () { return hit; });
      }).then(function (hit) {
        // Server mirror only for server-issued numeric ids; local-only stays local.
        if (hit && typeof hit.id === 'number') return serverDecide(hit.id, verdict);
        return false;
      }).then(refreshApprovals);
    } else if (t.dataset.act === 'more') {
      var box = SH.querySelector('li[data-tid="' + CSS.escape(id) + '"] .txt');
      if (box) {
        var open = box.classList.toggle('expanded');
        box.classList.toggle('collapsed', !open);
        t.textContent = open ? 'Show less' : 'Show all';
      }
    } else if (t.dataset.act === 'filter') {
      activeLabel = (activeLabel === label) ? '' : label;
      // jump to Saved pane so the result is visible (no scroll steal: tab switch only)
      showPane('pane-saved', false);
      refresh();
    }
  });

  SH.getElementById('clearSearch').addEventListener('click', function () {
    activeLabel = '';
    activeType = '';
    activeLoc = '';
    SH.getElementById('search').value = '';
    SH.getElementById('labelFilter').value = '';
    SH.getElementById('typeFilter').value = '';
    SH.getElementById('locFilter').value = '';
    refresh(); // user-initiated: no scroll steal, list re-renders in place
  });
  SH.getElementById('typeFilter').addEventListener('change', function (ev) {
    activeType = ev.target.value || '';
    refresh();
  });
  SH.getElementById('locFilter').addEventListener('change', function (ev) {
    activeLoc = ev.target.value || '';
    refresh();
  });
  try {
    chrome.storage.local.get('bv.verifyOrder').then(function (o) {
      verifyOn = !!(o && o['bv.verifyOrder']);
      var cb = SH.getElementById('verifyOrder');
      if (cb) cb.checked = verifyOn;
    });
  } catch (e) {}
  SH.getElementById('verifyOrder').addEventListener('change', function (ev) {
    verifyOn = !!ev.target.checked;
    try { chrome.storage.local.set({ 'bv.verifyOrder': verifyOn }); } catch (e) {}
    refresh();
  });
  SH.getElementById('labelFilter').addEventListener('change', function (ev) {
    activeLabel = ev.target.value || '';
    refresh();
  });

  var searchTimer = null;
  SH.getElementById('search').addEventListener('input', function () {
    // Debounced so each keystroke does not hammer GET /v1/bookmarks; no scroll steal.
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(refresh, 250);
  });
  chrome.storage.onChanged.addListener(function (chg) {
    if (chg['bv.verifyOrder']) { verifyOn = !!(chg['bv.verifyOrder'].newValue); refresh(); return; }
    if (chg[QUEUE_KEY] || chg[LABELS_KEY] || chg[LABELDEFS_KEY] || chg[WEBHOOKS_KEY] || chg[APPROVALS_KEY]) refresh();
    if (chg[IMPORT_KEY]) renderImport(chg[IMPORT_KEY].newValue); // progress never moves scroll
  });

  // --- Full-history import: user-started, checkpoint/resume, pause on challenge ---
  var IMPORT_KEY = 'bv.import.v1';
  function getImport() {
    return chrome.storage.local.get(IMPORT_KEY).then(function (o) { return o[IMPORT_KEY] || null; });
  }
  function setImport(patch) {
    return getImport().then(function (cur) {
      var nxt = Object.assign({}, cur || {}, patch, { updated_at: new Date().toISOString() });
      var obj = {}; obj[IMPORT_KEY] = nxt;
      return chrome.storage.local.set(obj).then(function () { renderImport(nxt); return nxt; });
    });
  }
  function fmtClock(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    try { return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }); }
    catch (e) { return d.toLocaleString(); }
  }
  function renderImport(st) {
    var el = SH.getElementById('impStatus');
    var bs = SH.getElementById('impStart');
    if (!el) return;
    if (!st || (!st.wish && !st.state)) {
      el.textContent = 'Not started yet. Your place is kept on this device.';
      if (bs) bs.textContent = 'Start import';
      return;
    }
    var done = st.state === 'done';
    var chal = st.state === 'challenge';
    var running = st.wish === 'run' && !done && !chal;
    var n = st.scrolls || 0, c = st.captured || 0;
    var base = done ? 'Finished. ' : chal ? 'Paused — ' + (st.reason || 'X asked us to slow down') + '. ' :
      running ? 'Importing slowly… ' : 'Paused. Your place is kept. ';
    var prog = n + ' scrolled · ' + c + ' saved here';
    var when = st.updated_at ? ' · ' + fmtClock(st.updated_at) : '';
    var tip = chal ? ' Tap Start import to try again.' :
      done ? ' Tap Start import to run it again.' :
      running ? ' Keep this tab open. You can Pause anytime.' : ' Tap Start import to pick up where you left off.';
    el.textContent = base + prog + when + '.' + tip;
    if (bs) bs.textContent = done ? 'Run again' : (running ? 'Running…' : (n ? 'Resume import' : 'Start import'));
  }
  function refreshImport() {
    return Promise.all([getImport(), getQueue()]).then(function (parts) {
      renderImport(parts[0]);
      var bar = SH.getElementById('impBar');
      if (bar) {
        var sc = (parts[0] && parts[0].scrolls) || 0;
        bar.style.width = Math.min(100, Math.round(sc / 15)) + '%'; // 1500 max scrolls
      }
      var qb = SH.getElementById('impQueue');
      if (qb) {
        var b = 0, l = 0, bo = 0;
        parts[1].forEach(function (r) {
          var st = statusOf(r);
          if (st === 'both') bo++;
          else if (st === 'liked') l++;
          else if (st === 'saved') b++;
        });
        qb.textContent = parts[1].length
          ? 'Waiting on this device: ' + bo + ' liked+bookmarked · ' + l + ' liked · ' + b + ' bookmarked.'
          : 'Queue empty — everything captured is on the server (or nothing captured yet).';
      }
    });
  }
  var __impStart = SH.getElementById('impStart');
  if (__impStart) __impStart.addEventListener('click', function () {
    getImport().then(function (cur) {
      var fresh = (!cur || cur.state === 'done')
        ? { wish: 'run', state: 'running', scrolls: 0, captured: 0, checkpointY: 0, checkpointId: '', reason: '', cooldownUntil: 0 }
        : { wish: 'run', state: 'running', reason: '', cooldownUntil: 0 };
      return setImport(fresh);
    });
  });
  var __impPause = SH.getElementById('impPause');
  if (__impPause) __impPause.addEventListener('click', function () {
    setImport({ wish: 'pause', state: 'paused' });
  });

  function planLine(p) {
    if (!p) return 'Plan: unknown (offline or no token). Staying local-only.';
    var d = p.plan_detail || {};
    var label = d.label || p.plan || 'Free';
    var extra = p.mode === 'test' ? ' · test mode' : '';
    var upd = p.updated_at ? ' · updated ' + p.updated_at : '';
    return 'Plan: ' + label + extra + upd;
  }

  function fetchPlan() {
    var el = SH.getElementById('plan');
    return getApi().then(function (a) {
      if (!a.apiBase || !a.token) {
        el.textContent = 'Plan: Free (local-only, no account connected).';
        return null;
      }
      el.textContent = 'Plan: checking…';
      return fetch(a.apiBase + '/v1/billing/me', {
        headers: { Authorization: 'Bearer ' + a.token }
      }).then(function (res) {
        if (!res.ok) throw new Error('http-' + res.status);
        return res.json();
      }).then(function (p) {
        try { chrome.storage.local.set({ 'bv.plan': p.plan || 'free' }); } catch (e) {}
        el.textContent = planLine(p);
        return p;
      }).catch(function () {
        el.textContent = 'Plan: unknown (could not reach billing). Staying local-only.';
        return null;
      });
    });
  }

  SH.getElementById('save').addEventListener('click', function () {
    var apiBase = SH.getElementById('apiBase').value.trim();
    var token = SH.getElementById('token').value.trim();
    chrome.storage.local.set({ 'bv.apiBase': apiBase, 'bv.token': token }).then(function () {
      SH.getElementById('status').textContent = apiBase && token ? 'Settings saved.' : 'Cleared — staying local-only.';
      fetchPlan();
      refresh();
    });
  });
  SH.getElementById('planBtn').addEventListener('click', fetchPlan);
  chrome.storage.local.get('bv.devMode').then(function (o) {
    SH.getElementById('devMode').checked = !!o['bv.devMode'];
  });
  SH.getElementById('devMode').addEventListener('change', function (e) {
    chrome.runtime.sendMessage({ type: 'bv-devmode', on: e.target.checked }, function () {
      SH.getElementById('tuneHint').textContent = e.target.checked
        ? 'Dev mode ON: tuning loads from server. Tap Refresh tuning, then scroll.'
        : 'Off = store build (frozen).';
    });
  });
  SH.getElementById('tuneBtn').addEventListener('click', function () {
    SH.getElementById('tuneHint').textContent = 'Fetching…';
    chrome.runtime.sendMessage({ type: 'bv-tuning-refresh' }, function (r) {
      SH.getElementById('tuneHint').textContent = r && r.ok
        ? 'Tuning v' + r.v + ' applied. Scroll to feel it.'
        : 'Server unreachable — frozen tuning stays.';
    });
  });
  function installedVer() {
    try { return 'v' + chrome.runtime.getManifest().version; }
    catch (e) { return 'preview'; }
  }
  function checkVersions() {
    var box = SH.getElementById('buildBox');
    var inst = installedVer();
    box.textContent = 'This extension: ' + inst + ' · checking published…';
    getApi().then(function (a) {
      var ops = (a.apiBase || DEFAULT_BASE).replace(/:8899\/?$/, ':8901');
      if (!/:8901/.test(ops)) ops = OPS_BASE;
      var lane = SH.getElementById('devMode').checked
        ? 'Logic lane: REMOTE (auto-updates ON)'
        : 'Logic lane: FROZEN bundled copy (turn on Developer mode)';
      return Promise.all([
        Promise.all([
          fetch(ops.replace(/\/$/, '') + '/ext/manifest.json').then(function (r) {
            if (!r.ok) throw new Error('http-' + r.status);
            return r.json();
          }).then(function (m) { return 'v' + (m.version || '?'); }).catch(function () { return null; }),
          fetch(ops.replace(/\/$/, '') + '/ext/build.json').then(function (r) {
            return r.json();
          }).then(function (b) { return b.built_at || null; }).catch(function () { return null; })
        ]).then(function (parts) { return { ver: parts[0], built: parts[1] }; }),
        chrome.storage.local.get('bv.tuning').then(function (o) {
          var t = o && o['bv.tuning'];
          return lane + (t && t.v ? ', tuning v' + t.v : '');
        }),
        fetch((a.apiBase || DEFAULT_BASE).replace(/\/$/, '') + '/health').then(function (r) {
          return r.json();
        }).then(function (h) { return 'Server: ' + (h.version || '?') + ' (' + (h.mode || '?') + ')'; })
        .catch(function () { return 'Server: unreachable'; })
      ]).then(function (parts) {
        var pub = parts[0] && parts[0].ver, built = parts[0] && parts[0].built,
            laneLine = parts[1], srv = parts[2];
        var when = built ? ' (built ' + fmtBuild(built) + ')' : '';
        var upd = !pub ? ' · published: unreachable (ops server down?)'
          : (pub === inst ? ' · published ' + pub + when + ' — YOU ARE UP TO DATE'
          : ' · published ' + pub + when + ' — UPDATE AVAILABLE (refresh files + reload, same folder!)');
        box.textContent = 'This extension: ' + inst + upd + '\n' + laneLine + '\n' + srv;
      });
    });
  }
  SH.getElementById('verCheck').addEventListener('click', checkVersions);
  SH.getElementById('sync').addEventListener('click', function () {
    SH.getElementById('status').textContent = 'Syncing…';
    chrome.runtime.sendMessage({ type: 'bv-sync-now' }, function (r) {
      SH.getElementById('status').textContent = r && r.ok
        ? 'Synced ' + (r.synced || 0) + ' bookmark(s).'
        : 'Still local (' + ((r && r.reason) || 'no connection') + '). Nothing lost.';
      refresh();
    });
  });
  SH.getElementById('wipe').addEventListener('click', function () {
    if (!confirm('Erase ALL saved tweets on this device AND on the server? Labels stay.')) return;
    var keys = [QUEUE_KEY, LABELS_KEY, IMPORT_KEY];
    chrome.storage.local.remove(keys, function () {
      getApi().then(function (a) {
        if (!a.apiBase || !a.token) { refresh(); refreshImport(); return; }
        fetch(a.apiBase.replace(/\/$/, '') + '/v1/bookmarks/all', {
          method: 'DELETE',
          headers: { Authorization: 'Bearer ' + a.token }
        }).then(function () { refresh(); refreshImport(); })
        .catch(function () { refresh(); refreshImport(); });
      });
    });
  });
  SH.getElementById('dl').addEventListener('click', function () {
    Promise.all([getQueue(), getLabelMap()]).then(function (parts) {
      var q = parts[0].map(function (r) {
        return Object.assign({}, r, { labels: labelsOf(r, parts[1]) });
      });
      var blob = new Blob([JSON.stringify(q, null, 2)], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'bookmarkvault-export.json';
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 5000);
    });
  });

  getApi().then(function (a) {
    SH.getElementById('apiBase').value = a.apiBase;
    SH.getElementById('token').value = a.token;
    var vs = SH.getElementById('viewServer');
    if (vs && a.apiBase) vs.href = a.apiBase.replace(/\/$/, '') + '/view';
  });
  refresh();
  refreshImport();
  fetchPlan();
  checkVersions();

  
    try { window.BVAPP.refresh = refresh; } catch (e) {}
  }

})();
