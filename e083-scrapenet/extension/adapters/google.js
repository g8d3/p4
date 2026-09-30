/* Adapter: Google search results — title/url/snippet/rank.
 * Works logged out (no login needed); unwraps /url?q= redirect links. */
globalThis.SNAdapters.register({
  id: "google-search", name: "Google search", dataset: "google-results",
  host_pattern: "(^|\\.)google\\.[a-z.]+$",
  detect: function (url, doc) {
    return /\/search/.test(url) && !!doc.querySelector("div#search div.g, div#search a h3");
  },
  extract: function (doc, url) {
    var q = ""; try { q = new URL(url).searchParams.get("q") || ""; } catch (e) {}
    var rows = [], rank = 0;
    doc.querySelectorAll("div#search div.g").forEach(function (g) {
      var h = g.querySelector("a h3") || g.querySelector("h3");
      var a = g.querySelector("a");
      var href = a ? (a.getAttribute("href") || "") : "";
      var m = href.match(/\/url\?q=([^&]+)/); if (m) { try { href = decodeURIComponent(m[1]); } catch (e) {} }
      var sn = g.querySelector("[data-sncf], .VwiC3b, .yXK7lf");
      var title = (h ? h.textContent : "").trim();
      if (!title || /^https?:/.test(href) === false) return;
      rank++;
      rows.push({ rank: rank, title: title.slice(0, 300), url: href.slice(0, 500), snippet: (sn ? sn.textContent : "").trim().slice(0, 500), query: q });
    });
    return { rows: rows.slice(0, 30) };
  },
  recipe: { id: "google-search", name: "Google search", dataset: "google-results", match: "google",
    description: "Ranked title + url + snippet rows from a Google results page (no login).",
    schema: ["rank", "title", "url", "snippet", "query"], where: "client",
    fn: "function transform(raw, ctx) {\n  const out = [];\n  for (const c of (raw.rows || raw.cards || [])) {\n    if (!c.title || !c.url) continue;\n    out.push({ rank: c.rank || 0, title: String(c.title).slice(0,300), url: c.url || '', snippet: (c.snippet || '').slice(0,500), query: c.query || '' });\n  }\n  return out;\n}" }
});
