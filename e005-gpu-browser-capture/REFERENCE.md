# Referencia: Pipeline de gráficos en Linux

## Historia: ¿qué es un TTY?

**TTY = Teletype (teletipo).** Máquina de los 50-70s: teclado + impresora de papel, conectada por cable serial a un mainframe. Escribías, el caracter viajaba a la computadora, ella devolvía texto para imprimir en un rodillo de papel.

Los monitores CRT reemplazaron al teletipo, pero el nombre **TTY** quedó. Hoy cada terminal en Linux es un `tty`:
- `/dev/tty1` — terminal físico (monitor+teclado conectado)
- `/dev/pts/0` — pseudo-terminal (SSH, tmux)

## La cadena de permisos para display

```
TTY físico (/dev/tty1)
  → logind te da un "seat" (sesión local)
  → pedís DRM master
  → compositor (Sway/Xorg) arranca
  → apps se conectan
  → grabación funciona
```

Sin TTY físico (SSH): logind responde "no data available" → no hay seat → no hay DRM master → ningún compositor moderno arranca. **Xvfb es la excepción** porque fue creado en los 90 antes de logind y DRM.

## Capas del pipeline gráfico

Cada capa tiene múltiples opciones. Se pueden combinar libremente.

### 1. Protocolo de display

| Protocolo | Quién renderiza | Ejemplos |
|-----------|----------------|----------|
| **X11** | Cada app dibuja directo (o via compositor) | Xorg, Xvfb |
| **Wayland** | Solo el compositor dibuja. Apps son clientes pasivos | Sway, Weston, Mutter, KWin |

### 2. Compositores (implementan el protocolo)

| Compositor | Protocolo | Librería base | wf-recorder? | Headless? | Notas |
|-----------|-----------|---------------|-------------|-----------|-------|
| **Xorg** | X11 | — | ❌ (usa x11grab) | ❌ | El servidor X clásico |
| **Xvfb** | X11 | — | ❌ (usa x11grab) | ✅ | Display virtual en RAM. No usa GPU |
| **Sway** | Wayland | wlroots (C) | ✅ sí | ❌ necesita TTY | i3-like, tiling |
| **Wayfire** | Wayland | wlroots (C++) | ✅ sí | ❌ necesita TTY | Efectos 3D |
| **Cage** | Wayland | wlroots (C) | ✅ sí | ❌ necesita TTY | Kiosk (una app fullscreen) |
| **River** | Wayland | wlroots (Zig) | ✅ sí | ❌ necesita TTY | Tiling dinámico |
| **Weston** | Wayland | libweston (C) | ❌ no | ✅ sí | Referencia de Wayland |
| **Mutter** | Wayland | GObject (C) | ❌ no | ❌ | GNOME |
| **KWin** | Wayland | KF5 (C++) | ❌ no | ❌ | KDE |

### 3. Desktop Environments (opcionales, sobre el compositor)

| DE | Compositor base | Notas |
|----|----------------|-------|
| GNOME | Mutter | Completo, pesado |
| KDE | KWin | Completo, pesado |
| Sway (solo WM) | Sway | Sin DE, solo ventanas |
| i3 | Xorg | X11, tiling |

### 4. Tipos de display

| Display | Dónde está el framebuffer | DMA-BUF? | GPU involucrada? | Funciona con Sway? | Vertical video? |
|---------|--------------------------|----------|-----------------|-------------------|-----------------|
| **Monitor real (HDMI/DP)** | VRAM (memoria de GPU) | ✅ sí | ✅ sí | ✅ sí | ✅ sí |
| **`amdgpu.virtual_display`** | VRAM | ✅ sí | ✅ AMD real | ✅ sí | ✅ sí |
| **VKMS** | RAM del sistema | ❌ no | ❌ software | ❌ no (allocator fail) | ❌ no |
| **Xvfb** | RAM del sistema | ❌ no | ❌ CPU | ❌ X11 | ✅ sí |
| **Weston headless** | RAM (EGL offscreen) | ❌ no | ✅ AMD via EGL | ❌ (no wlroots) | ❌ no |
| **Weston VNC** | RAM (EGL offscreen) | ❌ no | ✅ AMD via EGL | ❌ (no wlroots) | ❌ no |
| **Xvnc** | RAM del sistema | ❌ no | ❌ CPU | ❌ X11 | ✅ sí |
| **DRM lease** | VRAM | ✅ sí | ✅ AMD real | ⚠️ experimental | ⚠️ no probado |

