// One extension page, two tabs. The hash picks the tab, so a link can open
// settings straight away and the browser's back button behaves.
const PANELS = { inbox: "Inbox", settings: "Settings" };

function showPanel(name) {
  const want = PANELS[name] ? name : "inbox";
  // Which version is installed, in the user's face: after an update this is the
// only way to tell that the update actually happened.
const v = document.getElementById("version");
if (v) {
  const m = chrome.runtime.getManifest();
  v.textContent = "v" + m.version;
  v.title = "EchoLike Lite " + m.version + " · " + m.manifest_version + " · installed " + (chrome.runtime.getManifest().update_url ? "with updates" : "from a folder");
}

for (const key of Object.keys(PANELS)) {
    const on = key === want;
    const tab = document.getElementById("tab-" + key);
    const panel = document.getElementById("panel-" + key);
    if (tab) tab.setAttribute("aria-selected", on ? "true" : "false");
    if (panel) panel.classList.toggle("on", on);
  }
  if (location.hash.slice(1) !== want) history.replaceState(null, "", "#" + want);
  // A hash change is a same-document navigation: nothing reloads, so each panel has
  // to refresh its own data when it becomes visible.
  if (ready) window.dispatchEvent(new CustomEvent("echolike:tab", { detail: want }));
}

let ready = false;

// Which version is installed, in the user's face: after an update this is the
// only way to tell that the update actually happened.
const v = document.getElementById("version");
if (v) {
  const m = chrome.runtime.getManifest();
  v.textContent = "v" + m.version;
  v.title = "EchoLike Lite " + m.version + " · " + m.manifest_version + " · installed " + (chrome.runtime.getManifest().update_url ? "with updates" : "from a folder");
}

for (const key of Object.keys(PANELS)) {
  const tab = document.getElementById("tab-" + key);
  if (tab) tab.addEventListener("click", () => showPanel(key));
}
window.addEventListener("hashchange", () => showPanel(location.hash.slice(1)));
showPanel(location.hash.slice(1));
ready = true; // the initial render must not double-fetch what the panel scripts already loaded
