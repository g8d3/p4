import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { WebSocketServer } from 'ws';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = __dirname;
const MODELS_DIR = path.resolve(ROOT, '..', 'models');
const MEDIA_DIR = path.resolve(ROOT, '..', 'media');
const AG02_DIR = path.resolve(ROOT, '..', 'ag-02-client-b');
const AG03_OUTPUT = path.resolve(ROOT, '..', 'ag-03-video', 'output');
const HOST = "0.0.0.0";
const PORT = 8787;
const COMMAND_TIMEOUT_MS = 20000;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.vrm': 'model/gltf-binary',
  '.glb': 'model/gltf-binary',
  '.mp3': 'audio/mpeg',
  '.wav': 'audio/wav',
  '.pcm': 'application/octet-stream',
};

function sanitizeRel(p) {
  p = String(p || '').replace(/^\/+/, '');
  if (p.includes('..')) return null;
  return p;
}

function sendFile(res, filePath, contentType) {
  fs.stat(filePath, (err, st) => {
    if (err || !st.isFile()) {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: false, error: 'not found' }));
      return;
    }
    res.writeHead(200, {
      'Content-Type': contentType || MIME[path.extname(filePath)] || 'application/octet-stream',
      'Content-Length': st.size,
      'Cache-Control': 'no-store',
    });
    fs.createReadStream(filePath).pipe(res);
  });
}

const clients = new Map(); // id -> Set<ws>
const pending = new Map(); // cmdId -> { targets, responses, resolve, timer }

function registerClient(id, ws) {
  ws.clientId = id;
  if (!clients.has(id)) clients.set(id, new Set());
  clients.get(id).add(ws);
}

function unregisterClient(id, ws) {
  const set = clients.get(id);
  if (!set) return;
  set.delete(ws);
  if (set.size === 0) clients.delete(id);
}

function broadcast(kind, payload, targetIds = null) {
  let sent = 0;
  for (const [id, set] of clients) {
    if (targetIds && !targetIds.includes(id)) continue;
    for (const ws of set) {
      if (ws.readyState === 1) {
        ws.send(JSON.stringify({ type: kind, ...payload }));
        sent++;
      }
    }
  }
  return sent;
}

function resolvePending(cmdId) {
  const p = pending.get(cmdId);
  if (!p) return;
  clearTimeout(p.timer);
  pending.delete(cmdId);
  const results = p.targets.map((id) => p.responses.get(id)).filter(Boolean);
  const all = results.length === p.targets.length && p.targets.length > 0;
  p.resolve({
    ok: all,
    cmdId,
    client: p.targets.length === 1 ? p.targets[0] : p.targets,
    responses: results,
  });
}

function queueCommand(command, sender) {
  const cmd = { ...command };
  const { cmd: name, client: target, ...rest } = cmd;
  const targets = Array.isArray(target) ? target : target && target !== 'all' ? [target] : [...clients.keys()];
  if (targets.length === 0) {
    return Promise.resolve({ ok: false, error: 'no clients connected', clients: [...clients.keys()] });
  }
  const cmdId = cmd.cmdId || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const p = { targets, responses: new Map(), sender, timer: null };
  const promise = new Promise((resolve) => {
    p.resolve = resolve;
    p.timer = setTimeout(() => {
      pending.delete(cmdId);
      resolve({
        ok: false,
        error: `timeout after ${COMMAND_TIMEOUT_MS}ms`,
        cmdId,
        client: targets,
        responses: targets.map((id) => p.responses.get(id)).filter(Boolean),
      });
    }, COMMAND_TIMEOUT_MS);
  });
  pending.set(cmdId, p);
  const payload = { cmd: name, cmdId, ...rest };
  const sent = broadcast('cmd', payload, targets);
  if (sent === 0) {
    clearTimeout(p.timer);
    pending.delete(cmdId);
    return Promise.resolve({ ok: false, error: 'no connected client matched target', client: targets });
  }
  return promise;
}

