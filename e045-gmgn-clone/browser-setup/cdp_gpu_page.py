#!/usr/bin/env python3
"""cdp_gpu_page.py <port> — navigate a page target to chrome://gpu and read the feature-status text."""
import json, sys, time, urllib.request
import websocket

port = int(sys.argv[1])
# find a page target
targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
page = next(t for t in targets if t.get("type") == "page")
print("page target:", page.get("url"))
ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=15)
mid = [0]
def send(method, params=None):
    mid[0] += 1
    ws.send(json.dumps({"id": mid[0], "method": method, "params": params or {}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == mid[0]:
            return m.get("result", {})

send("Page.enable")
send("Runtime.enable")
send("Page.navigate", {"url": "chrome://gpu/"})
time.sleep(3)
res = send("Runtime.evaluate", {"expression": "document.body.innerText", "returnByValue": True})
txt = res.get("result", {}).get("value", "") or ""
print("\nsize:", len(txt))
print("---------------------------")
# Print the section headers + a slice around Feature Status
print(txt[:300])
print("...")
for kw in ["Feature Status", "Problems", "Video Decode", "WebGL", "GL_RENDERER", "GL_VENDOR", "Video Encode", "Canvas", "GPU compositing"]:
    idx = txt.find(kw)
    if idx >= 0:
        print(f"\n=== around '{kw}' ===")
        print(txt[idx:idx+500].replace("\n", " | "))
