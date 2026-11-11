// EchoLike inbox — the hosted, multi-tenant inbox behind the extension.
//
// One Cloudflare Worker + one D1 database. Every install that claims becomes its
// own tenant (`u_xxxx`) with its own device token; every row is scoped by
// user_id, so no tenant can read another's captures. Nothing to configure on the
// user's side: the extension claims on first capture.
//
//   GET  /api/health          -> capacity + protocol version (no auth)
//   POST /api/claim           -> {token, user}  open claim, rate-limited per IP
//   POST /api/likes           -> {"items":[...]}  Bearer token, quota-checked
//   GET  /api/likes?limit=100 -> the caller's own captures, JSON (Bearer token)
//   GET  /?t=<token>          -> the caller's own captures, readable page
//
// Multi-tenant rules that keep it honest:
//   * a device token is a random 32-hex secret, stored only as sha256;
//   * the tenant id is derived from the token, never from the request body;
//   * claims are capped per IP per hour, and devices per IP in total;
//   * every capture costs one unit of the monthly free quota (402 when spent);
//   * a request body is capped at 256 KB and a capture at 500 items.
const API = 2;
const FREE_PER_MONTH = 3000;
const CLAIM_PER_IP_HOUR = 5;
const DEVICES_PER_IP = 20;
const MAX_BODY = 256 * 1024;
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

async function tenant(env, auth) {
  const tok = (auth || "").replace(/^Bearer\s+/i, "").trim();
  if (!/^[0-9a-f]{32}$/.test(tok)) return null;
  const row = await env.DB.prepare(
    "SELECT d.user_id FROM devices d WHERE d.token_sha256 = ?1",
  )
    .bind(await sha256(tok))
    .first();
  return row ? { token: tok, user: row.user_id } : null;
}

async function usage(env, user) {
  const m = month();
  const row = await env.DB.prepare("SELECT n FROM usage WHERE user_id = ?1 AND month = ?2").bind(user, m).first();
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
    body = JSON.parse(await req.text() || "{}");
  } catch {
    return json({ ok: false, error: "bad json" }, 400);
  }
  const items = Array.isArray(body.items) ? body.items.slice(0, MAX_ITEMS) : null;
  if (!items) return json({ ok: false, error: "items must be a list" }, 400);

  const used = await usage(env, who.user);
  if (used >= FREE_PER_MONTH) {
    return json({ ok: false, error: "free quota for this month is spent", quota: FREE_PER_MONTH, used }, 402);
  }
  const room = Math.max(0, FREE_PER_MONTH - used);
  const take = items.slice(0, room);
  const at = now();
  const stmts = take.map((it) =>
    env.DB.prepare(
      "INSERT INTO likes (user_id, uid, kind, post_id, handle, url, text, clicked_at, ad, received_at)" +
        " VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
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
      "INSERT INTO usage (user_id, month, n) VALUES (?1, ?2, ?3)" +
        " ON CONFLICT(user_id, month) DO UPDATE SET n = n + ?3",
    ).bind(who.user, month(), take.length),
    env.DB.prepare("UPDATE devices SET last_seen = ?1 WHERE user_id = ?2").bind(at, who.user),
  );
  await env.DB.batch(stmts);
  return json({ ok: true, received: take.length, user: who.user, used: used + take.length, quota: FREE_PER_MONTH });
}

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function page(env, url) {
  const tok = url.searchParams.get("t") || "";
  const who = await tenant(env, "Bearer " + tok);
  if (!who) {
    return new Response(
      "<!doctype html><meta charset=utf-8><title>EchoLike inbox</title>" +
        "<body style='font:16px system-ui;max-width:640px;margin:40px auto;padding:0 16px'>" +
        "<h1>EchoLike inbox</h1><p>This is the hosted inbox. It is empty from here because no key was given.</p>" +
        "<p>Open it from the extension popup: <b>Open my inbox</b> carries your key.</p></body>",
      { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } },
    );
  }
  const rows = await env.DB.prepare(
    "SELECT kind, handle, url, text, clicked_at, ad FROM likes WHERE user_id = ?1 ORDER BY id DESC LIMIT 200",
  )
    .bind(who.user)
    .all();
  const list = (rows.results || [])
    .map(
      (r) =>
        `<li><b>${esc(r.kind)}</b> <a href="${esc(r.url)}" target="_blank" rel="noreferrer">@${esc(r.handle)}</a>` +
        `${r.ad ? " <small>ad</small>" : ""}<br><span>${esc((r.text || "").slice(0, 240))}</span>` +
        `<br><small>${esc(r.clicked_at || "")}</small></li>`,
    )
    .join("");
  const used = await usage(env, who.user);
  return new Response(
    "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>" +
      "<title>My EchoLike inbox</title>" +
      "<style>body{font:15px system-ui;max-width:680px;margin:24px auto;padding:0 14px}" +
      "li{margin:12px 0}small{color:#666}a{color:#1d9bf0}</style>" +
      `<h1>My EchoLike inbox</h1><p>Tenant <code>${esc(who.user)}</code> · ${used} of ${FREE_PER_MONTH} this month.</p>` +
      `<ul>${list || "<li>Nothing yet. Like a post on X.</li>"}</ul>`,
    { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } },
  );
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
    try {
      if (path === "/api/health") {
        return json({ ok: true, server: "echolike-inbox", api: API, claim: "open", free_per_month: FREE_PER_MONTH });
      }
      if (path === "/api/claim" && req.method === "POST") return await claim(env, req);
      if (path === "/api/likes" && req.method === "POST") {
        const who = await tenant(env, req.headers.get("authorization"));
        return who ? await postLikes(env, req, who) : json({ ok: false, error: "unauthorized" }, 401);
      }
      if (path === "/api/likes" && req.method === "GET") {
        const who = await tenant(env, req.headers.get("authorization"));
        if (!who) return json({ ok: false, error: "unauthorized" }, 401);
        const limit = Math.min(200, Math.max(1, Number(url.searchParams.get("limit") || 50)));
        const rows = await env.DB.prepare(
          "SELECT kind, post_id, handle, url, text, clicked_at, ad, received_at FROM likes WHERE user_id = ?1 ORDER BY id DESC LIMIT ?2",
        )
          .bind(who.user, limit)
          .all();
        return json({ ok: true, user: who.user, items: rows.results || [], used: await usage(env, who.user) });
      }
      if (path === "/" && req.method === "GET") return await page(env, url);
      return json({ ok: false, error: "not found" }, 404);
    } catch (e) {
      return json({ ok: false, error: "internal", detail: String(e && e.message).slice(0, 200) }, 500);
    }
  },
};