### 5. Programas de grabación

| Programa | Display | Cómo captura | DMA-BUF? | CPU | Comando ejemplo |
|----------|---------|-------------|----------|-----|----------------|
| **wf-recorder** | Wayland (wlroots) | wlr-screencopy protocol | ✅ con DMA-BUF, ❌ sin | 0% con DMA, ~5% sin | `wf-recorder -c h264_vaapi -f out.mp4` |
| **ffmpeg x11grab** | X11 | X11 SHM (lee píxeles de RAM) | ❌ no | ~5% | `ffmpeg -f x11grab -i :99.0 -vf "format=nv12,hwupload" -c:v h264_vaapi out.mp4` |
| **ffmpeg kmsgrab** | DRM/KMS | Captura directo del scanout buffer | ✅ sí | 0% | `ffmpeg -f kmsgrab -i - -vf "hwmap" -c:v h264_vaapi out.mp4` |
| **PipeWire** | Wayland/X11 | Captura vía portal/screencast | ✅ sí | 0% | Herramienta de escritorio, no CLI directa |

### 6. Encoders de video (dónde se comprime)

| Encoder | Dónde corre | GPU? | CPU? | Ejemplo |
|---------|------------|------|------|---------|
| **libx264** | CPU | ❌ | ✅ mucho | `-c:v libx264` |
| **h264_vaapi** | GPU (VAAPI) | ✅ sí | ❌ 0% | `-c:v h264_vaapi` |
| **h264_nvenc** | GPU (NVIDIA) | ✅ sí | ❌ 0% | `-c:v h264_nvenc` |
| **h264_amf** | GPU (AMD) | ✅ sí | ❌ 0% | `-c:v h264_amf` |

## El flujo completo "renderizar un píxel"

```
App (Chrome, juego) quiere mostrar un píxel AZUL en posición (100, 100)

1. API de gráficos
   Chrome usa WebGL/OpenGL/EGL para decirle al driver:
   "dibujá un píxel azul en (100, 100)"
   → genera comandos en un buffer

2. Driver AMD (amdgpu.ko)
   Traduce comandos genéricos a instrucciones específicas del Radeon 5625U
   → corre en el kernel

3. GPU ejecuta
   El Radeon lee los comandos:
   - Vertex Shader → calcula posición de triángulos
   - Rasterizer → convierte triángulos en píxeles
   - Fragment Shader → calcula color de cada píxel
   → escribe el resultado en VRAM

4. Scanout buffer
   El controlador de display lee el frame de VRAM línea por línea a 60 Hz
   → lo envía como señal eléctrica por HDMI
   → el monitor muestra el píxel azul

RENDERIZAR = todo el proceso (1→4)
RASTERIZAR = solo el paso de triángulos → píxeles (paso 3, parte del Vertex/Fragment)
FRAMEBUFFER = el bloque de memoria (VRAM o RAM) donde está el frame final
SCANOUT BUFFER = el framebuffer específico que el controlador HDMI está leyendo
```

## Dónde se mete la grabación en el flujo

```
           ┌─── DMA-BUF (wf-recorder con monitor real) ───┐
           │  GPU render → DMA-BUF → VAAPI encode → MP4   │
           │  0 copias, 0% CPU                             │
           └───────────────────────────────────────────────┘

           ┌─── x11grab + VAAPI (Xvfb o monitor real) ────┐
           │  GPU render → X SHM (CPU copy) → hwupload    │
           │  → VAAPI encode → MP4                         │
           │  1 copia CPU (~5%)                            │
           └───────────────────────────────────────────────┘

           ┌─── wf-recorder --no-dmabuf ───────────────────┐
           │  GPU render → wl_shm (CPU copy) → VAAPI → MP4 │
           │  1 copia CPU (~5%)                            │
           └───────────────────────────────────────────────┘

           ┌─── kmsgrab ───────────────────────────────────┐
           │  GPU render → kmsgrab (DRM) → VAAPI → MP4     │
           │  0 copias, 0% CPU (necesita DRM master)       │
           └───────────────────────────────────────────────┘
```

