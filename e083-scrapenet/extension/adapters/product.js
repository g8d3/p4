/* Adapter: generic product — JSON-LD first, DOM fallback.
 * Matches any host; detect() requires a real product signal. */
globalThis.SNAdapters.register({
  id: "generic-product", name: "Product", dataset: "products",
  host_pattern: ".",
  detect: function (url, doc) {
    var found = false;
    doc.querySelectorAll('script[type="application/ld+json"]').forEach(function (s) {
      try {
        var j = JSON.parse(s.textContent), arr = Array.isArray(j) ? j : [j];
        if (j && j["@graph"]) arr = arr.concat(j["@graph"]);
        arr.forEach(function (o) { if (o && /product/i.test([].concat(o["@type"] || []).join(","))) found = true; });
      } catch (e) {}
    });
    if (found || doc.querySelector("[itemtype*='Product'], [itemprop='price']")) return true;
    var bodyT = (doc.querySelector("body") || { textContent: "" }).textContent || "";
    var price = /[$€£¥]\s?\d[\d.,]*/.test(bodyT);
    var commerce = /(add to (cart|bag|basket)|buy now|checkout|in stock|availability|add to wishlist)/i.test(bodyT)
      || !!doc.querySelector("[class*='price'],[id*='price'],[class*='buy'],[class*='cart'],[class*='basket'],[class*='checkout']");
    return price && commerce;
  },
  extract: function (doc, url) {
    var ld = [];
    doc.querySelectorAll('script[type="application/ld+json"]').forEach(function (s) {
      try {
        var j = JSON.parse(s.textContent), arr = Array.isArray(j) ? j : [j];
        if (j && j["@graph"]) arr = arr.concat(j["@graph"]);
        arr.forEach(function (o) { ld.push(o); });
      } catch (e) {}
    });
    function meta(sel) { var m = doc.querySelector(sel); return m ? (m.getAttribute("content") || "").trim() : ""; }
    function first(sel) { var m = doc.querySelector(sel); return m ? (m.textContent || "").trim() : ""; }
    var prod = null;
    ld.forEach(function (o) { if (!prod && o && /product/i.test([].concat(o["@type"] || []).join(","))) prod = o; });
    var name, price, cur, img;
    if (prod) {
      var off = prod.offers || {};
      if (Array.isArray(off)) off = off[0] || {};
      name = prod.name || ""; price = off.price || off.lowPrice || ""; cur = off.priceCurrency || "";
      img = [].concat(prod.image || [])[0] || ""; if (typeof img === "object") img = img.url || "";
    } else {
      name = first("[itemprop='name']") || first("h1") || meta("meta[property='og:title']");
      price = (function () { var m = doc.querySelector("[itemprop='price']"); var v = m ? (m.getAttribute("content") || m.textContent) : ""; if (!v) { var t = (doc.querySelector("body") || { textContent: "" }).textContent || ""; var mm = t.match(/[$€£¥]\s?\d[\d.,]*/); v = mm ? mm[0] : ""; } return (v || "").trim(); })();
      cur = meta("meta[property='product:price:currency']"); img = meta("meta[property='og:image']");
    }
    return { rows: [{ name: String(name || "").slice(0, 300), price: String(price || "").slice(0, 50), currency: cur || "", image: img || "", url: url }], raw_extra: { jsonld: ld.slice(0, 10) } };
  },
  recipe: { id: "generic-product", name: "Product", dataset: "products", match: "shop|store|product",
    description: "Name + price + image from product pages, JSON-LD first (no login).",
    schema: ["name", "price", "currency", "image", "url"], where: "client",
    fn: "function transform(raw, ctx) {\n  const out = [];\n  for (const c of (raw.rows || raw.cards || [])) {\n    if (!c.name && !c.price) continue;\n    out.push({ name: (c.name || '').slice(0,300), price: String(c.price || '').slice(0,50), currency: c.currency || '', image: c.image || '', url: c.url || ctx.url || '' });\n  }\n  return out;\n}" }
});
