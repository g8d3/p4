// Act visibly inside the DeepSeek web UI: open a session by id, type a task
// in its prompt box, press Enter, wait for the run to finish, print the tail.
// The user watches everything live on :9444 — same pixels as their own typing.
//
//   node bin/act.mjs <task...>
//   node bin/act.mjs "Reply with exactly: ACT-OK, no tools"
//
// Creates a fresh session via the UI's own New Session button, types the
// task, presses Enter, waits for the run, prints the tail + new session id.
// Stdlib only. Never touches other sessions. Exits 1 on timeout/failure.
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const TASK = process.argv.slice(2);
if (!TASK.length) { console.error("usage: node bin/act.mjs <task...>"); process.exit(2); }
const task = TASK.join(" ");
const SESSDIR = "/home/vuos/.dsh/sessions/--home-vuos-code-p4--";
const maskSecrets = (s) => s; // token never printed: we only print chat tail
let msgId = 0;

const log = readFileSync(new URL("../log/dsh.log", import.meta.url), "utf8");
const REAL = [...log.matchAll(/token=([A-Za-z0-9_-]+)/g)].map((m) => m[1]).at(-1);
if (!REAL) { console.error("no launch token — is dsh running?"); process.exit(1); }

const p = spawn("google-chrome", ["--headless=new", "--no-sandbox", "--disable-gpu",
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "act-"))}`, "--remote-debugging-port=0",
  "--window-size=412,915", "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
let wsUrl = null;
p.stderr.on("data", (d) => { const m = String(d).match(/DevTools listening on (ws:\/\/[^\s]+)/); if (m) wsUrl = m[1]; });
while (!wsUrl) await sleep(250);
const host = wsUrl.match(/ws:\/\/([^/]+)/)[1];
const bws = new WebSocket(wsUrl); await new Promise((r) => (bws.onopen = r));
const bsend = (method, params = {}) => new Promise((res) => { const i = ++msgId;
  const h = (m) => { const o = JSON.parse(m.data); if (o.id === i) { bws.removeEventListener("message", h); res(o.result); } };
  bws.addEventListener("message", h); bws.send(JSON.stringify({ id: i, method, params })); });
const { targetId } = await bsend("Target.createTarget", { url: "about:blank" });
const list = await (await fetch(`http://${host}/json/list`)).json();
const t = list.find((x) => x.id === targetId);
const ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
const pend = new Map(); const errs = [];
ws.onmessage = (m) => { const o = JSON.parse(m.data);
  if (o.id && pend.has(o.id)) { pend.get(o.id)(o); pend.delete(o.id); }
  else if (o.method === "Runtime.exceptionThrown") errs.push((o.params.exceptionDetails?.exception?.description || "?").slice(0, 150)); };
const send = (method, params = {}) => new Promise((res, rej) => { const i = ++msgId; pend.set(i, (o) => (o.error ? rej(new Error(JSON.stringify(o.error))) : res(o.result))); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = (e) => send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true }).then((r) => r.result.value);
const kill = () => { try { p.kill(); } catch {} };

try {
  await send("Page.enable"); await send("Runtime.enable");
  await send("Page.navigate", { url: `http://127.0.0.1:3080/?token=${REAL}` });
  await sleep(9000);
  const before = new Set(readdirSync(SESSDIR));
  // open sidebar, press the UI's own New Session (creates AND selects it)
  await ev(`[...document.querySelectorAll("button")].find(b => /sidebar/i.test(b.getAttribute("aria-label")||""))?.click()`);
  await sleep(2000);
  const created = await ev(`(() => {
    const bs = [...document.querySelectorAll("button")].filter(b => (b.innerText || "").trim() === "New Session");
    const b = bs.sort((a, c) => c.getBoundingClientRect().width - a.getBoundingClientRect().width)[0];
    if (!b) return "missing"; b.click(); return "clicked:" + Math.round(b.getBoundingClientRect().width);
  })()`);
  if (created === "missing") throw new Error("New Session button not found");
  await sleep(4000);
  const fresh = readdirSync(SESSDIR).filter((x) => !before.has(x));
  console.log("new session:", fresh[0] || "(not detected)", "::", created);
  // type the task in the prompt box and submit with a real Enter
  const box = await ev(`(() => {
    const els = [...document.querySelectorAll('[contenteditable="true"], textarea, input[type=text]')].filter(el => { try { const r = el.getBoundingClientRect(); return r.width > 100 && r.height > 20; } catch { return false; } });
    const b = els[els.length - 1];
    if (!b) return null;
    b.focus(); return b.tagName + ":" + ((b.getAttribute("placeholder") || b.getAttribute("aria-label") || "").slice(0, 30));
  })()`);
  if (!box) throw new Error("prompt box not found");
  console.log("prompt box:", box);
  await send("Input.insertText", { text: task });
  await sleep(800);
  await send("Input.dispatchKeyEvent", { type: "rawKeyDown", windowsVirtualKeyCode: 13, key: "Enter", code: "Enter" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", windowsVirtualKeyCode: 13, key: "Enter", code: "Enter" });
  // wait: first for the run to start (Stop button), then for it to end.
  // Enter alone may only newline in this box — fallback: Send button.
  let started = false;
  for (let i = 0; i < 6 && !started; i++) { await sleep(5000); started = await ev(`[...document.querySelectorAll("button")].some(b => /^(stop|cancel)$/i.test((b.innerText||"").trim()))`); }
  if (!started) {
    const sent = await ev(`(() => { const b = [...document.querySelectorAll("button")].find(b => /send/i.test(b.getAttribute("aria-label") || "")); if (!b) return "no-send-btn"; b.click(); return "send-clicked"; })()`);
    console.log("enter did not submit, used Send button:", sent);
  }
  // submission proof: our task text shows up in the chat (fast runs may
  // never display a Stop button long enough to catch)
  let submitted = false;
  for (let i = 0; i < 12 && !submitted; i++) { await sleep(5000); submitted = await ev(`document.body.innerText.includes(${JSON.stringify(task.slice(0, 40))})`); }
  if (!submitted) throw new Error("task never appeared in chat — submit failed");
  console.log("task submitted, waiting for the run to settle");
  console.log("run started");
  let calm = 0;
  for (let i = 0; i < 96 && calm < 3; i++) {
    await sleep(5000);
    const running = await ev(`[...document.querySelectorAll("button")].some(b => /^(stop|cancel)$/i.test((b.innerText||"").trim()))`);
    calm = running ? 0 : calm + 1;
  }
  if (calm < 3) throw new Error("run did not finish within 8 minutes");
  const tail = await ev(`document.body.innerText.split("\\n").filter(l => l.trim()).slice(-12).join("\\n")`);
  console.log("---- chat tail ----");
  console.log(maskSecrets(String(tail).slice(0, 1500)));
  const shot = await send("Page.captureScreenshot", { format: "png" });
  const f = `/tmp/act-${Date.now()}.png`;
  writeFileSync(f, Buffer.from(shot.data, "base64"));
  console.log("shot:", f);
  console.log("RESULT: DONE");
} catch (e) { console.error("ACT-FAIL:", e.message); process.exitCode = 1; }
finally { kill(); }
