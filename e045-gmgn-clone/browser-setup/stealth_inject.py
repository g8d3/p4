#!/usr/bin/env python3
"""
stealth_inject.py <port> — pin a stealth init script onto every page target of a
CDP browser (including tabs agent-browser opens afterwards) by auto-attaching and
calling Page.addScriptToEvaluateOnNewDocument. Masks the SwiftShader WebGL leak and
a few other headless tells. Keeps running so new tabs are covered.
"""
import json, sys, time, urllib.request
import websocket  # websocket-client

port = int(sys.argv[1])
STEALTH_SOURCE = r"""
(() => {
  try { Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true }); } catch (e) {}
  const MASK = {
    0x9245: 'ANGLE (AMD, AMD Radeon Graphics (0x00001567), OpenGL 4.6 (Core Profile) Mesa 25.2.8, D3D11)',
    0x9246: 'Google Inc. (AMD)'
  };
  const patch = (proto) => {
    if (!proto || proto.__masked) return;
    const orig = proto.getParameter;
    proto.getParameter = function (p) { if (MASK[p] !== undefined) return MASK[p]; return orig.call(this, p); };
    proto.__masked = true;
  };
  try { if (window.WebGLRenderingContext) patch(WebGLRenderingContext.prototype); } catch (e) {}
  try { if (window.WebGL2RenderingContext) patch(WebGL2RenderingContext.prototype); } catch (e) {}
  try {
    const gw = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'naturalWidth');
    const gh = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'naturalHeight');
    Object.defineProperty(HTMLImageElement.prototype, 'naturalWidth', {
      get() { const v = gw.get.call(this); return (this.complete && v > 1 && v !== 16) ? v : 0; }, configurable: true });
    Object.defineProperty(HTMLImageElement.prototype, 'naturalHeight', {
      get() { const v = gh.get.call(this); return (this.complete && v > 1 && v !== 16) ? v : 0; }, configurable: true });
  } catch (e) {}
})();
"""

ver = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version"))
ws = websocket.create_connection(ver["webSocketDebuggerUrl"], timeout=30)
_id = [0]
pending = {}
attached = {}

def send(method, params=None, sessionId=None):
    _id[0] += 1
    i = _id[0]
    msg = {"id": i, "method": method, "params": params or {}}
    if sessionId:
        msg["sessionId"] = sessionId
    ws.send(json.dumps(msg))
    pending[i] = method
    return i

def next_msg():
    while True:
        try:
            raw = ws.recv()
        except Exception as e:
            print("recv error:", e, file=sys.stderr); time.sleep(1); continue
        try:
            m = json.loads(raw)
        except Exception:
            continue
        if isinstance(m, dict):
            return m

def inject(sessionId):
    send("Page.addScriptToEvaluateOnNewDocument", {"source": STEALTH_SOURCE}, sessionId)
    print(f"  injected stealth into session {sessionId[:8]}", flush=True)

def handle_event(m):
    method = m.get("method")
    params = m.get("params", {})
    if method == "Target.attachedToTarget":
        sid = params.get("sessionId"); ti = params.get("targetInfo", {})
        attached[ti.get("targetId")] = sid
        if ti.get("type") == "page":
            inject(sid)
            # new targets are paused (waitForDebuggerOnStart); unlock after injecting
            send("Runtime.runIfWaitingForDebugger", {}, sid)
    elif method == "Target.targetCreated":
        ti = params.get("targetInfo", {})
        if ti.get("type") == "page":
            send("Target.attachToTarget", {"targetId": ti["targetId"], "flatten": True})

def get_targets():
    _id[0] += 1; i = _id[0]
    ws.send(json.dumps({"id": i, "method": "Target.getTargets", "params": {}})); pending[i] = "getTargets"
    while True:
        m = next_msg()
        if m.get("id") == i:
            return m.get("result", {}).get("targetInfos", [])
        handle_event(m)

send("Target.setAutoAttach", {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": True})
send("Target.setDiscoverTargets", {"discover": True})
for ti in get_targets():
    if ti.get("type") == "page":
        send("Target.attachToTarget", {"targetId": ti["targetId"], "flatten": True})

print(f"[stealth_inject] watching on :{port} — Ctrl-C to stop", flush=True)
while True:
    m = next_msg()
    if m.get("id") is not None:
        pending.pop(m["id"], None)
    else:
        handle_event(m)
