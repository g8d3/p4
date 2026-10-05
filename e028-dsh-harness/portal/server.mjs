// dsh portal: password + passkey (WebAuthn) login for the DeepSeek Harness UI.
// No terminal needed: log in from a browser, press "Open dsh".
//
// Why passkeys need a hostname: WebAuthn rpId must be a real hostname, never
// a bare IP. This portal's public name is the tailnet MagicDNS host
// (see needs.json: public_host). Passkey login/registration only work when
// the portal is opened via https://<public_host>:<ts_portal_port>; the LAN-IP
// URL keeps working with the shared password + dsh token flow.
//
// Accounts: the first registered user becomes admin. Later users join via
// single-use invite links created by an admin. The shared password stays as
// break-glass recovery. Users are stored in USERS_FILE (0600, gitignored).
// Stdlib only (node >= 18).
import { createServer } from "node:https";
import { readFileSync, writeFileSync, existsSync, chmodSync, renameSync } from "node:fs";
import { scryptSync, timingSafeEqual, randomBytes, randomUUID } from "node:crypto";
import { networkInterfaces } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { b64urlToBuf, bufToB64url, verifyRegistration, verifyAssertion } from "./webauthn.mjs";

const DIR = dirname(fileURLToPath(import.meta.url));
let NEEDS = {};
try { NEEDS = JSON.parse(readFileSync(resolve(DIR, "../needs.json"), "utf8")); } catch {}
const PORTAL_PORT = Number(process.env.PORTAL_PORT ?? NEEDS?.ports?.portal ?? 8090);
const PUBLIC_HOST = process.env.PUBLIC_HOST ?? NEEDS?.public_host ?? "localhost";
const TS_PORTAL_PORT = Number(process.env.TS_PORTAL_PORT ?? NEEDS?.ts_portal_port ?? 9443);
const TS_DSH_PORT = Number(process.env.TS_DSH_PORT ?? NEEDS?.ts_dsh_port ?? 9444);
const TLS_PORT = Number(process.env.DSH_TLS_PORT ?? NEEDS?.ports?.lan_tls ?? 8443);
const LOG_PATH = resolve(DIR, process.env.DSH_LOG ?? "../log/dsh.log");
const PEM_PATH = resolve(DIR, process.env.DSH_PEM ?? "../cert/dsh.pem");
const PASS_FILE = resolve(DIR, process.env.PASS_FILE ?? "./.pass.json");
const USERS_FILE = resolve(DIR, process.env.USERS_FILE ?? "./users.json");
const RP_ID = PUBLIC_HOST;
const ORIGINS = [`https://${PUBLIC_HOST}:${TS_PORTAL_PORT}`];
const SESSION_TTL_MS = 12 * 3600 * 1000;

// ---------- helpers ----------
function lanHost() {
  if (process.env.DSH_LAN_HOST) return process.env.DSH_LAN_HOST;
  for (const ifs of Object.values(networkInterfaces())) {
    for (const i of ifs ?? []) {
      if (i.family === "IPv4" && !i.internal && !i.address.startsWith("172.")) return i.address;
    }
  }
  for (const ifs of Object.values(networkInterfaces())) {
    for (const i of ifs ?? []) if (i.family === "IPv4" && !i.internal) return i.address;
  }
  return "127.0.0.1";
}
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function readBody(req, limit = 65536) {
  return new Promise((res, rej) => {
    let n = 0; const chunks = [];
    req.on("data", (c) => { n += c.length; if (n > limit) { rej(new Error("too large")); req.destroy(); } else chunks.push(c); });
    req.on("end", () => res(Buffer.concat(chunks).toString("utf8")));
    req.on("error", rej);
  });
}
async function readJson(req) { return JSON.parse(await readBody(req)); }

// ---------- password (break-glass recovery) ----------
function readPass() {
  if (!existsSync(PASS_FILE)) return null;
  return JSON.parse(readFileSync(PASS_FILE, "utf8"));
}
function verifyPassword(password, rec) {
  try {
    const h = scryptSync(password, Buffer.from(rec.salt, "hex"), 64);
    const e = Buffer.from(rec.hash, "hex");
    return h.length === e.length && timingSafeEqual(h, e);
  } catch { return false; }
}
function setPassword(password) {
  const salt = randomBytes(16).toString("hex");
  const hash = scryptSync(password, Buffer.from(salt, "hex"), 64).toString("hex");
  writeFileSync(PASS_FILE, JSON.stringify({ salt, hash }, null, 2), { mode: 0o600 });
  try { chmodSync(PASS_FILE, 0o600); } catch {}
}

