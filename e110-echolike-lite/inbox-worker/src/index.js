// EchoLike inbox — the hosted, multi-tenant inbox behind the extension.
//
// One Cloudflare Worker + one D1 database. Every install that claims becomes its
// own tenant (`u_xxxx`) with its own device token; every row is scoped by
// user_id, so no tenant can read another's captures.
//
// ENCRYPTED BY DEFAULT: the extension seals each capture with AES-256-GCM in the
// browser and uploads {uid, iv, ct}. This worker stores opaque ciphertext and its
// operator cannot read a single like. Decryption happens in the reader's browser,
// from `/#t=<token>&k=<key>` — both secrets live in the URL fragment, which is
// never sent to the server, so neither token nor key ever reaches a log.
//
//   GET  /api/health          -> capacity + protocol version (no auth)
//   POST /api/claim           -> {token, user}  open claim, rate-limited per IP
//   POST /api/likes           -> {"items":[{uid,iv,ct}]}  Bearer token, quota-checked
//   GET  /api/likes?limit=100 -> the caller's own blobs, JSON (Bearer token)
//   GET  /                    -> the decrypting reader (static HTML + WebCrypto)
//
//   DIAGNOSTICS (no capture content, ever)
//   POST /api/telemetry        -> {events:[{action, ok, code, ms, error, host, version}]}
//                                 best effort, no auth required, whitelist + caps
//
//   ACCOUNTS (optional, for recovery — capturing never needs one)
//   POST /api/account/start   -> {email} mails a 6-digit code (Resend)
//   POST /api/account/verify  -> {email, code, token?} -> {atoken}, links this device
//   GET  /api/account         -> {email, tenants, captures, has_key}
//   POST /api/account/key     -> stores a key backup WRAPPED WITH A PASSPHRASE
//   GET  /api/account/key     -> hands the wrapped backup back; unusable here
//
// Rules that keep it honest:
//   * a device token is a random 32-hex secret, stored only as sha256;
//   * the tenant id is derived from the token, never from the request body;
//   * claims are capped per IP per hour, and devices per IP in total;
//   * every capture costs one unit of the monthly free quota (402 when spent);
//   * a body is capped at 256 KB, an item at 16 KB, and 500 items per request.
const API = 3;
const FREE_PER_MONTH = 3000;
const CLAIM_PER_IP_HOUR = 20; // a household or a test suite never needs more; a bot still caps at DEVICES_PER_IP
const DEVICES_PER_IP = 50; // one household, office or CGNAT can share an address; the monthly quota still bounds it
const MAX_BODY = 512 * 1024;
const MAX_ITEM = 24 * 1024;
const MAX_ITEMS = 500;
const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "authorization, content-type",
  "access-control-allow-methods": "GET, POST, OPTIONS",
};

const json = (obj, code = 200) =>
  new Response(JSON.stringify(obj), {
    status: code,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...CORS },
  });

const hex = (n) =>
  Array.from(crypto.getRandomValues(new Uint8Array(n)), (b) => b.toString(16).padStart(2, "0")).join("");

async function sha256(s) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(d), (b) => b.toString(16).padStart(2, "0")).join("");
}

const now = () => new Date().toISOString().slice(0, 19) + "Z";
const month = () => new Date().toISOString().slice(0, 7); // YYYY-MM
const clamp = (s, n) => (typeof s === "string" ? s.slice(0, n) : s == null ? null : String(s).slice(0, n));
const b64ish = (s) => typeof s === "string" && /^[A-Za-z0-9+/=_-]{1,16000}$/.test(s);

async function tenant(env, auth) {
  const tok = (auth || "").replace(/^Bearer\s+/i, "").trim();
  if (!/^[0-9a-f]{32}$/.test(tok)) return null;
  const row = await env.DB.prepare("SELECT d.user_id FROM devices d WHERE d.token_sha256 = ?1")
    .bind(await sha256(tok))
    .first();
  return row ? { token: tok, user: row.user_id } : null;
}

async function usage(env, user) {
  const row = await env.DB.prepare("SELECT n FROM usage WHERE user_id = ?1 AND month = ?2").bind(user, month()).first();
  return row ? row.n : 0;
}

