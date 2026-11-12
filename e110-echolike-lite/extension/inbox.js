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

// Replies · reposts · likes · bookmarks · views, and when it was published.
const fmt = (n) => (n == null ? "–" : n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "K" : String(n));
function countsLine(it) {
  const c = it.counts || {};
  const bits = [
    ["replies", c.replies],
    ["reposts", c.reposts],
    ["likes", c.likes],
    ["bookmarks", c.bookmarks],
    ["views", c.views],
  ]
    .filter(([, v]) => v != null)
    .map(([k, v]) => fmt(v) + " " + k);
  if (it.media) bits.push(it.media + " media");
  return bits.length ? '<br><small>' + esc(bits.join(" · ")) + "</small>" : "";
}

// Four dates, all kept on purpose: when I clicked, when this browser saved it,
// when the inbox received it, when the post was published. They are different
// events, and the point of sorting by one of them is to see the others.
function datesLine(it) {
  const bits = [
    ["liked", it.clicked_at],
    ["saved", it.captured_at],
    ["arrived", it.received_at],
    ["published", it.published_at || it.tweet_time],
  ]
    .filter(([, v]) => v)
    .map(([k, v]) => k + " " + localTime(v));
  return bits.length ? "<br><small>" + esc(bits.join(" · ")) + "</small>" : "";
}

// ---- Sorting ---------------------------------------------------------------
// Arrival order is not a user-meaningful order. Every surface offers the same
// keys, newest/most first by default, and remembers the choice.
const SORTS = [
  ["clicked_at", "my interaction", "date"],
  ["captured_at", "captured in this browser", "date"],
  ["received_at", "arrived in the inbox", "date"],
  ["published_at", "post published", "date"],
  ["reposts", "reposts", "count"],
  ["likes", "post likes", "count"],
  ["replies", "replies", "count"],
  ["bookmarks", "bookmarks", "count"],
  ["views", "views", "count"],
];
const sortKind = (key) => (SORTS.find((s) => s[0] === key) || SORTS[0])[2];

function sortValue(it, key) {
  const v =
    key === "received_at"
      ? it.received_at
      : key === "captured_at"
        ? it.captured_at
        : key === "published_at"
          ? it.published_at || it.tweet_time
          : key === "clicked_at"
            ? it.clicked_at
            : it.counts
              ? it.counts[key]
              : null;
  if (v == null || v === "") return null;
  if (sortKind(key) === "date") {
    const t = Date.parse(v);
    return isNaN(t) ? null : t;
  }
  const n = Number(v);
  return isNaN(n) ? null : n;
}

function sortRows(rows, key, desc) {
  return rows.slice().sort((a, b) => {
    const x = sortValue(a, key);
    const y = sortValue(b, key);
    // An unknown value never pretends to be the oldest or the smallest: it goes last.
    if (x == null || y == null) return x == null ? (y == null ? 0 : 1) : -1;
    return desc ? y - x : x - y;
  });
}

const SORT_KEY = "el_sort";
const SORT_DIR = "el_sort_desc";
let sortKey = localStorage.getItem(SORT_KEY) || "clicked_at";
let sortDesc = localStorage.getItem(SORT_DIR) !== "0";

function dirLabel() {
  return sortKind(sortKey) === "date"
    ? sortDesc
      ? "newest first"
      : "oldest first"
    : sortDesc
      ? "most first"
      : "least first";
}

function paintSort() {
  $("sort").innerHTML = SORTS.map(
    ([k, label]) => '<option value="' + k + '">' + esc(label) + "</option>",
  ).join("");
  $("sort").value = sortKey;
  $("dir").textContent = dirLabel();
}

// Re-render without touching the network: sorting and filtering are a view, not a fetch.
function repaint() {
  render(sortRows(shown.filter(matchesFilter), sortKey, sortDesc));
}

// ---- Filtering -------------------------------------------------------------
// "Which ones are missing?" must be answerable without reading the list: one
// filter for the ones the inbox does not have yet, one for the kind, one for ads,
// one for media. Marked rows also say "waiting to send" on their own line.
const FILTERS = [
  ["all", "all captures"],
  ["waiting", "not in the inbox yet"],
  ["like", "likes"],
  ["bookmark", "bookmarks"],
  ["unlike", "unlikes"],
  ["ads", "ads"],
  ["media", "with media"],
];
let filterKey = localStorage.getItem("el_filter") || "all";