// ---------- users ----------
function loadUsers() {
  if (!existsSync(USERS_FILE)) return { users: [], invites: [] };
  return JSON.parse(readFileSync(USERS_FILE, "utf8"));
}
function saveUsers(db) {
  const tmp = USERS_FILE + ".tmp";
  writeFileSync(tmp, JSON.stringify(db, null, 2), { mode: 0o600 });
  try { chmodSync(tmp, 0o600); } catch {}
  renameSync(tmp, USERS_FILE);
}
const findUser = (db, id) => db.users.find((u) => u.id === id);
const findByCred = (db, credId) => db.users.find((u) => u.credentials.some((c) => c.credId === credId));
const validName = (n) => /^[a-zA-Z0-9._-]{2,32}$/.test(n ?? "");

// ---------- sessions / rate limit ----------
const sessions = new Map(); // sid -> {exp, uid, method}
const pending = new Map();  // id -> {exp, kind, ...}
const attempts = new Map();
setInterval(() => {
  const now = Date.now();
  for (const [k, v] of sessions) if (v.exp < now) sessions.delete(k);
  for (const [k, v] of pending) if (v.exp < now) pending.delete(k);
}, 60_000).unref();
function rateLimited(ip) {
  const now = Date.now();
  const ts = (attempts.get(ip) ?? []).filter((t) => now - t < 60_000);
  ts.push(now); attempts.set(ip, ts);
  return ts.length > 12;
}
function issueSession(uid, method) {
  const sid = randomUUID();
  sessions.set(sid, { exp: Date.now() + SESSION_TTL_MS, uid, method });
  return sid;
}
function sessionOf(req) {
  const m = (req.headers.cookie ?? "").match(/dsh-portal=([A-Za-z0-9-]+)/);
  if (!m) return null;
  const s = sessions.get(m[1]);
  if (!s || s.exp < Date.now()) { sessions.delete(m[1]); return null; }
  return { sid: m[1], ...s };
}
function isAdmin(db, sess) {
  if (!sess) return false;
  if (sess.uid === "recovery") return true;
  return !!findUser(db, sess.uid)?.admin;
}
function reqHost(req) { return (req.headers.host ?? "").split(":")[0].toLowerCase(); }
const isPublicHost = (req) => reqHost(req) === PUBLIC_HOST.toLowerCase();

// ---------- dsh token ----------
function dshToken() {
  try {
    const log = readFileSync(LOG_PATH, "utf8");
    const m = log.match(/token=([A-Za-z0-9_-]+)/g);
    return m ? m[m.length - 1].slice(6) : null;
  } catch { return null; }
}
function dshTarget(req) {
  const token = dshToken();
  if (!token) return null;
  const base = isPublicHost(req) ? `https://${PUBLIC_HOST}:${TS_DSH_PORT}` : `https://${lanHost()}:${TLS_PORT}`;
  return `${base}/?token=${encodeURIComponent(token)}`;
}