async function claim(env, req) {
  const ip = req.headers.get("cf-connecting-ip") || "unknown";
  const ua = clamp(req.headers.get("user-agent"), 160);
  const hourAgo = Math.floor(Date.now() / 1000) - 3600;

  const recent = await env.DB.prepare("SELECT COUNT(*) AS n FROM claims WHERE ip = ?1 AND at > ?2")
    .bind(ip, hourAgo)
    .first();
  if ((recent?.n || 0) >= CLAIM_PER_IP_HOUR) {
    return json({ ok: false, error: "too many claims from this address, try later" }, 429);
  }
  const total = await env.DB.prepare("SELECT COUNT(*) AS n FROM devices WHERE ip = ?1").bind(ip).first();
  if ((total?.n || 0) >= DEVICES_PER_IP) {
    return json({ ok: false, error: "this address has claimed the maximum number of devices" }, 409);
  }

  const user = "u_" + hex(6);
  const device = "d_" + hex(6);
  const token = hex(16);
  const at = now();
  await env.DB.batch([
    env.DB.prepare("INSERT INTO users (id, created_at, ip, ua) VALUES (?1, ?2, ?3, ?4)").bind(user, at, ip, ua),
    env.DB.prepare(
      "INSERT INTO devices (id, user_id, token_sha256, created_at, last_seen, ip, ua) VALUES (?1, ?2, ?3, ?4, ?4, ?5, ?6)",
    ).bind(device, user, await sha256(token), at, ip, ua),
    env.DB.prepare("INSERT INTO claims (ip, at) VALUES (?1, ?2)").bind(ip, Math.floor(Date.now() / 1000)),
  ]);
  return json({ ok: true, token, user, server: "echolike-inbox", api: API });
}

async function postLikes(env, req, who) {
  const len = Number(req.headers.get("content-length") || 0);
  if (len > MAX_BODY) return json({ ok: false, error: "payload too large" }, 413);
  let body;
  try {
    body = JSON.parse((await req.text()) || "{}");
  } catch {
    return json({ ok: false, error: "bad json" }, 400);
  }
  const items = Array.isArray(body.items) ? body.items.slice(0, MAX_ITEMS) : null;
  if (!items) return json({ ok: false, error: "items must be a list" }, 400);
  // A client that says it speaks API 4 must encrypt: no plaintext from it, ever.
  // Older clients (1.1.x) cannot, so their captures are accepted and flagged
  // `legacy` — losing a user's queue to enforce a rule is not a trade worth making.
  const modern = Number(req.headers.get("x-echolike-api") || 0) >= 4;
  for (const it of items) {
    if (!it) return json({ ok: false, error: "items must be objects" }, 400);
    const sealed = b64ish(it.ct) && b64ish(it.iv);
    if (sealed) {
      if (String(it.ct).length > MAX_ITEM) return json({ ok: false, error: "one item is too large" }, 413);
      continue;
    }
    if (modern) return json({ ok: false, error: "items must carry iv + ct" }, 400);
    if (!it.text && !it.url && !it.handle) return json({ ok: false, error: "item has nothing in it" }, 400);
  }

  const used = await usage(env, who.user);
  if (used >= FREE_PER_MONTH) {
    return json({ ok: false, error: "free quota for this month is spent", quota: FREE_PER_MONTH, used }, 402);
  }
  const take = items.slice(0, Math.max(0, FREE_PER_MONTH - used));
  const at = now();
  const stmts = take.map((it) =>
    b64ish(it.ct) && b64ish(it.iv)
      ? env.DB.prepare(
          "INSERT INTO likes (user_id, uid, iv, ct, bytes, received_at, legacy) VALUES (?1, ?2, ?3, ?4, ?5, ?6, 0)",
        ).bind(who.user, clamp(it.uid, 64), it.iv, it.ct, String(it.ct).length, at)
      : env.DB.prepare(
          "INSERT INTO likes (user_id, uid, kind, post_id, handle, url, text, clicked_at, ad, received_at, legacy)" +
            " VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, 1)",
        ).bind(
          who.user,
          clamp(it.uid, 64),
          clamp(it.kind, 20),
          clamp(it.id, 40),
          clamp(it.handle, 80),
          clamp(it.url, 500),
          clamp(it.text, 1400),
          clamp(it.clicked_at, 40),
          it.ad ? 1 : 0,
          at,
        ),
  );
  stmts.push(
    env.DB.prepare(
      "INSERT INTO usage (user_id, month, n) VALUES (?1, ?2, ?3) ON CONFLICT(user_id, month) DO UPDATE SET n = n + ?3",
    ).bind(who.user, month(), take.length),
    env.DB.prepare("UPDATE devices SET last_seen = ?1 WHERE user_id = ?2").bind(at, who.user),
  );
  await env.DB.batch(stmts);
  return json({ ok: true, received: take.length, user: who.user, used: used + take.length, quota: FREE_PER_MONTH });
}

