/**
 * Static file server for the chair studio viewer.
 *
 * Why this kind of server: a glTF viewer is pure static assets (HTML/JS/CSS/JSON,
 * and .glb/.gltf binaries). No backend logic, no framework — just a tiny static
 * file server with correct MIME types and clean URL handling. This is the
 * simplest thing that hosts a glTF viewer reliably; it also serves .glb/.gltf
 * with the proper media types so the export feature works end-to-end.
 *
 * Run:  npm start   (or: node server.js)
 * Open: http://localhost:5173
 */
import http from "node:http";
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 5190);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".gltf": "model/gltf+json",
  ".glb": "model/gltf-binary",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".wasm": "application/wasm",
  ".woff2": "font/woff2",
};

const server = http.createServer(async (req, res) => {
  try {
    // Strip query string, guard against path traversal, default to index.html.
    let urlPath = decodeURIComponent(req.url.split("?")[0]);
    if (urlPath === "/") urlPath = "/index.html";

    const normalized = path.normalize(urlPath).replace(/^(\.\.[\/\\])+/, "");
    const filePath = path.join(__dirname, normalized);

    // Basic protection: the resolved path must stay inside the project root.
    if (!filePath.startsWith(__dirname)) {
      res.writeHead(403);
      return res.end("Forbidden");
    }

    const data = await fs.readFile(filePath);
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      "Content-Type": MIME[ext] || "application/octet-stream",
      "Cache-Control": "no-store",
    });
    res.end(data);
  } catch (err) {
    if (err.code === "ENOENT") {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      return res.end("404 — Not found");
    }
    res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("500 — Internal server error");
  }
});

server.listen(PORT, () => {
  console.log(`\n  Chair Studio running`);
  console.log(`  ▸ http://localhost:${PORT}`);
  console.log(`  ▸ ctrl-c to stop\n`);
});
