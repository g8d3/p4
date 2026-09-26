// BookmarkVault page-context hook (runs in MAIN world via chrome.scripting).
// Observes fetch/XHR payloads and postMessages tweet records to the content script.
// No network calls, no DOM writes — CSP-safe (no inline script).
(function () {
  'use strict';
  var TUN = null; // dev tuning pushed from content script (same defaults bundled)
  try {
    window.addEventListener('message', function (ev) {
      if (ev.data && ev.data.__bvTuning) TUN = ev.data.__bvTuning;
    });
  } catch (e) {}
  function getp(o, path) {
    try {
      var cur = o, parts = String(path).split('.');
      for (var i = 0; i < parts.length; i++) {
        if (cur == null) return '';
        cur = cur[parts[i] === '*' ? Object.keys(cur)[0] : parts[i]];
      }
      return typeof cur === 'string' ? cur : '';
    } catch (e) { return ''; }
  }
  function pick(obj, out) {
    if (!obj || typeof obj !== 'object') return;
    if (Array.isArray(obj)) { for (var i = 0; i < obj.length; i++) pick(obj[i], out); return; }
    // GraphQL tweet shape: legacy.full_text + core.user_results.legacy.screen_name
    if (obj.legacy && typeof obj.legacy.full_text === 'string' &&
        (obj.rest_id || obj.legacy.id_str)) {
      var user = '';
      var paths = (TUN && TUN.namePaths) || ['core.user_results.result.legacy.screen_name'];
      for (var pi = 0; pi < paths.length && !user; pi++) user = getp(obj, paths[pi]);
      var deep = !TUN || TUN.deepName !== false;
      var dd = (TUN && TUN.deepDepth) || 6;
      if (!user && deep) user = findName(obj, 0, dd) || '';
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
  function findName(o, depth, maxd) {
    // fallback for new shapes (e.g. history page): first screen_name in subtree
    if (!o || typeof o !== 'object' || depth > (maxd || 6)) return '';
    if (typeof o.screen_name === 'string' && o.screen_name) return o.screen_name;
    if (typeof o.username === 'string' && o.username) return o.username;
    for (var k in o) {
      if (!Object.prototype.hasOwnProperty.call(o, k)) continue;
      if (k === 'legacy' && o[k] && typeof o[k].full_text === 'string') continue; // skip self text
      var r = findName(o[k], depth + 1, maxd);
      if (r) return r;
    }
    return '';
  }
  function emit(payload) {
    try {
      var out = [];
      var data = typeof payload === 'string' ? JSON.parse(payload) : payload;
      pick(data, out);
      if (out.length) window.postMessage({ __bv: true, records: out.slice(0, 100) }, '*');
    } catch (e) {}
  }
  try {
    var histPage = /\/i\/history/.test(location.pathname);
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
    var ox = window.XMLHttpRequest.prototype.open;
    window.XMLHttpRequest.prototype.open = function (m, u) {
      try { this.__bvUrl = String(u || ''); } catch (e) {}
      return ox.apply(this, arguments);
    };
    var os = window.XMLHttpRequest.prototype.send;
    window.XMLHttpRequest.prototype.send = function () {
      var self = this;
      self.addEventListener('load', function () {
        if (/Bookmark|bookmark/i.test(self.__bvUrl || '') || (histPage && /graphql/i.test(self.__bvUrl || ''))) {
          try { emit(self.responseText || ''); } catch (e) {}
        }
      });
      return os.apply(this, arguments);
    };
  } catch (e) {}
})();
