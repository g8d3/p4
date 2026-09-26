
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
  var BV_CSS = /*__BV_CSS__*/"";
  var BV_HTML = /*__BV_HTML__*/"";
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

