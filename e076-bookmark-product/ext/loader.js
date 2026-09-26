// BookmarkVault bootstrapper (thin, frozen): loads the real app (panel.js)
// remotely when devMode is ON (hot lane: F5 is enough), else the bundled
// snapshot. Code is fetched by/via the background worker; only evaluated
// here. Last resort: slim DOM-only capture so browsing is never silent.
(function () {
  'use strict';
  function run(code, remote) {
    if (window.__bvBooted) return;
    window.__bvBooted = true;
    try {
      // Remote eval sets __bvRemote ONLY on full success (flag appended after
      // code); __bvIsRemote marks the remote path so boot skips the wait.
      // A thrown eval (e.g. CSP) is reported with its message for diagnosis.
      (0, eval)((remote ? 'window.__bvIsRemote=true;\n' : '') + code +
        '\n;window.__bvRemote=true;\n//# sourceURL=bv-panel.js');
    } catch (e) {
      try { chrome.runtime.sendMessage({ type: 'bv-devnote',
        note: 'panel-eval-blocked:' + String((e && e.message) || e).slice(0, 160) }); } catch (e2) {}
      slim();
    }
  }
  function fetchVia(type, then) {
    try {
      chrome.runtime.sendMessage({ type: type }, function (r) { then(r); });
    } catch (e) { then(null); }
  }
  // Slim fallback: DOM-only capture, no import scroll, no UI.
  function slim() {
    if (window.__bvBooted) return;
    window.__bvBooted = true;
    try {
      var seen = {};
      setInterval(function () {
        var fresh = [];
        document.querySelectorAll('article[data-testid="tweet"]').forEach(function (el) {
          var link = el.querySelector('a[href*="/status/"]');
          var m = link ? /\/status\/(\d+)/.exec(link.getAttribute('href') || '') : null;
          if (!m || seen[m[1]]) return;
          seen[m[1]] = 1;
          var t = el.querySelector('[data-testid="tweetText"]');
          fresh.push({ id: m[1], text: (t ? t.innerText : '').slice(0, 2000),
            source: 'dom-slim', page: 'other' });
        });
        if (fresh.length) {
          try { chrome.runtime.sendMessage({ type: 'bv-capture', records: fresh }); } catch (e) {}
        }
      }, 4000);
    } catch (e) {}
  }
  try {
    chrome.storage.local.get('bv.devMode', function (o) {
      if (o && o['bv.devMode']) {
        fetchVia('bv-fetch-remote', function (r) {
          if (r && r.ok && r.code) { run(r.code, true); return; }
          try { chrome.runtime.sendMessage({ type: 'bv-devnote', note: 'panel-remote-fail' }); } catch (e) {}
          fetchVia('bv-fetch-local', function (r2) {
            if (r2 && r2.ok && r2.code) run(r2.code);
            else slim();
          });
        });
      } else {
        fetchVia('bv-fetch-local', function (r) {
          if (r && r.ok && r.code) run(r.code);
          else slim();
        });
      }
    });
  } catch (e) { slim(); }
})();
