(function () {
// EchoLike Lite — settings page. Everything the popup should not hold: a second
// inbox, the recovery code, and the optional account. Each card owns its own
// message line, so one failure never looks like another's.
const $ = (id) => document.getElementById(id);

const send = (type, extra) => chrome.runtime.sendMessage(Object.assign({ type }, extra || {}));
const esc = (s) =>
  String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const say = (id, text, kind) => {
  $(id).className = "msg " + (kind || "mut");
  $(id).innerHTML = text;
};
const mask = (v) => "•".repeat(Math.max(0, (v || "").length - 4)) + (v || "").slice(-4);

let state = {};

async function refresh() {
  state = await send("state");
  const connected = !!(state.url && state.hasToken);
  $("url").value = state.url || "";
  // The one code the user ever copies: it carries the list, its access and the key.
  // The raw key stays inside the product (the reader URL is built from it).
  $("key").value = state.pairCode || state.keyCode || "";
  $("key").type = "password";
  $("revealkey").textContent = "Reveal";

  say(
    "inboxstatus",
    connected
      ? '<span class="ok">Connected</span> to <b>' + esc(state.url.replace(/^https?:\/\//, "")) + "</b>" +
          (state.pending ? ' · <span class="err">' + state.pending + " waiting to send</span>" : "") +
          " · " + state.total + " saved in this browser"
      : '<span class="err">Not connected.</span> ' +
          (state.pending ? state.pending + " capture(s) waiting to send. " : "") +
          "Like a post on X: the first one connects an inbox by itself.",
  );

  // Which list this device is on: the id the server uses, so two phones can be
  // compared out loud ("both say 9f3a…").
  $("deviceid").innerHTML = state.url
    ? "This device writes to list <b>" + esc(state.listId || "—") + "</b>" +
      (state.phones > 1 ? " · <b>" + state.phones + " phones share it</b>" : "") +
      (state.accountEmail ? " · account <b>" + esc(state.accountEmail) + "</b>" : " · no account: this phone only")
    : "Not connected yet.";
  $("acctstatus").innerHTML = state.accountEmail
    ? '<span class="ok">Signed in as ' + esc(state.accountEmail) + "</span>" +
      (state.keyBackedAt
        ? ' · key backed up ' + esc(String(state.keyBackedAt).slice(0, 10))
        : ' · <span class="err">key not backed up</span>')
    : "Not signed in.";
  if (!$("email").value) $("email").value = state.accountEmail || "";
  // A signed-in account without a key backup cannot be read on a second device:
  // say it here, before it becomes a surprise ("some likes are not visible").
  if (state.accountToken) {
    const info = await send("account-info");
    if (info && info.ok && info.has_key === false) {
      $("acctstatus").innerHTML +=
        ' · <span class="err">no key backup yet: another browser will not be able to decrypt this account</span>';
    }
  }
  paintLearned();
  const ads = await chrome.storage.local.get({ hide_ads: true, fab_on: true });
  $("ads").checked = !!ads.hide_ads;
  $("fab").checked = ads.fab_on !== false;
  $("telon").checked = state.telOn !== false;
  paintLevel();
  $("telcount").textContent = state.telQueued ? state.telQueued + " waiting to be sent" : "";
  $("tellog").textContent = (state.telemetry || [])
    .map((e) =>
      [new Date(e.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }), e.action, e.ok === false ? "FAIL" : e.ok ? "ok" : "-", e.code || "", e.error || "", e.detail || ""]
        .join(" ")
        .trim(),
    )
    .join("\n") || "nothing yet";
}

// 1 · Inbox -----------------------------------------------------------------
$("save").addEventListener("click", async () => {
  const url = $("url").value.trim().replace(/\/$/, "");
  const token = $("token").value.trim();
  if (!url) return say("inboxstatus", "An address is needed.", "err");
  const r = token ? await send("save", { url, token }) : await send("claim", { url });
  $("token").value = "";
  await refresh();
  if (r && r.ok === false) return say("inboxstatus", esc(r.error), "err");
});

$("forget").addEventListener("click", async () => {
  await send("forget");
  await refresh();
  say("inboxstatus", "Disconnected. Catches stay in this browser until you connect again.", "mut");
});

// the ads switch is a storage flag the content script watches
$("ads").addEventListener("change", async () => {
  await chrome.storage.local.set({ hide_ads: $("ads").checked });
});

// A phone has no devtools, so the page asks the open X tab what its timeline looks
// like (tags and attributes only) and sends that with the diagnostics: the next DOM
// change gets read instead of guessed. `chrome.tabs` works here because the extension
// already holds host permissions for x.com.
async function adsReport() {
  let tabs = [];
  try {
    tabs = await chrome.tabs.query({ url: ["https://x.com/*", "https://twitter.com/*"] });
  } catch (e) {
    return null;
  }
  for (const t of tabs) {
    try {
      const r = await chrome.tabs.sendMessage(t.id, { type: "ads-report" });
      if (r) return r;
    } catch (e) {
      /* no content script in that tab yet: try the next one */
    }
  }
  return null;
}

// The one press that gets a real page out of a phone: the same report the Send button
// files, on the clipboard, as text — with the markup at the privacy level the owner
// chose. Numbers first (`geo`), so the hole a hidden ad leaves can be read without the
// markup at all.
$("adscopy").addEventListener("click", async () => {
  say("adsmsg", "Reading the X tab…");
  const r = await adsReport();
  if (!r) {
    return say("adsmsg", "No X tab answered. Open x.com in this browser, scroll until an ad shows, and press again.", "err");
  }
  const blob = JSON.stringify({ version: r.version || null, line: r.line, geo: r.geo || [], rich: r.rich || null }, null, 1);
  try {
    await navigator.clipboard.writeText(blob);
    say(
      "adsmsg",
      '<span class="ok">Copied.</span> ' + Math.round(blob.length / 1024) + " KB, " +
        (r.geo || []).length + " list(s) measured, " + r.marked + " ad(s) hidden. Paste it where it is being fixed.",
      "ok",
    );
  } catch (e) {
    // A browser that refuses the clipboard still gets an honest answer: the text is in
    // the box below, one long-press away from being copied by hand.
    const box = document.createElement("textarea");
    box.value = blob;
    box.style.cssText = "width:100%;height:120px;font:11px monospace";
    $("adsmsg").after(box);
    box.select();
    say("adsmsg", "This browser refused the clipboard — the text is below, select and copy it.", "err");
  }
});

// What the owner taught by marking ads on X: two marks of the same kind learn the
// word, and from then on it hides by itself. Shown here so it can also be forgotten.
async function paintLearned() {
  const s = await chrome.storage.local.get({ ads_learned: [], ads_pending: [], ads_skel: [], ads_skel_pending: "" });
  const n = (s.ads_learned || []).length;
  const p = (s.ads_pending || []).length;
  const k = (s.ads_skel || []).length;
  const q = s.ads_skel_pending ? 1 : 0;
  const parts = [];
  if (n) parts.push("<b>" + n + "</b> word(s)");
  if (k) parts.push("<b>" + k + "</b> shape(s)");
  $("adslearned").innerHTML = parts.length
    ? "Learned from your marks: " + parts.join(" and ") + " — ads like those are hidden by themselves."
    : p || q
      ? "One mark kept. Mark one more ad like it and it is learned."
      : "Nothing marked yet. On X, press the circle → <b>Mark an ad…</b>.";
  $("adsclear").style.display = n || p || k || q ? "inline-block" : "none";
}

$("adsclear").addEventListener("click", async () => {
  await chrome.storage.local.set({ ads_learned: [], ads_pending: [], ads_skel: [], ads_skel_pending: "" });
  await paintLearned();
  say("adsmsg", "Forgotten. Only the built-in words hide ads now.", "mut");
});

$("adscheck").addEventListener("click", async () => {
  say("adsmsg", "Reading the X tab…");
  const r = await adsReport();
  if (!r) {
    return say("adsmsg", "No X tab answered. Open x.com in this browser, scroll until an ad shows, and press again.", "err");
  }
  // Structure and short fingerprints only (see `adsReport` in content.js): the words
  // travel as 8-hex hashes, so a disclosure we do not know yet can be looked up in a
  // dictionary without the phone ever sending text.
  // Two rows leave at every level: the compact line (always structure + fingerprints)
  // in the diagnostics table, and the rich report, which carries what the owner's
  // privacy level allows — the labels, or the markup itself.
  const detail = (r.line || "").slice(0, 1200);
  await send("tel", { action: "ads.report", info: { ok: r.marked > 0, host: "x.com", detail } });
  const sent = r.rich ? await send("adreport", { report: r.rich }) : null;
  if (sent && sent.ok === false) {
    return say(
      "adsmsg",
      "The report is queued and goes out with the next send (" + esc(sent.error || "inbox unreachable") + ").",
      "err",
    );
  }
  say(
    "adsmsg",
    r.marked
      ? '<span class="ok">Sent.</span> ' + r.marked + " post(s) are already hidden on that tab."
      : '<span class="ok">Sent.</span> That tab shows ' + r.articles +
          " posts and none is recognised as an ad. This is what fixes it — no text or handle was sent.",
    "ok",
  );
  refresh();
});

// the circle on x.com: same idea, one flag plus its position
$("fab").addEventListener("change", async () => {
  await chrome.storage.local.set({ fab_on: $("fab").checked });
});
$("fabreset").addEventListener("click", async () => {
  await chrome.storage.local.set({ fab_x: null, fab_y: null });
  if (!$("fab").checked) {
    $("fab").checked = true;
    await chrome.storage.local.set({ fab_on: true });
  }
  say("keymsg", "The button goes back to the bottom right corner on the next X tab you open.", "ok");
});

// What a report is allowed to carry: its owner decides, not the code.
async function paintLevel() {
  const s = await chrome.storage.local.get({ report_level: "full" });
  const v = String(s.report_level || "full");
  $("reportlevel").value = v;
  say(
    "reportlevelmsg",
    v === "shapes"
      ? "Reports carry structure and fingerprints only."
      : v === "labels"
        ? "Reports carry structure and the short words as they are."
        : "Reports carry structure, the short words, and the card's markup — enough to write the rule from here.",
    "mut",
  );
}

$("reportlevel").addEventListener("change", async () => {
  await chrome.storage.local.set({ report_level: $("reportlevel").value });
  await paintLevel();
});

$("telon").addEventListener("change", async () => {
  await chrome.storage.local.set({ tel_on: $("telon").checked });
  refresh();
});

$("telcopy").addEventListener("click", async () => {
  await navigator.clipboard.writeText($("tellog").textContent);
  say("keymsg", "Diagnostics copied.", "ok");
});

$("telsend").addEventListener("click", async () => {
  await send("tel-flush");
  await refresh();
  say("keymsg", "Sent.", "ok");
});

// 2 · Recovery code ---------------------------------------------------------
$("revealkey").addEventListener("click", () => {
  const showing = $("key").type === "text";
  $("key").type = showing ? "password" : "text";
  $("revealkey").textContent = showing ? "Reveal" : "Hide";
});

$("copykey").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("key").value);
    say("keymsg", '<span class="ok">Copied.</span> Keep it somewhere you would keep a password.', "ok");
  } catch (e) {
    say("keymsg", "Copy failed: select the field and copy it by hand.", "err");
  }
});

