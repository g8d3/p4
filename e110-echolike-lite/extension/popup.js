// EchoLike Lite — popup. Three things only: what is happening, one button, and
// the list. Everything else lives in the extension's own page (app.html), whose
// second tab is the settings: a 320px popup is not a settings screen.
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

// The hosted inbox is the only inbox whose reader page we can serve ourselves.
// (DEFAULT_INBOX lives in background.js — a different scope, so it is not visible here.)
const HOSTED_HOST = "inbox-lite.echolike.app";

function onHosted(s) {
  if (!s.url) return false;
  try {
    return new URL(s.url).host === HOSTED_HOST;
  } catch (e) {
    return false;
  }
}

async function refresh() {
  const s = await send("state");
  const connected = !!(s.url && s.hasToken);
  const ads = await chrome.storage.local.get({ hide_ads: true });
  $("ads").checked = !!ads.hide_ads;
  $("find").textContent = connected ? "Reconnect" : "Find my inbox";
  renderList(s.items || []);
  // A hosted inbox is read on the web (works on any device, nothing to install);
  // only an inbox on your own machine needs the extension's own page, because that
  // page fetches same-origin. Either way the key stays in the fragment, never sent.
  const open = $("open");
  if (connected) {
    open.href = onHosted(s)
      ? s.url + "/#t=" + encodeURIComponent(s.token || "") + "&k=" + encodeURIComponent(s.keyCode || "")
      : "app.html#inbox";
    open.textContent = onHosted(s) ? "Open my inbox on echolike.app →" : "Open my inbox →";
    open.style.display = "inline";
  } else {
    open.style.display = "none";
  }
  const st = $("status");
  const at = s.url ? " <small>" + esc(s.url.replace(/^https?:\/\//, "")) + "</small>" : "";
  const quota =
    s.last && s.last.quota && typeof s.last.used === "number" ? ` <small>${s.last.used}/${s.last.quota} this month</small>` : "";
  if (!connected) {
    st.innerHTML = s.pending
      ? `<span class="err">${s.pending} waiting to send.</span> Nothing is lost${s.defaultInbox ? " — they go to the hosted inbox on the next like, or press Find my inbox" : " — press Find my inbox"}.`
      : s.defaultInbox
        ? "Nothing to set up: your first like connects to the hosted inbox by itself. Or press Find my inbox to use your own server."
        : "Not connected yet. Your likes are already saved in this browser.";
  } else if (s.pending) {
    st.innerHTML = `<span class="err">${s.pending} waiting to send.</span> ${s.last && s.last.error ? esc(s.last.error) : ""}${at}`;
  } else if (s.last && s.last.ok) {
    st.innerHTML = `<span class="ok">✓ Connected.</span> <small>(${s.total} saved here)</small>${at}${quota}`;
  } else {
    st.innerHTML = `Connected, nothing pending. <small>(${s.total} saved here)</small>${at}${quota}`;
  }
}

async function find() {
  $("find").disabled = true;
  $("status").innerHTML = "Looking for an inbox on this computer…";
  const r = await send("discover");
  $("find").disabled = false;
  await refresh();
  if (r && r.ok === false) {
    $("status").innerHTML = '<span class="err">' + esc(r.error) + "</span> Open <b>Settings</b> to point it at your own server.";
  }
}

$("find").addEventListener("click", find);

// Settings is a tab of the extension's own page, not a separate screen.
$("settings").addEventListener("click", () => chrome.tabs.create({ url: chrome.runtime.getURL("app.html#settings") }));

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
