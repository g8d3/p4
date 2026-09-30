/* ScrapeNet adapter registry (vanilla MV3, zero deps).
 * Contract per adapter: { id, name, host_pattern, dataset,
 *   detect(url, doc) -> bool, extract(doc, url) -> { rows, raw_extra? },
 *   recipe: { id, name, dataset, match, description, schema, fn, where } }
 * `doc` is only ever touched via querySelector(All)/title — the same calls
 * work on a real document and on the fake DOM in test/adapters_test.js.
 * Registration order = match priority (specific sites first, generics last).
 * Add a new adapter in <30 lines: copy adapters/x.js, change the pattern,
 * detect() and extract(), done. No new permissions or deps needed. */
(function () {
  var list = [];

  function register(a) {
    if (!a || !a.id || !a.name || !a.host_pattern || !a.dataset ||
        typeof a.detect !== "function" || typeof a.extract !== "function" || !a.recipe) {
      throw new Error("adapter needs {id,name,host_pattern,dataset,detect,extract,recipe}");
    }
    if (list.some(function (x) { return x.id === a.id; })) {
      throw new Error("duplicate adapter id: " + a.id);
    }
    list.push(a);
  }

  function hostOf(url) {
    try { return new URL(url).hostname.toLowerCase(); } catch (e) { return ""; }
  }

  function detect(url, doc) {
    var host = hostOf(url);
    for (var i = 0; i < list.length; i++) {
      var a = list[i];
      try {
        if (new RegExp(a.host_pattern, "i").test(host) && a.detect(url, doc)) return a;
      } catch (e) { /* a broken adapter must never break detection */ }
    }
    return null;
  }

  /* Privacy: strip credential-bearing markup client-side before any snapshot
   * leaves the page. Keeps JSON-LD (needed for suggest) and drops everything
   * that can hold secrets: inputs, textareas, selects, non-LD scripts,
   * styles, comments, password/token-ish attributes. Caps at 100KB. */
  function stripSnapshot(html) {
    var s = String(html || "");
    s = s.replace(/<!--[\s\S]*?-->/g, "");
    s = s.replace(/<script(?![^>]*ld\+json)[^>]*>[\s\S]*?<\/script\s*>/gi, "");
    s = s.replace(/<style[^>]*>[\s\S]*?<\/style\s*>/gi, "");
    s = s.replace(/<input\b[^>]*>/gi, "");
    s = s.replace(/<textarea\b[^>]*>[\s\S]*?<\/textarea\s*>/gi, "");
    s = s.replace(/<select\b[^>]*>[\s\S]*?<\/select\s*>/gi, "");
    s = s.replace(/\s(on\w+|password|passwd|pwd|auth_token|api[_-]?key|secret|sessionid|csrf\w*)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "");
    s = s.replace(/\s+/g, " ");
    var truncated = s.length > 100 * 1024;
    if (truncated) s = s.slice(0, 100 * 1024);
    return { html: s, truncated: truncated };
  }

  var api = { list: list, register: register, detect: detect, stripSnapshot: stripSnapshot };
  globalThis.SNAdapters = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
