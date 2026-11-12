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

// ---- Encryption: the inbox only ever sees ciphertext ------------------------
// AES-256-GCM with a key generated here, on first run, and never sent anywhere.
// The server stores {iv, ct} blobs; a stolen token is worth nothing without the
// key. The key is shown once as a recovery code: it is the only way to read the
// hosted inbox on another device, and nobody can regenerate it.
// base64url, unpadded: the recovery code travels in URLs and copy-paste, and "+"
// in a fragment comes back as a space, which would silently corrupt the key.
const b64 = (u8) =>
  btoa(String.fromCharCode.apply(null, Array.from(u8)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
const unb64 = (s) => {
  let t = String(s).replace(/-/g, "+").replace(/_/g, "/");
  while (t.length % 4) t += "=";
  const b = atob(t);
  const u = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i);
  return u;
};

async function keyCode() {
  const s = await chrome.storage.local.get({ key: "" });
  if (s.key) return s.key;
  const raw = crypto.getRandomValues(new Uint8Array(32));
  const k = b64(raw);
  await chrome.storage.local.set({ key: k });
  return k;
}

async function aesKey() {
  return crypto.subtle.importKey("raw", unb64(await keyCode()), "AES-GCM", false, ["encrypt"]);
}

// One blob per capture: {uid, iv, ct}. The uid stays readable so retries are idempotent by eye.
async function seal(item) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    await aesKey(),
    new TextEncoder().encode(JSON.stringify(item)),
  );
  return { uid: item.uid, iv: b64(iv), ct: b64(new Uint8Array(ct)) };
}

async function state() {
  const s = await chrome.storage.local.get({
    url: "",
    token: "",
    outbox: [],
    items: [],
    last: null,
    defaultTriedAt: 0,
    accountEmail: "",
    accountToken: "",
    keyBackedAt: null,
    telemetry: [],
    telq: [],
    tel_on: true,
  });
  return s;
}

// ---- diagnostics -----------------------------------------------------------
// One line per thing the user asked for, so a failure can be read afterwards
// instead of guessed at. Only the shape of the attempt is recorded: action, ok,
// http code, host, milliseconds, error text, version. Never a capture — no text,
// no handle, no url. Kept locally (last 200) and uploaded in the same pass as a
// send, so there is no extra traffic of its own.
const TEL_KEEP = 200;

async function tel(action, info) {
  const e = {
    action: String(action),
    ok: info && typeof info.ok === "boolean" ? info.ok : null,
    code: info && info.code ? Number(info.code) : null,
    ms: info && Number.isFinite(info.ms) ? info.ms : null,
    host: info && info.host ? String(info.host) : null,
    error: info && info.error ? String(info.error).slice(0, 160) : null,
    detail: info && info.detail ? String(info.detail).slice(0, 200) : null,
    at: new Date().toISOString(),
    version: chrome.runtime.getManifest().version,
  };
  try {
    const s = await chrome.storage.local.get({ telemetry: [], telq: [], tel_on: true });
    if (!s.tel_on) return;
    await chrome.storage.local.set({
      telemetry: s.telemetry.concat([e]).slice(-TEL_KEEP),
      telq: s.telq.concat([e]).slice(-TEL_KEEP),
    });
  } catch (err) {
    return; /* diagnostics must never break the thing they observe */
  }
  // Enabled means sent: no button, no timer. If it fails, the queue keeps them and
  // the next event (capture, X tab, online, page open, startup) tries again.
  telFlush();
}

let telSending = null;

async function telFlush() {
  if (telSending) return telSending;
  telSending = telFlushOnce().finally(() => {
    telSending = null;
  });
  return telSending;
}

async function telFlushOnce() {
  const s = await chrome.storage.local.get({ telq: [], tel_on: true, url: "", token: "" });
  if (!s.tel_on || !s.telq.length) return;
  const base = (s.url || DEFAULT_INBOX).replace(/\/$/, "");
  if (!base) return;
  const batch = s.telq.slice(-20);
  const headers = { "content-type": "application/json" };
  if (s.token) headers.authorization = "Bearer " + s.token;
  try {
    const r = await timed(base + "/api/telemetry", { method: "POST", headers, body: JSON.stringify({ events: batch }) }, 8000);
    if (r.ok) await chrome.storage.local.set({ telq: s.telq.slice(0, Math.max(0, s.telq.length - batch.length)) });
  } catch (e) {
    /* offline: keep them queued */
  }
}

