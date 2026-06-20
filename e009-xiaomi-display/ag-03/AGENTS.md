# ag-03 — Wayland virtual display + noVNC + audio

Display virtual Wayland con acceso remoto desde un browser.

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md)

## Arquitectura

```
Sway (wlroots) → HEADLESS-1 (virtual output, 720×1280)
  ├── wayvnc (WebSocket) ──→ noVNC en browser (puerto 8083)
  │     └── DMA-BUF screencopy (wlr-screencopy)
  └── grim → ffmpeg → MJPEG stream (puerto 8082, alternativo)

PulseAudio (remote-audio.monitor)
  └── ffmpeg → MP3 → /audio endpoint (puerto 8083)
```

## Uso

```bash
# Crear display virtual
SWAYSOCK=/run/user/1000/sway-ipc.1000.$(pgrep -u $USER sway).sock
swaymsg -s "$SWAYSOCK" create_output
swaymsg -s "$SWAYSOCK" output HEADLESS-1 resolution 720x1280

# Arrancar wayvnc (WebSocket)
WAYLAND_DISPLAY=wayland-1 nohup wayvnc -o HEADLESS-1 --websocket -f 15 0.0.0.0 5901 &

# Arrancar servidor web (noVNC + audio)
WAYLAND_DISPLAY=wayland-1 nohup python3 noVNC-audio-server.py &
```

## Puertos

| Puerto | Servicio | Protocolo |
|--------|----------|-----------|
| 5901 | wayvnc (WebSocket) | RFB over WS |
| 8082 | MJPEG stream (grim + ffmpeg) | HTTP |
| 8083 | noVNC + audio (una URL) | HTTP |

## Variables de entorno

- `STREAM_OUTPUT` — output a capturar (default: HEADLESS-1)
- `STREAM_FPS` — frames por segundo para MJPEG (default: 10)

---

## Descubrimientos técnicos

### Display virtual sin DRM

**Dato clave**: Sway (wlroots) puede crear outputs virtuales con `swaymsg create_output`. No necesita VKMS, GPU virtual, ni sudo. El output virtual usa DMA-BUF de la GPU real (AMD card2).

```
swaymsg create_output                    → crea HEADLESS-1
swaymsg output HEADLESS-1 resolution 720x1280
```

### DRM master

El DRM master lo tiene el compositor en el TTY activo. Con Sway en tty1:
- Sway tiene DRM master sobre card2 (AMD)
- Xorg (tty2) pierde DRM master cuando se cambia a tty1
- wayvnc captura con DMA-BUF a través del protocolo wlr-screencopy

### VKMS no es necesario

VKMS (Virtual KMS) crea un display virtual en card1, pero Sway ya crea outputs virtuales nativos (`HEADLESS-1`). VKMS sería útil si quisiéramos un segundo compositor Wayland sin display físico, pero con Sway ya corriendo, HEADLESS-1 es suficiente.

### wayvnc vs x11vnc

| | x11vnc | wayvnc |
|---|--------|--------|
| Captura | X11 framebuffer (CPU) | wlr-screencopy (DMA-BUF) |
| Eficiencia | Software, lento | GPU, rápido |
| Audio | No | No |
| Autenticación | `-nopw` | `enable_auth=false` en config |
| WebSocket | No (necesita proxy) | `--websocket` nativo |
| RFB protocol | 3.8 | 3.8 |

### noVNC CDN

El paquete npm `@novnc/novnc@1.7.0` usa ES modules. No funciona con `<script src>` normal. Se necesita:
```html
<script type="module">
import RFB from 'https://cdn.jsdelivr.net/npm/@novnc/novnc@1.7.0/core/rfb.js';
</script>
```

El polyfill de `crypto.randomUUID` es necesario para HTTP (no es secure context):
```html
<script>if(!crypto.randomUUID){crypto.randomUUID=function(){return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){var r=Math.random()*16|0,v=c=='x'?r:r&3|8;return v.toString(16)})}}</script>
```

### Escalado de noVNC en phones

noVNC 1.7.0 tiene `scaleViewport=true` pero no funciona bien en viewports phones. La solución es usar `transform: scale()` manual:

```javascript
var vw=window.innerWidth, vh=window.innerHeight-50;
var sx=vw/canvas.width, sy=vh/canvas.height;
var s=Math.min(sx, sy);
container.style.transform = 'scale('+s+')';
container.style.transformOrigin = 'top left';
container.style.position = 'absolute';
container.style.left = '0';
container.style.top = '0';
```

**Cuidado**: noVNC crea un canvas dentro de un `<div>`. El canvas HTML original (`<canvas id="vnc">`) queda vacío. El canvas de noVNC está en `#screen div:last-child canvas`.

### grim funciona con outputs headless

`grim -o HEADLESS-1` funciona correctamente con outputs virtuales de Sway. Captura via wlr-screencopy (DMA-BUF). Tiempo de captura: ~0.001s por frame.

### MJPEG stream (grim + ffmpeg)

Para streaming view-only (sin interactividad):
```bash
grim -o HEADLESS-1 - | ffmpeg -i - -f mjpeg -q:v 5 stream.jpg
```

O via Python (wayland-stream.py):
- grim captura PNG/JPEG del output
- ffmpeg convierte a JPEG
- aiohttp sirve como `multipart/x-mixed-replace`
- El browser muestra con `<img src="/stream">`

### Audio

El audio se sirve en el mismo puerto (8083) via un endpoint `/audio`:
1. PulseAudio tiene un sink `remote-audio.monitor`
2. ffmpeg captura el monitor y codifica a MP3
3. Se sirve como stream continuo
4. El browser reproduce con `<audio autoplay>`

### Error común: "Invalid data found when processing input"

ffmpeg return code 183 = "Invalid data found when processing input". Causa: el archivo de entrada no tiene formato válido o está vacío. Solución: verificar que el dato de entrada no esté vacío antes de procesar.

### Error común: "Cannot use import statement outside a module"

noVNC 1.7.0 es un ES module. Se necesita `<script type="module">` o el browser mostrará este error.

---

## Limitaciones conocidas

### Mouse
- Touch en cualquier parte = click izquierdo (no distingue tap vs drag)
- Cursor no se mueve al punto de touch
- Sensibilidad de drag descalibrada (el cursor no sigue al dedo)
- Sin soporte para scroll wheel
- Sin click derecho
- Ideal: touch en zona inferior = mover cursor, tap en cualquier parte = click

### Teclado
- No hay teclado virtual en la página
- Imposible enviar shortcuts como Super+Enter
- Necesita teclado virtual con teclas especiales (Super, Ctrl, Alt, Tab, etc.)

### Zoom/Pan
- Sin capacidad de zoom manual
- El usuario no puede verificar si ve toda la pantalla
- Ideal: gestos de pinch-to-zoom para encuadrar

### Escalado
- Se usa `transform: scale()` en el contenedor de noVNC
- Funciona pero no es perfecto (márgenes negros posibles)
- noVNC 1.7.0 tiene bugs con `scaleViewport` en viewport phones

---

## Trabajo futuro

1. **Touchpad mode**: implementar modo touchpad (mover dedo = mover cursor, tap = click)
2. **Virtual keyboard**: teclado con teclas especiales (Super, Ctrl, Alt, Tab, Esc, F1-F12)
3. **Scroll**: gesto de dos dedos para scroll
4. **Right click**: long press para click derecho
5. **Pinch-to-zoom**: gestos nativos del browser
6. **WebRTC**: reemplazar noVNC por WebRTC (video + audio + data channel para input)
7. **Audio sincronizado**: integrar audio en el mismo stream de video
