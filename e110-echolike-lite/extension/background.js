// EchoLike Lite — background. Saves every capture locally, forwards to the
// inbox when one is configured. The outbox survives restarts; failed sends
// retry on the next capture, on startup, or from the popup's Retry button.
// No alarms, no polling, no background traffic of any kind.
const MAX_ITEMS = 500;

async function state() {
  const s = await chrome.storage.local.get({ url: "", token: "", outbox: [], items: [], last: null });
  return s;
}

async function flush(verify) {
  const s = await state();
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
  if (!res.ok) {
    s.last = { ok: false, error: "inbox HTTP " + res.status, at: new Date().toISOString() };
    await chrome.storage.local.set({ last: s.last });
    return { ok: false, error: s.last.error, pending: s.outbox.length };
  }
  const n = s.outbox.length;
  s.last = { ok: true, error: null, at: new Date().toISOString() };
  await chrome.storage.local.set({ outbox: [], last: s.last });
  return { ok: true, sent: n, pending: 0 };
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
        : m && m.type === "save"
          ? chrome.storage.local.set({ url: String(m.url || ""), token: String(m.token || "") }).then(() => flush(true))
          : m && m.type === "state"
            ? state().then((s) => ({ url: s.url, pending: s.outbox.length, total: s.items.length, last: s.last, items: s.items.slice(-30).reverse() }))
            : null;
  if (!p) return;
  p.then(reply, (e) => reply({ ok: false, error: String((e && e.message) || e) }));
  return true;
});

chrome.runtime.onStartup.addListener(() => flush().catch(() => {}));
