(function () {
// EchoLike Lite — the full inbox, in an extension page.
// It talks to whatever inbox the extension is connected to, decrypts every blob
// with the key stored in this browser, and lets the user export the lot. Nothing
// here is sent anywhere: the fetch carries the token, the plaintext never leaves.
const $ = (id) => document.getElementById(id);
// Each box of controls has a code (P1, P2…) so a failure can be reported as a code.
const showSec = (code, on) => {
  const el = document.querySelector('[data-section="' + code + '"]');
  if (el) el.hidden = !on;
};

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
  out.foreign = 0; // sealed with another phone's key, so this one cannot read it
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
      out.foreign += 1;
    }
  }
  return out;
}

// One compact line of steam, unless the row is too narrow: the grid below does
// the alignment, this just holds the numbers.
const fmt = (n) => (n == null ? "–" : n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "K" : String(n));

// Short but unambiguous: "12 Nov 08:10", with the year only when it is not this one.
const shortTime = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return String(iso);
  const o = { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" };
  if (d.getFullYear() !== new Date().getFullYear()) o.year = "numeric";
  return d.toLocaleString([], o);
};

// X's own furniture, drawn small: a rounded avatar with the author's initial, the name
// in bold, the @handle and the time in grey, then the action row with icons in X's order
// (reply, repost, like, bookmark, views). Our extra fields (four dates, media, "saved by")
// sit under that row, where X puts nothing, so the shape stays recognisable.
const ICONS = {
  reply: "M3.5 4.5h13v9h-7l-4 3v-3h-2z",
  repost: "M5 9V6.5h9M15 11v2.5H6M12.5 4.5 15 6.5l-2.5 2M7.5 15.5 5 13.5l2.5-2",
  like: "M10 16.5S3.5 12.7 3.5 8.6A3.6 3.6 0 0 1 10 6.3a3.6 3.6 0 0 1 6.5 2.3c0 4.1-6.5 7.9-6.5 7.9z",
  bookmark: "M6 3.5h8v13l-4-3-4 3z",
  views: "M3.5 15V9M8 15V4.5M12.5 15v-3M17 15V7",
};
const icon = (name) =>
  '<svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"' +
  ' stroke-linejoin="round" stroke-linecap="round" aria-hidden="true"><path d="' + ICONS[name] + '"/></svg>';

// A colour per handle, stable: nobody's avatar is stored, so the initial does the work.
function avatar(it) {
  const label = String(it.author_name || it.handle || "?").trim();
  const h = [...String(it.handle || label)].reduce((a, c) => (a * 31 + c.codePointAt(0)) % 360, 7);
  return '<span class="av" style="background:hsl(' + h + ' 58% 44%)">' + esc(label[0].toUpperCase()) + "</span>";
}

// A grid, not a sentence: every value in its own column, so the numbers line up
// down the list and the eye can compare rows instead of re-reading them.
const STATS = [
  ["replies", "reply"],
  ["reposts", "repost"],
  ["likes", "like"],
  ["bookmarks", "bookmark"],
  ["views", "views"],
];
function statsGrid(it) {
  const c = it.counts || {};
  // Always five cells, in X's order, each an icon + its number: an unknown value is a
  // dash in its own column, never a hole that shifts its neighbours.
  const cells = STATS.map(
    ([k, ic]) => '<span title="' + k + '">' + icon(ic) + "<b>" + esc(fmt(c[k])) + "</b></span>",
  );
  return '<div class="grid stats">' + cells.join("") + "</div>";
}

// Four dates, all kept on purpose: when I clicked, when this browser saved it,
// when the inbox received it, when the post was published. They are different
// events, and the point of sorting by one of them is to see the others.
const DATES = [
  ["liked", "clicked_at"],
  ["saved", "captured_at"],
  ["arrived", "received_at"],
  ["published", "published_at"],
];
function datesGrid(it) {
  const cells = DATES.map(([label, field]) => {
    const v = it[field] || (field === "published_at" ? it.tweet_time : "");
    if (!v) return "";
    // The exact second, without widening the column: it lives in the tooltip.
    return '<span title="' + esc(localTime(v)) + '"><i>' + label + "</i> <b>" + esc(shortTime(v)) + "</b></span>";
  })
    .filter(Boolean);
  return cells.length ? '<div class="grid dates">' + cells.join("") + "</div>" : "";
}