// ---- diagnostics ----------------------------------------------------------
// The point of this endpoint is to answer "he pressed a button and something
// failed — what exactly?". It stores what a request did, never what it carried:
// the fields are whitelisted and truncated here, on the server, so a client
// mistake cannot leak a capture into the log.
const TEL_ACTIONS = /^[a-z][a-z0-9_.:-]{0,40}$/;
const TEL_MAX_EVENTS = 20;
const TEL_MAX_TEXT = 160;

async function telemetry(env, req) {
  const len = Number(req.headers.get("content-length") || 0);
  if (len > 8192) return json({ ok: false, error: "payload too large" }, 413);
  let body;
  try {
    body = JSON.parse((await req.text()) || "{}");
  } catch {
    return json({ ok: false, error: "bad json" }, 400);
  }
  const raw = Array.isArray(body.events) ? body.events.slice(0, TEL_MAX_EVENTS) : null;
  if (!raw) return json({ ok: false, error: "events must be a list" }, 400);

  const ip = req.headers.get("cf-connecting-ip") || "unknown";
  const ipHash = (await sha256("tel:" + ip)).slice(0, 16);
  const who = await tenant(env, req.headers.get("authorization"));
  const at = now();
  const rows = [];
  for (const e of raw) {
    if (!e || typeof e.action !== "string" || !TEL_ACTIONS.test(e.action)) continue;
    rows.push(
      env.DB.prepare(
        "INSERT INTO telemetry (at, ip_hash, user_id, version, action, ok, code, ms, host, error, detail)" +
          " VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
      ).bind(
        at,
        ipHash,
        who ? who.user : null,
        clamp(String(e.version || "").slice(0, 20), 20),
        e.action,
        e.ok === true ? 1 : e.ok === false ? 0 : null,
        Number.isFinite(Number(e.code)) && Number(e.code) > 0 ? Math.min(999, Number(e.code)) : null,
        Number.isFinite(Number(e.ms)) ? Math.min(600000, Math.max(0, Math.round(Number(e.ms)))) : null,
        clamp(String(e.host || "").slice(0, 60), 60),
        e.error ? clamp(String(e.error).slice(0, TEL_MAX_TEXT), TEL_MAX_TEXT) : null,
        e.detail ? clamp(String(e.detail).slice(0, 200), 200) : null,
      ),
    );
  }
  if (!rows.length) return json({ ok: true, stored: 0 });
  await env.DB.batch(rows);
  return json({ ok: true, stored: rows.length });
}

// ---- accounts -------------------------------------------------------------
async function accountOf(env, auth) {
  const tok = (auth || "").replace(/^Bearer\s+/i, "").trim();
  if (!/^[0-9a-f]{32}$/.test(tok)) return null;
  const row = await env.DB.prepare("SELECT a.id, a.email FROM account_tokens t JOIN accounts a ON a.id = t.account_id WHERE t.sha256 = ?1")
    .bind(await sha256(tok))
    .first();
  return row ? { id: row.id, email: row.email } : null;
}

const emailOk = (e) => typeof e === "string" && /^[^\s@]{1,64}@[^\s@]{1,190}\.[A-Za-z]{2,}$/.test(e.trim());

async function sendCode(env, email, code) {
  if (!env.RESEND_API_KEY) return "email is not configured on this inbox yet";
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { authorization: "Bearer " + env.RESEND_API_KEY, "content-type": "application/json" },
    body: JSON.stringify({
      from: env.MAIL_FROM || "EchoLike <hello@echolike.app>",
      to: [email],
      subject: "Your EchoLike inbox code: " + code,
      text:
        "Your code to sign in to your EchoLike inbox: " + code + "\n\n" +
        "It works for 10 minutes. If you did not ask for it, ignore this message.\n\n" +
        "Your likes stay encrypted: this account only restores access to them.",
    }),
  });
  return r.ok ? null : "the mail service refused (" + r.status + ")";
}

