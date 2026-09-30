#!/usr/bin/env node
/* Headless adapter unit asserts (node, zero deps). Loads the real adapter
 * files with a minimal fake DOM (same CSS subset the adapters use), so
 * adapter logic is tested without a browser. Real-page proof happens in the
 * driven browser (see ADAPTERS-E083-REPORT.md); this file guards regressions.
 * Exit 0 = all pass. */
"use strict";
const fs = require("fs");
const path = require("path");
const EXTD = path.join(__dirname, "..", "extension");
const AD = path.join(EXTD, "adapters");

let pass = 0;
function ok(cond, label) {
  if (!cond) { console.error("FAIL: " + label); process.exit(1); }
  pass++;
  console.log("ok: " + label);
}

/* ---------- minimal fake DOM ---------- */
const VOID = new Set(["meta", "input", "br", "img", "link", "hr", "area", "base", "col", "embed", "source", "track", "wbr"]);
class El {
  constructor(tag, attrs, parent) {
    this.tag = (tag || "").toLowerCase();
    this.attrs = attrs || {};
    this.kids = [];
    this.text = "";
    this.parent = parent || null;
  }
  get textContent() {
    return [this.text, ...this.kids.map((k) => k.textContent)].filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
  }
  getAttribute(n) {
    n = String(n).toLowerCase();
    return Object.prototype.hasOwnProperty.call(this.attrs, n) ? this.attrs[n] : null;
  }
  querySelectorAll(sel) { return select(this, sel); }
  querySelector(sel) { return select(this, sel)[0] || null; }
}
function parseAttrs(s) {
  const attrs = {};
  const re = /([A-Za-z0-9_:.-]+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s"'=<>`]+))?/g;
  let m;
  while ((m = re.exec(s))) {
    let v = m[2] || "";
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
    attrs[m[1].toLowerCase()] = v;
  }
  return attrs;
}
function parseHTML(html) {
  const root = new El("root", {});
  const stack = [root];
  let i = 0;
  const rawTag = (name) => {
    const close = new RegExp("</" + name + "\\s*>", "i");
    const rest = html.slice(i);
    const m = close.exec(rest);
    const end = m ? i + m.index + m[0].length : html.length;
    const body = m ? rest.slice(0, m.index) : rest;
    i = end;
    return body;
  };
  while (i < html.length) {
    const lt = html.indexOf("<", i);
    if (lt < 0) { stack[stack.length - 1].text += html.slice(i); break; }
    if (lt > i) stack[stack.length - 1].text += html.slice(i, lt);
    if (html.startsWith("<!--", lt)) {
      const end = html.indexOf("-->", lt + 4);
      i = end < 0 ? html.length : end + 3;
      continue;
    }
    const gt = html.indexOf(">", lt + 1);
    if (gt < 0) break;
    const inner = html.slice(lt + 1, gt).trim();
    i = gt + 1;
    if (!inner || inner.startsWith("!")) continue;
    if (inner[0] === "/") {
      const tag = inner.slice(1).split(/\s/)[0].toLowerCase();
      for (let k = stack.length - 1; k > 0; k--) {
        if (stack[k].tag === tag) { stack.length = k; break; }
      }
      continue;
    }
    const selfClose = inner.endsWith("/");
    const parts = (selfClose ? inner.slice(0, -1) : inner).trim().split(/\s+/);
    const tag = parts[0].toLowerCase();
    const attrs = parseAttrs((selfClose ? inner.slice(0, -1) : inner).slice(tag.length));
    const el = new El(tag, attrs, stack[stack.length - 1]);
    stack[stack.length - 1].kids.push(el);
    if (tag === "script" || tag === "style") { el.text = rawTag(tag); continue; }
    if (!VOID.has(tag) && !selfClose) stack.push(el);
  }
  return root;
}
function parseSimple(tok) {
  let nth = null;
  const nm = tok.match(/:nth-child\((\d+)\)$/);
  if (nm) { nth = parseInt(nm[1], 10); tok = tok.slice(0, nm.index); }
  const m = tok.match(/^([A-Za-z][A-Za-z0-9_-]*|\*)/);
  let tag = null, id = null;
  const classes = [], attrs = [];
  let i = 0;
  if (m) { tag = m[1].toLowerCase(); i = m[0].length; }
  while (i < tok.length) {
    const c = tok[i];
    if (c === "#") {
      const mm = tok.slice(i).match(/^#([A-Za-z0-9_-]+)/);
      if (!mm) return null;
      id = mm[1]; i += mm[0].length;
    } else if (c === ".") {
      const mm = tok.slice(i).match(/^\.([A-Za-z0-9_-]+)/);
      if (!mm) return null;
      classes.push(mm[1]); i += mm[0].length;
    } else if (c === "[") {
      const j = tok.indexOf("]", i);
      if (j < 0) return null;
      const inner = tok.slice(i + 1, j);
      const mm = inner.match(/^([A-Za-z0-9_-]+)(\^=|\*=|=)?(?:"([^"]*)"|'([^']*)'|([^\]"']*))?$/);
      if (!mm) return null;
      attrs.push([mm[1].toLowerCase(), mm[2] || "", mm[3] ?? mm[4] ?? mm[5] ?? ""]);
      i = j + 1;
    } else return null;
  }
  if (!tag && !id && !classes.length && !attrs.length && nth === null) return null;
  return { tag, id, classes, attrs, nth };
}
function matchSimple(el, s) {
  if (s.tag && s.tag !== "*" && el.tag !== s.tag) return false;
  if (s.id !== null && (el.attrs.id || "") !== s.id) return false;
  if (s.classes.length) {
    const have = new Set((el.attrs.class || "").split(/\s+/));
    if (s.classes.some((c) => !have.has(c))) return false;
  }
  for (const [n, op, v] of s.attrs) {
    const have = el.attrs[n];
    if (have === undefined) return false;
    if (op === "=" && have !== v) return false;
    if (op === "^=" && !have.startsWith(v)) return false;
    if (op === "*=" && !have.includes(v)) return false;
  }
  if (s.nth !== null) {
    if (!el.parent) return false;
    const sibs = el.parent.kids.filter((k) => k.tag);
    if (sibs.indexOf(el) + 1 !== s.nth) return false;
  }
  return true;
}
function desc(el) {
  const out = [];
  for (const k of el.kids) { out.push(k); out.push(...desc(k)); }
  return out;
}
function select(root, selector) {
  const out = [], seen = new Set();
  for (const grp of selector.split(",")) {
    const chain = grp.trim().split(/\s+/).map(parseSimple);
    if (!chain.length || chain.some((s) => !s)) continue;
    let cur = [root];
    for (const s of chain) {
      const nxt = [];
      for (const el of cur) for (const d of desc(el)) if (matchSimple(d, s)) nxt.push(d);
      cur = nxt;
    }
    for (const el of cur) if (!seen.has(el)) { seen.add(el); out.push(el); }
  }
  return out;
}
function fakeDoc(html, title) {
  const root = parseHTML(html);
  return {
    title: title || "",
    querySelectorAll: (sel) => select(root, sel),
    querySelector: (sel) => select(root, sel)[0] || null,
  };
}

/* ---------- load real adapter files ---------- */
const registrySrc = fs.readFileSync(path.join(AD, "registry.js"), "utf8");
eval(registrySrc); // sets globalThis.SNAdapters
const SN = globalThis.SNAdapters;
for (const f of ["x.js", "google.js", "product.js", "article.js"]) {
  eval(fs.readFileSync(path.join(AD, f), "utf8"));
}

/* ---------- asserts ---------- */
ok(SN.list.length >= 4, "registry has >=4 adapters (got " + SN.list.length + ")");
ok(new Set(SN.list.map((a) => a.id)).size === SN.list.length, "adapter ids unique");
for (const a of SN.list) {
  ok(/^[a-z0-9-]+$/.test(a.id) && a.recipe && a.recipe.id && a.recipe.dataset, "adapter " + a.id + " has recipe binding");
  ok(["client", "server", "both"].includes(a.recipe.where), "adapter " + a.id + " recipe.where valid");
}

// X timeline
const XURL = "https://x.com/home";
const XHTML = `<div><article data-testid="tweet"><a href="/elonmusk">x</a><div data-testid="tweetText">hello mars</div><a href="/elonmusk/status/123">t</a><time datetime="2026-09-01T00:00:00Z">x</time><div data-testid="like" aria-label="42 Likes">x</div></article></div>`;
ok(SN.detect(XURL, fakeDoc(XHTML))?.id === "x-timeline", "x detect fires on tweet markup");
ok(SN.detect(XURL, fakeDoc("<div>login wall</div>")) === null, "x detect silent on login wall");
{
  const { rows } = SN.detect(XURL, fakeDoc(XHTML)).extract(fakeDoc(XHTML), XURL);
  ok(rows.length === 1 && rows[0].text === "hello mars" && rows[0].author === "elonmusk" && rows[0].posted_at.startsWith("2026") && rows[0].likes === "42" && rows[0].url.includes("/status/123"), "x extract text/author/time/likes/url");
}

// Google search
const GURL = "https://www.google.com/search?q=scrapenet";
const GHTML = `<div id="search"><div class="g"><a href="/url?q=https://example.com/a&sa=U&ved=1"><h3>Alpha</h3></a><div class="VwiC3b">first snippet</div></div><div class="g"><a href="https://example.com/b"><h3>Beta</h3></a><div data-sncf="1">second snippet</div></div></div>`;
ok(SN.detect(GURL, fakeDoc(GHTML))?.id === "google-search", "google detect fires on results page");
ok(SN.detect("https://www.google.com/", fakeDoc(GHTML)) === null, "google detect silent off /search");
{
  const { rows } = SN.detect(GURL, fakeDoc(GHTML)).extract(fakeDoc(GHTML), GURL);
  ok(rows.length === 2 && rows[0].rank === 1 && rows[0].title === "Alpha" && rows[0].url === "https://example.com/a" && rows[0].snippet === "first snippet" && rows[0].query === "scrapenet", "google extract unwraps /url?q= + rank/snippet/query");
}

// Generic article
const AURL = "https://en.wikipedia.org/wiki/Web_scraping";
const AHTML = `<head><meta property="og:title" content="Web scraping"><meta name="author" content="Wiki Ed"></head><article><h1>Web scraping</h1><p>${"lorem ipsum dolor sit amet. ".repeat(20)}</p><p>${"more text here yes. ".repeat(20)}</p><p>${"third paragraph wow. ".repeat(20)}</p><time datetime="2026-01-02">x</time></article>`;
ok(SN.detect(AURL, fakeDoc(AHTML, "fallback"))?.id === "generic-article", "article detect fires (product registered but no product signal)");
{
  const { rows } = SN.list.find((a) => a.id === "generic-article").extract(fakeDoc(AHTML, "fallback"), AURL);
  ok(rows.length === 1 && rows[0].title === "Web scraping" && rows[0].author === "Wiki Ed" && rows[0].published === "2026-01-02" && rows[0].body.length > 200, "article extract title/author/published/body");
}

// Generic product: JSON-LD first
const PURL = "https://shop.example/p/9";
const PLD = `<head><script type="application/ld+json">{"@context":"x","@type":"Product","name":"Acme Phone","image":"https://shop.example/i.jpg","offers":{"@type":"AggregateOffer","lowPrice":"15.0","highPrice":"20.0","priceCurrency":"USD"}}</script></head><body><h1>Acme Phone</h1></body>`;
ok(SN.detect(PURL, fakeDoc(PLD))?.id === "generic-product", "product detect fires on JSON-LD");
{
  const out = SN.list.find((a) => a.id === "generic-product").extract(fakeDoc(PLD), PURL);
  ok(out.rows[0].name === "Acme Phone" && out.rows[0].price === "15.0" && out.rows[0].currency === "USD" && out.rows[0].image.includes("i.jpg"), "product extract prefers JSON-LD (AggregateOffer lowPrice)");
  ok(Array.isArray(out.raw_extra.jsonld) && out.raw_extra.jsonld.length === 1, "product raw carries jsonld for server ops");
}
// Generic product: DOM fallback (incl. books.toscrape live shape: no basket form)
const PDOM = `<body><h1>Cheap Widget</h1><p class="price_color">Only $9.99 today</p><p class="instock availability">In stock (22 available)</p></body>`;
ok(SN.detect(PURL, fakeDoc(PDOM))?.id === "generic-product", "product detect fires on price+buy DOM signal");
{
  const { rows } = SN.list.find((a) => a.id === "generic-product").extract(fakeDoc(PDOM), PURL);
  ok(rows[0].name === "Cheap Widget" && rows[0].price === "$9.99", "product DOM fallback name/price");
}
ok(SN.detect("https://example.com/", fakeDoc("<body><p>hi</p></body>")) === null, "no adapter fires on plain page");

// stripSnapshot privacy
{
  const dirty = `<html><!-- secret --><head><script>var token="abc";</script><script type="application/ld+json">{"@type":"Product"}</script></head><body><input type="password" value="hunter2"><textarea>ssn 123</textarea><select><option>visa</option></select><div class="p" password="x">hi</div><p>visible $5</p></body></html>`;
  const s = SN.stripSnapshot(dirty);
  ok(!s.html.includes("hunter2") && !s.html.includes("ssn") && !s.html.includes('var token') && !s.html.includes("<input") && !s.html.includes("<textarea") && !s.html.includes("secret"), "stripSnapshot removes inputs/secrets/scripts/comments");
  ok(s.html.includes("Product") && s.html.includes("visible $5"), "stripSnapshot keeps JSON-LD + content");
  const big = SN.stripSnapshot("x".repeat(200 * 1024));
  ok(big.html.length === 100 * 1024 && big.truncated === true, "stripSnapshot caps at 100KB");
}

// manifest validation
{
  const m = JSON.parse(fs.readFileSync(path.join(EXTD, "manifest.json"), "utf8"));
  ok(m.manifest_version === 3, "manifest v3");
  const js = (m.content_scripts || [])[0].js || [];
  for (const f of ["adapters/registry.js", "adapters/x.js", "adapters/google.js", "adapters/product.js", "adapters/article.js", "content.js"]) {
    ok(js.includes(f) && fs.existsSync(path.join(EXTD, f)), "manifest loads " + f + " (file exists)");
  }
}

console.log(`\nPASS (${pass} asserts)`);