function matchesFilter(it) {
  if (filterKey === "all") return true;
  if (filterKey === "waiting") return !!it.waiting;
  if (filterKey === "ads") return !!it.ad;
  if (filterKey === "media") return it.media != null && it.media !== "" && it.media !== 0;
  return it.kind === filterKey;
}

function paintFilter() {
  $("filter").innerHTML = FILTERS.map(
    ([k, label]) => '<option value="' + k + '">' + esc(label) + "</option>",
  ).join("");
  $("filter").value = filterKey;
}

// A count in the status line is a button: "15 not in the inbox yet" opens exactly
// those 15.
function showWaiting(n) {
  return '<button id="onlywaiting" class="act" type="button" style="padding:1px 6px;margin:0">' +
    n + " not in the inbox yet</button>";
}

function render(items) {
  const box = $("list");
  box.textContent = "";
  if (!items.length) {
    box.innerHTML = shown.length
      ? '<p class="mut">Nothing matches this filter. <button id="clearfilter" class="act" type="button">Show all</button></p>'
      : '<p class="mut">Nothing yet. Like a post on X.</p>';
    return;
  }
  for (const it of items) {
    const row = document.createElement("div");
    row.innerHTML =
      "<b>" + esc(it.kind) + "</b> " +
      (it.url ? '<a target="_blank" rel="noreferrer" href="' + esc(it.url) + '">@' + esc(it.handle) + "</a>" : esc(it.handle)) +
      (it.ad ? " <small>ad</small>" : "") +
      countsLine(it) +
      datesLine(it) +
      (it.waiting ? " <small>waiting to send</small>" : "") +
      (it.legacy ? " <small>unencrypted, from an older version</small>" : "") +
      (it.text ? "<br><span>" + esc(String(it.text).slice(0, 600)) + "</span>" : "");
    box.appendChild(row);
  }
}

let shown = [];

// One page at a time, until the inbox says we have them all. A single capped page
// made this page lie twice: captures further down looked "not sent yet", and the
// repair pass re-uploaded them as new ones.
async function readAll(base, headers, max) {
  const out = [];
  let total = 0;
  let extra = {};
  const cap = max || 5000;
  for (let offset = 0; offset < cap; ) {
    const r = await fetch(base + "?limit=500&offset=" + offset, { headers });
    if (!r.ok) return { ok: false, code: r.status, items: out, total, extra };
    const body = await r.json();
    const batch = body.items || [];
    out.push(...batch);
    if (body.total != null) total = body.total;
    if (body.used != null) extra = { used: body.used, quota: body.quota };
    if (!batch.length || out.length >= total) break;
    offset += batch.length;
  }
  return { ok: true, items: out, total: total || out.length, extra };
}

// Times come from the clock of whoever captured them and the server's UTC: always
// render them in the reader's own timezone.
const localTime = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d) ? String(iso) : d.toLocaleString([], { dateStyle: "short", timeStyle: "short" });
};

const tel = (action, info) => chrome.runtime.sendMessage({ type: "tel", action, info }).catch(() => {});

// Opening this tab repairs without being asked. There is no "send" step to
// remember: the page reads the inbox, and whatever this browser holds that the
// inbox does not is re-sealed and sent by itself, once per load.
let repaired = false;

