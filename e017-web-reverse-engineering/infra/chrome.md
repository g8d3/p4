# Chrome Headless — GPU, CPU & DataDome

## The Problem

Chrome headless on this system (AMD Barcelo GPU, Ubuntu 24.04) consumes high CPU and gets detected by DataDome.

## What We Tried

### 1. Default headless (`--headless=new`)
- CPU: ~256% total
- GPU process: `--use-gl=disabled` (software rendering)
- DataDome: Detects "HeadlessChrome" in User-Agent

### 2. ANGLE/EGL (`--use-gl=angle --use-angle=gl-egl`)
- CPU: ~262% total
- GPU process: Still `--use-gl=disabled`
- Chrome can't initialize EGL without display server

### 3. Vulkan (`--use-angle=vulkan --disable-vulkan-surface`)
- CPU: ~100%+ (worse)
- GPU process: `--use-gl=disabled` despite Vulkan flags
- vulkaninfo shows AMD GPU available, but Chrome doesn't use it

### 4. SwiftShader (`--use-gl=swiftshader`)
- CPU: ~19% (much better!)
- Software GL rendering, not real GPU
- Stable, no crashes

### 5. With extensions disabled (`--disable-extensions --disable-service-worker`)
- CPU: ~18% (best result!)
- Extensions (Adblock, Bitwarden) were running Service Workers in background
- Service Worker cache was 451MB

## Current Solution

Wrapper at `/usr/local/bin/google-chrome`:
- `--ozone-platform=headless`
- `--use-gl=swiftshader` (software GL, ~18% CPU)
- `--disable-extensions` (no background scripts)
- `--disable-service-worker` (no SW cache)
- `--remote-debugging-port=9222`
- `--remote-allow-origins=*`
- Custom User-Agent (removes "HeadlessChrome")
- Profile: `~/profiles/chrome-main`

## User-Agent Issue

Chrome headless sets User-Agent to include "HeadlessChrome":
```
Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/149.0.0.0 Safari/537.36
```

DataDome detects this and blocks API calls (OPTIONS 403, POST 403 + CAPTCHA).

Wrapper fixes this with `--user-agent=...Chrome/149.0.0.0 Safari/537.36` (no "Headless").

Result: OPTIONS preflight returns 200 instead of 403. But POST still returns 403 + CAPTCHA because DataDome uses other detection signals.

## GPU Without Display

According to Gemini, it IS possible to use GPU without Xvfb/Wayland using:
```
--headless=new
--use-angle=vulkan
--disable-vulkan-surface
--ozone-platform=headless
--enable-features=Vulkan,VulkanFromANGLE
```

However, on this AMD Barcelo system, Chrome still sets `--use-gl=disabled`. The GPU process shows Vulkan in flags but falls back to software rendering.

vulkaninfo confirms AMD GPU is available:
```
GPU id = 0 (AMD Radeon Graphics (RADV RENOIR))
GPU id = 1 (llvmpipe (LLVM 20.1.2, 256 bits))
```

## Potential Solutions

1. **Xvfb + non-headless Chrome**: Most reliable for bypassing DataDome. Chrome runs as normal browser on virtual display.
2. **Vulkan debugging**: Figure out why Chrome falls back to software despite Vulkan being available.
3. **Stealth libraries**: Playwright/Puppeteer with stealth plugins that patch headless detection.
4. **Session reuse**: Login once manually, reuse cookies for automation.

## CPU Benchmarks

| Configuration | Total CPU | Notes |
|--------------|-----------|-------|
| Default headless | 256% | Extensions + Service Workers |
| SwiftShader only | 19% | No extensions |
| SwiftShader + no extensions | 18% | Current solution |
| higgsfield.ai page | 19% | With current solution |
| YouTube | 27% | With current solution |
| Twitter/X | 95% | Heavy SPA, unavoidable |

## Files

- `/usr/local/bin/google-chrome` — Chrome wrapper
- `sites/higgsfield/notes.md` — DataDome issues specific to higgsfield
