# GPU Pipeline v2 — Virtual Display with Real GPU

## Goal

Find a virtual display setup where Godot uses the **real AMD GPU** (not llvmpipe/CPU) for headless/automated rendering.

## Environment

- **GPU**: AMD Barcelo (Radeon, RENOIR, radeonsi)
- **DRI devices**: `/dev/dri/card1`, `/dev/dri/renderD128`
- **Main display**: Xorg on `:0` (seat0, vt2), GPU via amdgpu/modesetting
- **OS**: Ubuntu 24.04, kernel 6.8.0-124-generic

## Approaches Tested

### Approach 1: Xorg with modesetting driver on virtual display `:1`

**Result: FAILS** — `drmSetMaster failed: Device or resource busy`

Starting a second Xorg server with the modesetting driver on display `:1` fails because the main Xorg on `:0` already holds DRM master on card1. Two X servers cannot share the same GPU via modesetting.

The first brief run did initialize DRI3 + glamor before being killed:
```
(II) modeset(0): glamor X acceleration enabled on AMD Radeon Graphics (radeonsi, renoir, ACO)
(II) modeset(0): [DRI2]   DRI driver: radeonsi
(II) Initializing extension DRI3
```

But subsequent runs consistently fail with `drmSetMaster failed`. Even `-sharevts` and `-keeptty` flags don't help.

**Commands tested**:
```bash
# Attempt 1: modesetting driver
sudo Xorg :1 -config /tmp/xorg-virtual.conf -noreset -nolisten tcp
# Log: DRI3 + glamor initialized, but server terminated after ~10s

# Attempt 2: modesetting + sharevts
sudo Xorg :1 -config /tmp/xorg-virtual.conf -noreset -nolisten tcp -sharevts
# Fatal: AddScreen/ScreenInit failed for driver 0

# Attempt 3: amdgpu driver + keeptty
sudo Xorg :1 -config /tmp/xorg-amdgpu.conf -noreset -nolisten tcp -keeptty
# Fatal: drmSetMaster failed: Device or resource busy
```

**Conclusion**: Not viable. The main Xorg holds exclusive DRM master on the single GPU.

### Approach 2: Xephyr (nested X server)

**Result: FAILS** — No DRI3, amdgpu cannot initialize inside Xephyr

Xephyr runs as a nested X server inside the parent display. It provides GLX but **no DRI3 extension**. The amdgpu driver fails to initialize:
```
_amdgpu_device_initialize: amdgpu_query_info(ACCEL_WORKING) failed (-13)
amdgpu: amdgpu_device_initialize failed.
```

Without DRI3, Vulkan cannot work. Xephyr falls back to software rendering.

**Commands tested**:
```bash
DISPLAY=:0 Xephyr :98 -screen 608x1080
# No DRI3 extension, amdgpu init fails

DISPLAY=:0 Xephyr :97 -screen 608x1080 -glamor
# Still no DRI3, same amdgpu failure
```

**Conclusion**: Not viable. Xephyr cannot provide DRI3/Vulkan access.

### Approach 3: Weston (Wayland compositor) with headless backend + GL renderer

**Result: WORKS** — Real AMD GPU with OpenGL ES 3.2 and Vulkan

Weston headless backend initializes the GL renderer on the real GPU:
```
GL renderer: AMD Radeon Graphics (radeonsi, renoir, ACO, DRM 3.57, 6.8.0-124-generic)
GL version: OpenGL ES 3.2 Mesa 25.2.8-0ubuntu0.24.04.1
```

Godot runs as a Wayland client inside Weston and uses the real GPU:
- **OpenGL**: `OpenGL API 4.6 (Core Profile) - Using Device: AMD - AMD Radeon Graphics (radeonsi, renoir, ACO)`
- **Vulkan**: `Vulkan 1.4.318 - Forward+ - Using Device #0: AMD - AMD Radeon Graphics (RADV RENOIR)`

**GPU verification**:
| Setup | Device Used | GPU Busy |
|-------|-------------|----------|
| Weston + Godot Vulkan | AMD RADV RENOIR | 1-3% |
| Xvfb + Godot Vulkan | llvmpipe (CPU) | 0% |

