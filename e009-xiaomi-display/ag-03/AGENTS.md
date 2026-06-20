# ag-03 — Wayland virtual display stream (MJPEG)

Streams a Sway headless output (HEADLESS-1) to a browser via MJPEG over HTTP.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md)

## Pipeline

```
Sway (wlroots) → HEADLESS-1 (virtual output, 720×1600)
  → grim (wlr-screencopy DMA-BUF)
    → ffmpeg (PNG → JPEG)
      → aiohttp (multipart/x-mixed-replace MJPEG)
        → Browser (<img src="/stream">)
```

## Uso

```bash
# Asegurar que HEADLESS-1 existe
swaymsg create_output
swaymsg output HEADLESS-1 resolution 720x1600

# Iniciar stream
WAYLAND_DISPLAY=wayland-1 python3 wayland-stream.py

# Abrir en navegador
# http://<host>:8082
```

## Puerto

- `8082` — página HTML + stream MJPEG

## Variables de entorno

- `STREAM_OUTPUT` — output a capturar (default: HEADLESS-1)
- `STREAM_FPS` — frames por segundo (default: 10)