// ---------- pages ----------
const css = `<style>body{font-family:system-ui,sans-serif;max-width:28rem;margin:3rem auto;padding:0 1rem}input,button{font-size:1rem;padding:.5rem;margin:.25rem 0;width:100%;box-sizing:border-box}button{cursor:pointer}table{width:100%;border-collapse:collapse;font-size:.9rem}td,th{border:1px solid #ccc;padding:.25rem .5rem;text-align:left}.err{color:#b00}.ok{color:#0a0}.small{font-size:.85rem;color:#555}form.inline{display:inline}form.inline button{width:auto;padding:.2rem .6rem;font-size:.85rem}</style>`;
const wkjs = `<script>
const eb=(s)=>Uint8Array.from(atob(s.replace(/-/g,"+").replace(/_/g,"/")),c=>c.charCodeAt(0));
const be=(b)=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\\+/g,"-").replace(/\\//g,"_").replace(/=+$/,"");
async function post(p,o){const r=await fetch(p,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(o)});const t=await r.json();if(!r.ok)throw new Error(t.error||("HTTP "+r.status));return t;}
async function pkLogin(){
  try{
    const name=document.getElementById("pkname").value.trim();
    const o=await post("/wk/login-options",{username:name||undefined});
    const cred=await navigator.credentials.get({publicKey:{...o.options,challenge:eb(o.options.challenge),allowCredentials:(o.options.allowCredentials||[]).map(c=>({...c,id:eb(c.id)}))}});
    const r=await post("/wk/login-verify",{loginId:o.loginId,id:cred.id,response:{authenticatorData:be(cred.response.authenticatorData),clientDataJSON:be(cred.response.clientDataJSON),signature:be(cred.response.signature),userHandle:cred.response.userHandle?be(cred.response.userHandle):null}});
    location.href="/";
  }catch(e){document.getElementById("msg").textContent="Passkey failed: "+e.message;}
}
async function pkRegister(isAdd){
  try{
    const name=document.getElementById("regname").value.trim();
    const inv=new URLSearchParams(location.search).get("invite");
    const url=isAdd?"/wk/add-key-options":"/wk/register-options";
    const o=await post(url,isAdd?{label:document.getElementById("keylabel").value.trim()||undefined}:{username:name,invite:inv||undefined});
    const cred=await navigator.credentials.create({publicKey:{...o.options,challenge:eb(o.options.challenge),user:{...o.options.user,id:eb(o.options.user.id)},excludeCredentials:(o.options.excludeCredentials||[]).map(c=>({...c,id:eb(c.id)}))}});
    const vurl=isAdd?"/wk/add-key-verify":"/wk/register-verify";
    await post(vurl,{regId:o.regId,id:cred.id,response:{attestationObject:be(cred.response.attestationObject),clientDataJSON:be(cred.response.clientDataJSON)},label:isAdd?(document.getElementById("keylabel").value.trim()||undefined):undefined});
    location.href="/";
  }catch(e){document.getElementById("msg").textContent="Registration failed: "+e.message;}
}
</script>`;