**Commands — Working**:
```bash
# 1. Start Weston headless with GL renderer
weston --backend=headless --renderer=gl --socket=wayland-99 &
sleep 2

# 2. Run Godot as Wayland client (Vulkan)
WAYLAND_DISPLAY=wayland-99 \
  ~/.local/bin/godot4 \
  --display-driver wayland \
  --rendering-driver vulkan \
  --path /home/vuos/code/p4/e002-avatar-podcast/ag-04/godot_project \
  -- /home/vuos/code/p4/e002-avatar-podcast/ag-04/godot_project/config.json

# 3. Run Godot as Wayland client (OpenGL)
WAYLAND_DISPLAY=wayland-99 \
  ~/.local/bin/godot4 \
  --display-driver wayland \
  --rendering-driver opengl3 \
  --path /home/vuos/code/p4/e002-avatar-podcast/ag-04/godot_project \
  -- /home/vuos/code/p4/e002-avatar-podcast/ag-04/godot_project/config.json
```

**Note**: The Weston DRM backend (`--backend=drm`) also uses the GPU but requires exclusive DRM master, which conflicts with the main Xorg. The headless backend avoids this by not claiming DRM master for display output.

## Comparison: Xvfb vs Weston

| Feature | Xvfb | Weston headless |
|---------|------|-----------------|
| DRI3 support | No | N/A (Wayland) |
| GPU rendering | No (llvmpipe) | Yes (AMD radeonsi) |
| Vulkan device | llvmpipe (CPU) | AMD RADV RENOIR |
| OpenGL device | llvmpipe (Mesa) | AMD radeonsi |
| Display protocol | X11 | Wayland |
| Godot flag | `--display-driver x11` | `--display-driver wayland` |
| GPU busy during render | 0% | 1-3% |
| Parallel instances | Yes (separate :N) | Yes (separate socket) |

## Recommendation

**Use Weston headless + Wayland** for GPU-accelerated Godot rendering.

### Full Pipeline (Two-Step)

**Step 1: Godot renders frames via Weston**
```bash
# Start Weston
weston --backend=headless --renderer=gl --socket=wayland-$DISPLAY_NUM &
sleep 2

# Render frames
WAYLAND_DISPLAY=wayland-$DISPLAY_NUM \
  ~/.local/bin/godot4 \
  --display-driver wayland \
  --rendering-driver vulkan \
  --path /path/to/godot_project \
  -- /path/to/config.json
```

**Step 2: ffmpeg VAAPI encode**
```bash
export LIBVA_DRIVER_NAME=radeonsi
ffmpeg -vaapi_device /dev/dri/renderD128 \
  -framerate 25 \
  -i frames/frame_%05d.png \
  -vf "format=nv12,hwupload" \
  -c:v h264_vaapi \
  -y output.mp4
```

### Parallel Rendering

Multiple Godot instances can render simultaneously, each with its own Weston compositor:
```bash
for i in 1 2 3; do
  weston --backend=headless --renderer=gl --socket=wayland-99$i &
  sleep 2
  WAYLAND_DISPLAY=wayland-99$i \
    ~/.local/bin/godot4 \
    --display-driver wayland \
    --rendering-driver vulkan \
    --path /path/to/project \
    -- /path/to/config$i.json &
done
```

All instances share the same GPU. The GPU parallelism advantage over CPU (Xvfb/llvmpipe) is that GPU can time-share rendering across all instances efficiently, while CPU encoding would serialize them.

### Installation Required

```bash
sudo apt-get install -y weston
```

## Performance Notes

- Godot rendering speed is ~10-13 fps on both Xvfb and Weston (2D content is not GPU-bound)
- The GPU advantage is **parallelism**: one GPU can render 10+ virtual displays simultaneously
- GPU busy stays low (1-3%) for 2D content, leaving headroom for parallel instances
- Vulkan and OpenGL both work via Weston; Vulkan is recommended for 3D content
