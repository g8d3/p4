#!/usr/bin/env python3
"""cdp_gpu.py <port> — call SystemInfo.getInfo on the browser target and print GPU/feature status."""
import json, sys, urllib.request
import websocket  # websocket-client

port = int(sys.argv[1])
ver = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version"))
ws_url = ver["webSocketDebuggerUrl"]
print(f"browser ws: {ws_url}")
ws = websocket.create_connection(ws_url, timeout=10)
ws.send(json.dumps({"id": 1, "method": "SystemInfo.getInfo"}))
raw = ""
while True:
    msg = json.loads(ws.recv())
    if msg.get("id") == 1:
        raw = msg.get("result", {})
        break
ws.close()

gpu = raw.get("gpu", {})
aux = raw.get("auxAttributes", {})
# basics
print("\n--- basic gpu ---")
print("vendorId :", gpu.get("vendorId"))
print("deviceId :", gpu.get("deviceId"))
print("name     :", gpu.get("name"))
print("driverVendor:", gpu.get("driverVendor"))
print("driverVersion:", gpu.get("driverVersion"))
print("glRenderer (active):", gpu.get("glRenderer"))
print("glVendor  (active):", gpu.get("glVendor"))
print("glImplementationParts:", json.dumps(gpu.get("glImplementationParts"), indent=2))
print("aux.glRenderer :", aux.get("glRenderer"))
print("aux.glVendor   :", aux.get("glVendor"))
print("aux.glImplementationParts:", json.dumps(aux.get("glImplementationParts"), indent=2))

print("\n--- feature status ---")
fs = aux.get("featureStatus", {})
for k in sorted(fs):
    v = fs[k]
    # highlight the interesting ones
    if any(s in k.lower() for s in ["vaapi","vulkan","opengl","webgl","canvas","video","gpu compositing","raster","acceler","gl","decod","encod","software"]):
        print(f"  {k}: {v}")

print("\n--- feature status (ALL, sorted) ---")
print(json.dumps(fs, indent=2))

print("\n--- problems ---")
print(json.dumps(raw.get("problems", []), indent=2))
