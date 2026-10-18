// Deep end-to-end test: drives a REAL headless Chrome (phone-sized viewport)
// with a VIRTUAL passkey authenticator through every portal button/input,
// then crawls the live dsh UI: inventory of all buttons/inputs/menus,
// click-through of nav, a safe terminal echo, read-only views. Screenshots
// under /tmp/dsh-e2e-<ts>/.
//
//   node bin/e2e.mjs            # everything (isolated test portal + live dsh)
//   node bin/e2e.mjs --portal   # portal only
//   node bin/e2e.mjs --dsh      # live dsh UI only
//
// Zero dependencies (node stdlib + global fetch/WebSocket). The live-dsh
// part never writes: no settings/credential changes, one harmless
// `echo` in the terminal if one is found. Exit 0 = all green, 1 = FAILs.
import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { scryptSync, randomBytes } from "node:crypto";

process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

const ROOT = new URL("..", import.meta.url).pathname;
const SHOTDIR = join(tmpdir(), `dsh-e2e-${Date.now()}`);
mkdirSync(SHOTDIR, { recursive: true });
const args = new Set(process.argv.slice(2));
const ONLY = args.has("--portal") ? "portal" : args.has("--dsh") ? "dsh" : "all";

let PASS = 0, FAIL = 0; const SKIPS = [];
let SECRETS = [];
const mask = (s) => { let o = String(s); for (const x of SECRETS) if (x) o = o.split(x).join("[SECRET]"); return o; };
const say = (ok, name, detail = "") => {
  if (ok === "SKIP") { SKIPS.push(name); return console.log(`SKIP  ${name} — ${mask(detail)}`); }
  ok ? PASS++ : FAIL++;
  console.log(`${ok ? "PASS " : "FAIL "} ${name}${detail ? " — " + mask(detail) : ""}`);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------------- CDP ----------------
let msgId = 0;
function connect(url) {
  const ws = new WebSocket(url);
  const pend = new Map(); const events = [];
  ws.onmessage = (m) => {
    const o = JSON.parse(m.data);
    if (o.id && pend.has(o.id)) { pend.get(o.id)(o); pend.delete(o.id); }
    else events.push(o);
  };
  const ready = new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  return { ws, events,
    send: (method, params = {}) => new Promise((res, rej) => {
      const id = ++msgId;
      pend.set(id, (o) => (o.error ? rej(new Error(`${method}: ${JSON.stringify(o.error)}`)) : res(o.result)));
      ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => { if (pend.has(id)) { pend.delete(id); rej(new Error(method + " timeout")); } }, 30000);
    }),
    ready };
}
async function launchChrome() {
  const profile = mkdtempSync(join(tmpdir(), "chrome-prof-"));
  const dbgLog = join(tmpdir(), `chrome-dbg-${Date.now()}.log`);
  const p = spawn("google-chrome", [
    "--headless=new", "--no-sandbox", "--disable-gpu", "--ignore-certificate-errors",
    `--user-data-dir=${profile}`, "--remote-debugging-port=0", "--window-size=412,915", "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });
  const fs2 = await import("node:fs");
  const out = fs2.createWriteStream(dbgLog);
  p.stderr.pipe(out);
  let wsUrl = null;
  for (let i = 0; i < 200 && !wsUrl; i++) {
    await sleep(250);
    try { const t = readFileSync(dbgLog, "utf8"); const m = t.match(/DevTools listening on (ws:\/\/[^\s]+)/); if (m) wsUrl = m[1]; } catch {}
    if (p.exitCode !== null) throw new Error("chrome exited early, see " + dbgLog);
  }
  if (!wsUrl) throw new Error("no DevTools URL, see " + dbgLog);
  const host = wsUrl.match(/ws:\/\/([^/]+)/)[1];
  const browser = connect(wsUrl); await browser.ready;
  const { targetId } = await browser.send("Target.createTarget", { url: "about:blank" });
  const list = await (await fetch(`http://${host}/json/list`)).json();
  const t = list.find((x) => x.id === targetId);
  if (!t) throw new Error("fresh page target not found");
  const page = connect(t.webSocketDebuggerUrl); await page.ready;
  await page.send("Page.enable"); await page.send("Runtime.enable"); await page.send("Log.enable");
  // NOTE: on modern Chrome the WebAuthn CDP domain only exists on the page
  // session, not the browser session (method-not-found otherwise).
  await page.send("WebAuthn.enable");
  const mkAuth = () => page.send("WebAuthn.addVirtualAuthenticator", { options: {
    protocol: "ctap2", transport: "usb", hasResidentKey: true,
    hasUserVerification: true, isUserVerified: true, automaticPresenceSimulation: true } }).then((r) => r.authenticatorId);
  let authenticatorId = await mkAuth();
  await page.send("Emulation.setDeviceMetricsOverride", { width: 412, height: 915, deviceScaleFactor: 2, mobile: true });
  const consoleErrors = [];
  const origOn = page.ws.onmessage;
  page.ws.onmessage = (m) => {
    try { const o = JSON.parse(m.data);
      if (o.method === "Log.entryAdded" && ["error"].includes(o.params?.entry?.level)) consoleErrors.push(o.params.entry.text);
      if (o.method === "Runtime.exceptionThrown") consoleErrors.push(o.params.exceptionDetails?.exception?.description || o.params.exceptionDetails?.text || "exception");
    } catch {}
    origOn(m);
  };
  const newDevice = async () => {
    // a second phone/computer = a second authenticator (also avoids the
    // excludeCredentials clash when the same virtual auth holds key #1)
    try { await page.send("WebAuthn.removeVirtualAuthenticator", { authenticatorId }); } catch {}
    authenticatorId = await mkAuth();
  };
  return { proc: p, browser, page, consoleErrors, newDevice,
    kill: () => { try { p.kill(); } catch {} } };
}
async function nav(pg, url, timeoutMs = 30000) {
  const loaded = new Promise((res) => {
    const h = setInterval(async () => {}, 1e9); clearInterval(h);
    const check = (m) => { try { const o = JSON.parse(m.data); if (o.method === "Page.loadEventFired") { pg.ws.removeEventListener?.("message", check); res(); } } catch {} };
    pg.ws.addEventListener("message", check);
    setTimeout(res, timeoutMs);
  });
  await pg.send("Page.navigate", { url });
  await loaded; await sleep(1200);
}
const ev = (pg, expr, awaitPromise = true) =>
  pg.send("Runtime.evaluate", { expression: expr, awaitPromise, returnByValue: true }).then((r) => r.result?.value);
async function shot(pg, name) {
  const { data } = await pg.send("Page.captureScreenshot", { format: "png" });
  const f = join(SHOTDIR, name); writeFileSync(f, Buffer.from(data, "base64")); return f;
}
const cookiesFor = async (pg) => {
  const { cookies } = await pg.send("Storage.getCookies");
  return cookies.map((c) => `${c.name}=${c.value}`).join("; ");
};
async function fetchAs(fetchOpts, url, opts = {}) {
  const r = await fetch(url, { redirect: "manual", ...opts });
  const loc = r.headers.get("location") || "";
  const body = await r.text().catch(() => "");
  return { status: r.status, loc, body };
}

// ---------------- test portal (isolated) ----------------
async function testPortal(chrome) {
  const { page } = chrome;
  const dir = mkdtempSync(join(tmpdir(), "portal-test-"));
  const FAKE = "t" + randomBytes(24).toString("base64url");
  SECRETS.push(FAKE);
  writeFileSync(join(dir, "dsh.log"), `dsh web: http://127.0.0.1:3080/?token=${FAKE}\n`);
  const PW = "e2e-recovery-pw-12345"; SECRETS.push(PW);
  const salt = randomBytes(16).toString("hex");
  writeFileSync(join(dir, "pass.json"), JSON.stringify({ salt, hash: scryptSync(PW, Buffer.from(salt, "hex"), 64).toString("hex") }));
  const usersFile = join(dir, "users.json"); writeFileSync(usersFile, JSON.stringify({ users: [], invites: [] }));
  const env = { ...process.env, PORTAL_PORT: "18090", PUBLIC_HOST: "localhost", TS_PORTAL_PORT: "18090",
    PASS_FILE: join(dir, "pass.json"), USERS_FILE: usersFile, DSH_LOG: join(dir, "dsh.log"),
    CLIENT_ERR_LOG: join(dir, "client-errors.log"),
    DSH_PEM: join(ROOT, "cert/dsh.pem"), DSH_LAN_HOST: "127.0.0.1" };
  const srv = spawn("node", [join(ROOT, "portal/server.mjs")], { env, stdio: "ignore" });
  await sleep(1500);
  const B = "https://localhost:18090";
  const users = () => JSON.parse(readFileSync(usersFile, "utf8"));

  try {
    // P1 landing
    await nav(page, B + "/");
    const land = await ev(page, "document.body.innerText");
    say(/passkey/i.test(land) && /recovery/i.test(land), "portal: landing shows passkey + recovery login", await shot(page, "p1-landing.png"));

    // P2 wrong password (API level)
    let r = await fetchAs(0, B + "/login", { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body: "password=nope" });
    say(r.status === 401 && /wrong password/i.test(r.body), "portal: wrong password rejected", `HTTP ${r.status}`);

    // P3 password login via UI
    await nav(page, B + "/");
    await ev(page, `document.querySelector('input[name=password],input[type=password]').value=${JSON.stringify(PW)}; document.querySelector('form[action="/login"]').submit()`);
    await sleep(1500);
    const home = await ev(page, "document.body.innerText");
    say(/open dsh/i.test(home), "portal: recovery-password login via UI", await shot(page, "p3-home.png"));

    // P4 /open hands the live token (authed fetch with browser cookies)
    let ck = await cookiesFor(page);
    r = await fetchAs(0, B + "/open", { headers: { cookie: ck } });
    say(r.status === 302 && r.loc.includes("token=" + FAKE), "portal: /open redirects with live token", `HTTP ${r.status}`);

    // P5 register first (admin) account via UI + virtual passkey
    await nav(page, B + "/register");
    await ev(page, `document.querySelector('#regname').value='e2e-admin'; document.querySelector('button[onclick*="pkRegister"]').click()`);
    for (let i = 0; i < 30; i++) { await sleep(1000); const u = await ev(page, "location.pathname"); if (u === "/") break; }
    const err5 = await ev(page, "document.querySelector('#msg')?.innerText||''");
    const home5 = await ev(page, "document.body.innerText");
    say(/open dsh/i.test(home5) && users().users.length === 1 && users().users[0].admin, "portal: passkey registration creates admin", err5 || await shot(page, "p5-registered.png"));

    // P6 logout then /open must bounce without token
    await fetchAs(0, B + "/logout", { method: "POST", headers: { cookie: await cookiesFor(page) } });
    await nav(page, B + "/open");
    say((await ev(page, "location.pathname")) === "/", "portal: logged-out /open bounces to login, no token");

    // P0 phone-error telemetry: register page without invite guides the
    // user AND beacons the server; the endpoint logs the ref id.
    await nav(page, B + "/register");
    const guided = /invite link/i.test(await ev(page, "document.body.innerText"));
    await sleep(2500);
    const cerrFile = join(dir, "client-errors.log");
    let cerr = ""; try { cerr = readFileSync(cerrFile, "utf8"); } catch {}
    const cref = "derr_test" + Date.now().toString(36);
    const cr = await fetchAs(0, B + "/wk/client-error", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ id: cref, flow: "e2e", name: "TestError", message: "telemetry probe" }) });
    let cerr2 = ""; try { cerr2 = readFileSync(cerrFile, "utf8"); } catch {}
    say(guided && cerr.includes("register-no-invite") && cr.status === 200 && cerr2.includes(cref), "portal: phone errors self-report with ref id", `guided=${guided} beacon=${cerr.includes("register-no-invite")} endpoint=${cr.status} ref-logged=${cerr2.includes(cref)}`);

    // P7 passkey login via UI
    await nav(page, B + "/");
    await ev(page, `document.querySelector('#pkname').value='e2e-admin'; document.querySelector('button[onclick*="pkLogin"]').click()`);
    for (let i = 0; i < 30; i++) { await sleep(1000); const t = await ev(page, "document.body.innerText"); if (/open dsh/i.test(t)) break; }
    const home7 = await ev(page, "document.body.innerText");
    say(/open dsh/i.test(home7), "portal: passkey login via UI", (await ev(page, "document.querySelector('#msg')?.innerText||''")) || await shot(page, "p7-passkey-login.png"));

    // P8 change password matrix via UI
    const change = async (cur, nxt) => {
      await nav(page, B + "/");
      await ev(page, `document.querySelector('input[name=current]').value=${JSON.stringify(cur)}; document.querySelector('input[name=next]').value=${JSON.stringify(nxt)}; document.querySelector('form[action="/change"]').submit()`);
      await sleep(1200); return ev(page, "document.body.innerText");
    };
    let t8 = await change("wrong-current-pw", "e2e-new-password-67890");
    const c1 = /current password wrong/i.test(t8);
    t8 = await change(PW, "short");
    const c2 = /at least 12/i.test(t8);
    const PW2 = "e2e-new-password-67890"; SECRETS.push(PW2);
    t8 = await change(PW, PW2);
    say(c1 && c2 && /password changed/i.test(t8), "portal: password change matrix (wrong/short/ok)");

    // P9 admin creates invite
    ck = await cookiesFor(page);
    r = await fetchAs(0, B + "/admin/invite", { method: "POST", headers: { cookie: ck } });
    const adm = await (await fetch(B + "/admin", { headers: { cookie: ck } })).text();
    const inv = (adm.match(/register\?invite=([A-Za-z0-9_-]+)/) || [])[1];
    say(r.status === 200 && !!inv, "portal: admin creates single-use invite");

    // P10 second user registers with invite
    await fetchAs(0, B + "/logout", { method: "POST", headers: { cookie: await cookiesFor(page) } });
    await nav(page, `${B}/register?invite=${inv}`);
    await ev(page, `document.querySelector('#regname').value='e2e-second'; document.querySelector('button[onclick*="pkRegister"]').click()`);
    for (let i = 0; i < 30; i++) { await sleep(1000); const t = await ev(page, "document.body.innerText"); if (/open dsh/i.test(t)) break; }
    say(users().users.length === 2, "portal: invite link yields second account");

    // P11 second device key enroll + removal (fresh authenticator = second device)
    await chrome.newDevice();
    await nav(page, B + "/");
    await ev(page, `document.querySelector('#keylabel').value='e2e-device2'; document.querySelector('button[onclick*="pkRegister(true)"]').click()`);
    await sleep(6000);
    const twoKeys = users().users.find((u) => u.name === "e2e-second")?.credentials?.length === 2;
    ck = await cookiesFor(page);
    const credId = users().users.find((u) => u.name === "e2e-second").credentials[0].credId;
    r = await fetchAs(0, B + "/account/remove-key", { method: "POST", headers: { cookie: ck, "content-type": "application/x-www-form-urlencoded" }, body: "credId=" + encodeURIComponent(credId) });
    const oneKey = users().users.find((u) => u.name === "e2e-second")?.credentials?.length === 1;
    const msg11 = await ev(page, "document.querySelector('#msg')?.innerText||''");
    say(twoKeys && r.status === 200 && oneKey, "portal: enroll second-device key + remove it", `twoKeys=${twoKeys} remove=${r.status} oneKey=${oneKey} msg=${msg11.slice(0, 120)}`);

    // P12 admin deletes second user (recovery login: the admin passkey lives
    // on the wiped authenticator = "another device"; passkey login itself
    // is already covered by P7)
    await fetchAs(0, B + "/logout", { method: "POST", headers: { cookie: await cookiesFor(page) } });
    await nav(page, B + "/");
    await ev(page, `document.querySelector('input[name=password],input[type=password]').value=${JSON.stringify(PW2)}; document.querySelector('form[action="/login"]').submit()`);
    for (let i = 0; i < 30; i++) { await sleep(1000); const t = await ev(page, "document.body.innerText"); if (/open dsh/i.test(t)) break; }
    ck = await cookiesFor(page);
    const adm2 = await (await fetch(B + "/admin", { headers: { cookie: ck } })).text();
    const uidM = adm2.match(/name="userId" value="([^"]+)"/);
    const delName = users().users.find((u) => u.name === "e2e-second")?.id;
    if (uidM || delName) {
      const uid = delName || uidM[1];
      r = await fetchAs(0, B + "/admin/delete-user", { method: "POST", headers: { cookie: ck, "content-type": "application/x-www-form-urlencoded" }, body: "uid=" + encodeURIComponent(uid) });
      say(!users().users.some((u) => u.name === "e2e-second"), "portal: admin deletes user", `HTTP ${r.status}`);
    } else say("SKIP", "portal: admin deletes user", "delete form not parseable");
    await shot(page, "p12-admin.png");
  } finally { try { srv.kill(); } catch {} }
}