## Por qué elegimos Xvfb + x11grab + VAAPI

| Requisito | Opciones | Elegido |
|-----------|----------|---------|
| Entorno | SSH sin TTY, sin escritorio | Xvfb (único que funciona sin TTY) |
| CPU mínimo | VAAPI, DMA-BUF | VAAPI sí, DMA-BUF no disponible sin monitor real |
| GPU estresada | WebGL + Vulkan + VAAPI | ✅ Chrome WebGL en GPU real + vkcube |
| Formato vertical | 608×1080 | ✅ x11grab captura la región exacta |
| Sin sudo | Permisos de usuario | ✅ Xvfb + Chrome + ffmpeg no requieren sudo |

## Cómo controlar un TTY físico desde SSH

Aunque no puedas "ver" el TTY físico, podés enviarle comandos:

```bash
# Cambiar a otro TTY (como cambiar de escritorio virtual en Linux)
chvt 3          # cambia el monitor a tty3
chvt 7          # vuelve a tty7 (donde suele estar el escritorio)

# Arrancar un programa en un TTY específico
openvt -- sway  # abre sway en el próximo TTY libre (tty7, tty8...)
openvt -c 7 -- sway  # lo abre específicamente en tty7

# Ejecutar algo en un TTY como root (para drm master, etc.)
sudo openvt -c 7 -- sway -c /ruta/config

# Enviar texto a un TTY (como si alguien escribiera ahí)
sudo sendkeys /dev/tty7 "comando"

# Ver quién tiene cada TTY
loginctl list-sessions
loginctl show-session <id> | grep TTY

# Liberar un TTY (matar el proceso que lo ocupa)
sudo fgconsole       # muestra el TTY activo actual
sudo chvt 1          # vuelve a tty1
```

### Cómo ver el TTY remoto (VNC/RDP)

No podés ver el TTY físico con los ojos desde SSH, pero podés transmitir su pantalla por red:

```bash
# Opción 1: Compartir el TTY real que ya está corriendo (ej: sway en tty7)
wayvnc 0.0.0.0:5900 &
# Desde cualquier dispositivo en la red, conectate con un cliente VNC a IP:5900
# Esto comparte exactamente lo que se ve en el monitor conectado al TTY físico.

# Opción 2: Crear un display virtual nuevo (no asociado a ningún TTY)
Xvnc :99 -geometry 608x1080 -depth 24 &
# Es como Xvfb pero con VNC integrado. Podés conectarte y verlo,
# pero no está ligado a ningún monitor físico ni TTY.

# Opción 3: x11vnc (compartir un X11 existente)
x11vnc -display :0 -forever &
# Comparte el Xorg que ya está corriendo en tty1 (escritorio local).
```

### VNC comparte un TTY o crea uno nuevo?

Depende del servidor VNC:

| Servidor VNC | Comparte un TTY existente? | Crea un display nuevo? |
|-------------|---------------------------|----------------------|
| **wayvnc** (wlroots) | ✅ Comparte el output de Sway (tty real) | ❌ No, necesita un compositor corriendo |
| **x11vnc** | ✅ Comparte un X11 existente (tty real) | ❌ No, necesita Xorg corriendo |
| **Xvnc** (TigerVNC) | ❌ No | ✅ Crea un display virtual nuevo (como Xvfb pero VNC) |
| **weston VNC backend** | ❌ No | ✅ Weston arranca con backend VNC, sin TTY |

En tu caso (SSH sin escritorio, sin TTY físico activo):
- **wayvnc** no sirve porque no hay Sway corriendo en un TTY
- **Xvnc** sirve: crea un display virtual + permite verlo por VNC
- **weston --backend=vnc** sirve: compositor Wayland + VNC integrado, sin TTY

Ejemplo con weston + VNC (sin TTY):

```bash
weston --backend=vnc-backend.so --width=608 --height=1080 --socket=wayland-1
# Crea un compositor Wayland sin TTY, accesible por VNC en puerto 5900
# Pero wf-recorder NO funciona con weston (solo wlroots)
```

