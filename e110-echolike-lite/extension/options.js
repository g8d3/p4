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
  $("key").value = state.keyCode || "";
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
  const ads = await chrome.storage.local.get({ hide_ads: true });
  $("ads").checked = !!ads.hide_ads;
  $("telon").checked = state.telOn !== false;
  $("telcount").textContent = state.telQueued ? state.telQueued + " waiting to be sent" : "";
  $("tellog").textContent = (state.telemetry || [])
    .map((e) => [e.at.slice(11, 19), e.action, e.ok === false ? "FAIL" : e.ok ? "ok" : "-", e.code || "", (e.ms || "") + "ms", e.error || ""].join(" ").trim())
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