async function accountStart(env, req) {
  let body;
  try {
    body = JSON.parse((await req.text()) || "{}");
  } catch {
    return json({ ok: false, error: "bad json" }, 400);
  }
  const email = String(body.email || "").trim().toLowerCase();
  if (!emailOk(email)) return json({ ok: false, error: "that does not look like an email address" }, 400);
  const ip = req.headers.get("cf-connecting-ip") || "unknown";
  const hourAgo = Math.floor(Date.now() / 1000) - 3600;
  const recent = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM login_codes c JOIN accounts a ON a.id = c.account_id WHERE a.email = ?1 AND c.expires_at > ?2",
  )
    .bind(email, hourAgo)
    .first();
  if ((recent?.n || 0) >= 5) return json({ ok: false, error: "too many codes for this address, try later" }, 429);

  let acc = await env.DB.prepare("SELECT id FROM accounts WHERE email = ?1").bind(email).first();
  if (!acc) {
    const id = "a_" + hex(6);
    await env.DB.prepare("INSERT INTO accounts (id, email, created_at) VALUES (?1, ?2, ?3)")
      .bind(id, email, now())
      .run();
    acc = { id };
  }
  const code = String(100000 + (crypto.getRandomValues(new Uint32Array(1))[0] % 900000));
  await env.DB.prepare("INSERT INTO login_codes (account_id, code_sha256, expires_at, ip) VALUES (?1, ?2, ?3, ?4)")
    .bind(acc.id, await sha256(code), Math.floor(Date.now() / 1000) + 600, ip)
    .run();
  // A local/dev deployment returns the code instead of mailing it; production
  // has no such flag and can never read a code back.
  const dev = env.ECHO_DEV_CODE === "1";
  const why = dev ? null : await sendCode(env, email, code);
  if (why) return json({ ok: false, error: why }, 503);
  return json(dev ? { ok: true, code, dev: true } : { ok: true, sent: true });
}

async function accountVerify(env, req) {
  let body;
  try {
    body = JSON.parse((await req.text()) || "{}");
  } catch {
    return json({ ok: false, error: "bad json" }, 400);
  }
  const email = String(body.email || "").trim().toLowerCase();
  const code = String(body.code || "").replace(/\D/g, "");
  if (!emailOk(email) || code.length !== 6) return json({ ok: false, error: "email and a 6-digit code are needed" }, 400);
  const acc = await env.DB.prepare("SELECT id FROM accounts WHERE email = ?1").bind(email).first();
  if (!acc) return json({ ok: false, error: "wrong code" }, 401);
  const hit = await env.DB.prepare(
    "SELECT rowid FROM login_codes WHERE account_id = ?1 AND code_sha256 = ?2 AND used = 0 AND expires_at > ?3",
  )
    .bind(acc.id, await sha256(code), Math.floor(Date.now() / 1000))
    .first();
  if (!hit) return json({ ok: false, error: "wrong or expired code" }, 401);
  await env.DB.prepare("UPDATE login_codes SET used = 1 WHERE rowid = ?1").bind(hit.rowid).run();

  const atoken = hex(16);
  await env.DB.prepare("INSERT INTO account_tokens (sha256, account_id, created_at, last_seen) VALUES (?1, ?2, ?3, ?3)")
    .bind(await sha256(atoken), acc.id, now())
    .run();
  // Attach the calling device's tenant, so a reinstall can find its captures again.
  const dev = await tenant(env, req.headers.get("authorization"));
  if (dev) {
    await env.DB.prepare("INSERT OR IGNORE INTO account_tenants (account_id, user_id, linked_at) VALUES (?1, ?2, ?3)")
      .bind(acc.id, dev.user, now())
      .run();
  }
  return json({ ok: true, account: { id: acc.id, email }, atoken });
}

