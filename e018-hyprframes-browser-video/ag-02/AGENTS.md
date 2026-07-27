# e018 ag-02 — AI News Video Pipeline

Genera videos automáticos estilo "AI news briefing" a partir de un script con etiquetas de emoción.

## Inherits

- [p4/AGENTS.md](/home/vuos/code/p4/AGENTS.md) — contexto general
- [e018-hyprframes-browser-video/AGENTS.md](/home/vuos/code/p4/e018-hyprframes-browser-video/AGENTS.md) — scope del experimento

## Pipeline real (verificado)

```
1. Agente externo (ChatGPT/Gemini + Google) ──→ script.md (con etiquetas [EXCITED], [SERIOUS], etc.)
2. Eleven Labs TTS ──→ narration.mp3     ← el usuario hace esto externamente
3. Parakeet ASR (model_worker.py) ──→ transcripción + timestamps por palabra
4. align_srt.py ──→ script.srt (chunks ~5 palabras) + script.manifest.json
5. pipeline.py: agent-browser ──→ Pixabay (descarga 1 video por segmento)
                ffmpeg ──→ concatena + subtítulos + audio → FINAL.mp4
```

**Nota**: el pipeline NO genera TTS. El audio viene de Eleven Labs (o cualquier TTS externo). El script `pipeline.py` también puede generar TTS con edge-tts como fallback, pero el resultado no tendrá las inflexiones emocionales de Eleven Labs.

## Servicios persistentes

```bash
# Worker ASR (Parakeet en RAM, ~20s carga)
source .venv/bin/activate
nohup python3 bin/model_worker.py > /tmp/worker.log 2>&1 &
WORKER_PID=$!

# Chrome para descargar videos de Pixabay
google-chrome --headless --remote-debugging-port=9222 --no-first-run \
  --no-default-browser-check --disable-gpu "about:blank" > /tmp/chrome.log 2>&1 &
CHROME_PID=$!
```

## Cómo generar un video nuevo

```bash
# 1. Poner el script en output/script.md (con etiquetas Eleven Labs)
# 2. Generar audio con Eleven Labs externamente → output/narration.mp3
# 3. Ajustar SEARCH_TERMS en bin/pipeline.py si cambian los temas
# 4. Ejecutar:

source .venv/bin/activate
export TMPDIR=/home/vuos/tmp

# Paso A: alinear subtítulos contra el audio real
python3 bin/align_srt.py output/narration.mp3

# Paso B: descargar videos y ensamblar
python3 bin/pipeline.py output/script.md
```

O en un solo comando si el pipeline tiene el audio ya listo.

## Output

- `output/FINAL.mp4` — video renderizado
- `output/<nombre>.srt` — subtítulos sincronizados (chunks ~5 palabras)
- `output/<nombre>.manifest.json` — metadatos por segmento

## Notas técnicas

- **Subtítulos**: FontSize=18, blanco sólido, Outline=2, MarginV=50. Chunks de ~5 palabras.
- **Videos**: descargados de Pixabay en 1280×720, escalados a 1080×1920 con crop centrado.
- **Audio**: Eleven Labs (externo). El pipeline NO debe regenerar TTS si ya existe el audio.
- **Sync**: los subtítulos se alinean con timestamps de Parakeet + texto exacto del script.
- **Duración**: el video mide la duración real del audio (`-shortest`).
- **Tags de emoción**: `[EXCITED]`, `[SERIOUS]`, `[LOWERS VOICE]`, `[DRAMATIC PAUSE]`, `[CASUAL TONE]`, `[ANALYTICAL]`, etc. — compatibles con Eleven Labs.
