// EchoLike Lite — background. Saves every capture locally, forwards to the
// inbox when one is configured. The outbox survives restarts; failed sends
// retry on the next capture, on startup, or from the popup's Retry button.
// No alarms, no polling: the only traffic is the claim the user asks for
// (discover/claim), a send when something is queued, and the health check that
// comes with it.
const MAX_ITEMS = 500;
// Must match `CONTENT_API` in content.js: an import refuses to run on a tab whose
// script speaks an older walk, and reloads it instead.
const CONTENT_API = 8;

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
async function sealWith(code, item) {
  const key = await crypto.subtle.importKey("raw", unb64(code), "AES-GCM", false, ["encrypt"]);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(JSON.stringify(item)));
  return { uid: item.uid, iv: b64(iv), ct: b64(new Uint8Array(ct)) };
}

async function seal(item) {
  return sealWith(await keyCode(), item);
}

// Who this device is, as the inbox sees it: one row, no plaintext, no decryption.
// Needed because "which list am I looking at" cannot be answered from local storage.
async function inboxIdentity(s) {
  if (!s.url || !s.token) return { listId: "", phones: 0 };
  try {
    const r = await timed(
      s.url.replace(/\/$/, "") + "/api/likes?limit=1",
      { headers: { authorization: "Bearer " + s.token } },
      6000,
    );
    if (!r.ok) return { listId: "", phones: 0 };
    const j = await r.json().catch(() => null);
    return { listId: (j && j.user) || "", phones: (j && j.phones) || 1 };
  } catch (e) {
    return { listId: "", phones: 0 };
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
  telSending = (async () => {
    // An event can arrive while a batch is in flight; without this loop it waited
    // for the next user action, which is how a row "went missing" from a run.
    for (let i = 0; i < 3; i++) {
      const left = await telFlushOnce();
      if (!left) break;
    }
  })().finally(() => {
    telSending = null;
  });
  return telSending;
}

async function telFlushOnce() {
  const s = await chrome.storage.local.get({ telq: [], tel_on: true, url: "", token: "" });
  if (!s.tel_on || !s.telq.length) return 0;
  const base = (s.url || DEFAULT_INBOX).replace(/\/$/, "");
  if (!base) return 0;
  const batch = s.telq.slice(-20);
  const headers = { "content-type": "application/json" };
  if (s.token) headers.authorization = "Bearer " + s.token;
  try {
    const r = await timed(base + "/api/telemetry", { method: "POST", headers, body: JSON.stringify({ events: batch }) }, 8000);
    if (r.ok) await chrome.storage.local.set({ telq: s.telq.slice(0, Math.max(0, s.telq.length - batch.length)) });
    const after = await chrome.storage.local.get({ telq: [] });
    return after.telq.length;
  } catch (e) {
    return 0; // offline: keep them queued
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
  // Signed in? Then the whole account counts, not just this device: two browsers,
  // one inbox.
  const readUrl = s.accountToken ? base + "/api/account/likes" : base + "/api/likes";
  const auth = "Bearer " + (s.accountToken || s.token);
  // Read the inbox TO THE END. A single capped page used to lie: captures past the
  // page looked missing, so every repair re-uploaded them as new ones (45 rows of
  // duplicates, and the real captures pushed out of the window the user sees).
  let have = new Set();
  try {
    for (let offset = 0; offset < 5000; ) {
      const r = await timed(readUrl + "?limit=500&offset=" + offset, { headers: { authorization: auth } }, 15000);
      if (!r.ok) throw new Error("HTTP " + r.status);
      const j = await r.json().catch(() => null);
      const batch = (j && j.items) || [];
      for (const it of batch) if (it.uid) have.add(it.uid);
      const total = j && typeof j.total === "number" ? j.total : 0;
      if (!batch.length || have.size >= total) break;
      offset += batch.length;
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

// Send exactly these captures. The page can decrypt, so it is the only side that
// can tell "this post is already in the inbox under another copy" from "this one
// never arrived". The worker cannot: it holds ciphertext and uids.
async function sendUids(uids) {
  const s = await state();
  if (!s.url || !s.token) return { ok: false, error: "not connected: press Find my inbox first" };
  const want = new Set(uids || []);
  const items = s.items.filter((i) => i.uid && want.has(i.uid));
  if (!items.length) return { ok: true, added: 0, pending: s.outbox.length, error: null };
  const queued = new Set(s.outbox.map((i) => i.uid));
  const sealed = [];
  for (const it of items) if (!queued.has(it.uid)) sealed.push(await seal(it));
  if (sealed.length) {
    await chrome.storage.local.set({ outbox: s.outbox.concat(sealed).slice(-MAX_ITEMS) });
  }
  const r = await flush(true);
  return { ok: r.ok, added: sealed.length, pending: r.pending, error: r.error || null };
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

// ---- Shared spaces ----------------------------------------------------------
// A space is a list several people write to. Two rules keep it safe and simple:
//   * joining is by a ONE-TIME, expiring invite (not a permanent shared secret),
//   * the content key belongs to the members: the server stores ciphertext and member
//     ids, and each phone decrypts the whole space with the key it was invited with.
// That is also what makes "who else saved this post" possible without telling the
// server anything about the posts: the members' rows are decrypted here.
const SPACE_KEY_SLOT = { spaces: [] };
const SPACE_CODE = 2; // {v,u,s,t,k,n}: v2 codes are invites, v1 pairs a phone

async function localSpaces() {
  return (await chrome.storage.local.get(SPACE_KEY_SLOT)).spaces || [];
}

async function saveSpaces(list) {
  await chrome.storage.local.set({ spaces: list });
}

async function callAt(base, path, token, opts) {
  const headers = { "content-type": "application/json", authorization: "Bearer " + token };
  const r = await timed(
    String(base).replace(/\/$/, "") + path,
    Object.assign({ method: "GET", headers }, opts || {}),
    20000,
  ).catch(() => null);
  if (!r) return { ok: false, error: "that inbox did not answer" };
  const j = await r.json().catch(() => null);
  if (!j) return { ok: false, error: "HTTP " + r.status };
  return j;
}

async function spaceCreate(name) {
  const s = await state();
  const base = (s.url || DEFAULT_INBOX).replace(/\/$/, "");
  if (!base || !s.token) return { ok: false, error: "connect an inbox first" };
  const j = await callAt(base, "/api/spaces", s.token, {
    method: "POST",
    body: JSON.stringify({ name: String(name || "").trim().slice(0, 60) }),
  });
  if (!j.ok) return j;
  const key = b64(crypto.getRandomValues(new Uint8Array(32)));
  const sp = { id: j.space.id, name: j.space.name, url: base, key, role: "owner", joined_at: j.space.created_at };
  await saveSpaces((await localSpaces()).filter((x) => x.id !== sp.id).concat([sp]));
  await tel("space.create", { ok: true, host: base });
  return { ok: true, space: sp };
}

async function spaceInvite(id) {
  const sp = (await localSpaces()).find((x) => x.id === id);
  if (!sp) return { ok: false, error: "unknown space" };
  const s = await state();
  const j = await callAt(sp.url, "/api/spaces/" + encodeURIComponent(id) + "/invite", s.token, {
    method: "POST",
    body: JSON.stringify({ hours: 24 }),
  });
  if (!j.ok) return { ok: false, error: j.error || "could not create an invitation" };
  const code = b64(
    new TextEncoder().encode(JSON.stringify({ v: SPACE_CODE, u: sp.url, s: sp.id, t: j.token, k: sp.key, n: sp.name || "" })),
  );
  await tel("space.invite", { ok: true, host: sp.url });
  return { ok: true, code, expires_at: j.expires_at, hours: j.hours };
}

async function spaceJoin(code) {
  let o;
  try {
    o = JSON.parse(new TextDecoder().decode(unb64(String(code || "").trim().replace(/\s+/g, ""))));
  } catch (e) {
    return { ok: false, error: "that is not an invite code" };
  }
  if (!o || o.v !== SPACE_CODE || !o.s || !o.t || !o.k) return { ok: false, error: "that is not an invite code" };
  const s = await state();
  const base = String(o.u || s.url || DEFAULT_INBOX).replace(/\/$/, "");
  const j = await callAt(base, "/api/spaces/" + encodeURIComponent(o.s) + "/join", s.token, {
    method: "POST",
    body: JSON.stringify({ token: o.t }),
  });
  if (!j.ok) {
    await tel("space.join", { ok: false, host: base, error: String(j.error || "") });
    return { ok: false, error: String(j.error || "that invitation did not work") };
  }
  const sp = {
    id: o.s,
    name: (j.space && j.space.name) || o.n || "shared space",
    url: base,
    key: o.k,
    role: (j.space && j.space.role) || "member",
    joined_at: j.joined_at || new Date().toISOString(),
  };
  await saveSpaces((await localSpaces()).filter((x) => x.id !== sp.id).concat([sp]));
  await tel("space.join", { ok: true, host: base });
  return { ok: true, space: sp, already: !!j.already };
}

async function spaceList() {
  const s = await state();
  const mine = await localSpaces();
  const out = [];
  for (const sp of mine) {
    // One request per space: the list is small, and the counts stay honest.
    const j = await callAt(sp.url, "/api/spaces/" + encodeURIComponent(sp.id), s.token).catch(() => null);
    if (!j || j.ok === false) {
      out.push(Object.assign({}, sp, { unreachable: true }));
      continue;
    }
    out.push(
      Object.assign({}, sp, {
        name: (j.space && j.space.name) || sp.name,
        role: j.role || sp.role,
        members: (j.members || []).length,
        memberList: (j.members || []).map((m) => ({ user: m.user_id, role: m.role })),
      }),
    );
  }
  return { ok: true, spaces: out, base: (s.url || DEFAULT_INBOX).replace(/\/$/, "") };
}

// The whole space, decrypted here: `items` are the members' captures (one row per post),
// `saved` lists the members who hold each post — the social signal, computed locally.
async function spaceRead(id) {
  const sp = (await localSpaces()).find((x) => x.id === id);
  if (!sp) return { ok: false, error: "unknown space" };
  const s = await state();
  const rows = [];
  let total = 0;
  let members = [];
  for (let offset = 0; offset < 5000; ) {
    const j = await callAt(sp.url, "/api/spaces/" + encodeURIComponent(id) + "/likes?limit=500&offset=" + offset, s.token);
    if (!j.ok) return { ok: false, error: String(j.error || "could not read that space") };
    const batch = j.items || [];
    rows.push(...batch);
    total = j.total || rows.length;
    members = j.members || members;
    if (!batch.length || rows.length >= total) break;
    offset += batch.length;
  }
  const aes = await crypto.subtle.importKey("raw", unb64(sp.key), "AES-GCM", false, ["decrypt"]);
  const items = [];
  let foreign = 0;
  const saved = {};
  const former = {};
  const current = new Set((members || []).map((m) => m.user_id));
  const seenPost = new Set();
  const merged = [];
  for (const b of rows) {
    let it;
    try {
      const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(b.iv) }, aes, unb64(b.ct));
      it = Object.assign(JSON.parse(new TextDecoder().decode(plain)), { received_at: b.received_at, member: b.member });
    } catch (e) {
      foreign += 1;
      continue;
    }
    items.push(it);
    const k = String(it.kind || "") + "|" + String(it.id || it.uid || "");
    // Count only people who are in the space right now; a removed member's capture
    // stays in the space (it was shared), but it no longer speaks for the group.
    if (it.member && current.has(it.member)) {
      if (!saved[k]) saved[k] = [];
      if (saved[k].indexOf(it.member) < 0) saved[k].push(it.member);
    } else if (it.member) {
      former[k] = (former[k] || 0) + 1;
    }
    if (seenPost.has(k)) continue;
    seenPost.add(k);
    merged.push(it);
  }
  return {
    ok: true,
    space: { id: sp.id, name: sp.name, role: sp.role },
    items: merged,
    total: merged.length,
    raw: rows.length,
    foreign,
    members,
    saved,
    former,
  };
}

// Pushing this browser's captures into a space: re-sealed with the space key, so every
// member can read them, while the personal copy keeps its own key.
async function spaceShare(id) {
  const sp = (await localSpaces()).find((x) => x.id === id);
  if (!sp) return { ok: false, error: "unknown space" };
  const s = await state();
  if (!s.items.length) return { ok: true, added: 0, total: 0 };
  const sealed = [];
  for (const it of s.items) sealed.push(await sealWith(sp.key, it));
  let added = 0;
  for (let i = 0; i < sealed.length; i += 100) {
    const j = await callAt(sp.url, "/api/spaces/" + encodeURIComponent(id) + "/likes", s.token, {
      method: "POST",
      body: JSON.stringify({ items: sealed.slice(i, i + 100) }),
    });
    if (!j.ok) return { ok: false, error: String(j.error || "could not share"), added, total: s.items.length };
    added += j.received || 0;
  }
  await tel("space.share", { ok: true, host: sp.url, detail: "added=" + added + " total=" + sealed.length });
  return { ok: true, added, total: s.items.length };
}

async function spaceLeave(id, user) {
  const sp = (await localSpaces()).find((x) => x.id === id);
  if (!sp) return { ok: false, error: "unknown space" };
  const s = await state();
  const j = await callAt(sp.url, "/api/spaces/" + encodeURIComponent(id) + "/leave", s.token, {
    method: "POST",
    body: JSON.stringify(user ? { user } : {}),
  });
  if (!j.ok) return { ok: false, error: String(j.error || "could not leave") };
  if (!user) await saveSpaces((await localSpaces()).filter((x) => x.id !== id));
  return { ok: true, removed: j.removed };
}

// ---- Two phones, one list ---------------------------------------------------
// A pairing code is {url, token, key} in base64url: the list's address, its device
// token and the key that decrypts it. Pasting it makes this phone read and write the
// SAME tenant as the other one, instead of a brand-new tenant nobody else can see —
// which is what "two phones, same account" looked like before, and why the new phone
// showed nothing.
const pairCode = (url, token, key) =>
  b64(new TextEncoder().encode(JSON.stringify({ v: 1, u: url, t: token, k: key })));

function readPairCode(code) {
  let o;
  try {
    o = JSON.parse(new TextDecoder().decode(unb64(String(code).trim().replace(/\s+/g, ""))));
  } catch (e) {
    return null;
  }
  if (!o || !o.u || !o.t || !o.k) return null;
  if (!/^[0-9a-f]{32}$/.test(String(o.t)) || String(o.k).length !== 43) return null;
  return { url: String(o.u).replace(/\/$/, ""), token: String(o.t), key: String(o.k) };
}

async function pair(code) {
  const p = readPairCode(code);
  if (!p) return { ok: false, error: "that is not a pairing code (it is long, one line, and starts with letters)" };
  const s = await state();
  // Talk to that list before adopting it: a code from a dead server must fail here,
  // with the old configuration still in place.
  let h;
  try {
    h = await timed(p.url + "/api/health", {}, 6000);
  } catch (e) {
    return { ok: false, error: "no answer from " + p.url + " — is that inbox reachable from this phone?" };
  }
  if (!h.ok) return { ok: false, error: "that inbox answered HTTP " + h.status };
  // The key has to open what the list already holds, or pairing produces a list of
  // unreadable rows: probe one blob before trusting it.
  let probe = null;
  try {
    const r = await timed(p.url + "/api/likes?limit=1", { headers: { authorization: "Bearer " + p.token } }, 8000);
    if (r.status === 401) return { ok: false, error: "that code's token is not valid any more (401)" };
    if (r.ok) probe = ((await r.json().catch(() => null)) || {}).items?.[0] || null;
  } catch (e) {
    return { ok: false, error: "the other list did not answer" };
  }
  if (probe && probe.ct && probe.iv) {
    try {
      const k = await crypto.subtle.importKey("raw", unb64(p.key), "AES-GCM", false, ["decrypt"]);
      await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(probe.iv) }, k, unb64(probe.ct));
    } catch (e) {
      return { ok: false, error: "that code's key does not open the other phone's captures: they are from another key, not from this list" };
    }
  }
  // Its own device token on that list: one phone can be revoked without touching the
  // other, and the list can honestly say how many phones write to it.
  let token = p.token;
  try {
    const d = await timed(p.url + "/api/devices", { method: "POST", headers: { authorization: "Bearer " + p.token } }, 8000);
    const dj = await d.json().catch(() => null);
    if (d.ok && dj && dj.token) token = dj.token;
  } catch (e) {
    /* an older inbox has no /api/devices: sharing the token still works */
  }
  await chrome.storage.local.set({ url: p.url, token, key: p.key, retryN: 0 });
  await tel("pair", { ok: true, host: p.url });
  // Whatever this phone captured under its own key is now re-sealed with the shared
  // key and pushed, so the two phones show one list and nothing is left behind.
  const synced = await syncAll().catch(() => ({ ok: false, error: "the list did not answer yet" }));
  return { ok: true, url: p.url, added: synced.added || 0, error: synced.error || null };
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
    // Chrome throttles rendering (and X's loader) in a hidden tab, which is exactly
    // how a list yields its first 7 rows and nothing else.
    await chrome.tabs.update(tab.id, { active: true }).catch(() => {});
    const r = await chrome.tabs.sendMessage(tab.id, { type: "import-start", mode, limit });
    if (!r) throw new Error("no answer");
    if (r.api !== CONTENT_API) {
      // The tab is running an older script: reload it and start again by itself.
      pendingImport = { mode, limit };
      await chrome.tabs.reload(tab.id);
      await tel("import.cmd", {
        ok: false,
        host: tab.url,
        error: "stale content script api=" + r.api + " want " + CONTENT_API,
        detail: "reloading the tab and starting again",
      });
      return {
        ok: false,
        needsReload: true,
        tabId: tab.id,
        autoRestart: true,
        error:
          "that tab was running an older EchoLike script (v" + (r.api || "?") + " of " + CONTENT_API +
          "). Reloading it now — the import starts by itself when the page is ready.",
      };
    }
    return r;
  } catch (e) {
    const where = (tab.url || "").replace(/^https:\/\/x\.com/, "") || "that tab";
    await tel("import.cmd", {
      ok: false,
      host: tab.url,
      error: "no content script in " + where + ": " + String(e.message || e),
    });
    pendingImport = { mode, limit };
    await chrome.tabs.reload(tab.id).catch(() => {});
    return {
      ok: false,
      needsReload: true,
      tabId: tab.id,
      tabUrl: tab.url,
      autoRestart: true,
      error:
        "the tab \"" + where + "\" had no EchoLike script yet (it was open before the extension was installed or updated). Reloading it now — the import starts by itself when the page is ready.",
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

// The actions a page can ask for: the circle on x.com opens a tab, and exports the
// user's own mirror. Both are local — no inbox, no network, nothing to configure.
async function exportItems(pick) {
  const s = await state();
  const want = String(pick || "all");
  const items = s.items.filter((it) =>
    want === "likes"
      ? it.kind === "like" || it.kind === "unlike"
      : want === "bookmarks"
        ? it.kind === "bookmark" || it.kind === "unbookmark"
        : true,
  );
  return { ok: true, pick: want, items };
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
                : m && m.type === "open"
            ? chrome.tabs
                .create({ url: chrome.runtime.getURL("app.html#" + (m.page === "settings" ? "settings" : "inbox")) })
                .then(() => ({ ok: true }))
            : m && m.type === "space-create"
              ? spaceCreate(m.name)
            : m && m.type === "space-invite"
              ? spaceInvite(m.id)
            : m && m.type === "space-join"
              ? spaceJoin(m.code)
            : m && m.type === "space-list"
              ? spaceList()
            : m && m.type === "space-read"
              ? spaceRead(m.id)
            : m && m.type === "space-share"
              ? spaceShare(m.id)
            : m && m.type === "space-leave"
              ? spaceLeave(m.id, m.user)
            : m && m.type === "pair"
                ? pair(m.code)
              : m && m.type === "send-uids"
              ? sendUids(m.uids)
            : m && m.type === "export"
              ? exportItems(m.pick)
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
                ...(await inboxIdentity(s)),
                keyCode: await keyCode(),
                accountEmail: s.accountEmail || "",
                accountToken: !!s.accountToken,
                pairCode: s.url && s.token ? pairCode(s.url, s.token, await keyCode()) : "",
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
