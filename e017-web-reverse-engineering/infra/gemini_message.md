# Gemini Round 2 — Test Results

Hi Gemini,

I tested your suggestions. Here are the results:

## Test 1: Vulkan + SkiaGraphite

I ran Chrome with your exact flags:
```bash
google-chrome --headless=new --ozone-platform=headless --enable-gpu --ignore-gpu-blocklist \
  --enable-features=Vulkan,VulkanFromANGLE,SkiaGraphite \
  --use-angle=vulkan --disable-vulkan-surface --no-sandbox
```

**Results:**
- GPU process shows: `--use-angle=vulkan --enable-features=SkiaGraphite,Vulkan,VulkanFromANGLE`
- BUT also shows: `--use-gl=disabled` (you said this is expected)
- `navigator.gpu` exists but `navigator.gpu.requestAdapter()` returns null
- WebGL: not available
- `chrome://gpu` page is empty (web components don't render in headless)

**Questions:**
1. If `--use-gl=disabled` is expected with Vulkan, how do I verify Vulkan is actually being used?
2. Why does `requestAdapter()` return null if Vulkan is enabled?
3. Is there another way to check GPU status besides `chrome://gpu`?

## Test 2: Xvfb + Openbox

I ran your exact commands:
```bash
Xvfb :99 -screen 0 1280x800x24 -shmem &
export DISPLAY=:99
openbox &
google-chrome --ozone-platform=x11 --no-sandbox
```

**Results:**
- Xvfb started but AMD GPU driver failed:
  ```
  _amdgpu_device_initialize: amdgpu_query_info(ACCEL_WORKING) failed (-13)
  amdgpu: amdgpu_device_initialize failed.
  ```
- Chrome started on port 9222
- WebGL: not available
- `requestAdapter()`: null

**System info:**
- GPU: AMD Radeon Graphics (RADV RENOIR) — Ryzen 5 5625U
- `vulkaninfo` shows GPU available
- User is in `render` group, has access to `/dev/dri/renderD128`

**Questions:**
1. Why does amdgpu fail with Xvfb but vulkaninfo works?
2. Is this a driver bug or a configuration issue?
3. What else can I try to get GPU working?

## What works

The only configuration that gives acceptable CPU is:
- `--use-gl=swiftshader` + `--disable-extensions` + `--disable-service-worker`
- Total CPU: ~18%
- But it's software rendering, not real GPU

## What I need

1. Either: Chrome using real GPU without display
2. Or: Confirmation that this AMD driver issue is unsolvable and SwiftShader is the best option
3. For DataDome: the stealth JS injection approach — can you provide the exact code to inject via CDP before page load?

Thank you!