let flushing = null;

async function flush(verify) {
  // One flush at a time: two in flight would post the same queue twice.
  if (flushing) return flushing;
  flushing = flushOnce(verify).finally(() => {
    flushing = null;
  });
  return flushing;
}

async function flushOnce(verify) {
  let s = await state();
  // First capture of a fresh install connects itself: the inbox on this computer
  // if there is one, the hosted one otherwise. No button, no address, no token.
  if (!s.url && s.outbox.length && (!s.defaultTriedAt || Date.now() - s.defaultTriedAt > DEFAULT_RETRY_MS)) {
    await chrome.storage.local.set({ defaultTriedAt: Date.now() });
    for (const url of CANDIDATES.concat(DEFAULT_INBOX ? [DEFAULT_INBOX] : [])) {
      let h;
      try {
        h = await timed(url + "/api/health", {}, 2500);
      } catch (e) {
        continue;
      }
      if (!h.ok) continue;
      if ((await claimAt(url, true)).ok) break;
    }
    s = await state();
  }
  if (!s.url || !s.token) return { ok: true, pending: s.outbox.length };
  // Nothing queued and no verification asked: stay quiet (no background traffic).
  if (!s.outbox.length && !verify) return { ok: true, pending: 0 };
  // Anything queued before encryption existed is sealed now, here, before it goes
  // out: a v4 client must never upload plaintext, and the queue must not be stuck
  // for ever because of the version it was written by.
  let queue = s.outbox;
  if (queue.some((it) => !it.ct)) {
    const sealed = [];
    for (const it of queue) sealed.push(it.ct ? it : await seal(it));
    await chrome.storage.local.set({ outbox: sealed });
    queue = sealed;
    s = Object.assign({}, s, { outbox: sealed });
  }
  let res;
  const started = Date.now();
  try {
    res = await fetch(s.url.replace(/\/$/, "") + "/api/likes", {
      method: "POST",
      headers: {
        authorization: "Bearer " + s.token,
        "content-type": "application/json",
        "x-echolike-api": "4", // this client only ever sends sealed blobs
      },
      body: JSON.stringify({ items: queue }),
    });
  } catch (e) {
    // No timer, no retry loop: the next event that exists (a new capture, an X tab
    // loading, the browser saying it is online again, the page opening, startup)
    // sends this queue.
    await tel("send.unreachable", { ok: false, host: s.url, ms: Date.now() - started, error: String(e.message || e) });
    s.last = { ok: false, error: "unreachable: " + String(e.message || e).slice(0, 100), at: new Date().toISOString() };
    await chrome.storage.local.set({ last: s.last });
    return { ok: false, error: s.last.error, pending: s.outbox.length };
  }
  await tel("send", { ok: res.ok, code: res.status, host: s.url, ms: Date.now() - started, error: res.ok ? null : "HTTP " + res.status });
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
    const j = await res.json().catch(() => null);
    const why = j && j.error ? String(j.error).slice(0, 120) : "inbox HTTP " + res.status;
    s.last = {
      ok: false,
      error: res.status === 400 && j && j.error && /iv \+ ct/.test(j.error) ? "the inbox needs a newer version of this extension" : why,
      at: new Date().toISOString(),
    };
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
  // Only the items actually sent leave the queue: clearing all of it loses any
  // capture that was taken while this request was in flight.
  const sent = new Set(queue.map((i) => i.uid));
  const after = await chrome.storage.local.get({ outbox: [] });
  const left = after.outbox.filter((i) => !sent.has(i.uid));
  await chrome.storage.local.set({ outbox: left, last: s.last });
  telFlush();
  return { ok: true, sent: n, pending: left.length, used: s.last.used, quota: s.last.quota };
}