async function accountSummary(env, who) {
  const tenants = await env.DB.prepare("SELECT user_id FROM account_tenants WHERE account_id = ?1").bind(who.id).all();
  const ids = (tenants.results || []).map((r) => r.user_id);
  let captures = 0;
  for (const id of ids) {
    const row = await env.DB.prepare("SELECT COUNT(*) AS n FROM likes WHERE user_id = ?1").bind(id).first();
    captures += row?.n || 0;
  }
  const kb = await env.DB.prepare("SELECT updated_at FROM key_backups WHERE account_id = ?1").bind(who.id).first();
  return json({
    ok: true,
    account: { id: who.id, email: who.email },
    tenants: ids,
    captures,
    has_key: !!kb,
    key_updated_at: kb ? kb.updated_at : null,
  });
}

// The account is the unit of reading: every device it owns, newest first. Each
// blob is still sealed per device key, so the reader dedupes by (kind, id) after
// decrypting — the same like captured in two browsers is one like.
async function accountLikes(env, url, who) {
  const limit = Math.min(500, Math.max(1, Number(url.searchParams.get("limit") || 200)));
  const rows = await env.DB.prepare(
    "SELECT l.uid, l.iv, l.ct, l.text, l.handle, l.url, l.kind, l.clicked_at, l.ad, l.legacy, l.received_at" +
      " FROM likes l JOIN account_tenants t ON t.user_id = l.user_id" +
      " WHERE t.account_id = ?1 ORDER BY l.id DESC LIMIT ?2",
  )
    .bind(who.id, limit)
    .all();
  const total = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM likes l JOIN account_tenants t ON t.user_id = l.user_id WHERE t.account_id = ?1",
  )
    .bind(who.id)
    .first();
  const tenants = await env.DB.prepare("SELECT user_id FROM account_tenants WHERE account_id = ?1").bind(who.id).all();
  return json({
    ok: true,
    account: who.id,
    tenants: (tenants.results || []).map((r) => r.user_id),
    items: rows.results || [],
    total: total?.n || 0,
    quota: FREE_PER_MONTH,
  });
}

async function accountKey(env, req, who) {
  if (req.method === "GET") {
    const row = await env.DB.prepare("SELECT salt, iterations, iv, ct, updated_at FROM key_backups WHERE account_id = ?1")
      .bind(who.id)
      .first();
    return row ? json({ ok: true, backup: row }) : json({ ok: false, error: "no key backup yet" }, 404);
  }
  let body;
  try {
    body = JSON.parse((await req.text()) || "{}");
  } catch {
    return json({ ok: false, error: "bad json" }, 400);
  }
  const iterations = Number(body.iterations || 0);
  if (!b64ish(body.salt) || !b64ish(body.iv) || !b64ish(body.ct) || iterations < 100000 || String(body.ct).length > 4096) {
    return json({ ok: false, error: "that is not a wrapped key" }, 400);
  }
  await env.DB.prepare(
    "INSERT INTO key_backups (account_id, salt, iterations, iv, ct, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6)" +
      " ON CONFLICT(account_id) DO UPDATE SET salt = ?2, iterations = ?3, iv = ?4, ct = ?5, updated_at = ?6",
  )
    .bind(who.id, body.salt, iterations, body.iv, body.ct, now())
    .run();
  return json({ ok: true, stored: true });
}

