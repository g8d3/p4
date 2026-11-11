// EchoLike Lite — popup. Four controls: url, token, Save, Retry.
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
  $("url").value = s.url || "";
  renderList(s.items || []);
  const st = $("status");
  if (!s.url) {
    st.innerHTML = "Not connected. Paste your inbox address below.";
  } else if (s.pending) {
    st.innerHTML = `<span class="err">${s.pending} waiting to send.</span> ${s.last && s.last.error ? s.last.error : ""} <small>(${s.total} saved here)</small>`;
  } else if (s.last && s.last.ok) {
    st.innerHTML = `<span class="ok">✓ Connected.</span> <small>(${s.total} saved here)</small>`;
  } else {
    st.innerHTML = `Connected, nothing pending. <small>(${s.total} saved here)</small>`;
  }
}

$("save").addEventListener("click", async () => {
  const url = $("url").value.trim().replace(/\/$/, "");
  const token = $("token").value.trim();
  if (!url || !token) {
    $("status").innerHTML = '<span class="err">Both fields are needed.</span>';
    return;
  }
  const r = await send("save", { url, token });
  $("token").value = "";
  await refresh();
  if (r && r.ok === false && r.error) $("status").innerHTML = '<span class="err">' + r.error + "</span>";
});

$("retry").addEventListener("click", async () => {
  await send("retry");
  refresh();
});

refresh();
