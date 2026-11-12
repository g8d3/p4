(function () {
// EchoLike Lite — the full inbox, in an extension page.
// It talks to whatever inbox the extension is connected to, decrypts every blob
// with the key stored in this browser, and lets the user export the lot. Nothing
// here is sent anywhere: the fetch carries the token, the plaintext never leaves.
const $ = (id) => document.getElementById(id);

const unb64 = (s) => {
  let t = String(s).replace(/-/g, "+").replace(/_/g, "/");
  while (t.length % 4) t += "=";
  const b = atob(t);
  const u = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i);
  return u;
};

const esc = (s) =>
  String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function decryptAll(key, blobs) {
  const aes = await crypto.subtle.importKey("raw", unb64(key), "AES-GCM", false, ["decrypt"]);
  const out = [];
  for (const b of blobs) {
    // A v2 inbox (or a self-hosted one from before encryption) still hands back
    // readable items: show those as they are.
    if (!b.ct) {
      out.push(b);
      continue;
    }
    try {
      const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(b.iv) }, aes, unb64(b.ct));
      out.push(Object.assign(JSON.parse(new TextDecoder().decode(plain)), { received_at: b.received_at }));
    } catch (e) {
      out.push({ kind: "unreadable", handle: "", text: "This capture was sealed with another key.", url: "" });
    }
  }
  return out;
}

function render(items) {
  const box = $("list");
  box.textContent = "";
  if (!items.length) {
    box.innerHTML = '<p class="mut">Nothing yet. Like a post on X.</p>';
    return;
  }
  for (const it of items) {
    const row = document.createElement("div");
    row.innerHTML =
      "<b>" + esc(it.kind) + "</b> " +
      (it.url ? '<a target="_blank" rel="noreferrer" href="' + esc(it.url) + '">@' + esc(it.handle) + "</a>" : esc(it.handle)) +
      (it.ad ? " <small>ad</small>" : "") +
      (it.waiting ? " <small>waiting to send</small>" : "") +
      (it.legacy || (!it.__sealed && it.text) ? " <small>unencrypted, from an older version</small>" : "") +
      (it.text ? "<br><span>" + esc(String(it.text).slice(0, 600)) + "</span>" : "") +
      "<br><small>" + esc(it.clicked_at || it.received_at || "") + "</small>";
    box.appendChild(row);
  }
}

let shown = [];

async function load() {
  const s = await chrome.runtime.sendMessage({ type: "state" });
  if (!s.url || !s.hasToken) {
    // No inbox yet: show what is in this browser, and say so honestly.
    const local = (s.items || []).slice().reverse();
    shown = local;
    $("status").innerHTML =
      '<span class="mut">No inbox connected yet, so this is only what this browser has kept (' +
      local.length +
      ").</span>";
    $("export").style.display = local.length ? "inline-block" : "none";
    render(local);
    return;
  }
  $("status").textContent = "Loading from " + s.url.replace(/^https?:\/\//, "") + "…";
  let r;
  try {
    r = await fetch(s.url.replace(/\/$/, "") + "/api/likes?limit=200", {
      headers: { authorization: "Bearer " + s.token },
    });
  } catch (e) {
    $("status").innerHTML = '<span class="err">Inbox unreachable.</span> ' + (s.pending ? s.pending + " waiting locally." : "");
    $("retry").style.display = s.pending ? "inline-block" : "none";
    return;
  }
  if (r.status === 401) {
    $("status").innerHTML = '<span class="err">This inbox says the key is not valid (401). Reconnect from the popup.</span>';
    return;
  }
  if (!r.ok) {
    $("status").innerHTML = '<span class="err">Inbox answered HTTP ' + r.status + ".</span>";
    return;
  }
  const body = await r.json();
  const fromInbox = await decryptAll(s.keyCode, body.items || []);
  // What is in this browser but not in the inbox yet: the honest answer to
  // "did my likes arrive?", which the popup alone cannot give.
  const local = (await chrome.storage.local.get({ items: [], outbox: [] })).items;
  const sentUids = new Set(fromInbox.map((i) => i.uid));
  const waiting = local.filter((i) => !sentUids.has(i.uid));
  shown = fromInbox.concat(waiting.map((i) => Object.assign({}, i, { waiting: true })));
  const quota = body.used != null && body.quota ? " · " + body.used + "/" + body.quota + " this month" : "";
  $("status").innerHTML =
    '<span class="ok">' + fromInbox.length + "</span> in the inbox" +
    ' · ' + local.length + " in this browser" +
    (waiting.length ? ' · <span class="err">' + waiting.length + " waiting to send</span>" : "") +
    quota;
  $("export").style.display = shown.length ? "inline-block" : "none";
  $("retry").style.display = waiting.length ? "inline-block" : "none";
  render(shown);
}

$("export").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(shown, null, 1)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "echolike-inbox.json";
  a.click();
});

$("retry").addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "retry" });
  load();
});

load();
})();
