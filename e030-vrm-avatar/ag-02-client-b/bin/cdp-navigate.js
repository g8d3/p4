#!/usr/bin/env node
// Minimal CDP helper: navigate a page target and wait for load.
import http from 'node:http';
import { WebSocket } from 'ws';

const [port, url] = [process.argv[2] || '9223', process.argv[3] || 'http://127.0.0.1:8787/viewer-b.html'];

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
const page = targets.find((t) => t.type === 'page');
if (!page) { console.error('no page target'); process.exit(1); }
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
await send('Page.navigate', { url });
// Wait for load event.
await new Promise((res) => {
  const t = setTimeout(res, 8000);
  ws.on('message', (d) => {
    const m = JSON.parse(d.toString());
    if (m.method === 'Page.loadEventFired') { clearTimeout(t); res(); }
  });
});
console.log('navigated to', url);
ws.close();
