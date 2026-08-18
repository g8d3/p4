const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.mp3': 'audio/mpeg',
  '.wav': 'audio/wav',
};

function sendFile(res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Not Found');
      return;
    }
    const type = MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': type });
    res.end(data);
  });
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  let p = url.pathname;

  if (p === '/') {
    sendFile(res, path.join(ROOT, 'index.html'));
    return;
  }

  // Inject TTS API keys into the page as globals (never committed to git).
  // The page reads window.KIE_API_KEY / window.DEEPGRAM_API_KEY; when a key is
  // absent the page falls back to browser speech.
  if (p === '/globals.js') {
    const keys = {
      KIE_API_KEY: process.env.KIE_API_KEY || '',
      DEEPGRAM_API_KEY: process.env.DEEPGRAM_API_KEY || '',
    };
    res.writeHead(200, { 'Content-Type': 'text/javascript; charset=utf-8', 'Cache-Control': 'no-cache' });
    res.end(`window.KIE_API_KEY=${JSON.stringify(keys.KIE_API_KEY)};window.DEEPGRAM_API_KEY=${JSON.stringify(keys.DEEPGRAM_API_KEY)};`);
    return;
  }

  if (p.startsWith('/lib/')) {
    const filePath = path.join(ROOT, p);
    if (!filePath.startsWith(ROOT)) {
      res.writeHead(403, { 'Content-Type': 'text/plain' });
      res.end('Forbidden');
      return;
    }
    if (fs.existsSync(filePath)) sendFile(res, filePath);
    else {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Not Found');
    }
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not Found');
});

server.listen(8788, '0.0.0.0', () => {
  console.log('Dream Player listening on http://0.0.0.0:8788');
});
