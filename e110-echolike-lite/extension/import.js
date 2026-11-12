// EchoLike Lite — the Import tab. Everything that walks your own X history lives
// here: it is the one part of the product that is deliberately a button, because
// scroll-walking history on a timer is what a scraper looks like.
(function () {
  const $ = (id) => document.getElementById(id);
  const send = (type, extra) => chrome.runtime.sendMessage(Object.assign({ type }, extra || {}));
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // Verified with the owner: neither lives at the obvious path.
  const LISTS = { likes: "https://x.com/i/history/likes", bookmarks: "https://x.com/i/history" };

  function render(p) {
    if (!p) {
      $("istatus").innerHTML = "Nothing imported yet.";
      return;
    }
    const what = p.mode === "bookmarks" ? "bookmarks" : "likes";
    if (p.state === "running") {
      $("istatus").innerHTML =
        '<span class="ok">Importing ' + what + ":</span> " + (p.collected || 0) + " of " + (p.of || "?") +
        " collected, " + (p.sent || 0) + " sent. Keep that X tab open — it scrolls itself.";
      return;
    }
    const why = { limit: "reached your count", end: "the list ended", timeout: "ten-minute guard", cancelled: "cancelled" }[p.reason] || p.state;
    const skipped = Math.max(0, (p.collected || 0) - (p.sent || 0));
    $("istatus").innerHTML =
      '<span class="ok">' + (p.collected || 0) + " " + what + "</span> collected, " + (p.sent || 0) + " sent" +
      (skipped ? ' <small>(' + skipped + " already in this browser, not sent twice)</small>" : "") +
      " · " + esc(why) + (p.at ? " · " + esc(localTime(p.at)) : "");
  }

  const localTime = (iso) => {
    if (!iso) return "";
    const d = new Date(iso);
    return isNaN(d) ? String(iso) : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  // The tabs a user actually has open, named by path: "which tab?" was the complaint.
  async function loadTabs() {
    const r = await send("tabs");
    const sel = $("itab");
    const keep = sel.value;
    sel.textContent = "";
    const tabs = (r && r.tabs) || [];
    if (!tabs.length) {
      const o = document.createElement("option");
      o.value = "";
      o.textContent = "(no X tab open — use the button below)";
      sel.appendChild(o);
      return;
    }
    for (const t of tabs) {
      const o = document.createElement("option");
      o.value = String(t.id);
      const path = (t.url || "").replace(/^https:\/\/x\.com/, "").replace(/^https:\/\/twitter\.com/, "") || "/";
      o.textContent = (t.active ? "● " : "") + path + (t.title ? " — " + t.title.slice(0, 40) : "");
      sel.appendChild(o);
    }
    const wanted = $("imode").value === "bookmarks" ? "/i/history" : "/i/history/likes";
    const best = tabs.find((t) => (t.url || "").includes(wanted)) || tabs.find((t) => String(t.id) === keep);
    if (best) sel.value = String(best.id);
  }

  $("itabs").addEventListener("click", loadTabs);

  $("iopen").addEventListener("click", async () => {
    const url = LISTS[$("imode").value] || LISTS.likes;
    await chrome.tabs.create({ url });
    $("istatus").innerHTML =
      "Opened <b>" + esc(url.replace(/^https:\/\/x\.com/, "x.com")) +
      "</b>. Wait for it to load, then press <b>Start import</b> — or press Start now and it starts by itself when the page is ready.";
  });

  async function refresh() {
    const s = await chrome.storage.local.get({ import_progress: null });
    render(s.import_progress);
    await loadTabs();
    const running = s.import_progress && s.import_progress.state === "running";
    $("istart").disabled = !!running;
    $("icancel").disabled = !running;
  }

  $("imode").addEventListener("change", () => {
    $("ilist").href = LISTS[$("imode").value] || LISTS.likes;
  });

  $("istart").addEventListener("click", async () => {
    $("istart").disabled = true;
    $("istatus").textContent = "Looking for an open X tab…";
    const tabId = Number($("itab").value) || null;
    const r = await send("import-start", { mode: $("imode").value, limit: Number($("ilimit").value), tabId });
    if (!r || r.ok === false) {
      $("istatus").innerHTML = '<span class="err">' + esc((r && r.error) || "could not start") + "</span>";
      if (r && r.tabId) {
        const btn = document.createElement("button");
        btn.className = "act";
        btn.textContent = "Reload that tab and start";
        btn.onclick = async () => {
          await chrome.tabs.reload(r.tabId);
          $("istatus").textContent = "Reloading the tab… when it finishes, press Start again.";
        };
        $("istatus").appendChild(document.createElement("br"));
        $("istatus").appendChild(btn);
      }
      $("istart").disabled = false;
      await loadTabs();
      return;
    }
    render({ state: "running", mode: $("imode").value, of: Number($("ilimit").value), collected: 0, sent: 0 });
  });

  $("icancel").addEventListener("click", async () => {
    await send("import-cancel");
  });

  // The content script writes progress to storage as it goes: no polling here.
  chrome.storage.onChanged.addListener((ch) => {
    if (ch.import_progress) render(ch.import_progress.newValue);
  });

  window.addEventListener("echolike:tab", (e) => {
    if (e.detail === "import") refresh();
  });

  refresh();
})();