### DRM master y virtual displays (relación con TTY)

Los virtual displays no cambian la necesidad de TTY para obtener DRM master. Siguen siendo parte de `card1` (la GPU), y `card1` necesita DRM master igual que antes.

La diferencia es que **nosotros ya podemos obtener DRM master sin TTY físico** ejecutando Sway como root. `sudo` bypass logind y llama directo a `drmSetMaster()`.

Lo que falló en el primer intento exitoso fue la **resolución del monitor HDMI** (dio 0×0 porque estaba en estado inconsistente después de matar sddm). Los virtual displays no tienen ese problema — el driver AMD les asigna 1920×1080 automáticamente.

| Modo | TTY | DRM master? | Sway corre? | Resolución |
|------|-----|------------|------------|------------|
| Sway como usuario (no root) | SSH | ❌ logind deniega | ❌ no arranca | — |
| Sway como root (sudo) | SSH | ✅ drmSetMaster directo | ✅ sí | 0×0 (HDMI sin modo) |
| Sway como root + virtual displays | SSH | ✅ drmSetMaster directo | ✅ sí | **1920×1080** |

Flujo post-reboot con virtual displays:

```
SSH → sudo sway (root, bypass logind)
  → DRM master adquirido (drmSetMaster)
  → Detecta: HDMI-A-1 (0×0, ignorado), VIRTUAL-1 (1920×1080), VIRTUAL-2, VIRTUAL-3
  → Crea socket Wayland en /run/sway-recording/

En otra terminal SSH:
  XDG_RUNTIME_DIR=/run/sway-recording WAYLAND_DISPLAY=wayland-1 \
  wf-recorder -o VIRTUAL-1 -c h264_vaapi -f video.mp4
  → DMA-BUF real, 0% CPU, sin sudo
```

### AMD Virtual Display (la solución para grabación headless con DMA-BUF, pero mata el display físico)

El driver AMD tiene un parámetro que crea displays virtuales **en la GPU real**, con scanout buffer en VRAM y DMA-BUF funcional.

**⚠️ Limitación importante**: este parámetro **reemplaza** todos los displays físicos (HDMI, DP, eDP) por virtuales. No es posible tener ambos. Es un modo exclusivo para servidores/cloud sin monitor.

```bash
# Agregar a GRUB_CMDLINE_LINUX en /etc/default/grub
amdgpu.virtual_display=0000:05:00.0,3

# Actualizar grub y reiniciar
sudo update-grub2 && sudo reboot
```

Después del reinicio aparecen conectores virtuales:

```bash
ls /sys/class/drm/card1-* | grep VIRTUAL
# → card1-VIRTUAL-1, card1-VIRTUAL-2, card1-VIRTUAL-3
```

Beneficios vs Xvfb:

| Aspecto | Xvfb | AMD Virtual Display |
|---------|------|-------------------|
| DMA-BUF | ❌ no | ✅ sí |
| CPU copy | ~5% | 0% |
| GPU encoding | ✅ VAAPI | ✅ VAAPI sin hwupload |
| wf-recorder | ❌ no compatible | ✅ funciona directo |
| Múltiples displays | ✅ ilimitados | ✅ hasta N configurados |
| Arranque | instantáneo | disponible solo post-reboot |

Con esto, el pipeline pasa a ser:

```bash
# Arrancar Sway en el display virtual (sin monitor, sin TTY físico)
# Sway detecta VIRTUAL-1 como output real → DMA-BUF funciona

# Grabar con DMA-BUF (0 CPU)
wf-recorder -o VIRTUAL-1 -c h264_vaapi -f out.mp4
```

Ejemplo real que funciona en este proyecto (sin amd virtual display, con Xvfb):

```bash
# Desde SSH:
sudo openvt -c 7 -- sway -c /etc/sway-recording-config
# Sway arranca en tty7, toma DRM master, crea socket Wayland
# Vuelvo a SSH y me conecto al socket:
XDG_RUNTIME_DIR=/run/sway-recording WAYLAND_DISPLAY=wayland-1 wf-recorder ...
```

## Mapa completo: opciones de display virtual

