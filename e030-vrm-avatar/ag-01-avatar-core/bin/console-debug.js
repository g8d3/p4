#!/usr/bin/env node
// Debug: reload page, capture console + exceptions for N seconds.
import http from 'node:http';
import { WebSocket } from 'ws';

const port = process.argv[2] || '9222';
const ms = parseInt(process.argv[3] || '12000', 10);

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
const events = [];
ws.on('message', (d) => {
  const m = JSON.parse(d.toString());
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
  if (m.method === 'Runtime.consoleAPICalled') {
    const args = m.params.args.map((a) => a.value ?? a.description ?? a.type).join(' ');
    events.push(`[console.${m.params.type}] ${args}`);
  } else if (m.method === 'Runtime.exceptionThrown') {
    events.push(`[exception] ${m.params.exceptionDetails.text} ${m.params.exceptionDetails.exception?.description || ''}`);
  } else if (m.method === 'Log.entryAdded') {
    events.push(`[log] ${m.params.entry.level}: ${m.params.entry.text}`);
  }
});
await new Promise((res, rej) => { ws.on('open', res); ws.on('error', rej); });
const send = (method, params) => new Promise((res, rej) => {
  const mid = ++id;
  pending.set(mid, (m) => (m.error ? rej(new Error(m.error.message)) : res(m.result)));
  ws.send(JSON.stringify({ id: mid, method, params }));
});
await send('Runtime.enable');
await send('Log.enable');
await send('Page.enable');
await send('Page.reload', { ignoreCache: true });
await new Promise((r) => setTimeout(r, ms));
console.log(events.length ? events.join('\n') : '(no console events)');
ws.close();