function handleCmdMessage(msg) {
  if (!msg || typeof msg !== 'object') return;
  if (msg.type === 'register') {
    const id = String(msg.id || '');
    if (!id) return;
    registerClient(id, msg.ws);
    msg.ws.send(JSON.stringify({ type: 'registered', id, server: 'avatar-server', protocol: '1.0' }));
    return;
  }
  if (msg.type === 'cmdResponse') {
    const p = pending.get(msg.cmdId);
    if (!p) return;
    const rid = msg.clientId || msg.client || msg.ws.clientId;
    if (!rid || !p.targets.includes(rid)) return;
    const { ws: _ws, type: _t, ...clean } = msg;
    if (!p.responses.has(rid)) p.responses.set(rid, clean);
    if (p.responses.size >= p.targets.length) resolvePending(msg.cmdId);
    return;
  }
  if (msg.type === 'cmd' || msg.cmd) {
    const command = msg.cmd ? { ...msg } : { ...msg };
    delete command.type;
    queueCommand(command, msg.ws).then((result) => {
      if (msg.ws && msg.ws.readyState === 1) {
        msg.ws.send(JSON.stringify({ type: 'cmdResponse', ...result }));
      }
    });
    return;
  }
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${HOST}:${PORT}`);

  if (req.method === 'GET' && (url.pathname === '/health' || url.pathname === '/health/')) {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, server: 'avatar-server', protocol: '1.0', clients: [...clients.keys()], pid: process.pid }));
    return;
  }

  if (req.method === 'POST' && url.pathname === '/cmd') {
    let body = '';
    req.on('data', (c) => { body += c; if (body.length > 1e6) req.destroy(); });
    req.on('end', () => {
      let command;
      try { command = JSON.parse(body); } catch {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: false, error: 'invalid JSON' }));
        return;
      }
      queueCommand(command, null).then((result) => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        try {
          res.end(JSON.stringify({ ...command, ...result }));
        } catch (err) {
          res.end(JSON.stringify({ ok: false, error: `serialization failed: ${err.message}`, cmdId: command.cmdId }));
        }
      });
    });
    return;
  }

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: false, error: 'method not allowed' }));
    return;
  }

  let p = url.pathname;
  if (p === '/') p = '/viewer.html';

  if (p === '/viewer.html') {
    sendFile(res, path.join(ROOT, 'viewer.html'), MIME['.html']);
    return;
  }

  if (p === '/viewer-b.html') {
    sendFile(res, path.join(AG02_DIR, 'viewer-b.html'), MIME['.html']);
    return;
  }

  const clientBPrefix = '/client-b/';
  if (p.startsWith(clientBPrefix)) {
    const rel = sanitizeRel(p.slice(clientBPrefix.length));
    if (!rel) { res.writeHead(403); res.end('forbidden'); return; }
    sendFile(res, path.join(AG02_DIR, rel));
    return;
  }

  const vend = '/vendor/';
  if (p.startsWith(vend)) {
    const rel = sanitizeRel(p.slice(vend.length));
    if (!rel) { res.writeHead(403); res.end('forbidden'); return; }
    sendFile(res, path.join(ROOT, 'node_modules', rel));
    return;
  }

  const modelsPrefix = '/models/';
  if (p.startsWith(modelsPrefix)) {
    const rel = sanitizeRel(p.slice(modelsPrefix.length));
    if (!rel) { res.writeHead(403); res.end('forbidden'); return; }
    sendFile(res, path.join(MODELS_DIR, rel));
    return;
  }

  const mediaPrefix = '/media/';
  if (p.startsWith(mediaPrefix)) {
    const rel = sanitizeRel(p.slice(mediaPrefix.length));
    if (!rel) { res.writeHead(403); res.end('forbidden'); return; }
    const shared = path.join(MEDIA_DIR, rel);
    const ag03 = path.join(AG03_OUTPUT, rel);
    fs.stat(shared, (err, st) => {
      if (!err && st.isFile()) { sendFile(res, shared); return; }
      fs.stat(ag03, (err2, st2) => {
        if (!err2 && st2.isFile()) { sendFile(res, ag03); return; }
        sendFile(res, path.join(MEDIA_DIR, rel));
      });
    });
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ ok: false, error: 'not found', path: p }));
});

const wss = new WebSocketServer({ server, path: '/' });
wss.on('connection', (ws) => {
  ws.isClient = false;
  ws.on('message', (data) => {
    let msg;
    try { msg = JSON.parse(data.toString()); } catch { return; }
    if (typeof msg === 'object') {
      msg.ws = ws;
      handleCmdMessage(msg);
    }
  });
  ws.on('close', () => {
    if (ws.clientId) unregisterClient(ws.clientId, ws);
  });
  ws.send(JSON.stringify({ type: 'hello', server: 'avatar-server', protocol: '1.0' }));
});

server.listen(PORT, HOST, () => {
  console.log(`avatar-server listening on http://${HOST}:${PORT}`);
  console.log(`models: ${MODELS_DIR}`);
  console.log(`media: ${MEDIA_DIR}`);
});