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
// Rules that keep it honest:
//   * a device token is a random 32-hex secret, stored only as sha256;
//   * the tenant id is derived from the token, never from the request body;
//   * claims are capped per IP per hour, and devices per IP in total;
//   * every capture costs one unit of the monthly free quota (402 when spent);
//   * a body is capped at 256 KB, an item at 16 KB, and 500 items per request.
const API = 3;
const FREE_PER_MONTH = 3000;
const CLAIM_PER_IP_HOUR = 20; // a household or a test suite never needs more; a bot still caps at DEVICES_PER_IP
const DEVICES_PER_IP = 20;
const MAX_BODY = 256 * 1024;
const MAX_ITEM = 16 * 1024;
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
  for (const it of items) {
    // Only the shape is checked. Nothing here can read the content.
    if (!it || !b64ish(it.ct) || !b64ish(it.iv)) return json({ ok: false, error: "items must carry iv + ct" }, 400);
    if (String(it.ct).length > MAX_ITEM) return json({ ok: false, error: "one item is too large" }, 413);
  }

  const used = await usage(env, who.user);
  if (used >= FREE_PER_MONTH) {
    return json({ ok: false, error: "free quota for this month is spent", quota: FREE_PER_MONTH, used }, 402);
  }
  const take = items.slice(0, Math.max(0, FREE_PER_MONTH - used));
  const at = now();
  const stmts = take.map((it) =>
    env.DB.prepare(
      "INSERT INTO likes (user_id, uid, iv, ct, bytes, received_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
    ).bind(who.user, clamp(it.uid, 64), it.iv, it.ct, String(it.ct).length, at),
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
function readHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  const t = h.get('t');
  const k = h.get('k');
  if (t) { token = t; localStorage.setItem('el_token', t); }
  if (k) { key = k; localStorage.setItem('el_key', k); }
  if (location.hash) history.replaceState(null, '', location.pathname);
  return { t, k };
}
readHash();
// An already-open tab that receives a new key must pick it up, not ignore it.
window.addEventListener('hashchange', () => { if (readHash().t || readHash().k) { $('ask').style.display = 'none'; load(); } });
let items = [];
let aes = null;

async function importKey(k) {
  return crypto.subtle.importKey('raw', b64d(k), 'AES-GCM', false, ['decrypt']);
}
async function decrypt(blob) {
  const plain = await crypto.subtle.decrypt({name:'AES-GCM', iv: b64d(blob.iv)}, aes, b64d(blob.ct));
  return JSON.parse(new TextDecoder().decode(plain));
}
function render(rows) {
  const box = $('list');
  box.textContent = '';
  if (!rows.length) { box.innerHTML = '<p class=mut>Nothing yet. Like a post on X.</p>'; return; }
  for (const it of rows) {
    const d = document.createElement('div');
    d.innerHTML = '<b>' + esc(it.kind) + '</b> <a target=_blank rel=noreferrer href="' + esc(it.url) + '">@' + esc(it.handle) + '</a>' +
      (it.ad ? ' <small>ad</small>' : '') +
      (it.text ? '<br><span>' + esc(String(it.text).slice(0, 400)) + '</span>' : '') +
      '<br><small>' + esc(it.clicked_at || it.received_at || '') + '</small>';
    box.appendChild(d);
  }
}
async function load() {
  if (!token) { $('status').innerHTML = '<span class=err>No key for this inbox.</span> Open it from the extension popup: <b>Open my inbox</b>.'; return; }
  $('status').textContent = 'Loading…';
  let r;
  try { r = await fetch('/api/likes?limit=200', {headers:{authorization:'Bearer ' + token}}); }
  catch (e) { $('status').innerHTML = '<span class=err>Network error.</span>'; return; }
  if (r.status === 401) { $('status').innerHTML = '<span class=err>This inbox key is not valid any more.</span>'; return; }
  const body = await r.json();
  const rows = body.items || [];
  if (!key) { $('status').textContent = rows.length + ' encrypted capture(s) waiting.'; $('ask').style.display='block'; return; }
  try { aes = await importKey(key); } catch (e) { $('status').innerHTML = '<span class=err>That recovery code is not valid.</span>'; $('ask').style.display='block'; return; }
  try { items = await Promise.all(rows.map(decrypt)); }
  catch (e) { $('status').innerHTML = '<span class=err>Wrong recovery code: these captures do not decrypt.</span>'; $('ask').style.display='block'; return; }
  $('status').innerHTML = '<span class=ok>' + items.length + '</span> capture(s)' + (body.used!=null ? ' · ' + body.used + '/' + body.quota + ' this month' : '');
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
          free_per_month: FREE_PER_MONTH,
        });
      }
      if (path === "/api/claim" && req.method === "POST") return await claim(env, req);
      if (path === "/api/likes" && req.method === "POST") {
        const who = await tenant(env, req.headers.get("authorization"));
        return who ? await postLikes(env, req, who) : json({ ok: false, error: "unauthorized" }, 401);
      }
      if (path === "/api/likes" && req.method === "GET") {
        const who = await tenant(env, req.headers.get("authorization"));
        if (!who) return json({ ok: false, error: "unauthorized" }, 401);
        const limit = Math.min(200, Math.max(1, Number(url.searchParams.get("limit") || 100)));
        const rows = await env.DB.prepare(
          "SELECT uid, iv, ct, received_at FROM likes WHERE user_id = ?1 ORDER BY id DESC LIMIT ?2",
        )
          .bind(who.user, limit)
          .all();
        return json({ ok: true, user: who.user, items: rows.results || [], used: await usage(env, who.user) });
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
