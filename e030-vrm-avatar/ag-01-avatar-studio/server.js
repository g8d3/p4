const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const MODELS_DIR = path.join(ROOT, 'models');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.vrm': 'model/gltf-binary',
  '.png': 'image/png',
  '.css': 'text/css; charset=utf-8',
};

function send(res, status, body, type) {
  res.writeHead(status, { 'Content-Type': type, 'Cache-Control': 'no-cache' });
  res.end(body);
}

function sendFile(res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      send(res, 404, 'Not Found', 'text/plain');
      return;
    }
    const type = MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': type });
    res.end(data);
  });
}

function listModels() {
  try {
    return fs.readdirSync(MODELS_DIR)
      .filter((f) => f.endsWith('.vrm'))
      .sort();
  } catch {
    return [];
  }
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  let p = url.pathname;

  if (p === '/') {
    sendFile(res, path.join(ROOT, 'index.html'));
    return;
  }

  if (p === '/models/manifest.json') {
    const models = listModels().map((name) => ({ name, url: `/models/${name}` }));
    send(res, 200, JSON.stringify(models), 'application/json; charset=utf-8');
    return;
  }

  if (p.startsWith('/models/')) {
    const name = path.basename(p).replace(/\.vrm$/, '');
    const filePath = path.join(MODELS_DIR, `${name}.vrm`);
    if (!filePath.startsWith(MODELS_DIR)) {
      send(res, 403, 'Forbidden', 'text/plain');
      return;
    }
    if (fs.existsSync(filePath)) {
      sendFile(res, filePath);
    } else {
      send(res, 404, 'Not Found', 'text/plain');
    }
    return;
  }

  if (p.startsWith('/lib/')) {
    const filePath = path.join(ROOT, p);
    if (!filePath.startsWith(ROOT)) {
      send(res, 403, 'Forbidden', 'text/plain');
      return;
    }
    if (fs.existsSync(filePath)) {
      sendFile(res, filePath);
    } else {
      send(res, 404, 'Not Found', 'text/plain');
    }
    return;
  }

  send(res, 404, 'Not Found', 'text/plain');
});

server.listen(8787, '0.0.0.0', () => {
  console.log('Avatar Studio listening on http://0.0.0.0:8787');
});