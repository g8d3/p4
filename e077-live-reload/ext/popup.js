// Popup: the ONE setting. Changing IP needs no reinstall — save here, done.
const input = document.getElementById("s");
const msg = document.getElementById("m");
const open = document.getElementById("o");

chrome.storage.local.get("serverUrl", ({ serverUrl }) => {
  if (serverUrl) {
    input.value = serverUrl;
    open.href = serverUrl;
  }
});

document.getElementById("b").onclick = () => {
  const v = input.value.trim().replace(/\/$/, "");
  chrome.storage.local.set({ serverUrl: v }, () => {
    msg.textContent = "saved — reload the test page";
    open.href = v;
  });
};
