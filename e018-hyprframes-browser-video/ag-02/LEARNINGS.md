# Session Learnings — e018 ag-02

## Pipeline Architecture

The final pipeline for AI news videos:

```
1. Agente externo (ChatGPT/Gemini + Google) ──→ script.md (con etiquetas [EXCITED], [SERIOUS], etc.)
2. Eleven Labs TTS ──→ narration.mp3     ← externo, no edge-tts
3. Parakeet ASR (model_worker.py) ──→ transcripción + timestamps por palabra
4. align_srt.py ──→ script.srt (chunks ~5 palabras) + script.manifest.json
5. pipeline.py: agent-browser ──→ Pixabay (descarga 1 video por segmento)
                ffmpeg ──→ concatena + subtítulos + audio → FINAL.mp4
```

## Key Technical Decisions

### TTS
- **Eleven Labs** es el TTS correcto (tiene etiquetas de emoción reales: [EXCITED], [SERIOUS], etc.)
- `edge-tts` NO soporta etiquetas de emoción — solo sirve como fallback
- El audio externo se alinea con el script mediante transcripción + matching de palabras

### Parakeet (ASR)
- Modelo: `parakeet-ctc-0.6b` (2.3GB)
- Se carga en un proceso separado (`model_worker.py`) vía Unix socket
- Tarda ~20s en cargar, luego ~14s por 138s de audio (9.8x realtime)
- El worker DEBE persistir en memoria, no reiniciarlo cada vez
- El audio de entrada debe ser **mono** (estéreo causa TypeError)

### Números en subtítulos
- Parakeet transcribe números como palabras ("five point six", "sixty four billion")
- Se deben convertir a dígitos ("5.6", "64 billion") con un post-proceso
- Usar `enhance_srt.py` o similar

### Fuentes de imágenes para Ken Burns
- **Wikipedia/Wikimedia**: SVG vectorial (logos) y fotos. URLs predecibles, sin captcha. Resolución limitada (~250px thumbs, originales hasta 2000px)
- **Unsplash vía Google Images**: Fotos de alta calidad (1920px+). Sin captcha. Hay que navegar a Unsplash para descargar
- **Freepnglogo**: Logos PNG con transparencia hasta 2000x2000. Buenos para logos técnicos
- PNGs con transparencia (alpha) necesitan fondo blanco antes de aplicar zoompan

### Ken Burns effect (zoompan)
- ffmpeg filter: `zoompan=z='1.0+0.008*on':d=frames:fps=30:s=1080x1920`
- El zoom máximo debe ser limitado a ~1.3x para que no se salga del cuadro
- Variar efectos: zoom lento, zoom rápido, zoom out, paneo arriba, paneo izquierda, estático
- Para PNGs con alpha: primero overlay sobre fondo blanco, luego zoompan

### Concatenación de videos
- Todos los segmentos deben estar en el mismo codec/formato para concat demuxer
- Stock videos de Pixabay (WebM) + Ken Burns (WebM) = se concatenan con `-f concat`
- El concat final recodifica a H.264 + AAC
- Si todos fueran MP4, el concat podría ser copia directa (más rápido)

### Subtítulos con highlighting
- ASS format permite palabras en distintos colores
- Palabras clave (OpenAI, GPT, Gemini, etc.) en amarillo, resto en blanco
- FontSize=18, Outline=2, MarginV=50

### Errores comunes y soluciones
1. **Pantallas negras**: PNGs con alpha se renderizan como negro si no se agrega fondo blanco
2. **Imágenes reutilizadas**: cada segmento debe tener su propia imagen única
3. **Descargas fallidas**: archivos <200 bytes son descargas corruptas
4. **Worker crashes**: el modelo espera audio mono, no estéreo
5. **pkill NO se usa**: siempre matar por PID guardado
6. **Archivos en /tmp**: no poner nada en /tmp, siempre en output/

### Timing del pipeline
| Etapa | Tiempo | Notas |
|-------|--------|-------|
| TTS (Eleven Labs) | ~2min | Externo |
| Carga del modelo | ~20s | Una vez, proceso persistente |
| Transcripción | ~14s/138s | 9.8x realtime |
| Descarga de imágenes | ~3-5min | 11 búsquedas Google + curl |
| Ken Burns (11 clips) | ~40s | ffmpeg zoompan |
| Concat final | ~3-5min | ffmpeg |
| **Total** | **~10min** | Sin contar TTS externo |

## Reglas para futuros agentes

1. **NUNCA usar pkill** — guardar PIDs al iniciar procesos
2. **NUNCA poner archivos en /tmp** — usar siempre `output/`
3. **El worker DEBE ser persistente** — no reiniciar entre transcripciones
4. **Audio mono** — convertir a mono antes de transcribir
5. **PNGs con alpha** — agregar fondo blanco antes de Ken Burns
6. **Cada segmento = imagen única** — no reutilizar imágenes
7. **Documentar timestamps** — saber cuánto tarda cada etapa
8. **Verificar descargas** — archivos <200 bytes son corruptos
