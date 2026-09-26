// BookmarkVault bootstrapper (thin, frozen): the real app (panel.js) loads
// statically via manifest. This guard only starts the slim DOM-only capture
// if the panel never boots (e.g. partial update). No remote eval: x.com CSP
// blocks it (see docs/extension-devtooling.md CSP verdict) — remote DATA
// (tuning) still flows through the background worker.
(function () {
  'use strict';
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
    setTimeout(function () {
      try {
        if (window.__bvUIBooted) return;
        if (document.getElementById('bv-pill')) return;
        try { chrome.runtime.sendMessage({ type: 'bv-devnote', note: 'panel-missing-slim' }); } catch (e) {}
        slim();
      } catch (e) { slim(); }
    }, 6000);
  } catch (e) {}
})();
