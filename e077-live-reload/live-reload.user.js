// ==UserScript==
// @name         Live Reload Loader
// @namespace    e077
// @version      1.1
// @description  Install once in Queta (.user.js). Takes a server address, receives its URL list, hot-injects them.
// @match        *://*/*
// @run-at       document-idle
// @grant        GM_xmlhttpRequest
// @connect      192.168.0.177
// ==/UserScript==

/* THE ONE SETTING (single manual edit, then never again):
   your PC's dev server address. The URL LIST comes from the server itself
   (GET <SERVER>/config), so adding files needs no reinstall. */
const SERVER = "http://192.168.0.177:8080";
const POLL_MS = 1000;

(function () {
  "use strict";
  let lastV = null;
  let host = null;

  // Strict pages (x.com, …) block fetch via CSP connect-src.
  // GM_xmlhttpRequest bypasses page CSP where the engine supports it; else fetch fallback.
  function netGet(url) {
    return new Promise(function (resolve, reject) {
      try {
        if (typeof GM_xmlhttpRequest === "function") {
          GM_xmlhttpRequest({
            method: "GET", url: url,
            onload: function (r) {
              if (r.status >= 200 && r.status < 300) resolve(r.responseText);
              else reject(new Error("http " + r.status));
            },
            onerror: reject,
          });
        } else {
          fetch(url).then(function (r) {
            if (!r.ok) throw new Error("http " + r.status);
            return r.text();
          }).then(resolve, reject);
        }
      } catch (e) { reject(e); }
    });
  }

  function ensureHost() {
    if (host && document.contains(host)) return host;
    host = document.createElement("div");
    host.id = "__live_reload_host__";
    host.style.cssText =
      "position:fixed;left:12px;bottom:12px;z-index:2147483647;max-width:80vw";
    document.documentElement.appendChild(host);
    return host;
  }

  function toast(msg) {
    const t = document.createElement("div");
    t.textContent = msg;
    t.style.cssText =
      "position:fixed;top:12px;right:12px;z-index:2147483647;" +
      "background:#000;color:#fff;font:500 13px system-ui;" +
      "padding:6px 10px;border-radius:8px;opacity:.9";
    document.documentElement.appendChild(t);
    setTimeout(() => t.remove(), 1500);
  }

  async function refresh() {
    const el = ensureHost();
    try {
      const cfg = JSON.parse(await netGet(`${SERVER}/config.json?ts=${Date.now()}`));
      const files = cfg.files || [];
      const texts = await Promise.all(
        files.map((f) => netGet(`${SERVER}${f.path}?ts=${Date.now()}`).then((t) => ({ ...f, t })))
      );
      el.innerHTML = "";
      for (const f of texts.filter((f) => f.type === "js")) {
        // eslint-disable-next-line no-eval
        window.eval(f.t);
      }
      if (typeof window.__LIVE_RENDER === "function") window.__LIVE_RENDER(el);
      for (const f of texts.filter((f) => f.type === "html")) {
        const wrap = document.createElement("div");
        wrap.innerHTML = f.t;
        el.appendChild(wrap);
      }
    } catch (e) {
      el.innerHTML = `<div style="padding:8px 12px;border-radius:10px;background:#7f1d1d;color:#fff;font:500 13px system-ui">⚠️ live server unreachable: ${SERVER}</div>`;
    }
  }

  async function poll() {
    try {
      const t = await netGet(`${SERVER}/version?ts=${Date.now()}`);
      const { v } = JSON.parse(t);
      if (lastV === null) {
        lastV = v;
        await refresh();
        toast(`🔌 live connected (v${v})`);
      } else if (v !== lastV) {
        lastV = v;
        await refresh();
        toast(`⚡ updated → v${v}`);
      }
    } catch {
      /* server off — retry silently */
    }
  }

  poll();
  setInterval(poll, POLL_MS);
})();
