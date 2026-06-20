# ag-01 — Display virtual + API Xiaomi

Display virtual vertical (720×1600) con VNC web + audio streaming para explorar la API Xiaomi MIMO (TTS/ASR).

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, tmux conventions

## Requisitos

- Xvfb, x11vnc, openbox (opcional)
- ffmpeg, PulseAudio/PipeWire
- Edge TTS (`pip install edge-tts`)
- Python 3 con `websockets`, `aiohttp`

## Variables de Entorno

```
XIAOMI_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1
XIAOMI_API_KEY=tp-...
```

## Scripts

| Script | Función |
|--------|---------|
| `bin/virt-display <num> <res>` | Xvfb + VNC en display virtual |
| `bin/nova-chrome <display>` | Chrome con perfil Nova en ese display |
| `bin/subtitle <texto>` | Escribe en ventana de subtítulos (xterm en display virtual) |
| `bin/speak <texto>` | Subtitle + Edge TTS por stream HTTP |
| `bin/xiaomi-api` | CLI para TTS/ASR de Xiaomi |

## Servidor Unificado

```
server/unified-server.py
```

Sirve en un solo puerto (8080):
- Página web con noVNC (cliente VNC en el browser)
- Stream de audio MP3 desde PulseAudio
- Endpoint de subtítulos
- Proxy WebSocket para VNC

## Uso Rápido

```bash
# 1. Arrancar display virtual
bin/virt-display 1 720x1600

# 2. Servidor unificado
python3 server/unified-server.py

# 3. Chrome en el display virtual
bin/nova-chrome :1 --disable-gpu --start-maximized

# 4. Abrir en navegador: http://<host-ip>:8080
```

## API Xiaomi

```bash
# Listar modelos
bin/xiaomi-api models

# TTS
bin/xiaomi-api tts --text "Hola mundo" --voice Mia --play

# ASR
bin/xiaomi-api asr --audio audio.wav
```

## Problemas conocidos

- Chrome en Xvfb sin window manager tiende a morir. Solución: `DISPLAY=:1 openbox --sm-disable &` antes de Chrome.
- x11vnc con `-bg` puede fallar si el proceso padre muere. Usar sin `-bg` o con `nohup`.
- aiohttp no acepta charset en content_type. Usar `content_type="text/plain", charset="utf-8"`.

## Self-command

```bash
tmux send-keys -t 9-1 "echo running" Enter
```