// One capture, one card: where it is from, what it is worth, when it happened,
// and what it says — each in its own block so the layout never becomes a paragraph.
function rowHtml(it, opt) {
  const o = opt || {};
  const name = it.author_name || it.handle || "post";
  const when = it.published_at || it.clicked_at;
  const savedBy = (o.savedBy || []).length;
  const tags =
    '<span class="tag kind">' + esc(it.kind) + "</span>" +
    (it.ad ? ' <span class="tag">ad</span>' : "") +
    (it.media ? ' <span class="tag">' + esc(it.media) + " media</span>" : "") +
    (savedBy > 1 ? ' <span class="tag good">saved by ' + savedBy + " people here</span>" : "") +
    (it.waiting ? ' <span class="tag warn">waiting to send</span>' : "") +
    (it.dup ? ' <span class="tag">also in this browser</span>' : "") +
    (it.legacy ? ' <span class="tag">unencrypted, older version</span>' : "");
  return (
    '<div class="head">' + avatar(it) +
    '<div class="ident"><b>' + esc(name) + "</b>" +
    (it.url
      ? ' <a class="at" target="_blank" rel="noreferrer" href="' + esc(it.url) + '">@' + esc(it.handle) + "</a>"
      : ' <span class="at">@' + esc(it.handle) + "</span>") +
    (when ? '<span class="at"> · ' + esc(shortTime(when)) + "</span>" : "") +
    '<div class="tags">' + tags + "</div>" +
    "</div></div>" +
    (it.text ? '<p class="body">' + esc(String(it.text).slice(0, 600)) + "</p>" : "") +
    statsGrid(it) +
    datesGrid(it) +
    (savedBy > 1 || o.former
      ? '<p class="savedby">' +
        (savedBy > 1
          ? "also saved by " +
            esc(o.savedBy.map((m) => "member " + String(m).replace(/^u_/, "").slice(0, 6)).slice(0, 6).join(", "))
          : "") +
        (o.former ? (savedBy > 1 ? " · " : "") + o.former + " no longer in this space" : "") +
        "</p>"
      : "")
  );
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
  ["dups", "second copies in this browser"],
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
  if (filterKey === "dups") return !!it.dup;
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
    row.className = "cap";
    row.innerHTML = rowHtml(it);
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
    if (body.used != null) extra = Object.assign({}, extra, { used: body.used, quota: body.quota });
    if (body.user) extra.user = body.user;
    if (body.phones != null) extra.phones = body.phones;
    if (body.account) extra.account = body.account;
    if (body.email) extra.email = body.email;
    if (body.tenants) extra.tenants = body.tenants;
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
    $("identity").innerHTML = "<b>no inbox yet</b> · this device only";
    showSec("P2", !!local.length);
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
  got.foreign = decrypted.foreign || 0;
  // Two browsers, one X account: the same like shows up once, not twice. Also a
  // capture stored twice by an older release: keep the first (newest) copy.
  const seen = new Set();
  const postKey = (it) => (it.kind || "") + "|" + (it.id || it.uid || "");
  const fromInbox = decrypted.filter((it) => {
    const k = postKey(it);
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  // What is in this browser but not in the inbox yet: the honest answer to
  // "did my likes arrive?". The inbox is read to the end above, so "missing"
  // really means missing.
  //
  // Two sets, deliberately built from the rows BEFORE the display dedupe above:
  // a row that was folded away because the same post also arrived under another
  // uid is still a row the inbox HAS. Building "sent" from the deduped list was a
  // permanent false alarm: the page said "not sent", the send found nothing to do
  // (it compares uids server-side), and the warning never cleared.
  const sentUids = new Set(got.items.map((b) => b.uid).filter(Boolean));
  const sentPosts = new Set(decrypted.map(postKey));
  for (const it of fromInbox) if (it.uid) sentUids.add(it.uid);
  const local = (await chrome.storage.local.get({ items: [], outbox: [] })).items;
  // A local capture counts as arrived when its uid is there, or when the same post
  // is: the user cares that the like made it, not which of their two copies did.
  const waiting = local.filter((i) => !sentUids.has(i.uid) && !sentPosts.has(postKey(i)));
  const waitingUids = new Set(waiting.map((i) => i.uid));
  // A capture whose POST is in the inbox but whose own row is not: the same post
  // twice in this browser (a re-like, or a live capture plus an import). It is not
  // unsent — the inbox has that post — so it is counted and named, never sent again.
  const dups = local.filter((i) => !waitingUids.has(i.uid) && !sentUids.has(i.uid) && sentPosts.has(postKey(i)));
  shown = fromInbox
    .concat(waiting.map((i) => Object.assign({}, i, { waiting: true })))
    .concat(dups.map((i) => Object.assign({}, i, { dup: true })));
  const used = got.extra.used != null ? got.extra.used : null;
  const quota = used != null && got.extra.quota ? " · " + used + "/" + got.extra.quota + " this month" : "";
  // Never leave "which account am I looking at" to guesswork: the list's own id, and
  // how many phones write to it. Two phones on one list is the normal case, not an
  // edge case, and it is the whole difference between "my likes are missing" and
  // "my other phone has its own list".
  const short = (id) => String(id || "");
  const listId = got.extra.account || got.extra.user || "";
  const phones = got.extra.phones || got.extra.tenants?.length || 1;
  const who = acct
    ? "account <b>" + esc(got.extra.email || s.accountEmail || "signed in") + "</b> · " + phones + " phone" + (phones === 1 ? "" : "s")
    : "<b>list " + esc(short(listId)) + "</b>" + (phones > 1 ? " · " + phones + " phones" : " · this phone only");
  $("identity").innerHTML =
    who +
    (phones > 1
      ? ""
      : ' · <button id="addphone" class="act" type="button" style="padding:1px 8px;margin:0">＋ Add my other phone</button>') +
    (got.foreign
      ? ' · <span class="err">' + got.foreign + " from another code: paste your other phone's code to read " +
        (got.foreign === 1 ? "it" : "them") + "</span>"
      : "");
  $("status").innerHTML =
    '<span class="ok">' + fromInbox.length + "</span> " + (acct ? "in my account " : "in the inbox ") +
    "<small>" + esc(s.url.replace(/^https?:\/\//, "")) + "</small>" +
    ' · ' + local.length + " in this browser" +
    (waiting.length ? ' · <span class="err">' + showWaiting(waiting.length) + "</span>" : "") +
    (dups.length ? ' · ' + dups.length + " second cop" + (dups.length === 1 ? "y" : "ies") + " of a post already in the inbox" : "") +
    quota;
  $("export").style.display = shown.length ? "inline-block" : "none";
  showSec("P2", !!shown.length);
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
    await chrome.runtime
      .sendMessage({ type: "send-uids", uids: waiting.map((i) => i.uid).filter(Boolean) })
      .catch(() => {});
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
  const uids = shown.filter((i) => i.waiting && i.uid).map((i) => i.uid);
  $("status").textContent = uids.length
    ? "Sending " + uids.length + " now…"
    : "Nothing is waiting: the inbox already has all of them.";
  const r = uids.length ? await chrome.runtime.sendMessage({ type: "send-uids", uids }) : { ok: true, added: 0 };
  $("retry").disabled = false;
  await load();
  if (r && r.ok === false) {
    $("status").innerHTML = '<span class="err">' + esc(r.error || "could not send") + "</span> Nothing was lost.";
  }
});

// ---- Spaces: the collaborative tab -----------------------------------------
// Create, invite (one-time code), join, read, share, leave. The space view renders the
// same cards as the inbox, with "saved by N people here" coming from decrypting every
// member's row locally — the server never learns which post is which.
let openSpace = null;
// A repaint replaces the rows, so a message written before it would vanish (that is
// how "shared 1 of 1" disappeared and looked like nothing happened). Messages live
// here and are re-applied after every paint.
const spaceMsgs = {};
function saySpace(id, html) {
  spaceMsgs[id] = html;
  const el = document.querySelector('[data-space-msg="' + id + '"]');
  if (el) el.innerHTML = html;
}

function painter1(id, on) {
  const el = document.querySelector('[data-section="' + id + '"]');
  if (el) el.hidden = !on;
}

async function paintSpaces() {
  const r = await chrome.runtime.sendMessage({ type: "space-list" }).catch(() => null);
  const box = $("spacelist");
  if (!r || r.ok === false) {
    box.innerHTML = '<p class="err">' + esc((r && r.error) || "could not read your spaces") + "</p>";
    return;
  }
  if (!r.spaces.length) {
    box.innerHTML = '<p class="mut">No spaces yet. Create one, or join with an invite.</p>';
    return;
  }
  box.textContent = "";
  for (const sp of r.spaces) {
    const row = document.createElement("div");
    row.className = "spacerow";
    row.innerHTML =
      "<b>" + esc(sp.name || "shared space") + "</b>" +
      (sp.role === "owner" ? ' <span class="tag kind">owner</span>' : "") +
      (sp.unreachable
        ? ' <span class="err">unreachable</span>'
        : ' <span class="at">· ' + (sp.members || 1) + " member" + ((sp.members || 1) === 1 ? "" : "s") + "</span>") +
      '<p style="margin:6px 0 0">' +
      '<button class="act" data-space="' + esc(sp.id) + '" data-what="open" type="button">Open</button>' +
      '<button class="act" data-space="' + esc(sp.id) + '" data-what="invite" type="button">Invite</button>' +
      '<button class="act" data-space="' + esc(sp.id) + '" data-what="invites" type="button">Active codes</button>' +
      '<button class="act" data-space="' + esc(sp.id) + '" data-what="share" type="button">Share my captures</button>' +
      '<button class="act" data-space="' + esc(sp.id) + '" data-what="leave" type="button">' +
      (sp.role === "owner" ? "Delete for me" : "Leave") +
      "</button></p>" +
      '<div class="msg mut" data-space-msg="' + esc(sp.id) + '"></div>';
    if (spaceMsgs[sp.id]) row.querySelector("[data-space-msg]").innerHTML = spaceMsgs[sp.id];
    box.appendChild(row);
  }
}

async function showSpace(id) {
  const r = await chrome.runtime.sendMessage({ type: "space-read", id }).catch(() => null);
  if (!r || r.ok === false) {
    $("spacehead").innerHTML = '<p class="err">' + esc((r && r.error) || "could not open that space") + "</p>";
    painter1("P16", true);
    return;
  }
  openSpace = r;
  const me = (await chrome.storage.local.get({ url: "", token: "" })).token;
  $("spacehead").innerHTML =
    "<b>" + esc(r.space.name) + "</b> · " + r.items.length + " post" + (r.items.length === 1 ? "" : "s") +
    " · " + (r.members || []).length + " member" + ((r.members || []).length === 1 ? "" : "s") +
    (r.foreign ? ' · <span class="err">' + r.foreign + " unreadable here</span>" : "") +
    '<p style="margin:6px 0 0"><button class="act" id="spaceback" type="button">← All spaces</button></p>';
  const box = $("spacelistitems");
  box.textContent = "";
  if (!r.items.length) {
    box.innerHTML = '<p class="mut">Nothing shared here yet. Press <b>Share my captures</b> in the list above.</p>';
    painter1("P16", true);
    painter1("P15", false);
    return;
  }
  for (const it of sortRows(r.items, sortKey, sortDesc)) {
    const k = String(it.kind || "") + "|" + String(it.id || it.uid || "");
    const row = document.createElement("div");
    row.className = "cap";
    row.innerHTML = rowHtml(it, { savedBy: (r.saved && r.saved[k]) || [], former: (r.former && r.former[k]) || 0, me });
    box.appendChild(row);
  }
  painter1("P15", false);
  painter1("P16", true);
}

async function paintInvites(id) {
  const r = await chrome.runtime.sendMessage({ type: "space-invites", id }).catch(() => null);
  if (!r || r.ok === false) {
    saySpace(id, esc((r && r.error) || "could not read the invitations"));
    return;
  }
  const live = r.invites.filter((i) => i.active);
  if (!live.length) {
    saySpace(id, '<span class="mut">No code can be used right now. Press <b>Invite</b> to make one.</span>');
    return;
  }
  saySpace(
    id,
    live
      .map(
        (i) =>
          '<div style="font-size:11px;color:#555">' +
          (i.max_uses - i.uses) + " use" + (i.max_uses - i.uses === 1 ? "" : "s") + " left · expires " +
          esc(shortTime(i.expires_at)) +
          ' <button class="act" data-space="' + esc(id) + '" data-what="invite-revoke" data-invite="' + esc(i.id) +
          '" type="button" style="padding:1px 7px;margin-left:6px">Revoke</button></div>',
      )
      .join(""),
  );
}

document.addEventListener("click", async (e) => {
  const t = e.target instanceof Element ? e.target.closest("[data-space],[data-what]") : null;
  if (!t) return;
  const id = t.getAttribute("data-space");
  const what = t.getAttribute("data-what");
  if (!id || !what) return;
  const say = (text, cls) => saySpace(id, '<span class="' + (cls || "mut") + '">' + text + "</span>");
  if (what === "open") return showSpace(id);
  if (what === "share") {
    say("sharing…");
    const r = await chrome.runtime.sendMessage({ type: "space-share", id }).catch(() => null);
    if (!r || r.ok === false) {
      say(esc((r && r.error) || "could not share"), "err");
      return;
    }
    await paintSpaces();
    say(r.added ? "shared " + r.added + " of " + r.total + " captures" : "already shared", "ok");
    return;
  }
  if (what === "invite") {
    // Ask how many people and for how long, once, inline: the answer changes the code
    // and a one-use code was the reason inviting a second person needed a second trip.
    saySpace(
      id,
      '<div class="inviteform">' +
        '<label>for <select data-inv-uses>' +
        '<option value="1">1 person</option>' +
        '<option value="2">2 people (or my 2 phones)</option>' +
        '<option value="3" selected>3 people</option>' +
        '<option value="5">5 people</option>' +
        '<option value="10">10 people</option>' +
        "</select></label>" +
        '<label>valid <select data-inv-hours>' +
        '<option value="1">1 hour</option>' +
        '<option value="24" selected>24 hours</option>' +
        '<option value="72">3 days</option>' +
        '<option value="168">7 days</option>' +
        "</select></label>" +
        '<button class="act primary" data-space="' + esc(id) + '" data-what="invite-make" type="button">Create invite</button>' +
        "</div>",
    );
    return;
  }
  if (what === "invite-make") {
    const box = t.closest(".inviteform");
    const uses = box ? Number(box.querySelector("[data-inv-uses]").value) : 1;
    const hours = box ? Number(box.querySelector("[data-inv-hours]").value) : 24;
    say("creating an invite…");
    const r = await chrome.runtime.sendMessage({ type: "space-invite", id, uses, hours }).catch(() => null);
    if (!r || r.ok === false) {
      say(esc((r && r.error) || "could not create an invitation"), "err");
      return;
    }
    let copied = "";
    try {
      await navigator.clipboard.writeText(r.code);
      copied = " Copied to the clipboard.";
    } catch (err) {
      copied = " Select the code and copy it.";
    }
    await paintSpaces();
    saySpace(
      id,
      '<input readonly onclick="this.select()" style="font:11px ui-monospace,monospace;width:100%;box-sizing:border-box;padding:7px;border:1px solid #ccc;border-radius:7px" value="' +
        esc(r.code) + '">' +
        '<div class="mut" style="font-size:11px;margin-top:4px">Works <b>' + r.uses + " time" + (r.uses === 1 ? "" : "s") +
        "</b>, expires <b>" + esc(shortTime(r.expires_at)) + "</b>. Send it to whoever you want in — the same code works for all of them, up to that count." +
        esc(copied) + "</div>",
    );
    return;
  }
  if (what === "invite-revoke") {
    const invite = t.getAttribute("data-invite");
    const r = await chrome.runtime.sendMessage({ type: "space-revoke-invite", id, invite }).catch(() => null);
    if (!r || r.ok === false) {
      say(esc((r && r.error) || "could not revoke it"), "err");
      return;
    }
    await paintInvites(id);
    say("that code no longer works", "ok");
    return;
  }
  if (what === "invites") {
    return paintInvites(id);
  }
  if (what === "leave") {
    const r = await chrome.runtime.sendMessage({ type: "space-leave", id }).catch(() => null);
    if (!r || r.ok === false) {
      say(esc((r && r.error) || "could not leave"), "err");
      return;
    }
    painter1("P16", false);
    await paintSpaces();
    say("you are out of that space", "ok");
  }
});

$("spacecreate").addEventListener("click", async () => {
  const name = $("spacename").value.trim();
  if (!name) {
    $("spacenew").innerHTML = '<span class="err">Give the space a name first.</span>';
    return;
  }
  $("spacecreate").disabled = true;
  $("spacenew").textContent = "creating…";
  const r = await chrome.runtime.sendMessage({ type: "space-create", name }).catch(() => null);
  $("spacecreate").disabled = false;
  if (!r || r.ok === false) {
    $("spacenew").innerHTML = '<span class="err">' + esc((r && r.error) || "could not create it") + "</span>";
    return;
  }
  $("spacename").value = "";
  $("spacenew").innerHTML = '<span class="ok">Created. Press <b>Invite</b> to make a code: choose how many people and how long.</span>';
  paintSpaces();
});

$("spacejoin").addEventListener("click", async () => {
  const code = $("spacecode").value.trim();
  if (!code) {
    $("spacemsg").innerHTML = '<span class="err">Paste the invite code first.</span>';
    return;
  }
  $("spacejoin").disabled = true;
  $("spacemsg").textContent = "checking the invitation…";
  const r = await chrome.runtime.sendMessage({ type: "space-join", code }).catch(() => null);
  $("spacejoin").disabled = false;
  if (!r || r.ok === false) {
    $("spacemsg").innerHTML = '<span class="err">' + esc((r && r.error) || "that did not work") + "</span>";
    return;
  }
  $("spacecode").value = "";
  $("spacemsg").innerHTML = '<span class="ok">You are in <b>' + esc(r.space.name) + "</b>" +
    (r.already ? " (you were already a member)" : "") + ". Press <b>Open</b> to see it.</span>";
  paintSpaces();
});

document.addEventListener("click", (e) => {
  if (e.target instanceof Element && e.target.id === "spaceback") {
    painter1("P16", false);
    painter1("P15", true);
    paintSpaces();
  }
});

window.addEventListener("echolike:tab", (e) => {
  if (e.detail === "spaces") paintSpaces();
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
document.addEventListener("click", async (e) => {
  const t = e.target instanceof Element ? e.target : null;
  if (!t) return;
  if (t.id === "addphone") {
    $("joinbox").style.display = "block";
    $("joinmsg").textContent = "";
    $("joinin").focus();
    return;
  }
  if (t.id === "joinclose") {
    $("joinbox").style.display = "none";
    return;
  }
  if (t.id === "joinbtn") {
    const code = $("joinin").value.trim();
    if (!code) {
      $("joinmsg").innerHTML = '<span class="err">Paste the code from the other phone first.</span>';
      return;
    }
    t.disabled = true;
    $("joinmsg").textContent = "Checking that code against the other list…";
    const r = await chrome.runtime.sendMessage({ type: "pair", code }).catch(() => null);
    t.disabled = false;
    if (!r || r.ok === false) {
      $("joinmsg").innerHTML = '<span class="err">' + esc((r && r.error) || "that did not work") + "</span>";
      return;
    }
    $("joinin").value = "";
    $("joinbox").style.display = "none";
    $("joinmsg").textContent = "";
    return load();
  }
  const chip = t.closest("#onlywaiting,#clearfilter");
  if (!chip) return;
  filterKey = chip.id === "onlywaiting" ? "waiting" : "all";
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