// 3 · Account and key backup ------------------------------------------------
$("sendcode").addEventListener("click", async () => {
  const email = $("email").value.trim();
  if (!email) return say("acctmsg", "An email address is needed.", "err");
  say("acctmsg", "Sending…");
  const r = await send("acct-start", { email });
  await refresh();
  if (!r || r.ok === false) return say("acctmsg", esc((r && r.error) || "failed"), "err");
  say("acctmsg", '<span class="ok">Code sent.</span> It works for 10 minutes and lands in your email.', "ok");
});

$("verify").addEventListener("click", async () => {
  const email = $("email").value.trim();
  const code = $("code").value.trim();
  if (!email || code.length !== 6) return say("acctmsg", "Email and the 6 digits are needed.", "err");
  say("acctmsg", "Checking…");
  const r = await send("acct-verify", { email, code });
  await refresh();
  if (!r || r.ok === false) return say("acctmsg", esc((r && r.error) || "wrong or expired code"), "err");
  $("code").value = "";
  say(
    "acctmsg",
    '<span class="ok">Signed in.</span> Now choose a passphrase and back up your key, or you gain nothing on a new phone.',
    "ok",
  );
});

$("backup").addEventListener("click", async () => {
  const phrase = $("phrase").value;
  if (!phrase) return say("acctmsg", "Type the passphrase first: it is what protects the backup.", "err");
  say("acctmsg", "Wrapping your key…");
  const r = await send("key-save", { passphrase: phrase });
  await refresh();
  if (!r || r.ok === false) return say("acctmsg", esc((r && r.error) || "failed"), "err");
  $("phrase").value = "";
  say("acctmsg", '<span class="ok">Key backed up.</span> On a new device: sign in, then Restore key with this passphrase.', "ok");
});

$("restore").addEventListener("click", async () => {
  const phrase = $("phrase").value;
  if (!phrase) return say("acctmsg", "Type the passphrase you used for the backup.", "err");
  if (!confirm("This replaces the key in this browser with the one from your backup. Captures already saved here stay readable; anything waiting to be sent has to go first.")) return;
  say("acctmsg", "Unwrapping your key…");
  const r = await send("key-restore", { passphrase: phrase });
  await refresh();
  if (!r || r.ok === false) return say("acctmsg", esc((r && r.error) || "failed"), "err");
  $("phrase").value = "";
  say("acctmsg", '<span class="ok">Key restored.</span> Open my inbox to see everything again.', "ok");
});

window.addEventListener("echolike:tab", (e) => {
  if (e.detail === "settings") refresh();
});

refresh();
})();
