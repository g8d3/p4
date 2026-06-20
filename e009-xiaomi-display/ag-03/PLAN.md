# Plan — Display virtual vertical: grabación + transmisión

## Estado actual

- Display virtual: HEADLESS-1 (720×1280) en Sway
- Acceso remoto: noVNC en browser (puerto 8083)
- Audio: endpoint /audio en el mismo puerto
- **Grabación: IMPLEMENTADA ✅** (fase 1 completada)
- Transmisión en vivo: funciona (noVNC + audio)

## Fase 1: Grabación con VNC (completada)

**Objetivo**: grabar 10-30 segundos de actividad en HEADLESS-1.

**Resultado**: ✅ Exitoso

**Archivo**: `grabacion_fase1.mkv`

| Métrica | Valor |
|---------|-------|
| Duración | 9.86 s |
| Resolución | 720×1280 |
| Codec video | H.264 (libx264, CRF 23, ultrafast) |
| Codec audio | AAC, 48kHz, stereo |
| Tamaño archivo | 166 KB |
| Tasa de bits | 134 Kbps |
| FPS | 1 (contenido estático, sin cambios de frames) |
| CPU durante grabación | 8.7% (vs 6.1% baseline) |
| RAM | 3.3 GB (sin cambio) |
| GPU | 0% (sin encode GPU, fue CPU only) |

**Herramientas usadas**:
- `wf-recorder -o HEADLESS-1 -c libx264 --audio -f grabacion_fase1.mkv`

**Observaciones**:
- wf-recorder captura DMA-BUF (wlr-screencopy) + PipeWire audio
- El display estaba casi estático (solo cursor moviéndose), por eso el FPS fue bajo
- xdotool no funciona en Wayland (necesita `wtype` o `ydotool` para input)
- El terminal foot no mostró contenido porque xdotool no envió las teclas correctamente
- El archivo MKV tiene tanto video como audio sincronizados

**Pendiente para mejoras**:
- Usar `ydotool` o `wtype` en vez de `xdotool` para input en Wayland
- Abrir navegador con video para probar grabación con movimiento + audio
- Probar con diferentes calidades (CRF) y codecs (VP9, AV1)

## Fase 2: Transmisión con WebRTC

**Objetivo**: reemplazar noVNC por WebRTC para transmitir video + audio en vivo.

**Por qué WebRTC**:
- Video + audio en una sola conexión
- Baja latencia (<500ms)
- Hardware encode (VAAPI)
- Una sola URL en el browser

**Componentes**:
- `wf-recorder` captura HEADLESS-1 + PipeWire audio
- `ffmpeg` encode con VAAPI
- Servidor WHIP (e.g., `whip-server`, `live777`)
- Browser reproduce con WHEP

**Alternativas**:
- KasmVNC (VNC con audio nativo)
- FFmpeg + WebSocket + MSE
- OBS + WHIP

**Métricas a extraer**:
- `top` / `htop`: CPU%, GPU%, RAM durante transmisión
- `radeontop`: uso de VAAPI encode
- `iperf3`: ancho de banda real de la conexión
- Tamaño de la trama WebRTC por segundo
- FPS real de transmisión
- Latencia de extremo a extremo (timestamp overlay)
- Tiempo de buffering del browser
- Calidad subjetiva (comparar frame A/B con Phase 1)

## Fase 3: Comparación

| Métrica | noVNC (actual) | WebRTC (fase 2) |
|---------|---------------|-----------------|
| Latencia | ~200-500ms | <500ms |
| CPU | ~15% (grim + ffmpeg) | ~5% (VAAPI) |
| GPU | DMA-BUF read | VAAPI encode |
| RAM | ~50MB | ~30MB |
| Red | ~1.5 Mbps (MJPEG) | ~500 Kbps (VP8) |
| Audio | ❌ separado | ✅ sincronizado |
| Interactividad | ✅ mouse/teclado | ⚠️ data channel |
| Complejidad | ✅ baja | 🔴 alta |

## Decisiones pendientes

1. ¿Qué grabadora usar? `wf-recorder` vs `grim` + `ffmpeg`
2. ¿Servidor WHIP para WebRTC? `whip-server` vs `live777` vs custom
3. ¿Mantener noVNC como fallback?
4. ¿Cómo integrar audio en WebRTC?
5. ¿Grabación en formato MKV o MP4?

## Notas

- El usuario quiere comparar: complejidad de implementación, recursos (CPU/GPU/RAM/red/disco)
- La grabación es independiente de la transmisión
- El usuario accede desde celular, la pantalla es vertical
- Los scripts están en `ag-03/`
