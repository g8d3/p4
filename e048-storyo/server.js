import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = 8180;
const ORIGIN = "https://infiniteslop.ai";
const cloneDir = path.join(__dirname, "clone");

// MIME map
const mime = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript",
  ".mjs": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
  ".m3u8": "application/vnd.apple.mpegurl",
  ".ts": "video/mp2t",
  ".mp4": "video/mp4",
  ".woff2": "font/woff2",
};

// Proxy helper: fetch from origin and pipe back
async function proxy(req, res, targetPath) {
  const url = `${ORIGIN}${targetPath}`;
  try {
    const headers = {};
    // forward relevant headers
    if (req.headers["content-type"]) headers["content-type"] = req.headers["content-type"];
    if (req.headers["content-length"]) headers["content-length"] = req.headers["content-length"];
    if (req.headers.cookie) headers.cookie = req.headers.cookie;

    let body;
    if (req.method !== "GET" && req.method !== "HEAD") {
      body = await new Promise((resolve) => {
        const chunks = [];
        req.on("data", (c) => chunks.push(c));
        req.on("end", () => resolve(Buffer.concat(chunks)));
      });
      if (body.length === 0) body = undefined;
    }

    const r = await fetch(url, {
      method: req.method,
      headers,
      body,
      redirect: "follow",
    });

    // copy status and headers
    const outHeaders = {};
    for (const [k, v] of r.headers.entries()) {
      if (["content-encoding", "content-length", "transfer-encoding", "connection"].includes(k.toLowerCase())) continue;
      outHeaders[k] = v;
    }
    // CORS for local dev
    outHeaders["access-control-allow-origin"] = "*";
    outHeaders["access-control-allow-methods"] = "GET,POST,PUT,DELETE,OPTIONS";
    outHeaders["access-control-allow-headers"] = "content-type,authorization";
    // cache
    if (targetPath.includes(".m3u8") || targetPath.includes(".ts")) {
      outHeaders["cache-control"] = "no-cache";
    }

    res.writeHead(r.status, outHeaders);
    if (req.method === "HEAD") return res.end();
    const buf = Buffer.from(await r.arrayBuffer());
    res.end(buf);
  } catch (e) {
    console.error("proxy error", targetPath, e.message);
    res.writeHead(502, { "content-type": "application/json", "access-control-allow-origin": "*" });
    res.end(JSON.stringify({ error: "proxy failed", detail: e.message }));
  }
}

function serveStatic(req, res, pathname) {
  // normalize
  let fp = pathname;
  if (fp === "/" || fp === "") fp = "/index.html";
  // prevent traversal
  fp = path.normalize(fp).replace(/^\/+/, "");
  let full = path.join(cloneDir, fp);
  // if directory, try index.html
  try {
    const stat = fs.statSync(full);
    if (stat.isDirectory()) full = path.join(full, "index.html");
  } catch {}
  // fallback to clone/index.html for SPA? no, 404
  if (!fs.existsSync(full)) return false;
  const ext = path.extname(full).toLowerCase();
  const ct = mime[ext] || "application/octet-stream";
  const data = fs.readFileSync(full);
  res.writeHead(200, {
    "content-type": ct,
    "cache-control": ext === ".html" ? "no-cache" : "public, max-age=3600",
    "access-control-allow-origin": "*",
  });
  res.end(data);
  return true;
}

