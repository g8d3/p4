// Network relay (service worker = extension context, exempt from page CSP).
// x.com and other strict sites block content-script fetch via connect-src;
// nothing in the content script touches the network anymore — it asks here.
const DEFAULT_SERVER = "http://192.168.0.177:8080";
function serverUrl(cb) {
  try {
    chrome.storage.local.get("serverUrl", ({ serverUrl }) =>
      cb((serverUrl || DEFAULT_SERVER).replace(/\/$/, ""))
    );
  } catch {
    cb(DEFAULT_SERVER);
  }
}
chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg && msg.type === "live-fetch" && typeof msg.url === "string") {
    fetch(msg.url)
      .then((r) => {
        if (!r.ok) throw new Error("http " + r.status);
        return r.text();
      })
      .then((t) => reply({ ok: true, t }))
      .catch(() => reply({ ok: false }));
    return true; // async reply
  }
  if (msg && msg.type === "live-report" && typeof msg.body === "string") {
    serverUrl((base) => {
      fetch(base + "/api/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: msg.body,
      })
        .then(() => reply({ ok: true }))
        .catch(() => reply({ ok: false }));
    });
    return true;
  }
});