| Display | Framebuffer | DMA-BUF | GPU | wlroots/Sway | wf-recorder | Vertical video | Notas |
|---------|-------------|---------|-----|-------------|-------------|----------------|-------|
| **Monitor real (HDMI/DP)** | VRAM | ✅ sí | ✅ AMD real | ✅ funciona | ✅ sí | ✅ sí | Necesita TTY o sudo para DRM master |
| **`amdgpu.virtual_display`** | VRAM | ✅ sí | ✅ AMD real | ✅ funciona | ✅ sí | ✅ sí | ❌ **Reemplaza displays físicos** (no pueden coexistir) |
| **VKMS** | RAM sistema | ❌ no importa | ❌ software | ❌ allocator fail | ❌ no | ❌ no | GPU virtual separada, pero wlroots no puede allocar buffers |
| **Xvfb** | RAM sistema | ❌ no | ❌ CPU | ❌ X11 | ❌ usa x11grab | ✅ sí | Funciona sin TTY, sin sudo, cualquier resolución |
| **Weston headless** | RAM (EGL) | ❌ no | ✅ AMD via EGL | ❌ no es wlroots | ❌ no | ❌ no | Compositor Wayland sin TTY, pero wf-recorder no lo soporta |
| **Weston VNC** | RAM (EGL) | ❌ no | ✅ AMD via EGL | ❌ no es wlroots | ❌ no | ❌ no | Igual que headless pero accesible por VNC |
| **Xvnc** | RAM sistema | ❌ no | ❌ CPU | ❌ X11 | ❌ usa x11grab | ✅ sí | Como Xvfb pero con VNC integrado |
| **DRM lease (drm-lease)** | VRAM | ✅ sí | ✅ AMD real | ⚠️ experimental | ⚠️ | ⚠️ | Divide la GPU en leases virtuales. No probado. |

### ¿Por qué no se puede tener display físico y virtual simultáneamente en AMD?

El parámetro `amdgpu.virtual_display` fue diseñado para servidores/cloud **sin monitor**. Cuando se activa, el driver AMD entra en modo 100% virtual:

```
amdgpu detecta physical connectors (HDMI, DP, eDP)
  → si virtual_display está seteado:
    → ignora todos los conectores físicos
    → crea solo conectores virtuales (Virtual-1, Virtual-2, ...)
```

No es posible tener ambos porque el driver AMD trata `virtual_display` como un modo exclusivo. No hay un parámetro "add virtual displays on top of physical ones".

**Las únicas formas de tener físico + virtual simultáneamente:**
1. **Dos GPUs diferentes**: una GPU para el display físico, otra para el virtual. Ejemplo: AMD interna + VKMS (pero VKMS no funciona con wlroots).
2. **DRM lease**: particionar la GPU en leases, cada una con sus propios displays. No probado en este proyecto.
3. **Entrada GRUB dual** (recomendado): un boot normal con display físico, y otro boot con `amdgpu.virtual_display` para grabación headless con dma-buf.

### VKMS: hallazgos

VKMS (Virtual Kernel Mode Setting) es un módulo del kernel que crea una GPU virtual completamente en software:

```
vkms.ko → /dev/dri/card1 → Virtual-1 (1024x768)
```

**Problema**: wlroots/Sway no puede crear un allocator de buffers para VKMS. El error es:
```
[ERROR] [wlr] [types/output/swapchain.c:109] Swapchain for output 'Virtual-1' failed test
[ERROR] [wlr] [render/allocator/allocator.c:146] Failed to create allocator
```

Esto ocurre tanto con renderizador GLES2 como pixman, y tanto en recovery como en boot normal. La causa probable es que VKMS no soporta los formatos/modifiers que wlroots requiere para el swapchain.

**Veredicto**: VKMS no es utilizable para grabación con Sway + wf-recorder en este kernel (6.8.0). Podría funcionar con compositores que no sean wlroots (Weston, Mutter).

## Trabajo futuro

### DMA-BUF con recorte de región

`wf-recorder --geometry` (recorte a formato vertical) **no es compatible con DMA-BUF**. La captura con DMA-BUF solo funciona para outputs completos. Alternativas:

