// EchoLike Lite — popup. Zero fields on first run: one button finds a local
// inbox and it issues a device token. Address + token stay under Advanced for
// an inbox on another machine, and are never needed for the common case.
const $ = (id) => document.getElementById(id);

async function send(type, extra) {
  return chrome.runtime.sendMessage(Object.assign({ type }, extra || {}));
}

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderList(items) {
  const box = $("list");
  box.textContent = "";
  if (!items.length) {
    box.innerHTML = '<p class="mut">Nothing captured yet. Like a post on x.com.</p>';
    return;
  }
  for (const it of items) {
    const row = document.createElement("div");
    const text = (it.text || "").replace(/\s+/g, " ").slice(0, 120);
    row.innerHTML =
      "<b>" + esc(it.kind) + "</b> <a href=\"" + esc(it.url) + "\" target=\"_blank\">@" + esc(it.handle) + "</a>" +
      (text ? "<br><span>" + esc(text) + "</span>" : "");
    box.appendChild(row);
  }
}

async function refresh() {
  const s = await send("state");
  const connected = !!(s.url && s.hasToken);
  if (s.url) $("url").value = s.url;
  const ads = await chrome.storage.local.get({ hide_ads: true });
  $("ads").checked = !!ads.hide_ads;
  $("find").textContent = connected ? "Reconnect" : "Find my inbox";
  $("find").hidden = false;
  renderList(s.items || []);
  const st = $("status");
  const at = s.url ? " <small>" + esc(s.url.replace(/^https?:\/\//, "")) + "</small>" : "";
  if (!connected) {
    st.innerHTML = s.pending
      ? `<span class="err">${s.pending} waiting to send.</span> Nothing is lost — start your inbox and press Find my inbox.`
      : "Not connected yet. Your likes are already saved in this browser.";
  } else if (s.pending) {
    st.innerHTML = `<span class="err">${s.pending} waiting to send.</span> ${s.last && s.last.error ? esc(s.last.error) : ""}${at}`;
  } else if (s.last && s.last.ok) {
    st.innerHTML = `<span class="ok">✓ Connected.</span> <small>(${s.total} saved here)</small>${at}`;
  } else {
    st.innerHTML = `Connected, nothing pending. <small>(${s.total} saved here)</small>${at}`;
  }
}

async function find() {
  $("find").disabled = true;
  $("status").innerHTML = "Looking for an inbox on this computer…";
  const r = await send("discover");
  $("find").disabled = false;
  await refresh();
  if (r && r.ok === false) {
    $("status").innerHTML = '<span class="err">' + esc(r.error) + "</span>";
    if (!r.url) $("adv").open = true;
  }
}

$("find").addEventListener("click", find);

$("save").addEventListener("click", async () => {
  const url = $("url").value.trim().replace(/\/$/, "");
  let token = $("token").value.trim();
  if (!url) {
    $("status").innerHTML = '<span class="err">An address is needed.</span>';
    $("adv").open = true;
    return;
  }
  // No token typed: ask the server for one (works when it is on your own network).
  if (!token) {
    const claim = await send("claim", { url });
    await refresh();
    if (!claim || claim.ok === false) {
      $("status").innerHTML = '<span class="err">' + esc((claim && claim.error) || "no inbox there") + "</span>";
      $("adv").open = true;
    }
    return;
  }
  const r = await send("save", { url, token });
  $("token").value = "";
  await refresh();
  if (r && r.ok === false && r.error) $("status").innerHTML = '<span class="err">' + esc(r.error) + "</span>";
});

$("forget").addEventListener("click", async () => {
  await send("forget");
  $("url").value = "";
  $("token").value = "";
  await refresh();
});

$("retry").addEventListener("click", async () => {
  await send("retry");
  refresh();
});

// Ads toggle: storage is the single source of truth; the content script listens for changes.
$("ads").addEventListener("change", async () => {
  await chrome.storage.local.set({ hide_ads: $("ads").checked });
});

// Opening the popup does not touch the network: nothing is probed and nothing is
// sent until the user presses Find my inbox (or a hosted DEFAULT_INBOX exists).
refresh();
