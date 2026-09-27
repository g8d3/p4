// Network relay (service worker = extension context, exempt from page CSP).
// x.com and other strict sites block content-script fetch via connect-src;
// nothing in the content script touches the network anymore — it asks here.
const DEFAULT_SERVER = "http://vuos-hcar5000mi.tail6918b0.ts.net:8080";
function serverUrl(cb) {
  try {
    chrome.storage.local.get("serverUrl", ({ serverUrl }) =>
      cb((serverUrl || DEFAULT_SERVER).replace(/\/$/, ""))
    );
  } catch {
    cb(DEFAULT_SERVER);
  }
}

// Lab mode: strip the page's CSP header, ONLY on user-named hosts, ONLY while on.
// The header carries per-load nonces, so it can't be surgically edited — removal
// is all-or-nothing per host. Badge shows while active. Dev-only, user's risk.
async function applyLabMode() {
  try {
    const { labOn, labHosts = [] } = await chrome.storage.local.get(["labOn", "labHosts"]);
    const hosts = labOn ? labHosts.map((h) => String(h).trim().toLowerCase()).filter(Boolean) : [];
    const rules = hosts.slice(0, 10).map((h, i) => ({
      id: i + 1,
      priority: 1,
      action: {
        type: "modifyHeaders",
        responseHeaders: [{ header: "content-security-policy", operation: "remove" }],
      },
      condition: { urlFilter: "||" + h, resourceTypes: ["main_frame"] },
    }));
    const old = await chrome.declarativeNetRequest.getDynamicRules();
    await chrome.declarativeNetRequest.updateDynamicRules({
      removeRuleIds: old.map((r) => r.id),
      addRules: rules,
    });
    chrome.action.setBadgeText({ text: rules.length ? "CSP" : "" });
    chrome.action.setBadgeBackgroundColor({ color: "#b45309" });
  } catch {}
}
applyLabMode();
if (chrome.storage && chrome.storage.onChanged) {
  chrome.storage.onChanged.addListener((chg) => {
    if (chg.labOn || chg.labHosts) applyLabMode();
  });
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
        headers: { "Content-Type": "text/plain" },
        body: msg.body,
      })
        .then(() => reply({ ok: true }))
        .catch(() => reply({ ok: false }));
    });
    return true;
  }
});
