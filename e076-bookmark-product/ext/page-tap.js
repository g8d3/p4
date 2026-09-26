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
  function pageType() {
    try {
      var p = location.pathname || '';
      if (/\/i\/bookmarks/.test(p)) return 'bookmarks';
      if (/\/likes/.test(p)) return 'likes';
      if (/\/i\/history/.test(p)) return 'history';
    } catch (e) {}
    return 'other';
  }
  function shouldCapture(url) {
    var u = String(url || '');
    var t = pageType();
    var bm = (TUN && TUN.matchUrl) || ['Bookmark', 'bookmark'];
    var lk = (TUN && TUN.matchUrlLikes) || ['Favorit', 'Favourit', 'Likes', 'likes', 'Favorite'];
    var hx = (TUN && TUN.matchUrlHistory) || ['graphql'];
    function any(list) { for (var i = 0; i < list.length; i++) if (u.indexOf(list[i]) >= 0) return true; return false; }
    if (any(bm)) return true;
    if (t === 'likes' && (any(lk) || /graphql/i.test(u))) return true;
    if (t === 'history' && any(hx)) return true;
    return false;
  }
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
  // Post kind + extra text: plain tweets carry everything in legacy.full_text,
  // but Articles keep the body behind /i/article/ links, and polls / media /
  // quotes live in card / quoted_status_result. We tag the kind and append
  // whatever preview strings the payload already has (card title, excerpt,
  // poll choices) so the saved copy is useful without extra requests.
  function kindOf(obj, text) {
    try {
      if (obj.article) return 'article';
      if (/\/i\/article\//.test(text || '')) return 'article';
      var cn = '';
      try { cn = String(obj.card && obj.card.legacy && obj.card.legacy.name || ''); } catch (e) {}
      if (/poll/i.test(cn)) return 'poll';
      if (/article/i.test(cn)) return 'article';
      if (/video|gif|media|image|player|moment|card/i.test(cn)) return 'media';
      if (obj.quoted_status_result || (obj.legacy && obj.legacy.quoted_status_id_str)) return 'quote';
      if (obj.legacy && obj.legacy.retweeted_status_result) return 'repost';
    } catch (e) {}
    return 'tweet';
  }
  function extraText(obj, kind) {
    var bits = [];
    try {
      var card = obj.card && obj.card.legacy;
      if (card && typeof card === 'object') {
        ['title', 'description'].forEach(function (k) {
          if (typeof card[k] === 'string' && card[k]) bits.push(card[k]);
        });
        // poll choices: binding_values as array [{key, value:{string_value}}] or map
        var bv = card.binding_values;
        function grabChoice(key, val) {
          if (!/^choice\d+_label$/i.test(key || '')) return;
          var v = val && val.string_value;
          if (typeof v === 'string' && v) bits.push('\u25FB ' + v);
        }
        if (Array.isArray(bv)) bv.forEach(function (b) {
          if (b) grabChoice(b.key, b.value);
        });
        else if (bv && typeof bv === 'object') Object.keys(bv).forEach(function (k) {
          grabChoice(k, bv[k]);
        });
      }
      if (kind === 'article') {
        var at = '';
        try {
          at = (obj.article && obj.article.article_results &&
                obj.article.article_results.result &&
                obj.article.article_results.result.title) || '';
        } catch (e) {}
        if (typeof at === 'string' && at) bits.unshift(at);
      }
    } catch (e) {}
    return bits.join('\n').slice(0, 1000);
  }
  var QUOTED_KEYS = { quoted_status_result: 1, quotedRefResult: 1,
    retweeted_status_result: 1, retweetedStatusResult: 1 };
  function pick(obj, out, ctx, order) {
    if (!obj || typeof obj !== 'object') return;
    if (Array.isArray(obj)) { for (var i = 0; i < obj.length; i++) pick(obj[i], out, ctx, order); return; }
    // Timeline entries carry sortIndex (bookmark order — X sends no bookmark
    // creation date, so this ordering is the sync-verification signal).
    var sub = ctx || 'direct';
    var ord = order || null;
    try { if (typeof obj.sortIndex === 'string' && obj.sortIndex) ord = ord || obj.sortIndex; } catch (e) {}
    // GraphQL tweet shape: legacy.full_text + core.user_results.legacy.screen_name
    if (obj.legacy && typeof obj.legacy.full_text === 'string' &&
        (obj.rest_id || obj.legacy.id_str)) {
      var user = '';
      var paths = (TUN && TUN.namePaths) || ['core.user_results.result.legacy.screen_name'];
      for (var pi = 0; pi < paths.length && !user; pi++) user = getp(obj, paths[pi]);
      var deep = !TUN || TUN.deepName !== false;
      var dd = (TUN && TUN.deepDepth) || 6;
      if (!user && deep) user = findName(obj, 0, dd) || '';
      var base = obj.legacy.full_text;
      var kind = kindOf(obj, base);
      var extra = extraText(obj, kind);
      out.push({
        id: String(obj.rest_id || obj.legacy.id_str),
        text: (base + (extra ? '\n\u2014 \u2014 \u2014\n' + extra : '')).slice(0, 3000),
        author: user,
        created_at: obj.legacy.created_at || '',
        source: 'xhr',
        page: pageType(),
        kind: kind,
        context: sub,
        saveOrder: ord
      });
      return;
    }
    for (var k in obj) {
      if (!Object.prototype.hasOwnProperty.call(obj, k)) continue;
      pick(obj[k], out, QUOTED_KEYS[k] ? 'quoted' : sub, ord);
    }
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
    var of = window.fetch;
    window.fetch = function () {
      var args = arguments;
      return of.apply(this, args).then(function (res) {
        var url = '';
        try { url = (typeof args[0] === 'string' ? args[0] : args[0].url) || ''; } catch (e) {}
        if (shouldCapture(url)) {
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
        if (shouldCapture(self.__bvUrl || '')) {
          try { emit(self.responseText || ''); } catch (e) {}
        }
      });
      return os.apply(this, arguments);
    };
  } catch (e) {}
})();
