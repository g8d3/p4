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
  ".js": "text/javascript; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
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
  // ---- diagnostics API: loaders phone home so no human relays screenshots ----
  if (req.method === "OPTIONS") {
    res.statusCode = 204; // preflight (page-context POSTs)
    res.end();
    return;
  }
  const REPORTS = path.join(__dirname, "reports.log"); // JSON lines, gitignored
  if (url.pathname === "/api/report" && req.method === "POST") {
    let chunks = [];
    let n = 0;
    req.on("data", (c) => {
      n += c.length;
      if (n > 65536) req.destroy();
      else chunks.push(c);
    });
    req.on("end", () => {
      try {
        const body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
        body.receivedAt = new Date().toISOString();
        body.ip = req.socket.remoteAddress;
        fs.appendFile(REPORTS, JSON.stringify(body) + "\n", () => {});
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end('{"ok":true}');
      } catch {
        res.statusCode = 400;
        res.end('{"ok":false}');
      }
    });
    return;
  }
  if (url.pathname === "/api/reports") {
    fs.readFile(REPORTS, "utf8", (err, data) => {
      const lines = err ? [] : data.trim().split("\n").filter(Boolean).slice(-50);
      const items = lines
        .map((l) => {
          try {
            return JSON.parse(l);
          } catch {
            return null;
          }
        })
        .filter(Boolean)
        .reverse();
      res.setHeader("Content-Type", "application/json; charset=utf-8");
      res.end(JSON.stringify(items));
    });
    return;
  }

  if (url.pathname === "/" || url.pathname === "/index.html") {
    // The experiment page IS the entry point: install, status, run, scripts.
    // Served from repo root so there is exactly one copy.
    const page = path.join(__dirname, "..", "index.html");
    fs.readFile(page, (err, data) => {
      if (err) {
        res.statusCode = 500;
        res.end("index.html missing");
        return;
      }
      res.setHeader("Content-Type", "text/html; charset=utf-8");
      res.end(data);
    });
    return;
  }

  // Install artifacts: single copy at repo root, always installable from the phone.
  const ARTIFACTS = {
    "/live-reload.user.js": {
      file: path.join(__dirname, "..", "live-reload.user.js"),
      type: "text/javascript; charset=utf-8",
    },
    "/live-reload-ext.zip": {
      file: path.join(__dirname, "..", "dist", "live-reload-ext.zip"),
      type: "application/zip",
    },
  };
  if (ARTIFACTS[url.pathname]) {
    const a = ARTIFACTS[url.pathname];
    fs.readFile(a.file, (err, data) => {
      if (err) {
        res.statusCode = 404;
        res.end("artifact missing — did you set SERVER IP and rebuild the zip?");
        return;
      }
      res.setHeader("Content-Type", a.type);
      res.end(data);
    });
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
