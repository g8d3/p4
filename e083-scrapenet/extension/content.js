/* ScrapeNet content script (vanilla). Runs on all pages but only acts when
 * the current host is user-enabled in extension storage.
 * Pipeline: adapter detect -> extract -> recipe transform (per recipe.where)
 *   client: recipe.fn runs locally (private, default)
 *   server: raw + recipe go to POST /api/transform (declarative ops only)
 *   both:    run both, merge-dedupe
 * -> background -> collector /api/ingest.
 * Visit-time suggest: replies to scrapenet:detect (popup badge) and
 * scrapenet:snapshot (stripped DOM, capped 100KB, no inputs/passwords). */
(function () {
  const host = location.hostname;
  const AD = (typeof SNAdapters !== "undefined") ? SNAdapters : null;

  async function state() {
    return new Promise((res) => {
      chrome.storage.sync.get(
        { enabledHosts: [], activeRecipe: "product-price", collectorBase: "" },
        res
      );
    });
  }

  function enabled(s) {
    return (s.enabledHosts || []).some((h) => host === h || host.endsWith("." + h) || h === "*");
  }

  function hookNet() {
    const report = (url) => {
      try {
        chrome.runtime.sendMessage({ type: "scrapenet:noteRequest", url: String(url).slice(0, 300), host });
      } catch (e) { /* worker may be asleep */ }
    };
    if (window.fetch && !window.fetch.__sn) {
      const of = window.fetch;
      const nf = function (...a) {
        try { report(a[0] && a[0].url ? a[0].url : a[0]); } catch (e) {}
        return of.apply(this, a);
      };
      nf.__sn = true;
      window.fetch = nf;
    }
    const oo = XMLHttpRequest.prototype.open;
    if (!oo.__sn) {
      XMLHttpRequest.prototype.open = function (m, url, ...rest) {
        try { report(url); } catch (e) {}
        return oo.call(this, m, url, ...rest);
      };
      XMLHttpRequest.prototype.open.__sn = true;
    }
  }

  // --- legacy raw capture (fallback when no adapter matches) ---
  function rawCaptureLegacy() {
    const cards = [];
    document.querySelectorAll('[itemtype*="Product"], [class*="product"], [class*="card"], [class*="item"]').forEach((el) => {
      const txt = (sel) => (el.querySelector(sel) || {}).textContent || "";
      const name = (el.querySelector('[itemprop="name"]') || {}).textContent
        || txt("h1,h2,h3,.title,.name") || "";
      const price = (el.querySelector('[itemprop="price"]') || {}).content
        || (el.querySelector('[itemprop="price"]') || {}).textContent
        || [...el.textContent.matchAll(/[$€£]\s?[\d.,]+/g)].map((m) => m[0])[0] || "";
      const url = (el.querySelector("a") || {}).href || location.href;
      if (name.trim() || price) cards.push({ name: name.trim().slice(0, 200), price: String(price).slice(0, 50), url });
    });
    document.querySelectorAll('script[type="application/ld+json"]').forEach((s) => {
      try {
        const j = JSON.parse(s.textContent);
        const arr = Array.isArray(j) ? j : [j];
        arr.forEach((o) => {
          if (o && /Product|JobPosting/i.test(o["@type"] || "")) {
            cards.push({
              name: o.name || "", title: o.title || "",
              price: (o.offers && o.offers.price) || "",
              company: (o.hiringOrganization && o.hiringOrganization.name) || "",
              location: (o.jobLocation && o.jobLocation.address && o.jobLocation.address.addressLocality) || "",
              url: o.url || location.href
            });
          }
        });
      } catch (e) {}
    });
    return { url: location.href, host, at: new Date().toISOString(), cards: cards.slice(0, 50) };
  }

  function detectAdapter() {
    if (!AD) return null;
    try {
      return AD.detect(location.href, document);
    } catch (e) { return null; }
  }

  function extractRaw() {
    const a = detectAdapter();
    if (a) {
      let out = { rows: [] };
      try { out = a.extract(document, location.href) || out; } catch (e) { out = { rows: [], error: String(e).slice(0, 200) }; }
      return {
        url: location.href, host, at: new Date().toISOString(),
        adapter: a.id, rows: (out.rows || []).slice(0, 50),
        ...(out.raw_extra || {})
      };
    }
    return { ...rawCaptureLegacy(), adapter: null };
  }

  function strippedSnapshot() {
    const html = document.documentElement ? document.documentElement.outerHTML : "";
    if (AD) return AD.stripSnapshot(html);
    return { html: String(html).slice(0, 100 * 1024), truncated: html.length > 100 * 1024 };
  }

  function bg(msg) {
    return new Promise((res) => {
      try {
        chrome.runtime.sendMessage(msg, (r) => res(r || { ok: false, error: "no response" }));
      } catch (e) { res({ ok: false, error: String(e) }); }
    });
  }

  async function fetchRecipe(id, collectorBase) {
    const r = await bg({ type: "scrapenet:getRecipe", id, collectorBase });
    return (r && r.ok) ? r.recipe : null;
  }

  function looksUnsafe(fnStr) {
    const bad = ["fetch(", "xmlhttprequest", "websocket", "document.", "document[",
      "window.", "localstorage", "sessionstorage", "chrome.", "browser.",
      "eval(", "new function", "import(", "require(", "cookie", "sendbeacon",
      "navigator.", "location.", "<script", ".innerhtml", "for(;;)", "while(true"];
    const low = String(fnStr).toLowerCase();
    return bad.filter((p) => low.includes(p));
  }

  function applyRecipe(raw, fnStr) {
    const problems = looksUnsafe(fnStr);
    if (problems.length) throw new Error("unsafe recipe fn refused (" + problems.join(", ") + ")");
    const fn = new Function("raw", "ctx", `"use strict"; const transform = (${fnStr}); return transform(raw, {url: raw.url, at: raw.at});`);
    const out = fn(raw, {});
    if (!Array.isArray(out)) throw new Error("recipe must return an array");
    return out;
  }

  function mergeDedupe(a, b) {
    const seen = new Set(), out = [];
    for (const r of [...(a || []), ...(b || [])]) {
      const k = JSON.stringify(r);
      if (!seen.has(k)) { seen.add(k); out.push(r); }
    }
    return out.slice(0, 50);
  }

  async function serverTransform(recipe, raw) {
    let payload = { ...raw };
    const ops = recipe.ops || [];
    if (!raw.html && ops.some((o) => o && o.op === "css-select")) {
      const snap = strippedSnapshot();
      payload.html = snap.html;
    }
    const r = await bg({ type: "scrapenet:serverTransform", recipeId: recipe.id, ops, raw: payload });
    if (!r || !r.ok) throw new Error((r && r.error) || "server transform failed");
    return r.rows || [];
  }

  async function runOnce() {
    const s = await state();
    if (!enabled(s)) return { ok: false, error: "host not enabled" };
    hookNet();
    const raw = extractRaw();
    const rows0 = raw.rows || raw.cards || [];
    if (!rows0.length) return { ok: false, error: "no rows extracted" + (raw.adapter ? " (adapter " + raw.adapter + ")" : " (no adapter matched)") };
    const recipe = await fetchRecipe(s.activeRecipe, s.collectorBase);
    let records = rows0;
    let dataset = (raw.adapter && detectAdapter().dataset) || "default";
    if (recipe) {
      const where = recipe.where || "client";
      dataset = recipe.dataset || dataset;
      if (where === "client" || where === "both") {
        if (!recipe.fn) {
          if (where === "client") return { ok: false, error: "recipe has no client fn (use where=server)" };
        } else {
          try { records = applyRecipe(raw, recipe.fn); }
          catch (e) { if (where === "client") return { ok: false, error: "transform: " + String(e).slice(0, 200) }; records = []; }
        }
      }
      if (where === "server" || where === "both") {
        if (!(recipe.ops || []).length) {
          if (where === "server") return { ok: false, error: "recipe has no server ops (use where=client)" };
        } else {
          try {
            const srv = await serverTransform(recipe, raw);
            records = (where === "both") ? mergeDedupe(records, srv) : srv;
          } catch (e) { if (where === "server") return { ok: false, error: "server transform: " + String(e).slice(0, 200) }; }
        }
      }
    }
    if (!records.length) return { ok: false, error: "transform produced 0 records" };
    const r = await bg({ type: "scrapenet:capture", records: records.slice(0, 50), dataset, recipeId: s.activeRecipe, host });
    return { ok: !!(r && r.ok), accepted: (r && r.data && r.data.accepted) || 0, dataset, count: records.length, error: (r && r.error) || undefined, adapter: raw.adapter || null };
  }

  document.addEventListener("keydown", (e) => {
    if (e.altKey && (e.key === "s" || e.key === "S")) runOnce();
  });
  chrome.runtime.onMessage.addListener((msg, sender, reply) => {
    (async () => {
      if (!msg) return;
      if (msg.type === "scrapenet:scrapeNow") reply(await runOnce());
      else if (msg.type === "scrapenet:detect") {
        const a = detectAdapter();
        if (!a) { reply({ ok: true, match: null }); return; }
        let n = 0;
        try { n = (a.extract(document, location.href).rows || []).length; } catch (e) {}
        reply({ ok: true, match: { adapter: a.id, name: a.name, dataset: a.dataset, rows: n, recipe: a.recipe } });
      } else if (msg.type === "scrapenet:snapshot") {
        const snap = strippedSnapshot();
        reply({ ok: true, url: location.href, html: snap.html, truncated: snap.truncated, bytes: snap.html.length });
      }
    })();
    return true;
  });
  if (document.readyState === "complete") hookNetOnLoad();
  else window.addEventListener("load", hookNetOnLoad);
  async function hookNetOnLoad() {
    const s = await state();
    if (enabled(s)) hookNet();
    // Visit-time signal for the popup: stash the match where popup can read it.
    try {
      const a = detectAdapter();
      document.documentElement.setAttribute("data-sn-adapter", a ? a.id : "");
    } catch (e) {}
  }
})();
