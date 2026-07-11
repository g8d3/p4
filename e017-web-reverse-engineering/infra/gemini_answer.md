Aquí tienes el mensaje ultra-corto, directo y estructurado para que la otra inteligencia artificial entienda el problema y te genere el entorno de prueba de inmediato:

---

# Prompt for AI: Test Sway Headless for AMD GPU Acceleration

## Context & The Goal

The previous `amdgpu` Error `-13` was a **DRM Master / Auth** failure because Xvfb and Chrome Headless cannot lease the DRM node on this AMD Barcelo APU (Ubuntu 24.04).

We will bypass this by using **Sway (wlroots)** in headless mode. Sway acts as a legitimate Wayland compositor, authenticating correctly with `/dev/dri/renderD128`. Chrome will run as a standard desktop client on Wayland, offloading 100% of rendering to the real GPU.

## Verification Script

Run the following commands in the terminal to set up the headless Wayland environment and launch Chrome:

```bash
# 1. Setup Environment & Start Sway Headless
export WLR_BACKENDS=headless
export XDG_RUNTIME_DIR=/tmp/xdg-runtime-$USER
mkdir -p $XDG_RUNTIME_DIR && chmod 700 $XDG_RUNTIME_DIR

# Start Sway (ignores physical monitor check)
sway --unsupported-gpu > /dev/null 2>&1 &
sleep 2

# 2. Export the newly created Wayland display socket
export WAYLAND_DISPLAY=wayland-0

# 3. Launch Chrome targeting the Wayland compositor
google-chrome \
  --no-sandbox \
  --ozone-platform=wayland \
  --enable-gpu \
  --ignore-gpu-blocklist \
  --remote-debugging-port=9222 \
  --remote-allow-origins=* \
  ~/profiles/chrome-main

```

## Your Task

1. Verify if `amdgpu_device_initialize` error `-13` disappears in the logs.
2. Provide a quick Node.js/Python snippet using the CDP (port 9222) to evaluate `navigator.gpu.requestAdapter()` and check if it successfully returns the **AMD Radeon Graphics (RADV RENOIR)** adapter instead of `null`.