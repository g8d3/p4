// Tiny live-reload dev server — zero dependencies, Node stdlib only.
// Serves ./public/* with no-cache + CORS, watches files, bumps /version on change.
// Bind 0.0.0.0 so your phone on the same WiFi can reach it.
//
// Run: node server.js [port]   (default 8080)

const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = Number(process.argv[2] || 8080);
const PUBLIC = path.join(__dirname, "public");

let version = { v: 1, at: new Date().toISOString() };
function bump(reason) {
  version = { v: version.v + 1, at: new Date().toISOString() };
  console.log(`[reload] v${version.v} (${reason})`);
}

// Watch public/ for edits, creations, deletions.
try {
  fs.watch(PUBLIC, { recursive: true }, (_evt, file) => bump(file || "change"));
} catch (e) {
  console.log("[watch] recursive watch not supported, polling mtimes instead");
  const mtimes = new Map();
  setInterval(() => {
    for (const f of fs.readdirSync(PUBLIC)) {
      const p = path.join(PUBLIC, f);
      try {
        const m = fs.statSync(p).mtimeMs;
        if (mtimes.get(f) !== m) {
          mtimes.set(f, m);
          if (mtimes.has(f)) bump(f);
        }
      } catch {}
    }
  }, 500);
}

const MIME = {
  ".js": "text/javascript",
  ".html": "text/html",
  ".json": "application/json",
  ".css": "text/css",
  ".txt": "text/plain",
};

const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://x");
  // CORS + no-cache on everything (critical for phone dev)
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate");
  res.setHeader("Pragma", "no-cache");

  if (url.pathname === "/version") {
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify(version));
    return;
  }
  if (url.pathname === "/") {
    res.setHeader("Content-Type", "text/html");
    res.end(`<h1>live-reload dev server v${version.v}</h1>
<p>Edit <code>server/public/live.js</code> or <code>card.html</code> and your phone updates in ~1s.</p>
<ul><li><a href="/live.js">/live.js</a></li><li><a href="/card.html">/card.html</a></li><li><a href="/version">/version</a></li></ul>`);
    return;
  }

  const file = path.normalize(path.join(PUBLIC, decodeURIComponent(url.pathname)));
  if (!file.startsWith(PUBLIC)) {
    res.statusCode = 403;
    res.end("forbidden");
    return;
  }
  fs.readFile(file, (err, data) => {
    if (err) {
      res.statusCode = 404;
      res.end("not found");
      return;
    }
    res.setHeader("Content-Type", MIME[path.extname(file)] || "application/octet-stream");
    res.end(data);
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`live server on http://0.0.0.0:${PORT}/  (v${version.v})`);
  console.log(`from your phone use http://<THIS-PC-LAN-IP>:${PORT}/`);
});
