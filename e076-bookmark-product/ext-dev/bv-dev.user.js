// ==UserScript==
// @name         BookmarkVault DEV (auto-updates, no reinstall)
// @namespace    bookmarkvault-dev
// @version      0.3
// @description  DEV ONLY: mirrors ext capture, posts to ops server. Updates itself on reload.
// @match        https://x.com/i/bookmarks*
// @match        https://x.com/i/history*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      vuos-hcar5000mi.tail6918b0.ts.net
// @updateURL    http://vuos-hcar5000mi.tail6918b0.ts.net:8901/ext-dev/bv-dev.user.js
// @downloadURL  http://vuos-hcar5000mi.tail6918b0.ts.net:8901/ext-dev/bv-dev.user.js
// @run-at       document-idle
// ==/UserScript==
(function () {
  'use strict';
  var BASE = 'http://vuos-hcar5000mi.tail6918b0.ts.net:8901';
  var SEEN = {}, COUNT = 0;
  function post(kind, payload) {
    try {
      GM_xmlhttpRequest({ method: 'POST', url: BASE + '/api/telemetry',
        headers: { 'Content-Type': 'application/json' },
        data: JSON.stringify({ kind: kind, src: 'violentmonkey-dev', payload: payload }) });
    } catch (e) {}
  }
  function pick(obj, out) {
    if (!obj || typeof obj !== 'object') return;
    if (Array.isArray(obj)) { for (var i = 0; i < obj.length; i++) pick(obj[i], out); return; }
    if (obj.legacy && typeof obj.legacy.full_text === 'string' && (obj.rest_id || obj.legacy.id_str)) {
      var user = '';
      try { user = obj.core.user_results.result.legacy.screen_name || ''; } catch (e) {}
      out.push({ id: String(obj.rest_id || obj.legacy.id_str),
        text: obj.legacy.full_text.slice(0, 500), author: user,
        created_at: obj.legacy.created_at || '', source: 'vm-dev',
        raw_keys: Object.keys(obj).slice(0, 12),
        has_core: !!(obj.core && obj.core.user_results) });
      return;
    }
    for (var k in obj) { if (Object.prototype.hasOwnProperty.call(obj, k)) pick(obj[k], out); }
  }
  function emit(payload) {
    try {
      var out = [];
      pick(typeof payload === 'string' ? JSON.parse(payload) : payload, out);
      var fresh = out.filter(function (r) { if (SEEN[r.id]) return false; SEEN[r.id] = 1; return true; });
      if (!fresh.length) return;
      COUNT += fresh.length;
      hud('dev: ' + COUNT + ' captured here');
      post('dev-capture', { n: fresh.length, items: fresh.slice(0, 10),
        noAuthor: fresh.filter(function (r) { return !r.author; }).length });
    } catch (e) {}
  }
  var histPage = /\/i\/history/.test(location.pathname);
  try {
    var of = window.fetch;
    window.fetch = function () {
      var args = arguments;
      return of.apply(this, args).then(function (res) {
        var url = '';
        try { url = (typeof args[0] === 'string' ? args[0] : args[0].url) || ''; } catch (e) {}
        if (/Bookmark|bookmark/i.test(url) || (histPage && /graphql/i.test(url))) {
          try { res.clone().text().then(emit).catch(function () {}); } catch (e) {}
        }
        return res;
      });
    };
  } catch (e) { post('dev-error', { where: 'fetch-hook', msg: String(e).slice(0, 200) }); }
  function hud(t) {
    var el = document.getElementById('bv-dev-hud');
    if (!el) {
      el = document.createElement('div');
      el.id = 'bv-dev-hud';
      el.setAttribute('style', 'position:fixed;left:8px;right:8px;bottom:12px;z-index:999999;background:#311;color:#fff;border-radius:10px;padding:8px 12px;font:13px system-ui');
      document.body.appendChild(el);
    }
    el.textContent = 'BV-DEV: ' + t;
  }
  hud('watching here');
  post('dev-hello', { page: location.href });
})();