const adminHtml = `<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Admin - e048</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-zinc-950 text-white min-h-screen p-6">
<h1 class="text-xl font-bold">🔧 Admin Feedback — storyo.cc — cloned from infiniteslop.ai</h1><p class="text-zinc-400 text-sm">Storyo.cc — infinite stories, chat decides next · proxy live from infiniteslop.ai</p>
<div class="mt-6 grid gap-4 max-w-2xl">
  <div class="bg-zinc-900 p-4 rounded-xl border border-zinc-800"><h3 class="text-sm font-medium">💰 Costos hoy (Minimax H3 Max)</h3><p class="text-2xl font-mono mt-1">$0.00 <span class="text-zinc-500 text-sm">/ estimado</span></p><p class="text-xs text-zinc-500">$0.025/s @480p → $90/hora · L1 trial 6fps abarata</p></div>
  <div class="bg-zinc-900 p-4 rounded-xl border border-zinc-800"><h3 class="text-sm font-medium">📖 Character Bible</h3><textarea class="w-full mt-2 bg-black border border-zinc-800 rounded-lg p-3 text-xs font-mono h-24">{"characters":{"laura":"mujer 28, campera roja"},"style":"dark anime","rules":["NEVER change red jacket"]}</textarea></div>
  <div class="bg-zinc-900 p-4 rounded-xl border border-zinc-800"><h3 class="text-sm font-medium">📝 Living Summary</h3><textarea class="w-full mt-2 bg-black border border-zinc-800 rounded-lg p-3 text-xs h-20">Ep1: Laura llega a mansión -> Ep2: encuentra llave...</textarea></div>
  <div class="bg-zinc-900 p-4 rounded-xl border border-zinc-800"><h3 class="text-sm font-medium">🎬 Clone status</h3><p class="text-xs text-zinc-400 mt-2">Sirviendo <code>clone/index.html</code> idéntico al original (68KB HTML + 406KB hls.min.js). <br>Proxy: <code>/api/*</code>, <code>/status.json</code>, <code>/live/*</code> → <code>https://infiniteslop.ai</code></p><p class="text-xs text-green-400 mt-2">✓ Clon fiel activo en /</p><p class="text-xs text-zinc-500">Origen clon: <a href="https://infiniteslop.ai" target="_blank" class="underline">infiniteslop.ai</a> por @levelsio + fal.ai</p></div>
</div>
<p class="mt-6 text-center"><a href="/" class="text-sm text-zinc-500 underline">← Volver al player (clon)</a> · <a href="/api/health" class="text-sm text-zinc-500 underline">/api/health</a></p>
</body></html>`;

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const pathname = url.pathname;
  const search = url.search;

  // CORS preflight
  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "GET,POST,PUT,DELETE,OPTIONS",
      "access-control-allow-headers": "content-type,authorization",
      "access-control-max-age": "86400",
    });
    return res.end();
  }

  // Admin
  if (pathname === "/admin") {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    return res.end(adminHtml);
  }
  if (pathname === "/api/health") {
    res.writeHead(200, { "Content-Type": "application/json", "access-control-allow-origin": "*" });
    return res.end(JSON.stringify({ ok: true, exp: "storyo.cc", clone: "infiniteslop.ai", port: PORT, origin: ORIGIN }));
  }

  // Proxy API + live + status
  if (
    pathname.startsWith("/api/") ||
    pathname === "/status.json" ||
    pathname.startsWith("/live/") ||
    pathname === "/og.jpg" ||
    pathname.startsWith("/api")
  ) {
    return proxy(req, res, pathname + search);
  }

  // Storyo branded at /, original clone at /original
  if (pathname === "/original" || pathname === "/original/") {
    const orig = path.join(cloneDir, "original.html");
    if (fs.existsSync(orig)) {
      res.writeHead(200, {"content-type":"text/html; charset=utf-8","cache-control":"no-cache","access-control-allow-origin":"*"});
      return res.end(fs.readFileSync(orig));
    }
  }
  // Static clone (branded index.html at /)
  if (serveStatic(req, res, pathname + search.split("?")[0].replace(/\?.*/, ""))) return;

  // Fallback: try index.html for root-ish
  if (serveStatic(req, res, "/index.html")) return;

  res.writeHead(404, { "Content-Type": "text/plain" });
  res.end("404");
});

server.listen(PORT, "0.0.0.0", () => console.log(`storyo.cc listening on 0.0.0.0:${PORT} → proxy ${ORIGIN} (clone/index.html)`));
