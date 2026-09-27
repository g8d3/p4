// Live Reload Loader (content script) — config-driven, no hardcoded file list.
// The ONLY address: read from storage (set in popup), fallback = first-install default.
// The URL LIST comes from the server: GET <SERVER>/config.json -> {"files":[{path,type}]}.
// Add/remove files in server/public/ + one row in config.json — phone follows, no reinstall.

const DEFAULT_SERVER = "http://192.168.0.177:8080"; // works out of the box today; override in popup (IP changes need no reinstall)
const LOADER_VERSION = "1.7";
const POLL_MS = 1000;

let SERVER = "";
let lastV = null;
let host = null;
let INSTALL = "unknown";

async function getInstallId() {
  try {
    let { installId } = await chrome.storage.local.get("installId");
    if (!installId) {
      installId =
        (crypto.randomUUID ? crypto.randomUUID() : "id-" + Date.now() + "-" + Math.random().toString(16).slice(2));
      await chrome.storage.local.set({ installId });
    }
    return installId;
  } catch {
    return "unknown";
  }
}

// Diagnostics: phone home with every error so no human relays screenshots.
// Via background relay; if the worker is dead, direct POST; else queue for later.
async function report(kind, detail) {
  const entry = {
    installId: INSTALL,
    loader: "ext",
    loaderVersion: LOADER_VERSION,
    kind,
    detail: detail || {},
    page: location.href,
    at: new Date().toISOString(),
  };
  const direct = async () => {
    const r = await fetch(`${SERVER}/api/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...entry, via: "direct" }),
    });
    if (!r.ok) throw new Error("post failed");
  };
  const flush = async () => {
    try {
      const { pending = [] } = await chrome.storage.local.get("pending");
      if (!pending.length) return;
      for (const p of pending) {
        await fetch(`${SERVER}/api/report`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(p),
        }).catch(() => {});
      }
      await chrome.storage.local.set({ pending: [] });
    } catch {}
  };
  const queue = async () => {
    try {
      const { pending = [] } = await chrome.storage.local.get("pending");
      pending.push({ ...entry, via: "queued" });
      await chrome.storage.local.set({ pending: pending.slice(-20) });
    } catch {}
  };
  if (!SERVER) return;
  try {
    const res = await new Promise((resolve) => {
      try {
        chrome.runtime.sendMessage({ type: "live-report", body: JSON.stringify({ ...entry, via: "relay" }) }, (r) => {
          if (chrome.runtime.lastError || !r || !r.ok) resolve(null);
          else resolve(r);
        });
      } catch {
        resolve(null);
      }
    });
    if (res) flush();
    else await direct().then(flush).catch(queue);
  } catch {
    queue();
  }
}

// Prefer the background relay (immune to page CSP). If the worker is dead
// (some mobile browsers), fall back to direct page-context fetch: works on
// permissive pages, still blocked on strict ones — which then gets reported.
function bgFetch(url) {
  return new Promise((resolve, reject) => {
    const direct = () =>
      fetch(url).then(
        (r) => resolve({ text: async () => r.text(), json: async () => r.json() }),
        reject
      );
    try {
      chrome.runtime.sendMessage({ type: "live-fetch", url }, (res) => {
        if (chrome.runtime.lastError || !res || !res.ok) direct();
        else resolve({ text: async () => res.t, json: async () => JSON.parse(res.t) });
      });
    } catch (e) {
      direct();
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
    const jsFiles = texts.filter((f) => f.type === "js");
    // Execution ladder (browser variance is real — probe, don't assume):
    // 1) isolated-world eval — works on older Chromes (Queta proven), sealed on desktop Chrome 153+.
    // 2) page-context <script> injection — obeys only the page's own CSP (fine on plain pages).
    // 3) amber note + report — strict pages (x.com): HTML still live, JS can't run there.
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
          done = false; // isolated world sealed — fall through to injection
        }
        if (!done) {
          const s = document.createElement("script");
          s.textContent = "window.__LIVE_RUNID=" + JSON.stringify(runId) + ";\n" + f.t;
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
      wrap.innerHTML = f.t; // innerHTML + inline styles are CSP-safe (no script execution)
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
  if (!SERVER) return;
  try {
    const r = await bgFetch(`${SERVER}/version?ts=${Date.now()}`);
    const { v } = await r.json();
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
  }
}

async function boot() {
  INSTALL = await getInstallId();
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
