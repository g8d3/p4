#!/usr/bin/env node
// CDP console-message listener: prints console logs/errors from a page target.
import http from 'node:http';
import { WebSocket } from 'ws';

const port = process.argv[2] || '9223';
const duration = Number(process.argv[3] || 4000);

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
const page = targets.find((t) => t.type === 'page' && t.url.includes('8787'));
if (!page) { console.error('no page'); process.exit(1); }
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
ws.on('message', (d) => {
  const m = JSON.parse(d.toString());
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === 'Runtime.consoleAPICalled' || m.method === 'Runtime.exceptionThrown') {
    const detail = m.params?.exceptionDetails?.exception?.description
      || m.params?.args?.map((a) => a.value ?? a.description ?? '').join(' ')
      || '';
    console.log(`[${m.method}]`, detail);
  }
});
await new Promise((res, rej) => { ws.on('open', res); ws.on('error', rej); });
const send = (method, params) => new Promise((res, rej) => {
  const mid = ++id;
  pending.set(mid, (m) => (m.error ? rej(new Error(m.error.message)) : res(m.result)));
  ws.send(JSON.stringify({ id: mid, method, params }));
});
await send('Runtime.enable', {});
await new Promise((r) => setTimeout(r, duration));
ws.close();