// Zero-typing setup: the server mints the device token, the extension keeps it.
// One button; no address, no token to copy, nothing to truncate.
async function claimAt(url, quiet) {
  const base = String(url || "").replace(/\/$/, "");
  let cres;
  const started = Date.now();
  try {
    cres = await timed(base + "/api/claim", { method: "POST" }, 5000);
  } catch (e) {
    await tel("claim.unreachable", { ok: false, host: base, ms: Date.now() - started, error: String(e.message || e) });
    return { ok: false, url: base, error: "no answer from " + base };
  }
  const j = await cres.json().catch(() => null);
  await tel("claim", {
    ok: cres.ok,
    code: cres.status,
    host: base,
    ms: Date.now() - started,
    error: cres.ok ? null : (j && j.error) || "HTTP " + cres.status,
  });
  if (cres.status === 404) {
    return {
      ok: false,
      url: base,
      error: "that inbox is older than the extension (no /api/claim) — paste its token in Settings",
    };
  }
  if (!cres.ok || !j || !j.token) {
    return { ok: false, url: base, error: (j && j.error) || "inbox refused the claim (HTTP " + cres.status + ")" };
  }
  await chrome.storage.local.set({ url: base, token: j.token, retryN: 0 });
  if (quiet) return { ok: true, url: base, error: null, pending: 0 };
  const out = await flush(true);
  return { ok: out.ok, url: base, error: out.error || null, pending: out.pending };
}

// "Send everything in this browser": compare the local mirror with what the inbox
// already holds and re-queue whatever is missing. This is the repair path for a
// queue that diverged from the mirror (lost in the old flush race, or captured by
// a version whose outbox was cleared).
async function syncAll() {
  const s = await state();
  if (!s.url || !s.token) return { ok: false, error: "not connected: press Find my inbox first" };
  const base = s.url.replace(/\/$/, "");
  let have = new Set();
  // Signed in? Then the whole account counts, not just this device: two browsers,
  // one inbox.
  const readUrl = s.accountToken ? base + "/api/account/likes?limit=500" : base + "/api/likes?limit=500";
  try {
    const r = await timed(readUrl, { headers: { authorization: "Bearer " + (s.accountToken || s.token) } }, 15000);
    if (r.ok) {
      const j = await r.json().catch(() => null);
      have = new Set(((j && j.items) || []).map((i) => i.uid).filter(Boolean));
    }
  } catch (e) {
    return { ok: false, error: "the inbox did not answer" };
  }
  const queued = new Set(s.outbox.map((i) => i.uid));
  const missing = s.items.filter((i) => i.uid && !have.has(i.uid) && !queued.has(i.uid));
  if (!missing.length) {
    const r = await flush(true);
    return { ok: r.ok, added: 0, pending: r.pending, error: r.error || null };
  }
  const sealed = [];
  for (const it of missing) sealed.push(await seal(it));
  await chrome.storage.local.set({ outbox: s.outbox.concat(sealed).slice(-MAX_ITEMS) });
  const r = await flush(true);
  return { ok: r.ok, added: missing.length, pending: r.pending, error: r.error || null };
}

// Try everything in order and never stop at the first refusal: a local inbox that
// is full, old or mid-restart used to abort the whole attempt, which is how "Find
// my inbox" ended up doing nothing while a perfectly good hosted inbox was one
// step away.
async function discover() {
  const s = await state();
  if (s.url && s.token) {
    // Already connected: "Find my inbox" must still do the useful thing — send.
    const r = await flush(true);
    return { ok: r.ok, url: s.url, already: true, pending: r.pending, error: r.error || null };
  }
  const tried = [];
  for (const url of CANDIDATES.concat(DEFAULT_INBOX ? [DEFAULT_INBOX] : [])) {
    let hres;
    try {
      hres = await timed(url + "/api/health", {});
    } catch (e) {
      continue; // nothing listening there: try the next
    }
    if (!hres.ok) continue;
    const r = await claimAt(url);
    if (r.ok) return r;
    tried.push(url.replace(/^https?:\/\//, "") + ": " + (r.error || "claim refused"));
  }
  return {
    ok: false,
    error: tried.length
      ? "no inbox accepted this browser (" + tried.join("; ") + ")"
      : "nothing answered. Start the inbox on this computer, or press Find my inbox again in a moment",
  };
}

// ---- Account (optional): recovery of access, never of plaintext --------------
// Email + a 6-digit code gets an account token; the account links this device's
// tenant so a reinstall can find its captures again. The key itself can be backed
// up only WRAPPED with a passphrase we derive here: the inbox stores a blob it
// cannot open, and the passphrase never leaves this browser.
const PBKDF2_ITER = 210000;

async function derivePhrase(passphrase, salt, iterations, usage) {
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(passphrase), "PBKDF2", false, [
    "deriveKey",
  ]);
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations, hash: "SHA-256" },
    base,
    { name: "AES-GCM", length: 256 },
    false,
    [usage],
  );
}

