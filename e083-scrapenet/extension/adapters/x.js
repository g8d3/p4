/* Adapter: X (twitter) timeline — post text/author/time/likes.
 * Needs login on the real site (login wall without a session); the parse
 * itself targets article[data-testid="tweet"] which only exists logged in. */
globalThis.SNAdapters.register({
  id: "x-timeline", name: "X timeline", dataset: "x-posts",
  host_pattern: "(^|\\.)x\\.com$|(^|\\.)twitter\\.com$",
  detect: function (url, doc) {
    return !!doc.querySelector('article[data-testid="tweet"],div[data-testid="tweetText"]');
  },
  extract: function (doc, url) {
    var rows = [];
    doc.querySelectorAll('article[data-testid="tweet"]').forEach(function (a) {
      var t = a.querySelector('div[data-testid="tweetText"]');
      var text = (t ? t.textContent : "").trim();
      var tm = a.querySelector("time");
      var hrefs = Array.prototype.map.call(a.querySelectorAll("a"), function (x) { return x.getAttribute("href") || ""; });
      var lk = hrefs.filter(function (h) { return /^\/[^/]+\/status\/\d+/.test(h); })[0] || "";
      var author = (hrefs.filter(function (h) { return /^\/[A-Za-z0-9_]{1,15}$/.test(h); })[0] || "").slice(1);
      var like = a.querySelector('[data-testid="like"]');
      var likes = (like ? (like.getAttribute("aria-label") || "") : "").replace(/\D+/g, "");
      if (text || tm) rows.push({ text: text.slice(0, 2000), author: author, url: lk ? "https://x.com" + lk : url, posted_at: tm ? tm.getAttribute("datetime") : "", likes: likes });
    });
    return { rows: rows.slice(0, 50) };
  },
  recipe: { id: "x-timeline", name: "X timeline", dataset: "x-posts", match: "x|twitter",
    description: "Post text + author + time + likes from the X timeline (needs login).",
    schema: ["text", "author", "url", "posted_at", "likes"], where: "client",
    fn: "function transform(raw, ctx) {\n  const out = [];\n  for (const c of (raw.rows || raw.cards || [])) {\n    if (!c.text) continue;\n    out.push({ text: String(c.text).slice(0,2000), author: c.author || '', url: c.url || ctx.url || '', posted_at: c.posted_at || '', likes: c.likes || '' });\n  }\n  return out;\n}" }
});
