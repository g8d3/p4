# Plan — Display virtual vertical: grabación + transmisión

## Estado actual

- Display virtual: HEADLESS-1 (720×1280) en Sway
- Acceso remoto: noVNC en browser (puerto 8083)
- Audio: endpoint /audio en el mismo puerto
- Grabación: no implementada
- Transmisión en vivo: funciona (noVNC + audio)

## Fase 1: Grabación con VNC (actual)

**Objetivo**: grabar 10-30 segundos de actividad en HEADLESS-1.

**Qué grabar**:
- Abrir terminal (Super+Enter en Sway)
- Abrir navegador en el terminal
- Navegar a un video de YouTube
- Poner el video a sonar
- Grabar todo (video + audio)

**Resultado esperado**: archivo MKV con video 720×1280 + audio.

**Herramientas**:
- `wf-recorder` (grabación DMA-BUF + PipeWire para audio)
- `grim` + `ffmpeg` (alternativa sin wf-recorder)

**Limitación**: noVNC no tiene audio en la transmisión. La grabación sí tendría audio.

**Métricas a extraer**:
- `top` / `htop`: CPU%, GPU%, RAM antes/durante/después de grabación
- `nvidia-smi` o `radeontop`: uso de GPU encode
- `iostat`: disco durante la grabación
- `iperf3` o `speedtest-cli`: ancho de banda disponible
- Tamaño del archivo de grabación
- FPS real de grabación
- Tiempo de grabación vs duración real
- Latencia de captura (grim/wf-recorder)

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
