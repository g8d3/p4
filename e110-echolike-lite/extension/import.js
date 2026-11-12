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
    $("istatus").innerHTML =
      '<span class="ok">' + (p.collected || 0) + " " + what + "</span> collected, " + (p.sent || 0) +
      " sent · " + esc(why) + (p.at ? " · " + esc(String(p.at).slice(11, 19)) : "");
  }

  async function refresh() {
    const s = await chrome.storage.local.get({ import_progress: null });
    render(s.import_progress);
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
    const r = await send("import-start", { mode: $("imode").value, limit: Number($("ilimit").value) });
    if (!r || r.ok === false) {
      $("istatus").innerHTML = '<span class="err">' + esc((r && r.error) || "could not start") + "</span>";
      $("istart").disabled = false;
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
