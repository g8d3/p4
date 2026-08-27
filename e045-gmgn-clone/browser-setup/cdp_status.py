#!/usr/bin/env python3
"""cdp_status.py <port> — print the featureStatus + problems from SystemInfo.getInfo."""
import json, sys, urllib.request
import websocket

port = int(sys.argv[1])
ver = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version"))
ws = websocket.create_connection(ver["webSocketDebuggerUrl"], timeout=10)
ws.send(json.dumps({"id": 1, "method": "SystemInfo.getInfo"}))
while True:
    m = json.loads(ws.recv())
    if m.get("id") == 1:
        res = m.get("result", {})
        break
ws.close()

gpu = res.get("gpu", {})
aux = gpu.get("auxAttributes", {})
print("=== active GPU ===")
for d in gpu.get("devices", []):
    print(" ", d.get("vendorString"), "|", d.get("deviceString"), "|", d.get("driverVendor"), d.get("driverVersion"))
print("displayType:", aux.get("displayType"))
print("glRenderer:", aux.get("glRenderer"))
print("glVendor  :", aux.get("glVendor"))

print("\n=== featureStatus (interesting) ===")
fs = aux.get("featureStatus", {})
keys = ["gpu_compositing", "webgl", "webgl2", "canvas_oop_rasterization", "video_decode",
        "video_encode", "vaapi_video_decoder", "vaapi_video_encoder", "vulkan", "gl", "opengl",
        "software_rasterizer", "skia_graphite", "d3d11_video_decoder", "gpu_rasterization"]
for k in sorted(fs):
    if any(s in k.lower() for s in ["vaapi", "vulkan", "webgl", "video", "compositing", "gl", "raster", "acceler", "swiftshader", "opengl"]):
        print(f"  {k}: {fs[k]}")

print("\n=== featureStatus (ALL) ===")
for k in sorted(fs):
    print(f"  {k}: {fs[k]}")

print("\n=== problems ===")
print(json.dumps(res.get("problems", []), indent=2))
print("\n=== gpuDetails? ===")
print("keys:", list(res.keys()))
