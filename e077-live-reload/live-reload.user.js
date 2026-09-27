// ==UserScript==
// @name         Live Reload Loader
// @namespace    e077
// @version      1.8
// @description  Install once in Queta (.user.js). Takes a server address, receives its URL list, hot-injects them.
// @match        *://*/*
// @run-at       document-idle
// @grant        GM_xmlhttpRequest
// @connect      192.168.0.177
// @connect      vuos-hcar5000mi.tail6918b0.ts.net
// ==/UserScript==

/* THE ONE SETTING (single manual edit, then never again):
   your PC's dev server address. The URL LIST comes from the server itself
   (GET <SERVER>/config.json), so adding files needs no reinstall. */
const SERVER = "http://192.168.0.177:8080";
const LOADER_VERSION = "1.8";
const POLL_MS = 1000;

(function () {
  "use strict";
  let lastV = null;
  let host = null;
  let fails = 0; // consecutive network failures (CSP detection)
  let INSTALL = "unknown";
  try {
    INSTALL = localStorage.getItem("__live_id") || ("id-" + Date.now() + "-" + Math.random().toString(16).slice(2));
    localStorage.setItem("__live_id", INSTALL);
  } catch {}

  function netPost(url, body) {
    return new Promise(function (resolve, reject) {
      try {
        if (typeof GM_xmlhttpRequest === "function") {
          GM_xmlhttpRequest({
            method: "POST", url: url, data: body,
            headers: { "Content-Type": "application/json" },
            onload: function (r) {
              if (r.status >= 200 && r.status < 300) resolve();
              else reject(new Error("http " + r.status));
            },
            onerror: reject,
          });
        } else {
          fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: body })
            .then(function (r) { if (!r.ok) throw new Error("http " + r.status); })
            .then(resolve, reject);
        }
      } catch (e) { reject(e); }
    });
  }

  function pendingQueue() {
    try { return JSON.parse(localStorage.getItem("__live_pending") || "[]"); }
    catch { return []; }
  }

  // Diagnostics: phone home so no human relays screenshots. Queues offline.
  async function report(kind, detail) {
    const entry = {
      installId: INSTALL, loader: "user.js", loaderVersion: LOADER_VERSION,
      kind: kind, detail: detail || {}, page: location.href, at: new Date().toISOString(),
    };
    try {
      await netPost(`${SERVER}/api/report`, JSON.stringify({ ...entry, via: "direct" }));
      const q = pendingQueue();
      if (q.length) {
        for (const p of q) await netPost(`${SERVER}/api/report`, JSON.stringify(p)).catch(() => {});
        localStorage.setItem("__live_pending", "[]");
      }
    } catch {
      const q = pendingQueue();
      q.push({ ...entry, via: "queued" });
      try { localStorage.setItem("__live_pending", JSON.stringify(q.slice(-20))); } catch {}
    }
  }

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
      const jsFiles = texts.filter((f) => f.type === "js");
      // Execution ladder (see ext/content.js): isolated eval first,
      // page-context <script> injection second, amber note last.
      const runId = "r" + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36);
      let jsBlocked = false;
      let jsHow = "";
      try {
        for (const f of jsFiles) {
          let done = false;
          try {
            window.eval(f.t);
            done = true; // no throw = ran (render check happens below)
          } catch (e1) {
            done = false;
          }
          if (!done) {
            const s = document.createElement("script");
            s.textContent = "window.__LIVE_RUNID=" + JSON.stringify(runId) + ";" + "\n" + f.t;
            (document.head || document.documentElement).appendChild(s);
            s.remove();
          }
        }
        if (jsFiles.length && typeof window.__LIVE_RENDER !== "function" && window.__LIVE_RUNID !== runId) {
          jsBlocked = true;
          jsHow = "eval-sealed+injection-refused";
        }
      } catch (e) {
        jsBlocked = true;
        jsHow = String((e && e.message) || e).slice(0, 200);
      }
      if (typeof window.__LIVE_RENDER === "function" && !jsBlocked) window.__LIVE_RENDER(el);
      for (const f of texts.filter((f) => f.type === "html")) {
        const wrap = document.createElement("div");
        wrap.innerHTML = f.t;
        el.appendChild(wrap);
      }
      if (jsBlocked && jsFiles.length) {
        const note = document.createElement("div");
        note.style.cssText =
          "margin-top:8px;padding:8px 12px;border-radius:10px;background:#422006;color:#fef3c7;font:500 13px system-ui;border:1px solid #f59e0b";
        note.textContent = "⚠️ JS blocked here (page CSP or browser policy) — HTML still updates live. Develop JS on a plain page.";
        el.appendChild(note);
        report("eval-blocked", { files: jsFiles.map((f) => f.path), how: jsHow || "runid-mismatch" });
      }
    } catch (e) {
      el.innerHTML = `<div style="padding:8px 12px;border-radius:10px;background:#7f1d1d;color:#fff;font:500 13px system-ui">⚠️ live server unreachable: ${SERVER}</div>`;
      report("unreachable", { server: SERVER });
    }
  }

  async function poll() {
    try {
      const t = await netGet(`${SERVER}/version?ts=${Date.now()}`);
      const { v } = JSON.parse(t);
      fails = 0;
      if (lastV === null) {
        lastV = v;
        await refresh();
        toast(`🔌 live connected (v${v})`);
        report("boot", { serverVersion: v });
      } else if (v !== lastV) {
        lastV = v;
        await refresh();
        toast(`⚡ updated → v${v}`);
        report("applied", { serverVersion: v });
      }
    } catch {
      /* server off — retry silently */
      fails++;
      // Page CSP (x.com, …) blocks userscript network with no GM bridge to escape.
      // Say so once, plainly, instead of failing silently forever.
      if (fails === 5) toast("⛔ this page blocks userscripts (CSP) — install the .zip extension instead");
    }
  }

  poll();
  setInterval(poll, POLL_MS);
})();