// The reader: no secret in the request, everything is decrypted in the browser.
const PAGE = `<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>My EchoLike inbox</title>
<style>
body{font:15px system-ui;max-width:680px;margin:24px auto;padding:0 14px;color:#111}
h1{font-size:20px;margin:0 0 4px}small{color:#666}a{color:#1d9bf0}
#list div{border-top:1px solid #eee;padding:8px 0}
input{font:inherit;width:100%;box-sizing:border-box;padding:8px;border:1px solid #ccc;border-radius:8px}
button{font:inherit;padding:8px 12px;border-radius:8px;border:1px solid #ccc;background:#fff;cursor:pointer}
.ok{color:#00875a}.err{color:#d0021b}.mut{color:#666;font-size:13px}
</style>
<h1>My EchoLike inbox</h1>
<div id=status class=mut>…</div>
<div id=ask style="display:none">
  <p>Paste your recovery code to decrypt this inbox in your browser:</p>
  <input id=code placeholder="recovery code" autocomplete=off spellcheck=false>
  <p><button id=go>Decrypt</button></p>
</div>
<p class=mut>Everything below is decrypted here, in your browser. The server only stores encrypted blobs and cannot read them.</p>
<p><button id=export style="display:none">Download as JSON</button></p>
<div id=list></div>
<script>
const $ = (id) => document.getElementById(id);
const b64d = (s) => { let t = s.replace(/-/g,'+').replace(/_/g,'/'); while (t.length % 4) t += '='; const b = atob(t); const u = new Uint8Array(b.length); for (let i=0;i<b.length;i++) u[i]=b.charCodeAt(i); return u; };
const esc = (s) => String(s==null?"":s).replace(/[&<>"']/g, (c)=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
// Secrets ride in the fragment: never sent to the server, never in a log.
let token = localStorage.getItem('el_token') || '';
let key = localStorage.getItem('el_key') || '';
let atoken = localStorage.getItem('el_atoken') || '';
function readHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  const t = h.get('t');
  const k = h.get('k');
  const a = h.get('a');
  if (t) { token = t; localStorage.setItem('el_token', t); }
  if (k) { key = k; localStorage.setItem('el_key', k); }
  if (a) { atoken = a; localStorage.setItem('el_atoken', a); }
  if (location.hash) history.replaceState(null, '', location.pathname);
  return { t, k, a };
}
readHash();
// An already-open tab that receives a new key must pick it up, not ignore it.
window.addEventListener('hashchange', () => { const h = readHash(); if (h.t || h.k || h.a) { $('ask').style.display = 'none'; load(); } });
let items = [];
let aes = null;

async function importKey(k) {
  return crypto.subtle.importKey('raw', b64d(k), 'AES-GCM', false, ['decrypt']);
}
async function decrypt(blob) {
  const plain = await crypto.subtle.decrypt({name:'AES-GCM', iv: b64d(blob.iv)}, aes, b64d(blob.ct));
  return JSON.parse(new TextDecoder().decode(plain));
}
const fmtN = (n) => (n == null ? '–' : n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'K' : String(n));
// Counts and dates of one capture, for the reader.
function countsLine(it) {
  const c = it.counts || {};
  const bits = [['replies', c.replies], ['reposts', c.reposts], ['likes', c.likes], ['bookmarks', c.bookmarks], ['views', c.views]]
    .filter(([, v]) => v != null)
    .map(([k, v]) => fmtN(v) + ' ' + k);
  if (it.published_at) bits.push('published ' + new Date(it.published_at).toLocaleString());
  if (it.media) bits.push(it.media + ' media');
  return bits.length ? '<br><small>' + esc(bits.join(' · ')) + '</small>' : '';
}

function render(rows) {
  const box = $('list');
  box.textContent = '';
  if (!rows.length) { box.innerHTML = '<p class=mut>Nothing yet. Like a post on X.</p>'; return; }
  for (const it of rows) {
    const d = document.createElement('div');
    try {
      d.innerHTML = '<b>' + esc(it.kind) + '</b> <a target=_blank rel=noreferrer href="' + esc(it.url) + '">@' + esc(it.handle) + '</a>' +
        (it.ad ? ' <small>ad</small>' : '') +
        countsLine(it) +
        (it.text ? '<br><span>' + esc(String(it.text).slice(0, 400)) + '</span>' : '') +
        '<br><small>' + esc(new Date(it.clicked_at || it.received_at || 0).toLocaleString()) + '</small>';
    } catch (e) {
      // one malformed record must never empty the list
      d.textContent = (it && it.kind) || 'capture';
    }
    box.appendChild(d);
  }
}
async function load() {
  if (!token && !atoken) { $('status').innerHTML = '<span class=err>No key for this inbox.</span> Open it from the extension: <b>Open on echolike.app</b>.'; return; }
  $('status').textContent = 'Loading…';
  let r;
  const url = atoken ? '/api/account/likes?limit=200' : '/api/likes?limit=200';
  try { r = await fetch(url, {headers:{authorization:'Bearer ' + (atoken || token)}}); }
  catch (e) { $('status').innerHTML = '<span class=err>Network error.</span>'; return; }
  if (r.status === 401) { $('status').innerHTML = '<span class=err>This inbox key is not valid any more.</span>'; return; }
  const body = await r.json();
  const rows = body.items || [];
  if (!key) { $('status').textContent = rows.length + ' encrypted capture(s) waiting.'; $('ask').style.display='block'; return; }
  try { aes = await importKey(key); } catch (e) { $('status').innerHTML = '<span class=err>That recovery code is not valid.</span>'; $('ask').style.display='block'; return; }
  try {
    const all = await Promise.all(rows.map(decrypt));
    // Same X account in two browsers: one like, one row.
    const seen = new Set();
    items = all.filter((it) => { const k = (it.kind||'')+'|'+(it.id||it.uid||''); if (seen.has(k)) return false; seen.add(k); return true; });
  }
  catch (e) { $('status').innerHTML = '<span class=err>Wrong recovery code: these captures do not decrypt.</span>'; $('ask').style.display='block'; return; }
  $('status').innerHTML = '<span class=ok>' + (body.total!=null ? body.total : items.length) + '</span> capture(s) in this inbox' +
    (body.used!=null && body.quota ? ' · ' + body.used + '/' + body.quota + ' this month' : '') +
    (items.length < (body.total||0) ? ' · showing the newest ' + items.length : '');
  $('export').style.display = 'inline-block';
  render(items);
}
$('go').onclick = () => {
  const v = $('code').value.trim();
  if (!v) return;
  key = v; localStorage.setItem('el_key', v);
  $('ask').style.display = 'none';
  load();
};
$('export').onclick = () => {
  const blob = new Blob([JSON.stringify(items, null, 1)], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'echolike-inbox.json'; a.click();
};
load();
</script>`;

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
    try {
      if (path === "/api/health") {
        return json({
          ok: true,
          server: "echolike-inbox",
          api: API,
          claim: "open",
          encryption: "aes-256-gcm",
          min_client_api: 4,
          accounts: "email",
          email_configured: !!env.RESEND_API_KEY,
          free_per_month: FREE_PER_MONTH,
        });
      }
      if (path === "/api/claim" && req.method === "POST") return await claim(env, req);
      if (path === "/api/telemetry" && req.method === "POST") return await telemetry(env, req);
      if (path.startsWith("/api/account")) {
        const who = await accountOf(env, req.headers.get("authorization"));
        if (path === "/api/account/start" && req.method === "POST") return await accountStart(env, req);
        if (path === "/api/account/verify" && req.method === "POST") return await accountVerify(env, req);
        if (!who) return json({ ok: false, error: "unauthorized" }, 401);
        if (path === "/api/account" && req.method === "GET") return await accountSummary(env, who);
        if (path === "/api/account/likes" && req.method === "GET") return await accountLikes(env, url, who);
        if (path === "/api/account/key") return await accountKey(env, req, who);
        return json({ ok: false, error: "not found" }, 404);
      }
      if (path === "/api/likes" && req.method === "POST") {
        const who = await tenant(env, req.headers.get("authorization"));
        return who ? await postLikes(env, req, who) : json({ ok: false, error: "unauthorized" }, 401);
      }
      if (path === "/api/likes" && req.method === "GET") {
        const who = await tenant(env, req.headers.get("authorization"));
        if (!who) return json({ ok: false, error: "unauthorized" }, 401);
        const limit = Math.min(200, Math.max(1, Number(url.searchParams.get("limit") || 100)));
        const rows = await env.DB.prepare(
          "SELECT uid, iv, ct, text, handle, url, kind, clicked_at, ad, legacy, received_at" +
            " FROM likes WHERE user_id = ?1 ORDER BY id DESC LIMIT ?2",
        )
          .bind(who.user, limit)
          .all();
        const total = await env.DB.prepare("SELECT COUNT(*) AS n FROM likes WHERE user_id = ?1").bind(who.user).first();
        return json({
          ok: true,
          user: who.user,
          items: rows.results || [],
          total: total?.n || 0,
          used: await usage(env, who.user),
          quota: FREE_PER_MONTH,
        });
      }
      if (path === "/" && req.method === "GET") {
        return new Response(PAGE, {
          headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
        });
      }
      return json({ ok: false, error: "not found" }, 404);
    } catch (e) {
      return json({ ok: false, error: "internal", detail: String(e && e.message).slice(0, 200) }, 500);
    }
  },
};