// ---------------- live dsh UI ----------------
async function testDsh(chrome) {
  const { page, consoleErrors } = chrome;
  const log = readFileSync(join(ROOT, "log/dsh.log"), "utf8");
  const toks = [...log.matchAll(/token=([A-Za-z0-9_-]+)/g)].map((m) => m[1]);
  const REAL = toks[toks.length - 1];
  if (!REAL) { say(false, "dsh: launch token in log", "dsh not running?"); return; }
  SECRETS.push(REAL);
  const BASE = "http://127.0.0.1:3080";

  // D1 token exchange -> app boots
  consoleErrors.length = 0;
  await nav(page, `${BASE}/?token=${REAL}`, 45000);
  let noToken = false, bodyLen = 0; const trace = [];
  for (let i = 0; i < 90; i++) {
    const u = await ev(page, "location.href");
    noToken = !u.includes("token=");
    bodyLen = await ev(page, "document.body.innerText.length");
    if (i < 3 || i % 15 === 0) trace.push(`${i}s href=${String(u).slice(-40)} len=${bodyLen}`);
    // NOTE: the empty state (no session open) is only ~136 chars of text —
    // boot is proven by token-strip + key content, not by length.
    if (noToken && bodyLen > 100) break;
    await sleep(1000);
  }
  const title = await ev(page, "document.title");
  say(noToken && bodyLen > 100, "dsh: token exchange boots app, token stripped from URL", `title=${JSON.stringify(title)} body=${bodyLen} chars ${await shot(page, "d1-app.png")}`);

  // D2 full inventory of interactive elements
  const inv = await ev(page, `(() => {
    const q = (s) => [...document.querySelectorAll(s)];
    const vis = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    const label = (el) => (el.innerText || el.value || el.getAttribute('aria-label') || el.placeholder || el.tagName).trim().slice(0, 40);
    const out = {};
    for (const [k, s] of Object.entries({ button: 'button', input: 'input,textarea,select,[contenteditable]', link: 'a[href]', tab: '[role=tab]', menuitem: '[role=menuitem],[role=menu] button' }))
      { const els = q(s).filter(vis); out[k] = { n: els.length, sample: els.slice(0, 12).map(label) }; }
    return out;
  })()`);
  const total = ["button", "input", "link", "tab", "menuitem"].reduce((a, k) => a + (inv[k]?.n || 0), 0);
  say(total > 5, `dsh: UI inventory (${total} interactive elements)`, JSON.stringify(inv).slice(0, 600));

  // D3 click through views (read-only tour). EXCLUDED on purpose: anything
  // that creates state (New session/Add workspace/Add files), anything that
  // would mutate this live session (mode/access switches), and Account menu
  // items (one of them logs out). Exclusions are listed, not hidden.
  const SKIP_TOUR = ["new session", "add workspace", "add files", "standard mode", "access mode", "account menu", "log out", "sign out"];
  const tabs = await ev(page, `[...document.querySelectorAll('button, [role=tab], nav a, aside a')]
    .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && !el.disabled && !el.closest('form'); })
    .map(el => (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 40)).filter(Boolean)
    .filter((v, i, a) => a.indexOf(v) === i)`);
  const visit = (tabs || []).filter((t) => !SKIP_TOUR.some((s) => t.toLowerCase().includes(s))).slice(0, 14);
  const skipped = (tabs || []).filter((t) => SKIP_TOUR.some((s) => t.toLowerCase().includes(s)));
  let clicked = 0; const viewErrors = {};
  for (const t of visit) {
    try {
      const before = consoleErrors.length;
      await ev(page, `[...document.querySelectorAll('button, [role=tab], nav a, aside a')].find(el => ((el.innerText||el.getAttribute('aria-label')||'').trim().slice(0,40)) === ${JSON.stringify(t)})?.click()`);
      await sleep(1500); clicked++;
      await shot(page, `d3-view-${clicked}.png`);
      const fresh = [...new Set(consoleErrors.slice(before))].filter((e) => !/favicon/i.test(e));
      if (fresh.length) viewErrors[t] = fresh;
    } catch (e) { say(false, `dsh: view ${JSON.stringify(t)}`, mask(e.message)); }
  }
  // terminal lives behind "Add files or run commands": open the panel
  // (read-only), then probe exec with a side-effect-free echo.
  let termOpened = false;
  try {
    await ev(page, `[...document.querySelectorAll('button')].find(el => (el.innerText||'').includes('Add files or run commands'))?.click()`);
    await sleep(1500);
    termOpened = !!(await ev(page, "!!document.querySelector('.xterm, [class*=terminal], [aria-label*=terminal i]')"));
    await shot(page, "d3-terminal-panel.png");
  } catch (e) { viewErrors["terminal panel"] = [mask(e.message)]; }
  say(clicked === visit.length, `dsh: view tour (${clicked}/${visit.length} views, submits nothing)`, `saw: ${(tabs || []).join(" | ")} // skipped by policy: ${skipped.join(" | ") || "none"}`);

  // D4 inputs: type-then-clear every text entry (proves each accepts typing;
  // Enter is NEVER pressed, so nothing is submitted or launched)
  const nInputs = await ev(page, `(() => {
    const els = [...document.querySelectorAll('input, textarea, [contenteditable]')].filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && !el.readOnly && !el.disabled && el.type !== 'checkbox' && el.type !== 'radio' && el.type !== 'file'; });
    for (const el of els.slice(0, 20)) { el.focus(); document.execCommand('selectAll', false, null); document.execCommand('insertText', false, 'e2e-probe'); }
    const typed = els.slice(0, 20).filter(el => ((el.value ?? el.innerText) || '').includes('e2e-probe')).length;
    for (const el of els.slice(0, 20)) { el.focus(); document.execCommand('selectAll', false, null); document.execCommand('insertText', false, ''); el.dispatchEvent(new Event('input', { bubbles: true })); }
    return { found: els.length, typed };
  })()`);
  say(nInputs && nInputs.typed === Math.min(nInputs.found, 20), `dsh: inputs accept typing+clear without submitting (${nInputs ? nInputs.typed + "/" + nInputs.found : 0})`);

  // D5+D7 session flow (proven click path): open sidebar -> open an
  // existing session (read-only) -> Chat/Trajectory tabs -> New terminal
  // + side-effect-free echo -> right sidebar Plugins -> New tab (known
  // upstream bug check). Never presses Enter in the agent prompt box.
  const clickBtn = async (labelRe) => ev(page, `(() => {
    const b = [...document.querySelectorAll('button')].find(b => ${labelRe}.test((b.innerText || b.getAttribute('aria-label') || '').trim()));
    if (!b) return 'missing'; b.click(); return 'clicked';
  })()`);
  try {
    let d5 = [];
    let hiHere = false;
    for (let i = 0; i < 4 && !hiHere; i++) {
      hiHere = await ev(page, `[...document.querySelectorAll('span')].some(s => (s.textContent||'').trim() === 'Hi')`);
      if (!hiHere) {
        await ev(page, `[...document.querySelectorAll('button')].find(b => /sidebar/i.test(b.getAttribute('aria-label')||''))?.click()`);
        await sleep(1500);
      }
    }
    d5.push("sidebar-list=" + hiHere);
    d5.push("session=" + await ev(page, `(() => { const s = [...document.querySelectorAll('span')].find(s => (s.textContent||'').trim() === 'Hi'); if (!s) return 'missing'; s.click(); return 'opened'; })()`));
    await sleep(2500);
    d5.push("chat=" + await clickBtn("/^Chat$/"));
    await sleep(1200);
    await shot(page, "d5-chat.png");
    d5.push("trajectory=" + await clickBtn("/^Trajectory$/"));
    await sleep(1200);
    await shot(page, "d5-trajectory.png");
    let wsOpen = false;
    for (let i = 0; i < 3 && !wsOpen; i++) {
      wsOpen = await ev(page, `[...document.querySelectorAll('*')].some(el => (el.innerText || '').trim() === 'Workspace files' && (() => { try { return el.getBoundingClientRect().width > 0; } catch { return false; } })())`);
      if (!wsOpen) {
        await ev(page, `[...document.querySelectorAll('button')].find(b => /right sidebar/i.test(b.getAttribute('aria-label') || ''))?.click()`);
        await sleep(1500);
      }
    }
    d5.push("workspace-panel=" + wsOpen);
    const termRect = await ev(page, `(() => {
      const vis = (el) => { try { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; } catch { return false; } };
      const c = [...document.querySelectorAll('*')]
        .map(el => ({ t: (el.innerText || '').trim().replace(/\\s+/g, ' '), el }))
        .filter(x => vis(x.el) && x.t.includes('New terminal')).sort((a, b) => a.t.length - b.t.length)[0];
      if (!c) return null;
      const r = c.el.getBoundingClientRect();
      return { x: r.x + r.width / 2, y: r.y + r.height / 2, tag: c.el.tagName };
    })()`);
    d5.push("newterm=" + (termRect ? `row@${termRect.tag}` : "missing"));
    if (termRect) {
      // NOTE: el.click() does NOT open it (React row handler needs a real
      // pointer sequence); genuine CDP mouse press/release does.
      for (const type of ["mousePressed", "mouseReleased"]) {
        await page.send("Input.dispatchMouseEvent", { type, x: termRect.x, y: termRect.y, button: "left", clickCount: 1 });
        await sleep(300);
      }
    }
    let echoed = false;
    for (let i = 0; i < 15 && !echoed; i++) { await sleep(1000); echoed = await ev(page, "!!document.querySelector('.xterm')"); }
    d5.push("xterm=" + echoed);
    if (echoed) {
      await page.send("Input.insertText", { text: "echo E2E-PROBE-4242" });
      await page.send("Input.dispatchKeyEvent", { type: "rawKeyDown", windowsVirtualKeyCode: 13, key: "Enter", code: "Enter" });
      await page.send("Input.dispatchKeyEvent", { type: "keyUp", windowsVirtualKeyCode: 13, key: "Enter", code: "Enter" });
      let rendered = false;
      for (let i = 0; i < 20; i++) { await sleep(1000); if (await ev(page, "document.body.innerText.includes('E2E-PROBE-4242')")) { rendered = true; break; } }
      d5.push("echo-rendered=" + rendered);
      await shot(page, "d5-terminal.png");
      say(rendered, "dsh: session terminal echo renders output", d5.join(" "));
    } else say("SKIP", "dsh: session terminal echo renders output", d5.join(" "));
  } catch (e) { say(false, "dsh: session flow", mask(e.message)); }

  // D7 known upstream bug, tracked: the right-sidebar "New tab" button
  // with NO session surface mounted throws an Uncaught
  // "sidebarRight: no session surface is mounted" instead of a graceful
  // no-op (first click per state; the app survives it). Recorded for
  // upstream; the console test below exempts exactly this signature.
  try {
    const hit = viewErrors["New tab"] || [];
    const known = hit.some((e) => /no session surface is mounted/.test(e));
    const other = hit.filter((e) => !/no session surface is mounted/.test(e));
    await shot(page, "d7-newtab.png");
    if (other.length) say(false, "dsh: New tab shows unexpected errors", other.join(" | ").slice(0, 200));
    else if (known) say(true, "dsh: known upstream bug reproduced exactly (New tab, no session)", hit[0].slice(0, 160));
    else say("SKIP", "dsh: known upstream bug", "did not trigger this run (state-dependent one-shot)");
  } catch (e) { say(false, "dsh: New tab known-bug check", mask(e.message)); }

  // D6 auth gate on loopback API without session
  const r = await fetchAs(0, BASE + "/api/probe", { method: "POST", headers: { Origin: BASE, "Content-Type": "application/json" }, body: "{}" });
  say([401, 403, 404].includes(r.status), "dsh: loopback API gated (no anonymous access)", `HTTP ${r.status}`);

  const KNOWN_BUG = /no session surface is mounted/;
  const errs = [...new Set(consoleErrors)].filter((e) => !/favicon/i.test(e) && !KNOWN_BUG.test(e)).slice(0, 5);
  const perView = Object.entries(viewErrors).map(([v, es]) => `${v} => ${es.join(" | ").slice(0, 200)}`).join(" //// ");
  say(errs.length === 0, "dsh: zero NEW console errors (known New-tab issue tracked in D7)", perView.slice(0, 1200) || errs.join(" || ").slice(0, 1200) || `${clicked} views screenshotted`);
}

try {
  const chrome = await launchChrome();
  try {
    if (ONLY !== "dsh") await testPortal(chrome);
    if (ONLY !== "portal") await testDsh(chrome);
  } finally { chrome.kill(); }
} catch (e) { say(false, "e2e harness", mask(e.message)); }
console.log(`\nshots: ${SHOTDIR}\nskips: ${SKIPS.length ? SKIPS.join("; ") : "none"}\nRESULT: ${FAIL === 0 ? "ALL GREEN" : FAIL + " FAILURES"} (${PASS} passed)`);
process.exit(FAIL === 0 ? 0 : 1);