async function load() {
  const s = await chrome.runtime.sendMessage({ type: "state" });
  if (!s.url || !s.hasToken) {
    // No inbox yet: show what is in this browser, and say so honestly.
    // Read storage directly: the state message already trims and reverses.
    const local = (await chrome.storage.local.get({ items: [] })).items.slice();
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
    $("sorts").style.display = local.length ? "block" : "none";
    repaint();
    return;
  }
  $("status").textContent = "Loading from " + s.url.replace(/^https?:\/\//, "") + "…";
  const acct = s.accountToken ? (await chrome.storage.local.get({ accountToken: "" })).accountToken : "";
  const readUrl = acct ? s.url.replace(/\/$/, "") + "/api/account/likes" : s.url.replace(/\/$/, "") + "/api/likes";
  let got;
  try {
    got = await readAll(readUrl, { authorization: "Bearer " + (acct || s.token) });
  } catch (e) {
    tel("read.unreachable", { ok: false, host: s.url, error: String(e.message || e) });
    $("status").innerHTML = '<span class="err">Inbox unreachable.</span> ' + (s.pending ? s.pending + " waiting locally." : "");
    $("retry").style.display = s.pending ? "inline-block" : "none";
    return;
  }
  tel("read", { ok: got.ok, code: got.code || 200, host: s.url });
  if (!got.ok && got.code === 401) {
    $("status").innerHTML = '<span class="err">This inbox says the key is not valid (401). Reconnect from the popup.</span>';
    return;
  }
  if (!got.ok) {
    $("status").innerHTML = '<span class="err">Inbox answered HTTP ' + got.code + ".</span>";
    return;
  }
  const decrypted = await decryptAll(s.keyCode, got.items);
  // Two browsers, one X account: the same like shows up once, not twice. Also a
  // capture stored twice by an older release: keep the first (newest) copy.
  const seen = new Set();
  const fromInbox = decrypted.filter((it) => {
    const k = (it.kind || "") + "|" + (it.id || it.uid || "");
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  // What is in this browser but not in the inbox yet: the honest answer to
  // "did my likes arrive?". The inbox is read to the end above, so "missing"
  // really means missing.
  const local = (await chrome.storage.local.get({ items: [], outbox: [] })).items;
  const sentUids = new Set(fromInbox.map((i) => i.uid).filter(Boolean));
  const waiting = local.filter((i) => !sentUids.has(i.uid));
  shown = fromInbox.concat(waiting.map((i) => Object.assign({}, i, { waiting: true })));
  const used = got.extra.used != null ? got.extra.used : null;
  const quota = used != null && got.extra.quota ? " · " + used + "/" + got.extra.quota + " this month" : "";
  $("status").innerHTML =
    '<span class="ok">' + fromInbox.length + "</span> " + (acct ? "in my account " : "in the inbox ") +
    "<small>" + esc(s.url.replace(/^https?:\/\//, "")) + "</small>" +
    ' · ' + local.length + " in this browser" +
    (waiting.length ? ' · <span class="err">' + showWaiting(waiting.length) + "</span>" : "") +
    quota;
  $("export").style.display = shown.length ? "inline-block" : "none";
  $("sorts").style.display = shown.length ? "block" : "none";
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
  $("retry").textContent = waiting.length ? "Send " + waiting.length + " now" : "Send what is waiting";
  $("retry").style.display = waiting.length ? "inline-block" : "none";
  // Sending is automatic; this button only means "now, don't wait for the next turn".
  $("retry").classList.remove("primary");
  $("find").style.display = "none"; // already connected: reconnect lives in Settings
  if (s.last && s.last.ok === false && s.last.error) {
    $("status").innerHTML += ' · <span class="err">' + esc(s.last.error) + "</span>";
  }
  paintSort();
  paintFilter();
  repaint();
  // Missing captures are sent by themselves, no button. The button stays as an
  // explicit "now" for the impatient, not as the way the product works.
  if (waiting.length && !repaired) {
    repaired = true;
    $("status").innerHTML += ' · <span class="mut">sending them now…</span>';
    await chrome.runtime.sendMessage({ type: "sync" }).catch(() => {});
    return load();
  }
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

$("sort").addEventListener("change", () => {
  sortKey = $("sort").value;
  localStorage.setItem(SORT_KEY, sortKey);
  paintSort();
  repaint();
});

$("filter").addEventListener("change", () => {
  filterKey = $("filter").value;
  localStorage.setItem("el_filter", filterKey);
  paintFilter();
  repaint();
});

// The status line and the empty state can change the filter: one delegated
// listener, because those buttons are re-created on every render.
document.addEventListener("click", (e) => {
  const t = e.target instanceof Element ? e.target.closest("#onlywaiting,#clearfilter") : null;
  if (!t) return;
  filterKey = t.id === "onlywaiting" ? "waiting" : "all";
  localStorage.setItem("el_filter", filterKey);
  paintFilter();
  repaint();
});

$("dir").addEventListener("click", () => {
  sortDesc = !sortDesc;
  localStorage.setItem(SORT_DIR, sortDesc ? "1" : "0");
  paintSort();
  repaint();
});

paintSort();
paintFilter();
load();
})();
