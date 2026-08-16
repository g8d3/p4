#!/usr/bin/env node
// Capture a PNG screenshot from a headless Chrome page via CDP.
// Usage: node cdp-screenshot.js <port> <out.png> [url-match]
import http from 'node:http';
import fs from 'node:fs';
import { WebSocket } from 'ws';

const port = process.argv[2] || '9223';
const out = process.argv[3] || 'output/shot.png';
const match = process.argv[4] || 'viewer-b.html';

function httpJson(path) {
  return new Promise((resolve, reject) => {
    http.get({ host: '127.0.0.1', port, path, timeout: 5000 }, (res) => {
      let d = '';
      res.on('data', (c) => (d += c));
      res.on('end', () => { try { resolve(JSON.parse(d)); } catch (e) { reject(e); } });
    }).on('error', reject);
  });
}

const targets = await httpJson('/json/list');
const page = targets.find((t) => t.type === 'page' && t.url.includes(match));
if (!page) { console.error(`no page matching ${match}`); process.exit(1); }
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

await send('Page.enable', {});
const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
const buf = Buffer.from(shot.data, 'base64');
fs.writeFileSync(out, buf);
console.log(`saved ${out} (${buf.length} bytes)`);
ws.close();
