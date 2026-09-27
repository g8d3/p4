// Live Reload Loader (content script).
// Install ONCE, then edit http://<PC-LAN-IP>:8080/live.js + card.html freely.
//
// ★ BEFORE INSTALLING: set your PC's LAN IP here (e.g. 192.168.1.50).
// Find it with: hostname -I  (linux)  /  ipconfig  (windows)
const SERVER = "http://192.168.1.50:8080";
const POLL_MS = 1000;

let lastV = null;
let host = null;

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
    // Fetch fresh copies (cache-busted). live.js defines window.__LIVE_RENDER.
    const [js, html] = await Promise.all([
      fetch(`${SERVER}/live.js?ts=${Date.now()}`).then((r) => r.text()),
      fetch(`${SERVER}/card.html?ts=${Date.now()}`).then((r) => r.text()),
    ]);
    // eslint-disable-next-line no-eval
    window.eval(js);
    if (typeof window.__LIVE_RENDER === "function") {
      window.__LIVE_RENDER(el);
      // Append the HTML fragment below the JS-rendered box.
      const wrap = document.createElement("div");
      wrap.innerHTML = html;
      el.appendChild(wrap);
    }
  } catch (e) {
    el.innerHTML = `<div style="padding:8px 12px;border-radius:10px;background:#7f1d1d;color:#fff;font:500 13px system-ui">⚠️ live server unreachable: ${SERVER}</div>`;
  }
}

async function poll() {
  try {
    const r = await fetch(`${SERVER}/version?ts=${Date.now()}`);
    const { v } = await r.json();
    if (lastV === null) {
      lastV = v;
      await refresh(); // first paint
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
