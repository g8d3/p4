// One extension page, two tabs. The hash picks the tab, so a link can open
// settings straight away and the browser's back button behaves.
const PANELS = { inbox: "Inbox", settings: "Settings" };

function showPanel(name) {
  const want = PANELS[name] ? name : "inbox";
  for (const key of Object.keys(PANELS)) {
    const on = key === want;
    const tab = document.getElementById("tab-" + key);
    const panel = document.getElementById("panel-" + key);
    if (tab) tab.setAttribute("aria-selected", on ? "true" : "false");
    if (panel) panel.classList.toggle("on", on);
  }
  if (location.hash.slice(1) !== want) history.replaceState(null, "", "#" + want);
}

for (const key of Object.keys(PANELS)) {
  const tab = document.getElementById("tab-" + key);
  if (tab) tab.addEventListener("click", () => showPanel(key));
}
window.addEventListener("hashchange", () => showPanel(location.hash.slice(1)));
showPanel(location.hash.slice(1));
