// Minimal conforming avatar-server for client-B verification (ag-02 local).
// Implements the SAME /cmd + WS contract documented in ../AGENTS.md so the
// avatar CLI and client-B can be tested end-to-end even before ag-01 lands.
import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, normalize, resolve } from 'node:path';
import { WebSocketServer, WebSocket } from 'ws';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = __dirname;
const modelsDir = resolve(root, '..', 'models');
const mediaDir = resolve(root, 'media');
const port = Number(process.env.PORT || 8787);

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.vrm': 'model/vrm',
  '.glb': 'model/gltf-binary',
  '.mp3': 'audio/mpeg',
  '.wav': 'audio/wav',
  '.png': 'image/png',
  '.css': 'text/css; charset=utf-8',
};

const clients = new Map(); // ws -> { id }

function routePath(url) {
  const p = new URL(url, 'http://localhost').pathname;
  if (p === '/') return '/viewer-b.html';
  if (p.startsWith('/client-b')) return p.replace(/^\/client-b/, '');
  return p;
}

function resolveStatic(p) {
  const clean = normalize(p).replace(/^([/\\])+/, '');
  if (clean.startsWith('..')) return null;
  return join(root, clean);
}

function resolveModels(p) {
  const clean = normalize(p).replace(/^(models\/|[/\\])+/, '');
  if (clean.startsWith('..')) return null;
  return join(modelsDir, clean);
}

function resolveMedia(p) {
  const clean = normalize(p).replace(/^(media\/|[/\\])+/, '');
  if (clean.startsWith('..')) return null;
  return join(mediaDir, clean);
}

async function sendFile(res, filePath) {
  try {
    const s = await stat(filePath);
    if (!s.isFile()) throw new Error('not a file');
    const ext = filePath.slice(filePath.lastIndexOf('.'));
    res.writeHead(200, {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      'Content-Length': s.size,
      'Access-Control-Allow-Origin': '*',
    });
    createReadStream(filePath).pipe(res);
  } catch {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: false, error: 'not found' }));
  }
}

function broadcast(cmd, targetClient) {
  const msg = JSON.stringify({ type: 'command', command: cmd });
  let sent = 0;
  for (const [ws, info] of clients) {
    if (ws.readyState !== WebSocket.OPEN) continue;
    if (targetClient && targetClient !== 'all' && info.id !== targetClient) continue;
    ws.send(msg);
    sent++;
  }
  return sent;
}

function makeServer() {
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost');
    const path = routePath(req.url);

    if (req.method === 'GET' && url.pathname === '/health') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, clients: clients.size }));
      return;
    }

    if (req.method === 'POST' && url.pathname === '/cmd') {
      let body = '';
      req.on('data', (c) => (body += c));
      req.on('end', () => {
        let cmd;
        try {
          cmd = JSON.parse(body);
        } catch {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: false, error: 'invalid JSON' }));
          return;
        }
        const target = cmd.client || 'all';
        const id = cmd.id ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
        const outCmd = { ...cmd, id };
        const sent = broadcast(outCmd, target);
        // Fire-and-forget contract: the WS client replies with its own
        // response. For HTTP-only callers we acknowledge receipt.
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, id, deliveredTo: sent }));
      });
      return;
    }

    if (req.method === 'GET' && (path.startsWith('/models/') || url.pathname.startsWith('/models/'))) {
      await sendFile(res, resolveModels(path.startsWith('/models/') ? path : url.pathname));
      return;
    }

    if (req.method === 'GET' && (path.startsWith('/media/') || url.pathname.startsWith('/media/'))) {
      await sendFile(res, resolveMedia(path.startsWith('/media/') ? path : url.pathname));
      return;
    }

    if (req.method === 'GET') {
      const file = resolveStatic(path);
      if (file) {
        await sendFile(res, file);
        return;
      }
    }

    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: false, error: 'not found' }));
  });

  const wss = new WebSocketServer({ server, path: '/' });

  wss.on('connection', (ws) => {
    ws.on('message', (raw) => {
      let msg;
      try {
        msg = JSON.parse(raw.toString());
      } catch {
        return;
      }
      if (msg.type === 'register') {
        clients.set(ws, { id: msg.client || '?' });
        console.log(`[server] client registered: ${msg.client}`);
      } else if (msg.type === 'response' || msg.ok !== undefined) {
        // Echo client responses to all (used by CLI/tests to observe).
        const out = JSON.stringify({ type: 'response', response: msg });
        for (const [w, info] of clients) {
          if (w.readyState === WebSocket.OPEN && w !== ws) w.send(out);
        }
        // Also surface on an HTTP-accessible last-response channel for tests.
        lastResponses.push({ at: Date.now(), response: msg });
        if (lastResponses.length > 50) lastResponses.shift();
      }
    });
    ws.on('close', () => clients.delete(ws));
  });

  return server;
}

const lastResponses = [];

const server = makeServer();
server.listen(port, '127.0.0.1', () => {
  console.log(`avatar-test-server listening on http://127.0.0.1:${port}`);
  console.log(`models dir: ${modelsDir}`);
});

// Extra endpoint for tests to read observed WS responses.
server.on('request', (req, res) => {
  if (req.method === 'GET' && new URL(req.url, 'http://localhost').pathname === '/__responses') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(lastResponses));
  }
});
