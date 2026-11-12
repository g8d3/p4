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
      (it.legacy ? " <small>unencrypted, from an older version</small>" : "") +
      (it.text ? "<br><span>" + esc(String(it.text).slice(0, 600)) + "</span>" : "") +
      "<br><small>" + esc(it.clicked_at || it.received_at || "") + "</small>";
    box.appendChild(row);
  }
}

let shown = [];

const tel = (action, info) => chrome.runtime.sendMessage({ type: "tel", action, info }).catch(() => {});

// Opening this tab is a user action: drain whatever is queued, once per load.
let drained = false;

async function load() {
  const s = await chrome.runtime.sendMessage({ type: "state" });
  if (!drained && s.url && s.hasToken) {
    // Opening the page repairs: anything this browser holds that the inbox lacks is
    // re-sealed and sent. Opening it is a user action, so this is not polling.
    drained = true;
    const local = (await chrome.storage.local.get({ items: [] })).items;
    if (s.pending || local.length) {
      await chrome.runtime.sendMessage({ type: "sync" });
      return load();
    }
  }
  if (!s.url || !s.hasToken) {
    // No inbox yet: show what is in this browser, and say so honestly.
    // Read storage directly: the state message already trims and reverses.
    const local = (await chrome.storage.local.get({ items: [] })).items.slice().reverse();
    shown = local;
    $("status").innerHTML =
      '<span class="err">Not connected.</span> ' +
      (local.length ? local.length + " capture(s) are safe in this browser, waiting to be sent. " : "") +
      "Press <b>Find my inbox</b>: it uses the inbox on this computer if there is one, otherwise the hosted one. " +
      "No account, no address, nothing to type.";
    $("export").style.display = local.length ? "inline-block" : "none";
    $("find").textContent = local.length ? "Connect and send " + local.length : "Find my inbox";
    $("find").style.display = "inline-block";
    $("find").classList.add("primary");
    $("retry").style.display = "none";
    render(local);
    return;
  }
  $("status").textContent = "Loading from " + s.url.replace(/^https?:\/\//, "") + "…";
  let r;
  const acct = s.accountToken ? (await chrome.storage.local.get({ accountToken: "" })).accountToken : "";
  const readUrl = acct ? s.url.replace(/\/$/, "") + "/api/account/likes?limit=200" : s.url.replace(/\/$/, "") + "/api/likes?limit=200";
  try {
    r = await fetch(readUrl, { headers: { authorization: "Bearer " + (acct || s.token) } });
  } catch (e) {
    tel("read.unreachable", { ok: false, host: s.url, error: String(e.message || e) });
    $("status").innerHTML = '<span class="err">Inbox unreachable.</span> ' + (s.pending ? s.pending + " waiting locally." : "");
    $("retry").style.display = s.pending ? "inline-block" : "none";
    return;
  }
  tel("read", { ok: r.ok, code: r.status, host: s.url });
  if (r.status === 401) {
    $("status").innerHTML = '<span class="err">This inbox says the key is not valid (401). Reconnect from the popup.</span>';
    return;
  }
  if (!r.ok) {
    $("status").innerHTML = '<span class="err">Inbox answered HTTP ' + r.status + ".</span>";
    return;
  }
  const body = await r.json();
  const decrypted = await decryptAll(s.keyCode, body.items || []);
  // Two browsers, one X account: the same like shows up once, not twice.
  const seen = new Set();
  const fromInbox = decrypted.filter((it) => {
    const k = (it.kind || "") + "|" + (it.id || it.uid || "");
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  // What is in this browser but not in the inbox yet: the honest answer to
  // "did my likes arrive?", which the popup alone cannot give.
  const local = (await chrome.storage.local.get({ items: [], outbox: [] })).items;
  const sentUids = new Set(fromInbox.map((i) => i.uid));
  const waiting = local.filter((i) => !sentUids.has(i.uid));
  shown = fromInbox.concat(waiting.map((i) => Object.assign({}, i, { waiting: true })));
  const quota = body.used != null && body.quota ? " · " + body.used + "/" + body.quota + " this month" : "";
  $("status").innerHTML =
    '<span class="ok">' + fromInbox.length + "</span> " + (acct ? "in my account " : "in the inbox ") +
    "<small>" + esc(s.url.replace(/^https?:\/\//, "")) + "</small>" +
    ' · ' + local.length + " in this browser" +
    (waiting.length ? ' · <span class="err">' + waiting.length + " not in the inbox yet</span>" : "") +
    quota;
  $("export").style.display = shown.length ? "inline-block" : "none";
  // Only the hosted inbox has a reader page we serve ourselves.
  const hosted = (() => {
    try {
      return new URL(s.url).host === "inbox-lite.echolike.app";
    } catch (e) {
      return false;
    }
  })();
  const web = $("webinbox");
  if (hosted) {
    const deep = s.accountToken
      ? "/#a=" + encodeURIComponent(s.accountToken) + "&k=" + encodeURIComponent(s.keyCode || "")
      : "/#t=" + encodeURIComponent(s.token || "") + "&k=" + encodeURIComponent(s.keyCode || "");
    web.href = s.url + deep;
    web.style.display = "inline";
  } else {
    web.style.display = "none";
  }
  $("retry").textContent = waiting.length ? "Send " + waiting.length + " missing" : "Send what is waiting";
  $("retry").style.display = waiting.length ? "inline-block" : "none";
  $("retry").classList.toggle("primary", waiting.length > 0);
  $("find").style.display = "none"; // already connected: reconnect lives in Settings
  if (s.last && s.last.ok === false && s.last.error) {
    $("status").innerHTML += ' · <span class="err">' + esc(s.last.error) + "</span>";
  }
  render(shown);
}

$("find").addEventListener("click", async () => {
  $("find").disabled = true;
  $("status").innerHTML = "Looking for an inbox: this computer first, then the hosted one…";
  const r = await chrome.runtime.sendMessage({ type: "discover" });
  $("find").disabled = false;
  await load();
  if (r && r.ok === false) {
    $("status").innerHTML =
      '<span class="err">' + esc(r.error) + "</span> Nothing was lost. " +
      "Press <b>Find my inbox</b> again, or set your own server in <b>Settings</b>.";
  }
});

$("export").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(shown, null, 1)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "echolike-inbox.json";
  a.click();
});

// A capture, a send or a connection changes storage: the page shows it without a
// reload. Debounced (a burst of likes is one refresh), never a timer loop.
let refreshSoon = null;
chrome.storage.onChanged.addListener((changes) => {
  if (!["url", "token", "outbox", "last", "items", "accountToken", "key"].some((k) => k in changes)) return;
  clearTimeout(refreshSoon);
  refreshSoon = setTimeout(() => load(), 500);
});

window.addEventListener("online", async () => {
  $("status").textContent = "Back online: sending what is waiting…";
  await chrome.runtime.sendMessage({ type: "net-online" }).catch(() => {});
  load();
});

window.addEventListener("echolike:tab", (e) => {
  if (e.detail === "inbox") load();
});

$("retry").addEventListener("click", async () => {
  $("retry").disabled = true;
  $("status").textContent = "Sending everything this browser holds…";
  const r = await chrome.runtime.sendMessage({ type: "sync" });
  $("retry").disabled = false;
  await load();
  if (r && r.ok === false) {
    $("status").innerHTML = '<span class="err">' + esc(r.error || "could not send") + "</span> Nothing was lost.";
  }
});

load();
})();
