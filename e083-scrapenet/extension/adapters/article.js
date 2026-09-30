/* Adapter: generic article — title/author/published/body via
 * readability-lite heuristics (article/main scope, long <p> cluster).
 * Registered after site-specific adapters; matches any host. */
globalThis.SNAdapters.register({
  id: "generic-article", name: "Article", dataset: "articles",
  host_pattern: ".",
  detect: function (url, doc) {
    if (doc.querySelector("article, [itemtype*='Article']")) return true;
    var metas = doc.querySelectorAll("meta");
    for (var i = 0; i < metas.length; i++) {
      var p = (metas[i].getAttribute("property") || "").toLowerCase();
      if (p === "og:type" && /article/i.test(metas[i].getAttribute("content") || "")) return true;
    }
    var long = 0;
    doc.querySelectorAll("p").forEach(function (x) { if ((x.textContent || "").trim().length > 120) long++; });
    return long >= 3;
  },
  extract: function (doc, url) {
    function meta(sel, attr) { var m = doc.querySelector(sel); return m ? (m.getAttribute(attr || "content") || "").trim() : ""; }
    var scope = doc.querySelector("article") || doc.querySelector("main") || doc;
    var paras = [];
    scope.querySelectorAll("p").forEach(function (x) {
      var t = (x.textContent || "").trim();
      if (t.length > 40) paras.push(t);
    });
    var h1 = doc.querySelector("h1");
    return { rows: [{ title: (meta("meta[property='og:title']") || doc.title || (h1 ? h1.textContent : "")).trim().slice(0, 300),
      author: (meta("meta[name='author']") || meta("meta[property='article:author']") || (function () { var a = doc.querySelector("[rel='author'], [class*='author'], [class*='byline']"); return a ? a.textContent : ""; })()).trim().slice(0, 200),
      published: meta("meta[property='article:published_time']") || (function () { var t = doc.querySelector("time[datetime]"); return t ? t.getAttribute("datetime") : ""; })(),
      url: url, body: paras.slice(0, 20).join("\n\n").slice(0, 8000) }] };
  },
  recipe: { id: "generic-article", name: "Article", dataset: "articles", match: "article|news|blog|wiki",
    description: "Title + author + published date + body from article pages (no login).",
    schema: ["title", "author", "published", "url", "body"], where: "client",
    fn: "function transform(raw, ctx) {\n  const out = [];\n  for (const c of (raw.rows || raw.cards || [])) {\n    if (!c.title && !c.body) continue;\n    out.push({ title: (c.title || '').slice(0,300), author: c.author || '', published: c.published || '', url: c.url || ctx.url || '', body: (c.body || '').slice(0,8000) });\n  }\n  return out;\n}" }
});
