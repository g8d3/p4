/* ScrapeNet background service worker (vanilla, no deps).
 * Intercept model: content script extracts on user-enabled hosts, applies the
 * picked recipe transform, and sends normalized records here; we POST them to
 * the collector /api/ingest. Collector base URL lives in chrome.storage
 * (set in Options/Popup) — never hardcoded, so no IP/port literal appears.
 * The API token also lives here: content/popup never see it; they ask the
 * worker to make authed calls (ensureRecipe) or public ones (suggest,
 * serverTransform, getRecipe). */
const DEFAULTS = {
  collectorBase: "",
  nodeId: "node-1",
  apiToken: "",
  wallet: "",
  enabledHosts: [],
  activeRecipe: "product-price",
  publishOk: true,
  captured: 0
};

async function state() {
  const s = await chrome.storage.sync.get(DEFAULTS);
  return { ...DEFAULTS, ...s };
}

const seenRequests = [];

async function collectorCall(base, path, method, body) {
  const res = await fetch(base.replace(/\/+$/, "") + path, {
    method: method || "GET",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status, data };
}

chrome.runtime.onInstalled.addListener(async () => {
  const cur = await chrome.storage.sync.get(DEFAULTS);
  await chrome.storage.sync.set({ ...DEFAULTS, ...cur });
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    const s = await state();
    if (msg.type === "scrapenet:getState") {
      sendResponse({ ok: true, state: s });
    } else if (msg.type === "scrapenet:getRecipe") {
      // Public read: fetch one recipe by id for client-side transforms.
      const base = (msg.collectorBase || s.collectorBase || "").trim();
      if (!base) { sendResponse({ ok: false, error: "collector URL not set (see Options)" }); return; }
      try {
        const { data } = await collectorCall(base, "/api/recipes", "GET");
        const rec = (Array.isArray(data) ? data : []).find((x) => x.id === (msg.id || s.activeRecipe));
        if (!rec) sendResponse({ ok: false, error: "recipe not found: " + (msg.id || s.activeRecipe) });
        else sendResponse({ ok: true, recipe: rec });
      } catch (e) { sendResponse({ ok: false, error: String(e).slice(0, 200) }); }
    } else if (msg.type === "scrapenet:serverTransform") {
      // where=server|both: run declarative ops on the collector. Public.
      const base = s.collectorBase.trim();
      if (!base) { sendResponse({ ok: false, error: "collector URL not set (see Options)" }); return; }
      try {
        const body = msg.recipeId ? { recipe_id: msg.recipeId, raw: msg.raw } : { ops: msg.ops, raw: msg.raw };
        const { status, data } = await collectorCall(base, "/api/transform", "POST", body);
        if (status !== 200 || data.ok !== true) sendResponse({ ok: false, error: (data && data.error) || ("transform failed (" + status + ")") });
        else sendResponse({ ok: true, rows: data.rows || [] });
      } catch (e) { sendResponse({ ok: false, error: String(e).slice(0, 200) }); }
    } else if (msg.type === "scrapenet:suggest") {
      // Visit-time suggest on unmatched pages: public analysis endpoint.
      const base = s.collectorBase.trim();
      if (!base) { sendResponse({ ok: false, error: "collector URL not set (see Options)" }); return; }
      try {
        const { status, data } = await collectorCall(base, "/api/recipes/suggest", "POST", { url: msg.url, html: msg.html });
        if (status !== 200 || data.ok !== true) sendResponse({ ok: false, error: (data && data.error) || ("suggest failed (" + status + ")") });
        else sendResponse({ ok: true, proposal: data });
      } catch (e) { sendResponse({ ok: false, error: String(e).slice(0, 200) }); }
    } else if (msg.type === "scrapenet:ensureRecipe") {
      // One-click binding: create the recipe if missing (needs token).
      const base = s.collectorBase.trim();
      if (!base) { sendResponse({ ok: false, error: "collector URL not set (see Options)" }); return; }
      try {
        const { data: list } = await collectorCall(base, "/api/recipes", "GET");
        const found = (Array.isArray(list) ? list : []).find((x) => x.id === msg.recipe.id);
        if (found) { sendResponse({ ok: true, created: false, recipe: found }); return; }
        const { status, data } = await collectorCall(base, "/api/recipes", "POST", {
          ...msg.recipe, node_id: s.nodeId, token: s.apiToken || undefined
        });
        if (status === 200) sendResponse({ ok: true, created: true, recipe: data });
        else sendResponse({ ok: false, error: (data && data.error) || ("recipe create failed (" + status + ")"), signupHint: status === 401 });
      } catch (e) { sendResponse({ ok: false, error: String(e).slice(0, 200) }); }
    } else if (msg.type === "scrapenet:capture") {
      if (!s.collectorBase) {
        sendResponse({ ok: false, error: "collector URL not set (see Options)" });
        return;
      }
      const base = s.collectorBase.replace(/\/+$/, "");
      try {
        const res = await fetch(base + "/api/ingest", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            node_id: s.nodeId,
            token: s.apiToken || undefined,
            wallet: s.wallet,
            dataset: msg.dataset || "default",
            recipe_id: msg.recipeId || s.activeRecipe,
            publish_ok: s.publishOk !== false,
            records: msg.records || []
          })
        });
        const data = await res.json();
        if (data.ok) {
          const n = (s.captured || 0) + (data.accepted || 0);
          await chrome.storage.sync.set({ captured: n });
        }
        sendResponse({ ok: !!data.ok, data });
      } catch (e) {
        sendResponse({ ok: false, error: String(e) });
      }
    } else if (msg.type === "scrapenet:setWhere") {
      // Popup run_where switch: PUT the active recipe's where (needs token).
      const base = s.collectorBase.trim();
      if (!base) { sendResponse({ ok: false, error: "collector URL not set (see Options)" }); return; }
      if (!["client", "server", "both"].includes(msg.where)) {
        sendResponse({ ok: false, error: "where must be client|server|both" }); return;
      }
      try {
        const { status, data } = await collectorCall(base, "/api/recipes?id=" + encodeURIComponent(msg.id), "PUT", {
          where: msg.where, node_id: s.nodeId, token: s.apiToken || undefined
        });
        if (status === 200) sendResponse({ ok: true, recipe: data });
        else sendResponse({ ok: false, error: (data && data.error) || ("set where failed (" + status + ")"), signupHint: status === 401 });
      } catch (e) { sendResponse({ ok: false, error: String(e).slice(0, 200) }); }
    } else if (msg.type === "scrapenet:noteRequest") {
      seenRequests.unshift({ url: msg.url, host: msg.host, at: Date.now() });
      if (seenRequests.length > 20) seenRequests.pop();
      sendResponse({ ok: true, recent: seenRequests.slice(0, 5) });
    } else {
      sendResponse({ ok: false, error: "unknown message" });
    }
  })();
  return true;
});
