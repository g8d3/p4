#!/usr/bin/env node
// Quick CDP probe: evaluate JS in the page and print result + console errors.
import http from 'node:http';
import { WebSocket } from 'ws';

const port = process.argv[2] || '9222';
const expr = process.argv[3] || 'window.__probe || "no probe"';

function httpJson(path) {
  return new Promise((resolve, reject) => {
    http.get({ host: '127.0.0.1', port, path, timeout: 5000 }, (res) => {
      let data = '';
      res.on('data', (c) => (data += c));
      res.on('end', () => { try { resolve(JSON.parse(data)); } catch (e) { reject(e); } });
    }).on('error', reject);
  });
}

const targets = await httpJson('/json/list');
const page = targets.find((t) => t.type === 'page' && t.url.includes('8787'));
if (!page) { console.error('no page'); process.exit(1); }
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
ws.on('message', (d) => {
  const m = JSON.parse(d.toString());
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
await new Promise((res, rej) => { ws.on('open', res); ws.on('error', rej); });
const send = (method, params) => new Promise((res, rej) => {
  const mid = ++id;
  pending.set(mid, (m) => (m.error ? rej(new Error(m.error.message)) : res(m.result)));
  ws.send(JSON.stringify({ id: mid, method, params }));
});
const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
console.log(JSON.stringify(r?.result?.value ?? r, null, 2));
ws.close();