// Live Reload Loader (content script) — config-driven, no hardcoded file list.
// The ONLY address: read from storage (set in popup), fallback = first-install default.
// The URL LIST comes from the server: GET <SERVER>/config.json -> {"files":[{path,type}]}.
// Add/remove files in server/public/ + one row in config.json — phone follows, no reinstall.

const DEFAULT_SERVER = "http://192.168.0.177:8080"; // works out of the box today; override in popup (IP changes need no reinstall)
const POLL_MS = 1000;

let SERVER = "";
let lastV = null;
let host = null;

// ALL network goes through the background worker: strict pages (x.com, …)
// block content-script fetch via CSP connect-src, but extension-context
// fetch is exempt. Same Response shape the code already uses.
function bgFetch(url) {
  return new Promise((resolve, reject) => {
    try {
      chrome.runtime.sendMessage({ type: "live-fetch", url }, (res) => {
        if (chrome.runtime.lastError || !res || !res.ok) reject(new Error("bg fetch failed"));
        else resolve({ text: async () => res.t, json: async () => JSON.parse(res.t) });
      });
    } catch (e) {
      reject(e);
    }
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

function setupBox() {
  const el = ensureHost();
  el.innerHTML = `<div style="padding:8px 12px;border-radius:10px;background:#7f1d1d;color:#fff;font:500 13px system-ui">⚠️ live loader: set the dev server URL in the extension popup</div>`;
}

// Load the server-declared URL list and inject each file by type.
async function refresh() {
  const el = ensureHost();
  try {
    const cfg = await bgFetch(`${SERVER}/config.json?ts=${Date.now()}`).then((r) => r.json());
    const files = cfg.files || [];
    const texts = await Promise.all(
      files.map((f) => bgFetch(`${SERVER}${f.path}?ts=${Date.now()}`).then((r) => r.text()).then((t) => ({ ...f, t })))
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
  if (!SERVER) return;
  try {
    const r = await bgFetch(`${SERVER}/version?ts=${Date.now()}`);
    const { v } = await r.json();
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

async function boot() {
  try {
    const { serverUrl } = await chrome.storage.local.get("serverUrl");
    SERVER = (serverUrl || DEFAULT_SERVER).replace(/\/$/, "");
  } catch {
    SERVER = DEFAULT_SERVER;
  }
  if (!SERVER) {
    setupBox();
    return;
  }
  poll();
  setInterval(poll, POLL_MS);
  // Follow popup saves without page reload.
  if (chrome.storage && chrome.storage.onChanged) {
    chrome.storage.onChanged.addListener((chg) => {
      if (chg.serverUrl) {
        SERVER = (chg.serverUrl.newValue || "").replace(/\/$/, "");
        lastV = null;
        if (!SERVER) setupBox();
        else poll();
      }
    });
  }
}

boot();
