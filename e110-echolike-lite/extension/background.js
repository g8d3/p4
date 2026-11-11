// EchoLike Lite — background. Saves every capture locally, forwards to the
// inbox when one is configured. The outbox survives restarts; failed sends
// retry on the next capture, on startup, or from the popup's Retry button.
// No alarms, no polling: the only traffic is the claim the user asks for
// (discover/claim), a send when something is queued, and the health check that
// comes with it.
const MAX_ITEMS = 500;

// The hosted inbox: an install that has never been configured claims a tenant
// there by itself on the first capture — no address, no token, no click. Point
// it at empty to require an explicit inbox instead.
const DEFAULT_INBOX = "https://inbox-lite.echolike.app";
const DEFAULT_RETRY_MS = 30 * 60 * 1000; // a failed silent claim waits for the next capture

// Where a local inbox is likely to answer. Loopback only: nothing leaves this
// machine, and only the user's own server is ever probed.
const CANDIDATES = [
  "http://127.0.0.1:8931",
  "http://localhost:8931",
  "http://127.0.0.1:8911",
  "http://localhost:8911",
];

async function timed(url, opts, ms) {
  const c = new AbortController();
  const t = setTimeout(() => c.abort(), ms || 1500);
  try {
    return await fetch(url, Object.assign({ signal: c.signal }, opts || {}));
  } finally {
    clearTimeout(t);
  }
}

async function state() {
  const s = await chrome.storage.local.get({
    url: "",
    token: "",
    outbox: [],
    items: [],
    last: null,
    defaultTriedAt: 0,
  });
  return s;
}

async function flush(verify) {
  let s = await state();
  // First capture of a fresh install: claim a tenant on the hosted inbox, silently.
  if (
    !s.url &&
    DEFAULT_INBOX &&
    s.outbox.length &&
    (!s.defaultTriedAt || Date.now() - s.defaultTriedAt > DEFAULT_RETRY_MS)
  ) {
    await chrome.storage.local.set({ defaultTriedAt: Date.now() });
    if ((await claimAt(DEFAULT_INBOX)).ok) s = await state();
  }
  if (!s.url || !s.token) return { ok: true, pending: s.outbox.length };
  // Nothing queued and no verification asked: stay quiet (no background traffic).
  if (!s.outbox.length && !verify) return { ok: true, pending: 0 };
  let res;
  try {
    res = await fetch(s.url.replace(/\/$/, "") + "/api/likes", {
      method: "POST",
      headers: { authorization: "Bearer " + s.token, "content-type": "application/json" },
      body: JSON.stringify({ items: s.outbox }),
    });
  } catch (e) {
    s.last = { ok: false, error: "unreachable: " + String(e.message || e).slice(0, 100), at: new Date().toISOString() };
    await chrome.storage.local.set({ last: s.last });
    return { ok: false, error: s.last.error, pending: s.outbox.length };
  }
  if (res.status === 401) {
    s.last = { ok: false, error: "bad token (401)", at: new Date().toISOString() };
    await chrome.storage.local.set({ last: s.last });
    return { ok: false, error: s.last.error, pending: s.outbox.length };
  }
  if (res.status === 402) {
    const j = await res.json().catch(() => null);
    s.last = {
      ok: false,
      error: "free quota spent this month" + (j && j.quota ? " (" + j.used + "/" + j.quota + ")" : ""),
      at: new Date().toISOString(),
    };
    await chrome.storage.local.set({ last: s.last });
    return { ok: false, error: s.last.error, pending: s.outbox.length };
  }
  if (!res.ok) {
    s.last = { ok: false, error: "inbox HTTP " + res.status, at: new Date().toISOString() };
    await chrome.storage.local.set({ last: s.last });
    return { ok: false, error: s.last.error, pending: s.outbox.length };
  }
  const j = await res.json().catch(() => null);
  const n = s.outbox.length;
  s.last = {
    ok: true,
    error: null,
    at: new Date().toISOString(),
    used: j && typeof j.used === "number" ? j.used : null,
    quota: j && typeof j.quota === "number" ? j.quota : null,
  };
  await chrome.storage.local.set({ outbox: [], last: s.last });
  return { ok: true, sent: n, pending: 0, used: s.last.used, quota: s.last.quota };
}

// Zero-typing setup: the server mints the device token, the extension keeps it.
// One button; no address, no token to copy, nothing to truncate.
async function claimAt(url) {
  const base = String(url || "").replace(/\/$/, "");
  let cres;
  try {
    cres = await timed(base + "/api/claim", { method: "POST" }, 5000);
  } catch (e) {
    return { ok: false, url: base, error: "no answer from " + base };
  }
  const j = await cres.json().catch(() => null);
  if (cres.status === 404) {
    return {
      ok: false,
      url: base,
      error: "that inbox is older than the extension (no /api/claim) — paste its token under Advanced",
    };
  }
  if (!cres.ok || !j || !j.token) {
    return { ok: false, url: base, error: (j && j.error) || "inbox refused the claim (HTTP " + cres.status + ")" };
  }
  await chrome.storage.local.set({ url: base, token: j.token });
  const out = await flush(true);
  return { ok: out.ok, url: base, error: out.error || null, pending: out.pending };
}

async function discover() {
  const s = await state();
  if (s.url && s.token) return { ok: true, url: s.url, already: true, pending: s.outbox.length };
  for (const url of CANDIDATES) {
    let hres;
    try {
      hres = await timed(url + "/api/health", {});
    } catch (e) {
      continue; // nothing listening on that port: try the next
    }
    if (!hres.ok) continue;
    return claimAt(url);
  }
  // Nothing on this machine: fall back to the hosted inbox, same one tap.
  if (DEFAULT_INBOX) return claimAt(DEFAULT_INBOX);
  return { ok: false, error: "no inbox found on this computer" };
}

async function capture(item) {
  item.uid = (globalThis.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now());
  const s = await state();
  s.items.push(item);
  s.outbox.push(item);
  await chrome.storage.local.set({
    items: s.items.slice(-MAX_ITEMS),
    outbox: s.outbox.slice(-MAX_ITEMS),
  });
  const r = await flush();
  return r.ok && !r.pending ? { sent: true, uid: item.uid } : { saved: true, uid: item.uid, error: r.error || null };
}

chrome.runtime.onMessage.addListener((m, _sender, reply) => {
  const p =
    m && m.type === "capture"
      ? capture(m.item)
      : m && m.type === "retry"
        ? flush(true)
        : m && m.type === "discover"
          ? discover()
          : m && m.type === "claim"
            ? claimAt(m.url)
          : m && m.type === "forget"
            ? chrome.storage.local.remove(["url", "token"]).then(() => ({ ok: true }))
            : m && m.type === "save"
          ? chrome.storage.local.set({ url: String(m.url || ""), token: String(m.token || "") }).then(() => flush(true))
          : m && m.type === "state"
            ? state().then((s) => ({
                url: s.url,
                hasToken: !!s.token,
                token: s.token,
                defaultInbox: DEFAULT_INBOX,
                pending: s.outbox.length,
                total: s.items.length,
                last: s.last,
                items: s.items.slice(-30).reverse(),
              }))
            : null;
  if (!p) return;
  p.then(reply, (e) => reply({ ok: false, error: String((e && e.message) || e) }));
  return true;
});

chrome.runtime.onStartup.addListener(() => flush().catch(() => {}));
