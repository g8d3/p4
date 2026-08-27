#!/usr/bin/env python3
"""cdp_gpu_shadow.py <port> — pierce shadow DOM on chrome://gpu and dump innerText."""
import json, sys, time, urllib.request
import websocket

port = int(sys.argv[1])
targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
page = next(t for t in targets if t.get("type") == "page")
ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=20)
mid = [0]
def send(method, params=None):
    mid[0] += 1
    ws.send(json.dumps({"id": mid[0], "method": method, "params": params or {}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == mid[0]:
            return m.get("result", {})

send("Page.enable"); send("Runtime.enable")
send("Page.navigate", {"url": "chrome://gpu/"})
time.sleep(3.5)

expr = r"""
(() => {
  const texts = [];
  const walk = (root, depth) => {
    let el = root.querySelector && root.querySelector('*');
    // gather all elements recursively including shadow roots
    const all = root.querySelectorAll ? root.querySelectorAll('*') : [];
    for (const e of all) {
      if (e.shadowRoot) {
        walk(e.shadowRoot, depth+1);
      }
    }
  };
  // collect innerText of every element that has shadowRoot
  const out = [];
  const collect = (root) => {
    for (const e of (root.querySelectorAll ? root.querySelectorAll('*') : [])) {
      if (e.shadowRoot) collect(e.shadowRoot);
      if (e.tagName && e.tagName.match(/tab|div|span|td|tr|b/)) {
        const t = (e.innerText||'').trim();
        if (t && t.length > 2 && t.length < 200) out.push(t);
      }
    }
  };
  collect(document);
  return out.join('\n');
})()
"""
res = send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
txt = res.get("result", {}).get("value", "") or ""
print("captured chars:", len(txt))
for kw in ["Feature Status", "Video Decode", "Video Encode", "WebGL", "GL_RENDERER", "GL_VENDOR", "GPU compositing", "Canvas", "Problems", "Vulkan"]:
    idx = txt.find(kw)
    if idx >= 0:
        print(f"\n=== {kw} ===")
        print(txt[idx:idx+160].replace("\n", " | "))
print("\n--- known flags in dump ---")
for kw in ["Hardware accelerated", "Software only", "Unavailable", "Disabled", "SwiftShader", "llvmpipe", "AMD", "Vulkan", "VA-API", "VAAPI", "GL initial"]:
    c = txt.count(kw)
    if c: print(f"  '{kw}': {c}")
