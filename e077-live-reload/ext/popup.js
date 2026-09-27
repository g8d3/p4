// Popup: server address + lab mode. Everything here applies without reinstall.
const input = document.getElementById("s");
const msg = document.getElementById("m");
const open = document.getElementById("o");
const lab = document.getElementById("lab");
const hosts = document.getElementById("hosts");

chrome.storage.local.get(["serverUrl", "labOn", "labHosts"], (r) => {
  if (r.serverUrl) {
    input.value = r.serverUrl;
    open.href = r.serverUrl;
  }
  lab.checked = !!r.labOn;
  hosts.value = (r.labHosts || []).join(", ");
});

document.getElementById("b").onclick = () => {
  const v = input.value.trim().replace(/\/$/, "");
  const labHosts = hosts.value
    .split(",")
    .map((h) => h.trim().toLowerCase().replace(/^https?:\/\//, "").split("/")[0])
    .filter(Boolean);
  chrome.storage.local.set({ serverUrl: v, labOn: lab.checked, labHosts }, () => {
    msg.textContent = "saved — reload the test page";
    open.href = v;
  });
};
