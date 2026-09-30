/* ScrapeNet popup (vanilla). No hardcoded URLs: collector base comes from storage.
 * Visit-time suggest: asks the tab's content script what adapter (if any)
 * matches this page. Match -> one-click "Extract as dataset" (creates the
 * recipe binding, enables the host, captures immediately). No match ->
 * "Suggest extraction" sends a stripped snapshot (no inputs/passwords,
 * 100KB cap) to POST /api/recipes/suggest; the user approves with one click. */
async function get(defs) {
  return new Promise((r) => chrome.storage.sync.get(defs, r));
}
function bg(msg) {
  return new Promise((res) => {
    try { chrome.runtime.sendMessage(msg, (r) => res(r || { ok: false, error: "no response" })); }
    catch (e) { res({ ok: false, error: String(e) }); }
  });
}
function tabMsg(tabId, msg) {
  return new Promise((res) => {
    try { chrome.tabs.sendMessage(tabId, msg, (r) => res(r || { ok: false, error: "content script unreachable — reload the page" })); }
    catch (e) { res({ ok: false, error: String(e) }); }
  });
}
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function enableHost(host, recipeId) {
  const cur = await get({ enabledHosts: [], activeRecipe: "product-price" });
  const hosts = (cur.enabledHosts || []).includes(host) ? cur.enabledHosts : [...(cur.enabledHosts || []), host];
  await chrome.storage.sync.set({ enabledHosts: hosts, activeRecipe: recipeId || cur.activeRecipe });
  document.getElementById("en").checked = true;
}

