# Message for Gemini — Chrome Headless GPU + DataDome

Hi Gemini,

I'm building a web reverse engineering tool that uses Chrome headless via agent-browser. I need your help with two issues:

## Issue 1: Chrome GPU without display

I'm on Ubuntu 24.04 with AMD Barcelo (RADV RENOIR) GPU. I want Chrome headless to use the real GPU instead of software rendering.

I tried:
- `--use-gl=angle --use-angle=gl-egl` → `--use-gl=disabled`
- `--use-angle=vulkan --disable-vulkan-surface` → still `--use-gl=disabled`
- `--use-gl=swiftshader` → works but is software rendering

vulkaninfo shows the GPU is available:
```
GPU id = 0 (AMD Radeon Graphics (RADV RENOIR))
GPU id = 1 (llvmpipe (LLVM 20.1.2, 256 bits))
```

You mentioned the combo: `--headless=new --use-angle=vulkan --disable-vulkan-surface --ozone-platform=headless --enable-features=Vulkan,VulkanFromANGLE`

But Chrome still puts `--use-gl=disabled` in the GPU process. What am I missing? Is there a way to verify if Vulkan is actually being used despite the flag?

## Issue 2: DataDome bot protection

A website (higgsfield.ai) uses DataDome. Even with a custom User-Agent (removing "HeadlessChrome"), the API POST requests return 403 + CAPTCHA.

The OPTIONS preflight now returns 200 (after User-Agent fix), but the actual POST still fails.

DataDome seems to use multiple detection signals beyond User-Agent. What are all the signals DataDome checks? Is there a way to make Chrome headless pass DataDome without using Xvfb?

## Current setup

- Chrome wrapper at `/usr/local/bin/google-chrome`
- Uses SwiftShader (18% CPU) as fallback
- `--disable-extensions --disable-service-worker` for performance
- Profile at `~/profiles/chrome-main`

## What I want

1. Chrome using real GPU without display virtual
2. DataDome not blocking API calls from headless browser
3. If neither is possible with headless, what's the lightest virtual display setup?

Thank you!
