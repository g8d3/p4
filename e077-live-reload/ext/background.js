// Network relay (service worker = extension context, exempt from page CSP).
// x.com and other strict sites block content-script fetch via connect-src;
// nothing in the content script touches the network anymore — it asks here.
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
});