async function renderAdapterBox(tab, host) {
  const box = document.getElementById("adapterBox");
  const status = (t) => { document.getElementById("status").textContent = t; };
  let det;
  try { det = await tabMsg(tab.id, { type: "scrapenet:detect" }); }
  catch (e) { det = { ok: false }; }
  if (det && det.ok && det.match) {
    const m = det.match;
    box.innerHTML = `<div class="adapter"><b>${esc(m.name)}</b> detected — ${esc(m.rows)} rows → dataset <code>${esc(m.dataset)}</code><br><button id="extract">Extract ${esc(m.rows)} ${esc(m.name)} as dataset?</button></div>`;
    document.getElementById("extract").onclick = async () => {
      status("creating recipe binding…");
      const r = await bg({ type: "scrapenet:ensureRecipe", recipe: m.recipe });
      if (!r.ok) {
        status(r.signupHint ? "signup first: dashboard → Sign up, paste token in Options." : ("recipe failed: " + r.error));
        return;
      }
      await enableHost(host, m.recipe.id);
      status("capturing…");
      const c = await tabMsg(tab.id, { type: "scrapenet:scrapeNow" });
      status(c && c.ok ? `captured ${c.accepted} records → ${c.dataset}.` : ("capture: " + ((c && c.error) || "failed")));
      const s = await get({ captured: 0 });
      document.getElementById("status").textContent += ` (node total ${s.captured || 0})`;
    };
  } else {
    box.innerHTML = `<div class="prop"><span class="muted">No adapter matches this page.</span><br><button id="suggest">Suggest extraction</button><div id="prop"></div></div>`;
    document.getElementById("suggest").onclick = async () => {
      const prop = document.getElementById("prop");
      prop.textContent = "reading stripped snapshot…";
      const snap = await tabMsg(tab.id, { type: "scrapenet:snapshot" });
      if (!snap || !snap.ok) { prop.textContent = "snapshot failed: " + ((snap && snap.error) || "?"); return; }
      prop.textContent = "asking collector…";
      const s = await bg({ type: "scrapenet:suggest", url: snap.url, html: snap.html });
      if (!s.ok) { prop.textContent = "suggest failed: " + s.error; return; }
      const p = s.proposal;
      prop.innerHTML = `proposed dataset <code>${esc(p.dataset)}</code> (${esc(p.kind)}, confidence ${esc(p.confidence)})<br>fields: <code>${esc((p.fields || []).join(", "))}</code><br><span class="muted">${esc(p.reason)}</span><br><button id="approve">Approve &amp; create recipe</button>`;
      document.getElementById("approve").onclick = async () => {
        prop.textContent = "creating recipe…";
        const rid = String(p.dataset || "suggested").toLowerCase().replace(/[^a-z0-9._-]+/g, "-").slice(0, 48) || "suggested";
        const r = await bg({ type: "scrapenet:ensureRecipe", recipe: {
          id: rid, name: "Suggested: " + p.kind, dataset: p.dataset, match: "",
          description: "Visit-time suggest approved by user: " + p.reason,
          schema: p.fields || [], fn: "", where: "server", ops: p.proposed_ops || []
        } });
        if (!r.ok) {
          prop.textContent = r.signupHint ? "signup first: dashboard → Sign up, paste token in Options." : ("recipe failed: " + r.error);
          return;
        }
        await enableHost(host, r.recipe.id || rid);
        prop.textContent = "recipe saved — capturing…";
        const c = await tabMsg(tab.id, { type: "scrapenet:scrapeNow" });
        prop.textContent = c && c.ok ? `captured ${c.accepted} records → ${c.dataset}.` : ("capture: " + ((c && c.error) || "failed"));
      };
    };
  }
}

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const host = tab && tab.url ? new URL(tab.url).hostname : "";
  document.getElementById("host").textContent = host || "(no page)";
  const s = await get({ enabledHosts: [], activeRecipe: "product-price", collectorBase: "", nodeId: "node-1", captured: 0 });
  document.getElementById("en").checked = (s.enabledHosts || []).includes(host);
  document.getElementById("base").value = s.collectorBase || "";
  document.getElementById("status").textContent = `captured this node: ${s.captured || 0} records`;
  if (tab && tab.id && /^https?:/.test(tab.url || "")) {
    try { await renderAdapterBox(tab, host); } catch (e) { /* never break the popup */ }
  }
  let ids = ["product-price", "job-listing", "crypto-price"];
  let liveWhere = {};
  if (s.collectorBase) {
    try {
      const r = await fetch(s.collectorBase.replace(/\/+$/, "") + "/api/recipes");
      const list = await r.json();
      if (Array.isArray(list) && list.length) {
        ids = list.map((x) => x.id + (x.where && x.where !== "client" ? ` [${x.where}]` : ""));
        list.forEach((x) => { liveWhere[x.id] = x.where || "client"; });
      }
    } catch (e) {}
  }
  const paintWhere = () => {
    const w = liveWhere[sel.value] || "client";
    document.getElementById("where").value = w;
    document.getElementById("whereBadge").textContent = w === "client" ? "WHERE: CLIENT · browser" : w === "server" ? "WHERE: SERVER · AI refine" : "WHERE: BOTH";
  };
  const sel = document.getElementById("recipe");
  sel.innerHTML = "";
  ids.forEach((id) => {
    const o = document.createElement("option");
    o.value = id.split(" ")[0];
    o.textContent = id;
    if (o.value === s.activeRecipe) o.selected = true;
    sel.appendChild(o);
  });
  paintWhere();
  sel.onchange = paintWhere;
  document.getElementById("where").onchange = async (e) => {
    const w = e.target.value;
    document.getElementById("status").textContent = "setting where=" + w + "…";
    const r = await bg({ type: "scrapenet:setWhere", id: sel.value, where: w });
    if (!r.ok) {
      document.getElementById("status").textContent = r.signupHint ? "signup first: dashboard → Sign up, paste token in Options." : ("where failed: " + r.error);
      paintWhere();
      return;
    }
    liveWhere[sel.value] = r.recipe.where || w;
    paintWhere();
    document.getElementById("status").textContent = "runs where: " + liveWhere[sel.value] + " (live).";
  };
  document.getElementById("save").onclick = async () => {
    const cur = await get({ enabledHosts: [] });
    let hosts = cur.enabledHosts || [];
    const on = document.getElementById("en").checked;
    if (on && host && !hosts.includes(host)) hosts.push(host);
    if (!on && host) hosts = hosts.filter((h) => h !== host);
    await chrome.storage.sync.set({
      enabledHosts: hosts,
      activeRecipe: sel.value,
      collectorBase: document.getElementById("base").value.trim()
    });
    document.getElementById("status").textContent = "saved.";
  };
  document.getElementById("scrape").onclick = async () => {
    await chrome.storage.sync.set({
      activeRecipe: sel.value,
      collectorBase: document.getElementById("base").value.trim()
    });
    if (tab && tab.id) chrome.tabs.sendMessage(tab.id, { type: "scrapenet:scrapeNow" });
    document.getElementById("status").textContent = "scrape requested (Alt+S also works).";
  };
}
init();