async function acctBase() {
  const s = await state();
  return { base: (s.url || DEFAULT_INBOX).replace(/\/$/, ""), s };
}

async function acctCall(path, opts) {
  const { base, s } = await acctBase();
  if (!base) return { ok: false, error: "no inbox yet: like a post first" };
  const auth = (opts && opts.auth) || s.accountToken;
  const headers = { "content-type": "application/json" };
  if (auth) headers.authorization = "Bearer " + auth;
  const r = await timed(
    base + path,
    { method: (opts && opts.method) || "GET", headers, body: opts && opts.body ? JSON.stringify(opts.body) : undefined },
    15000,
  ).catch(() => null);
  if (!r) return { ok: false, error: "the inbox did not answer" };
  const j = await r.json().catch(() => null);
  if (!j) return { ok: false, error: "inbox HTTP " + r.status };
  return j;
}

async function acctStart(email) {
  const j = await acctCall("/api/account/start", { method: "POST", body: { email }, auth: "-" });
  await tel("account.start", { ok: j.ok === true, error: j.ok ? null : j.error, host: DEFAULT_INBOX.replace(/^https?:\/\//, "") });
  if (j.ok) await chrome.storage.local.set({ accountEmail: String(email).trim().toLowerCase() });
  return j;
}

async function acctVerify(email, code) {
  const { s } = await acctBase();
  const j = await acctCall("/api/account/verify", {
    method: "POST",
    body: { email, code },
    auth: s.token || "",
  });
  await tel("account.verify", { ok: j.ok === true, code: j.ok ? 200 : 401, error: j.ok ? null : j.error });
  if (j.ok && j.atoken) await chrome.storage.local.set({ accountToken: j.atoken, accountEmail: j.account.email });
  return j;
}

async function keySave(passphrase) {
  const { s } = await acctBase();
  if (!s.accountToken) return { ok: false, error: "sign in with your email first" };
  if (!passphrase || passphrase.length < 8) return { ok: false, error: "use at least 8 characters" };
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await derivePhrase(passphrase, salt, PBKDF2_ITER, "encrypt");
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(await keyCode()));
  const j = await acctCall("/api/account/key", {
    method: "POST",
    body: { salt: b64(salt), iterations: PBKDF2_ITER, iv: b64(iv), ct: b64(new Uint8Array(ct)) },
  });
  await tel("key.backup", { ok: j.ok === true, error: j.ok ? null : j.error });
  if (j.ok) await chrome.storage.local.set({ keyBackedAt: new Date().toISOString() });
  return j;
}

async function keyRestore(passphrase) {
  const { s } = await acctBase();
  if (!s.accountToken) return { ok: false, error: "sign in with your email first" };
  if (s.outbox.length) return { ok: false, error: "send what is waiting first (" + s.outbox.length + ")" };
  const j = await acctCall("/api/account/key");
  if (!j.ok || !j.backup) return { ok: false, error: j.error || "there is no key backup" };
  const b = j.backup;
  try {
    const key = await derivePhrase(passphrase, unb64(b.salt), b.iterations, "decrypt");
    const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(b.iv) }, key, unb64(b.ct));
    const code = new TextDecoder().decode(plain);
    if (code.length !== 43) return { ok: false, error: "that backup is not a key" };
    await chrome.storage.local.set({ key: code, keyBackedAt: b.updated_at || new Date().toISOString() });
    await tel("key.restore", { ok: true });
    // Whatever this browser captured under its own key is now re-sealed with the
    // account key and pushed, so the two browsers show one list.
    const synced = await syncAll();
    return { ok: true, restored: true, added: synced.added || 0, error: synced.error || null };
  } catch (e) {
    await tel("key.restore", { ok: false, error: "wrong passphrase" });
    return { ok: false, error: "wrong passphrase" };
  }
}

