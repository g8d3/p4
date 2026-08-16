#!/usr/bin/env node
// CDP screenshot helper for capture-frame.sh.
// Connects to Chrome remote debugging (default port 9222), finds the page
// target whose URL contains --match, and captures a PNG via Page.captureScreenshot.
import http from 'node:http';
import fs from 'node:fs';
import { WebSocket } from 'ws';

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const k = a.slice(2);
      args[k] = argv[i + 1] ?? true;
      if (args[k] !== true) i++;
    }
  }
  return args;
}

const { port = '9222', match = '127.0.0.1:8787', out } = parseArgs(process.argv.slice(2));
if (!out) {
  console.error('usage: capture-frame.js --port <port> --match <url-substr> --out <file.png>');
  process.exit(2);
}

function httpJson(path) {
  return new Promise((resolve, reject) => {
    http.get({ host: '127.0.0.1', port, path, timeout: 5000 }, (res) => {
      let data = '';
      res.on('data', (c) => (data += c));
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch (e) { reject(new Error(`bad JSON from CDP ${path}: ${e}`)); }
      });
    }).on('error', reject);
  });
}

async function main() {
  const targets = await httpJson('/json/list');
  const page = targets.find((t) => t.type === 'page' && t.url.includes(match));
  if (!page) {
    throw new Error(`no page target matching "${match}" on port ${port}`);
  }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();

  ws.on('message', (data) => {
    const msg = JSON.parse(data.toString());
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  });

  await new Promise((resolve, reject) => {
    ws.on('open', resolve);
    ws.on('error', reject);
  });

  function send(method, params) {
    return new Promise((resolve, reject) => {
      const mid = ++id;
      pending.set(mid, (msg) => (msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result)));
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
  }

  const r = await send('Page.captureScreenshot', { format: 'png', fromSurface: true });
  if (!r || !r.data) throw new Error('empty screenshot data');
  fs.writeFileSync(out, Buffer.from(r.data, 'base64'));
  ws.close();
  console.log(`captured ${out} (${fs.statSync(out).size} bytes) from ${page.url}`);
}

main().catch((e) => {
  console.error(`capture-frame failed: ${e.message}`);
  process.exit(1);
});