function loginPage(msg = "") {
  return `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>dsh portal</title>${css}</head><body>
<h1>dsh portal</h1><p id="msg" class="err">${esc(msg)}</p>
<h2>Passkey</h2><input id="pkname" placeholder="Username (optional)" autocomplete="username"><button onclick="pkLogin()">Log in with passkey</button>
<p class="small">No account yet? <a href="/register">Create one</a> (first account becomes admin; later ones need an invite).</p>
<hr><h2>Password (recovery)</h2><form method="POST" action="/login"><input type="password" name="password" placeholder="Recovery password" autocomplete="current-password" required><button type="submit">Log in</button></form>
${wkjs}</body></html>`;
}
function homePage(db, sess, msg = "") {
  const pub = isPublicHost.current;
  const me = sess.uid === "recovery" ? null : findUser(db, sess.uid);
  const keys = me ? me.credentials.map((c) => `<tr><td>${esc(c.label || c.credId.slice(0, 10) + "…")}</td><td class="small">${esc(c.created.slice(0, 10))}</td><td><form class="inline" method="POST" action="/account/remove-key"><input type="hidden" name="credId" value="${esc(c.credId)}"><button>remove</button></form></td></tr>`).join("") : "";
  return `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>dsh portal</title>${css}</head><body>
<h1>dsh portal</h1>${msg ? `<p class="ok">${esc(msg)}</p>` : ""}
<p class="small">Signed in as <b>${esc(me ? me.name + (me.admin ? " (admin)" : "") : "recovery")}</b> via ${esc(sess.method)}.</p>
<form method="GET" action="/open"><button type="submit">Open dsh</button></form>
${pub ? "" : `<p class="small">Tip: passkeys and the stable address live at <b>https://${esc(PUBLIC_HOST)}:${TS_PORTAL_PORT}</b> (this LAN-IP page keeps working with the password flow).</p>`}
${me ? `<hr><h2>Your passkeys</h2><table><tr><th>key</th><th>added</th><th></th></tr>${keys || `<tr><td colspan="3\" class=\"small\">none yet</td></tr>`}</table>
<h3>Add this device</h3><input id="keylabel" placeholder="Label, e.g. pixel-8"><button onclick="pkRegister(true)">Register passkey on this device</button><p id="msg" class="err"></p>${wkjs}` : ""}
${isAdmin(db, sess) ? `<hr><p><a href=\"/admin\">Admin: users &amp; invites</a></p>` : ""}
<hr><h2>Change recovery password</h2><form method="POST" action="/change"><input type="password" name="current" placeholder="Current password" autocomplete="current-password" required><input type="password" name="next" placeholder="New password (min 12 chars)" autocomplete="new-password" required><button type="submit">Change</button></form>
<hr><form method="POST" action="/logout"><button type="submit">Log out</button></form></body></html>`;
}
function registerPage(db, invite, msg = "") {
  const firstRun = db.users.length === 0;
  const inv = invite ? db.invites.find((i) => i.token === invite && !i.usedBy) : null;
  let body;
  if (!firstRun && !inv) {
    body = `<p class="err">${esc(msg || "You need a valid invite link — ask the admin.")}</p>`;
  } else {
    body = `${msg ? `<p class="err">${esc(msg)}</p>` : ""}<p class="small">${firstRun ? "No users yet — this account becomes <b>admin</b>." : "Invite accepted — pick a username."}</p>
<input id="regname" placeholder="Username (letters, digits, . _ -)" autocomplete="username"><button onclick="pkRegister(false)">Create account with passkey</button><p id="msg" class="err"></p>${wkjs}`;
  }
  return `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>dsh portal — register</title>${css}</head><body><h1>Create account</h1>${body}<p><a href="/">Back to login</a></p></body></html>`;
}
function adminPage(db, origin) {
  const rows = db.users.map((u) => `<tr><td>${esc(u.name)}${u.admin ? " (admin)" : ""}</td><td>${u.credentials.length}</td><td class="small">${esc(u.created.slice(0, 10))}</td><td>${u.admin ? "" : `<form class="inline" method="POST" action="/admin/delete-user"><input type="hidden" name="uid" value="${esc(u.id)}"><button>delete</button></form>`}</td></tr>`).join("");
  const invs = db.invites.map((i) => `<tr><td class="small">${i.usedBy ? "used by " + esc(i.usedBy) : `<a href=\"${esc(origin)}/register?invite=${esc(i.token)}\">invite link</a>`}</td><td class="small">${esc(i.created.slice(0, 10))}</td></tr>`).join("");
  return `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>dsh portal — admin</title>${css}</head><body><h1>Admin</h1>
<h2>Users</h2><table><tr><th>name</th><th>keys</th><th>created</th><th></th></tr>${rows || `<tr><td colspan="4" class="small">none</td></tr>`}</table>
<h2>Invites</h2><form method="POST" action="/admin/invite"><button type="submit">Create invite link</button></form><table><tr><th>link</th><th>created</th></tr>${invs}</table>
<p><a href="/">Back</a></p></body></html>`;
}

// ---------- server ----------
const server = createServer(
  { key: readFileSync(PEM_PATH), cert: readFileSync(PEM_PATH) },
  async (req, res) => {
    const url = new URL(req.url ?? "/", "https://x");
    const ip = req.socket.remoteAddress ?? "?";
    isPublicHost.current = isPublicHost(req);
    const send = (code, html, headers = {}) => {
      res.writeHead(code, { "content-type": "text/html; charset=utf-8", ...headers });
      res.end(html);
    };
    const sendJson = (code, obj) => {
      res.writeHead(code, { "content-type": "application/json" });
      res.end(JSON.stringify(obj));
    };
    const fail = (msg) => sendJson(400, { error: msg });
    try {
      const db = loadUsers();
      const sess = sessionOf(req);

      if (req.method === "GET" && url.pathname === "/") {
        if (!readPass()) return send(500, "Portal has no recovery password — ask the operator.");
        return send(200, sess ? homePage(db, sess) : loginPage());
      }

      if (req.method === "POST" && url.pathname === "/login") {
        if (rateLimited(ip)) return send(429, loginPage("Too many attempts — wait a minute."));
        const body = new URLSearchParams(await readBody(req));
        const rec = readPass();
        if (rec && verifyPassword(body.get("password") ?? "", rec)) {
          const sid = issueSession("recovery", "password");
          res.writeHead(302, { Location: "/", "Set-Cookie": `dsh-portal=${sid}; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200` });
          return res.end();
        }
        return send(401, loginPage("Wrong password."));
      }

      if (req.method === "GET" && url.pathname === "/open") {
        if (!sess) { res.writeHead(302, { Location: "/" }); return res.end(); }
        const target = dshTarget(req);
        if (!target) return send(502, homePage(db, sess, "dsh is not running or has no token yet."));
        res.writeHead(302, { Location: target });
        return res.end();
      }

      if (req.method === "POST" && url.pathname === "/change") {
        if (!sess) { res.writeHead(302, { Location: "/" }); return res.end(); }
        const body = new URLSearchParams(await readBody(req));
        const rec = readPass();
        const next = body.get("next") ?? "";
        if (!rec || !verifyPassword(body.get("current") ?? "", rec)) return send(401, homePage(db, sess, "Current password wrong — not changed."));
        if (next.length < 12) return send(400, homePage(db, sess, "New password must be at least 12 characters."));
        setPassword(next);
        return send(200, homePage(loadUsers(), sess, "Password changed."));
      }

      if (req.method === "POST" && url.pathname === "/logout") {
        if (sess) sessions.delete(sess.sid);
        res.writeHead(302, { Location: "/", "Set-Cookie": "dsh-portal=; Path=/; Max-Age=0" });
        return res.end();
      }

      if (req.method === "GET" && url.pathname === "/register") {
        const invite = url.searchParams.get("invite");
        if (!isPublicHost(req)) {
          return send(200, `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>register</title>${css}</head><body><h1>Create account</h1><p>Passkeys need the stable address — open this page at<br><b>https://${esc(PUBLIC_HOST)}:${TS_PORTAL_PORT}/register${invite ? "?invite=" + esc(invite) : ""}</b></p><p><a href="/">Back</a></p></body></html>`);
        }
        return send(200, registerPage(db, invite));
      }

      // ----- WebAuthn: registration -----
      if (req.method === "POST" && url.pathname === "/wk/register-options") {
        if (!isPublicHost(req)) return fail("use the public host for passkeys");
        const { username, invite } = await readJson(req);
        const firstRun = db.users.length === 0;
        if (!validName(username)) return fail("bad username (2-32 chars: letters, digits, . _ -)");
        if (db.users.some((u) => u.name.toLowerCase() === username.toLowerCase())) return fail("username taken");
        let inv = null;
        if (!firstRun) {
          inv = db.invites.find((i) => i.token === invite && !i.usedBy);
          if (!inv) return fail("a valid invite is required");
        }
        const challenge = randomBytes(32);
        const regId = randomUUID();
        const userId = randomUUID();
        pending.set(regId, { exp: Date.now() + 5 * 60_000, kind: "reg", challenge: challenge.toString("base64url"), username, userId, invite: inv?.token ?? null, admin: firstRun });
        return sendJson(200, {
          regId,
          options: {
            rp: { name: "dsh portal", id: RP_ID },
            user: { id: bufToB64url(Buffer.from(userId)), name: username, displayName: username },
            challenge: challenge.toString("base64url"),
            pubKeyCredParams: [{ type: "public-key", alg: -7 }, { type: "public-key", alg: -257 }],
            attestation: "none",
            authenticatorSelection: { userVerification: "preferred" },
            timeout: 120000,
          },
        });
      }

      if (req.method === "POST" && url.pathname === "/wk/register-verify") {
        const { regId, id, response } = await readJson(req);
        const p = pending.get(regId);
        if (!p || p.kind !== "reg") return fail("stale or unknown registration — restart it");
        pending.delete(regId);
        let clientData;
        try { clientData = JSON.parse(Buffer.from(b64urlToBuf(response.clientDataJSON)).toString("utf8")); }
        catch { return fail("bad clientData"); }
        if (clientData.type !== "webauthn.create") return fail("bad ceremony");
        if (!ORIGINS.includes(clientData.origin)) return fail("origin not allowed");
        if (clientData.challenge !== p.challenge) return fail("challenge mismatch");
        let cred;
        try { cred = verifyRegistration(response.attestationObject, RP_ID); }
        catch (e) { return fail("key rejected: " + e.message); }
        const fresh = loadUsers();
        if (fresh.users.some((u) => u.name.toLowerCase() === p.username.toLowerCase())) return fail("username taken");
        if (findByCred(fresh, cred.credId)) return fail("this passkey is already registered");
        let inv = null;
        if (!p.admin) {
          inv = fresh.invites.find((i) => i.token === p.invite && !i.usedBy);
          if (!inv) return fail("invite no longer valid");
          inv.usedBy = p.username; inv.usedAt = new Date().toISOString();
        }
        const user = { id: p.userId, name: p.username, admin: p.admin, created: new Date().toISOString(), credentials: [{ credId: cred.credId, jwk: cred.jwk, signCount: cred.signCount, label: "first passkey", created: new Date().toISOString() }] };
        fresh.users.push(user);
        saveUsers(fresh);
        const sid = issueSession(user.id, "passkey");
        res.writeHead(200, { "content-type": "application/json", "Set-Cookie": `dsh-portal=${sid}; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200` });
        return res.end(JSON.stringify({ ok: true }));
      }

      // ----- WebAuthn: login -----
      if (req.method === "POST" && url.pathname === "/wk/login-options") {
        if (!isPublicHost(req)) return fail("use the public host for passkeys");
        const { username } = await readJson(req).catch(() => ({}));
        let allow = [];
        if (username) {
          const u = db.users.find((x) => x.name.toLowerCase() === String(username).toLowerCase());
          if (!u) return fail("unknown user");
          allow = u.credentials.map((c) => ({ type: "public-key", id: c.credId }));
        }
        const challenge = randomBytes(32);
        const loginId = randomUUID();
        pending.set(loginId, { exp: Date.now() + 5 * 60_000, kind: "login", challenge: challenge.toString("base64url"), username: username ?? null });
        return sendJson(200, { loginId, options: { challenge: challenge.toString("base64url"), rpId: RP_ID, allowCredentials: allow, userVerification: "preferred", timeout: 120000 } });
      }

      if (req.method === "POST" && url.pathname === "/wk/login-verify") {
        if (rateLimited(ip)) return fail("too many attempts — wait a minute");
        const { loginId, id, response } = await readJson(req);
        const p = pending.get(loginId);
        if (!p || p.kind !== "login") return fail("stale login — restart it");
        pending.delete(loginId);
        const fresh = loadUsers();
        const user = findByCred(fresh, id);
        if (!user) return fail("unknown passkey — register first");
        if (p.username && user.name.toLowerCase() !== String(p.username).toLowerCase()) return fail("passkey does not belong to that user");
        const cred = user.credentials.find((c) => c.credId === id);
        let clientData;
        try { clientData = JSON.parse(Buffer.from(b64urlToBuf(response.clientDataJSON)).toString("utf8")); }
        catch { return fail("bad clientData"); }
        if (clientData.type !== "webauthn.get") return fail("bad ceremony");
        if (!ORIGINS.includes(clientData.origin)) return fail("origin not allowed");
        let signCount;
        try {
          signCount = verifyAssertion(
            { credentialId: id, authenticatorData: response.authenticatorData, clientDataJSON: response.clientDataJSON, signature: response.signature },
            { rpId: RP_ID, origin: clientData.origin, challengeB64: p.challenge, jwk: cred.jwk, storedCounter: cred.signCount }
          );
        } catch (e) { return fail("passkey rejected: " + e.message); }
        cred.signCount = signCount;
        saveUsers(fresh);
        const sid = issueSession(user.id, "passkey");
        res.writeHead(200, { "content-type": "application/json", "Set-Cookie": `dsh-portal=${sid}; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200` });
        return res.end(JSON.stringify({ ok: true }));
      }

      // ----- logged-in account management -----
      if (req.method === "POST" && url.pathname === "/wk/add-key-options") {
        if (!sess || sess.uid === "recovery") return fail("log in with a passkey account first");
        if (!isPublicHost(req)) return fail("use the public host for passkeys");
        const { label } = await readJson(req).catch(() => ({}));
        const me = findUser(db, sess.uid);
        if (!me) return fail("account gone");
        const challenge = randomBytes(32);
        const regId = randomUUID();
        pending.set(regId, { exp: Date.now() + 5 * 60_000, kind: "add", challenge: challenge.toString("base64url"), uid: me.id, label: String(label || "").slice(0, 40) || `device ${me.credentials.length + 1}` });
        return sendJson(200, {
          regId,
          options: {
            rp: { name: "dsh portal", id: RP_ID },
            user: { id: bufToB64url(Buffer.from(me.id)), name: me.name, displayName: me.name },
            challenge: challenge.toString("base64url"),
            pubKeyCredParams: [{ type: "public-key", alg: -7 }, { type: "public-key", alg: -257 }],
            attestation: "none",
            excludeCredentials: me.credentials.map((c) => ({ type: "public-key", id: c.credId })),
            authenticatorSelection: { userVerification: "preferred" },
            timeout: 120000,
          },
        });
      }

      if (req.method === "POST" && url.pathname === "/wk/add-key-verify") {
        const { regId, id, response } = await readJson(req);
        const p = pending.get(regId);
        if (!p || p.kind !== "add") return fail("stale — restart it");
        pending.delete(regId);
        if (!sess || sess.uid !== p.uid) return fail("session changed — log in again");
        let clientData;
        try { clientData = JSON.parse(Buffer.from(b64urlToBuf(response.clientDataJSON)).toString("utf8")); }
        catch { return fail("bad clientData"); }
        if (clientData.type !== "webauthn.create" || !ORIGINS.includes(clientData.origin) || clientData.challenge !== p.challenge) return fail("ceremony mismatch");
        let cred;
        try { cred = verifyRegistration(response.attestationObject, RP_ID); }
        catch (e) { return fail("key rejected: " + e.message); }
        const fresh = loadUsers();
        const me = findUser(fresh, p.uid);
        if (!me) return fail("account gone");
        if (findByCred(fresh, cred.credId)) return fail("this passkey is already registered");
        me.credentials.push({ credId: cred.credId, jwk: cred.jwk, signCount: cred.signCount, label: p.label, created: new Date().toISOString() });
        saveUsers(fresh);
        return sendJson(200, { ok: true });
      }

      if (req.method === "POST" && url.pathname === "/account/remove-key") {
        if (!sess || sess.uid === "recovery") { res.writeHead(302, { Location: "/" }); return res.end(); }
        const body = new URLSearchParams(await readBody(req));
        const fresh = loadUsers();
        const me = findUser(fresh, sess.uid);
        if (me) {
          me.credentials = me.credentials.filter((c) => c.credId !== body.get("credId"));
          saveUsers(fresh);
        }
        return send(200, homePage(loadUsers(), sess, "Passkey removed."));
      }

      // ----- admin -----
      if (req.method === "GET" && url.pathname === "/admin") {
        if (!isAdmin(db, sess)) { res.writeHead(302, { Location: "/" }); return res.end(); }
        // Invite links always use the public host: passkey enrollment fails on bare IPs.
        return send(200, adminPage(db, `https://${PUBLIC_HOST}:${TS_PORTAL_PORT}`));
      }
      if (req.method === "POST" && url.pathname === "/admin/invite") {
        if (!isAdmin(db, sess)) { res.writeHead(302, { Location: "/" }); return res.end(); }
        const fresh = loadUsers();
        const token = randomBytes(12).toString("base64url");
        fresh.invites.push({ token, created: new Date().toISOString(), usedBy: null });
        saveUsers(fresh);
        return send(200, adminPage(loadUsers(), `https://${PUBLIC_HOST}:${TS_PORTAL_PORT}`));
      }
      if (req.method === "POST" && url.pathname === "/admin/delete-user") {
        if (!isAdmin(db, sess)) { res.writeHead(302, { Location: "/" }); return res.end(); }
        const body = new URLSearchParams(await readBody(req));
        const fresh = loadUsers();
        const target = findUser(fresh, body.get("uid"));
        if (target && !target.admin) {
          fresh.users = fresh.users.filter((u) => u.id !== target.id);
          for (const [sid, s] of sessions) if (s.uid === target.id) sessions.delete(sid);
          saveUsers(fresh);
        }
        return send(200, adminPage(loadUsers(), `https://${PUBLIC_HOST}:${TS_PORTAL_PORT}`));
      }

      return send(404, "not found");
    } catch (e) {
      return sendJson(500, { error: "server error" });
    }
  }
);

if (!readPass()) {
  console.error("portal: no password file — refusing to start (set one first)");
  process.exit(1);
}
server.listen(PORTAL_PORT, "0.0.0.0", () => console.log(`portal -> https://0.0.0.0:${PORTAL_PORT} (public: https://${PUBLIC_HOST}:${TS_PORTAL_PORT})`));