// The importer hands over what it scraped: dozens or hundreds of old likes in one
// go. Anything this browser already has (by kind + post id) is dropped, so running
// an import twice, or importing the likes you already captured live, adds nothing.
async function captureBatch(items, source) {
  try {
    return await captureBatchInner(items, source);
  } catch (e) {
    await tel("import.batch", { ok: false, error: String(e.message || e), detail: "in=" + (items || []).length });
    return { ok: false, error: String(e.message || e) };
  }
}

async function captureBatchInner(items, source) {
  const s = await state();
  const known = new Set(s.items.map((i) => i.kind + "|" + i.id));
  const fresh = [];
  for (const it of items || []) {
    const key = String(it.kind) + "|" + String(it.id);
    if (!it.id || known.has(key)) continue;
    known.add(key);
    it.uid = globalThis.crypto && crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random();
    it.source = source || "import";
    fresh.push(it);
  }
  if (!fresh.length) return { ok: true, added: 0, sent: 0 };
  const sealed = [];
  for (const it of fresh) sealed.push(await seal(it));
  await chrome.storage.local.set({
    items: s.items.concat(fresh).slice(-MAX_ITEMS),
    outbox: s.outbox.concat(sealed).slice(-MAX_ITEMS),
  });
  const r = await flush();
  await tel("import.batch", {
    ok: r.ok,
    code: r.ok ? 200 : null,
    error: r.error || null,
    detail: "in=" + (items || []).length + " fresh=" + fresh.length + " pending=" + (r.pending || 0),
  });
  return { ok: true, added: fresh.length, sent: r.ok && !r.pending ? fresh.length : 0, error: r.error || null };
}

// The importer needs a logged-in X tab: send the command to the one that is open.
let pendingImport = null; // set when we open the list tab: the page's own load starts it

async function listTabs() {
  const tabs = await chrome.tabs.query({ url: ["https://x.com/*", "https://twitter.com/*"] });
  return {
    ok: true,
    tabs: tabs.map((t) => ({ id: t.id, url: t.url || "", title: t.title || "", active: !!t.active })),
  };
}

async function importStart(mode, limit, tabId) {
  const tabs = await chrome.tabs.query({ url: ["https://x.com/*", "https://twitter.com/*"] });
  await tel("import.cmd", {
    ok: true,
    detail: "mode=" + mode + " limit=" + limit + " tabs=" + tabs.length + " urls=" + tabs.map((t) => (t.url || "").replace("https://x.com", "")).join(",").slice(0, 120),
  });
  const wanted = mode === "bookmarks" ? "/i/history" : "/i/history/likes";
  if (!tabs.length) {
    pendingImport = { mode, limit };
    await chrome.tabs.create({
      url: mode === "bookmarks" ? "https://x.com/i/history" : "https://x.com/i/history/likes",
    });
    return { ok: false, needTab: true, error: "opening your list: it starts by itself as soon as the page is ready" };
  }
  // An explicit choice wins; then the tab that is actually the list; then the active one.
  const chosen = m0 => m0;
  const tab =
    (tabId ? tabs.find((t) => t.id === tabId) : null) ||
    tabs.find((t) => (t.url || "").includes(wanted)) ||
    tabs.find((t) => t.active) ||
    tabs[0];
  try {
    const r = await chrome.tabs.sendMessage(tab.id, { type: "import-start", mode, limit });
    return r || { ok: false, error: "that tab did not answer: reload it" };
  } catch (e) {
    const where = (tab.url || "").replace(/^https:\/\/x\.com/, "") || "that tab";
    await tel("import.cmd", {
      ok: false,
      host: tab.url,
      error: "no content script in " + where + ": " + String(e.message || e),
    });
    return {
      ok: false,
      needsReload: true,
      tabId: tab.id,
      tabUrl: tab.url,
      error: "the tab \"" + where + "\" has no EchoLike script yet (it was open before the extension was installed or updated). Reload that tab, or open the list with the button below.",
    };
  }
}