1. **Grabar completo + recortar en post**: `ffmpeg -i full.mp4 -vf "crop=608:1080:0:0" vertical.mp4`. La operación crop es metadata (no decodifica/reencoda si los códecs coinciden).
2. **Parchear wf-recorder**: añadir soporte para region DMA-BUF. `wlr-screencopy` protocol soporta regiones, pero wf-recorder no las implementa con DMA-BUF.
3. **Usar múltiples outputs virtuales**: en vez de recortar un output grande, crear outputs más pequeños (608×1080 cada uno) y grabar cada uno completo con DMA-BUF. Esto requiere que el driver AMD soporte resoluciones arbitrarias en displays virtuales.

### Multi-agente con displays virtuales independientes

Arquitectura actual (por implementar):

```
a0 (orchestrator)
├── ag-03: recording infra (Xvfb manager, shared resources)
├── ag-04: content agent 1 (Xvfb :99, Chrome, narration, recording)
├── ag-05: content agent 2 (Xvfb :100, Chrome, narration, recording)
├── ag-06: content agent 3 (Xvfb :101, Chrome, narration, recording)
└── ...
```

Cada agente corre en su propio `Xvfb` con resolución vertical (608×1080). La grabación usa `ffmpeg x11grab + VAAPI` (~5% CPU por agente, sin dma-buf). Los agentes son autónomos: deciden qué hacer, navegan, narran con edge-tts, y graban su progreso.

### Hacia displays virtuales con DMA-BUF en la misma GPU

La solución ideal (aún no implementada) requiere que un compositor wlroots (Sway) corra en la GPU AMD con múltiples outputs virtuales, cada uno con DMA-BUF funcional. Esto permitiría `wf-recorder` por output con 0% CPU.

Para lograrlo, se necesita:
1. Una forma de añadir displays virtuales al driver AMD sin perder los físicos (no resuelto en este kernel)
2. O una implementación de DRM lease que funcione con wlroots
3. O un parche a VKMS para que wlroots pueda allocar buffers

### Software autónomo de creación de contenido

Visión a largo plazo: un sistema que permite a cualquier persona (sin conocimientos técnicos) generar contenido automáticamente desde su uso diario del computador. El usuario habla con IA, navega, trabaja — y el sistema convierte eso en videos, streams, o artículos sin intervención manual.

Componentes del ecosistema:
- **Orquestador** (a0): gestiona agentes, asigna recursos, monitorea progreso
- **Agentes de contenido**: cada uno autónomo, con su display, narración TTS, y grabación
- **Memoria compartida**: los agentes pueden leer el trabajo de otros y colaborar
- **Streaming en vivo**: alternativa al video grabado, los agentes pueden transmitir en vivo
- **Personalización**: el usuario configura qué temas, estilo, y plataformas

## Glosario

| Término | Significado |
|---------|------------|
| **VRAM** | Memoria de la GPU (en iGPU, compartida con RAM del sistema) |
| **DMA** | Direct Memory Access — el hardware lee/escribe memoria sin intervención de CPU |
| **DMA-BUF** | Mecanismo del kernel para compartir buffers de GPU entre procesos sin copiar |
| **Framebuffer** | Bloque de memoria (VRAM o RAM) donde está el frame completo renderizado |
| **Scanout buffer** | Framebuffer que el controlador de display lee para enviar al monitor |
| **DRM** | Direct Rendering Manager — subsistema del kernel para gestionar GPUs |
| **KMS** | Kernel Mode Setting — parte de DRM que configura la resolución del display |
| **VAAPI** | Video Acceleration API — API para encoding/decoding de video en GPU |
| **Vulkan** | API de render 3D y compute, sucesor moderno de OpenGL |
| **EGL** | API intermediaria entre OpenGL/WebGL y el display (Wayland o X11) |
| **TTY** | Teletype — terminal de texto (físico o virtual) |
| **logind** | Sistema de log-in que gestiona sesiones y seats |
| **seat** | Conjunto de dispositivos (display, teclado, mouse) asignados a un usuario |
| **hwupload** | Filtro de ffmpeg que sube un frame de RAM a VRAM para encoding VAAPI |
| **Rasterizar** | Convertir triángulos/vértices en píxeles (paso dentro del render) |
| **Renderizar** | Proceso completo de convertir una escena 3D en imagen 2D |
