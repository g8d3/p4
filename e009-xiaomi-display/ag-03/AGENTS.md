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

### wf-recorder: bug con headless outputs

**Descubrimiento clave**: `wf-recorder` solo captura cuando hay **damage events** (actualizaciones de pantalla en el output).

- Contenido estático (terminal, fondo) = captura VACÍA (frame de 10KB)
- Contenido animado (weston-simple-shm) = captura perfecta (frame de 1MB+)

**Causa**: wf-recorder 0.4.1 depende de damage tracking de wlroots. Outputs headless no generan damage events para contenido estático.

**Solución temporal**: usar `weston-simple-shm` como placeholder visual para probar grabación, o usar `grim` en loop + ffmpeg para contenido estático.

**Solución ideal**: usar un compositor con damage tracking completo (Hyprland, o wlroots con patches) o grabar con grim frames.

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

### Touchpad mode: tap=click, drag=moves cursor

We replaced noVNC's built-in touch handling with custom JS:
- **Tap** (touch + lift <300ms, <15px movement) → left click at touch position
- **Drag** (touch + move) → relative cursor movement from current position
- No bottom-zone splitting needed — works uniformly across the screen

Implementation: prevent default noVNC touch events via `capture:true`, then handle `touchstart/touchmove/touchend` manually using `rfb.sendPointer(x, y, mask)`.

### Virtual keyboard always visible

A compact virtual keyboard with Esc, Tab, Super, Ctrl, Alt, Shift, Space, arrows (◀▲▼▶), F1-F12, Enter, Backspace. Always visible at bottom of page. Uses `VisualViewport` API to reposition above the phone's native keyboard when it opens.

### Audio clicks when recording with wf-recorder -a

The `-a` flag in wf-recorder introduces click/pop artifacts. **Solution**: record video and audio as separate processes:

```bash
wf-recorder -o HEADLESS-1 -f video.mp4 &         # video only
ffmpeg -f pulse -i <monitor> audio.aac &           # audio via ffmpeg
# later: ffmpeg -i video.mp4 -i audio.aac -c copy merged.mp4
```

### edge-tts vs piper-tts

| TTS | Latency | Quality | Dependency |
|-----|---------|---------|------------|
| edge-tts | ~3s (network) | Excellent | Internet required |
| piper-tts | ~1.2s (model load) | Good | 61MB ONNX model |

Piper loads the 61MB model on every invocation. For sub-100ms latency, keep a daemon process with the model preloaded.

### Guacamole connection via SQL injection

The `oznu/guacamole` Docker image bundles PostgreSQL + Tomcat + guacd in one container. The REST API returns 500 errors, but direct SQL injection works:

```bash
docker exec guac psql -U guacamole -d guacamole_db -c "
INSERT INTO guacamole_connection (connection_name, protocol) VALUES ('HEADLESS-1', 'vnc');
INSERT INTO guacamole_connection_parameter (connection_id, parameter_name, parameter_value)
  SELECT conn.connection_id, 'hostname', '192.168.0.93' FROM guacamole_connection conn WHERE ... ;
INSERT INTO guacamole_connection_permission (entity_id, connection_id, permission)
  SELECT e.entity_id, c.connection_id, 'READ'
  FROM guacamole_entity e, guacamole_connection c WHERE ... ;
"
```

### Display virtual sin VKMS

Confirmación: Sway crea outputs virtuales nativos (HEADLESS-1) sin usar VKMS (card1). VKMS se cargaba por `/etc/modules-load.d/vkms.conf` pero no lo usa nadie. Las CRTCs/planes de card1 están todos en null. Se eliminó el archivo de configuración.

---

## Limitaciones conocidas

### Mouse
- Touch = click izquierdo (funciona)
- Touchpad mode: drag = mover cursor (implementado)
- Sin scroll wheel (gesto de dos dedos pendiente)
- Sin click derecho (long press pendiente)

### Teclado
- Teclado virtual con Super, Ctrl, Alt, Tab, Esc, F1-F12, arrows (implementado)
- El teclado se reposiciona sobre el teclado nativo del phone (VisualViewport)

### Zoom/Pan
- Sin pinch-to-zoom
- El usuario no puede verificar si ve toda la pantalla

### Escalado
- `transform: scale()` en el contenedor de noVNC
- Funciona pero márgenes negros posibles
- noVNC 1.7.0 bugs con `scaleViewport` en viewport phones

---

## Trabajo futuro

1. ~~**Touchpad mode**: mover dedo = cursor, tap = click~~ ✅ Hecho
2. ~~**Virtual keyboard**: Super, Ctrl, Alt, Tab, Esc, F1-F12~~ ✅ Hecho
3. **Scroll**: gesto de dos dedos
4. **Right click**: long press
5. **Pinch-to-zoom**: gestos nativos
6. **WebRTC**: reemplazar noVNC (video + audio + data channel)
7. **Audio sincronizado**: integrar en el mismo stream
8. **VNC alternatives**: KasmVNC (ag-04), Apache Guacamole (ag-05) explorados