async function importCancel() {
  const tabs = await chrome.tabs.query({ url: ["https://x.com/*", "https://twitter.com/*"] });
  for (const t of tabs) {
    try {
      await chrome.tabs.sendMessage(t.id, { type: "import-cancel" });
    } catch (e) {
      /* a tab without the script is fine */
    }
  }
  return { ok: true };
}

async function capture(item) {
  item.uid = globalThis.crypto && crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
  const s = await state();
  s.items.push(item); // the local copy stays readable: it is the user's own browser
  s.outbox.push(await seal(item)); // what leaves this machine is ciphertext
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
          : m && m.type === "acct-start"
            ? acctStart(m.email)
            : m && m.type === "acct-verify"
              ? acctVerify(m.email, m.code)
              : m && m.type === "key-save"
                ? keySave(m.passphrase)
                : m && m.type === "key-restore"
                  ? keyRestore(m.passphrase)
                  : m && m.type === "forget"
            ? chrome.storage.local.remove(["url", "token"]).then(() => ({ ok: true }))
            : m && m.type === "capture-batch"
              ? captureBatch(m.items, m.source)
              : m && m.type === "tabs"
                ? listTabs()
                : m && m.type === "import-start"
                  ? importStart(m.mode, m.limit, m.tabId)
                : m && m.type === "import-cancel"
                  ? importCancel()
                  : m && m.type === "net-online"
              ? // The browser said the network is back: send what waited, repair what
                // the inbox never received, and flush the diagnostics backlog.
                syncAll()
                  .then((r) => telFlush().then(() => ({ ok: r.ok, error: r.error || null, added: r.added || 0 })))
              : m && m.type === "hello"
                ? // An X tab finished loading: the cheapest honest moment to retry — and,
                  // if an import is waiting for a tab to exist, the moment to start it.
                  (async () => {
                    if (pendingImport) {
                      const { mode, limit } = pendingImport;
                      pendingImport = null;
                      await importStart(mode, limit).catch(() => {});
                    }
                    const r = await flush(true);
                    await telFlush();
                    return { ok: r.ok, pending: r.pending, error: r.error || null };
                  })()
                : m && m.type === "account-info"
              ? acctCall("/api/account")
              : m && m.type === "sync"
              ? syncAll()
              : m && m.type === "tel"
              ? tel(m.action, m.info || {}).then(() => ({ ok: true }))
              : m && m.type === "tel-flush"
              ? telFlush().then(() => ({ ok: true }))
              : m && m.type === "save"
          ? chrome.storage.local.set({ url: String(m.url || ""), token: String(m.token || "") }).then(() => flush(true))
          : m && m.type === "state"
            ? state().then(async (s) => ({
                url: s.url,
                hasToken: !!s.token,
                token: s.token,
                keyCode: await keyCode(),
                accountEmail: s.accountEmail || "",
                accountToken: !!s.accountToken,
                keyBackedAt: s.keyBackedAt || null,
                telemetry: s.telemetry.slice(-40).reverse(),
                telOn: s.tel_on !== false,
                telQueued: s.telq.length,
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

// One page for the whole extension: the toolbar icon opens it (there is no popup).
// The version lives on the icon's own title, because that is the first thing a
// user hovers after installing an update.
function stampVersion() {
  const { version } = chrome.runtime.getManifest();
  chrome.action.setTitle({ title: "EchoLike Lite v" + version + " — open your inbox" });
}
chrome.runtime.onInstalled.addListener((d) => {
  stampVersion();
  telFlush();
  // An update may carry a fix for a queue that diverged: repair it once, silently.
  if (d.reason === "update" || d.reason === "install") syncAll().catch(() => {});
});
chrome.runtime.onStartup.addListener(() => {
  stampVersion();
  telFlush();
  syncAll().catch(() => {});
});
stampVersion();

chrome.action.onClicked.addListener(() => chrome.tabs.create({ url: chrome.runtime.getURL("app.html#inbox") }));
