// ★ THIS IS THE FILE YOU EDIT CONTINUOUSLY ★
// Every time you save, the server bumps /version and your phone re-runs this
// file within ~1 second. No reinstall, no page reload needed.
//
// Try: change the emoji, colors, or text below, save, watch your phone.

window.__LIVE_RENDER = function (host) {
  host.innerHTML = "";
  const box = document.createElement("div");
  box.style.cssText =
    "padding:12px 16px;border-radius:12px;font:600 15px system-ui;" +
    "background:#7c3aed;color:#fff;border:2px solid #facc15;" +
    "box-shadow:0 4px 24px rgba(0,0,0,.35)";
  // ↓↓↓ EDIT ME — change this and save ↓↓↓
  box.textContent = "🟣 LIVE v2 — I just edited this on PC! No reinstall!";
  // ↑↑↑ EDIT ME ↑↑↑
  host.appendChild(box);
};
