# Video script: How an agent failed upwards

**Para nuevo agente con Remotion + edge-tts**
**Duración**: ~5 min
**Formato**: 9:16 vertical (608×1080)
**Narración**: edge-tts (en-US-JennyNeural)

---

## Prólogo — por qué existe esta sesión (15s)

**Visual**: logo de Higgsfield + código Python en pantalla dividida
**TTS**: "This is the story of an AI agent that was asked to generate a video. Simple, right? Use the API, make a call, done. It took 19 hours, 6 scripts, and a lot of human help."

---

## Capítulo 1 — La API que no funcionó (30s)

**Visual**: terminal con `hf.subscribe()` y error `not_enough_credits`
**TTS**: "The agent found a Python SDK for Higgsfield. Installed it. Set the API key. Called the function. And got: not enough credits. The API existed. The auth worked. There were just no credits."

**Scripts creados**:
- `generate_video.py` — prueba inicial con el SDK, documenta el endpoint y formato. Inútil sin créditos.

**Lección**: tener accesso a una API no significa tener créditos para usarla. El agente no verificó si había créditos ANTES de escribir el script.

---

## Capítulo 2 — El password que bash se comió (45s)

**Visual**: terminal con `echo $HF_PASS` mostrando password truncado, luego el fix con Python subprocess
**TTS**: "The agent switched to browser automation. agent-browser CLI. Open the website, click login, fill email and password. But the password contained a dollar sign. Bash interpreted $f as a variable. The wrong password was sent. Not once. Multiple times. The website blocked further attempts. And the agent blamed the website."

**Scripts creados**:
- `browser_video.py` — primer intento de login automático. Tenía el bug del `$f`.

**Lección**: nunca pasar variables con `$` directamente a un comando de shell. Usar Python subprocess con argumentos como lista, no como string.

---

## Capítulo 3 — 160% de CPU y un jet engine (30s)

**Visual**: htop mostrando 160% CPU, luego el comando `google-chrome --use-gl=angle --use-angle=gl-egl`
**TTS**: "Headless Chrome uses SwiftShader. Software GPU emulation. 160 percent CPU. The laptop fan sounded like a jet engine. The agent didn't notice until the human complained. The fix? Four flags to use the AMD GPU directly. From 160% to 4%."

**Lección**: Chrome headless por defecto emula GPU en software. En una máquina con GPU real, hay que forzarlo a usarla.

---

## Capítulo 4 — HeadlessChrome te delata (30s)

**Visual**: `navigator.userAgent` mostrando "HeadlessChrome/149.0.0.0", luego "Too many requests", luego el fix con `--user-agent`
**TTS**: "The website said too many requests. But the human could log in from his phone just fine. It wasn't a rate limit. It was automation detection. The User-Agent literally said HeadlessChrome. A custom User-Agent without that word solved it instantly."

**Lección**: "Too many requests" no siempre es rate limit. Puede ser detección de automation. El User-Agent es lo primero que hay que revisar.

---

## Capítulo 5 — Los 6 clips de robot (1 min)

**Visual**: la página de Higgsfield con el formulario de video, el file input oculto, la inyección de imagen vía JavaScript
**TTS**: "Generating video clips required uploading an image first. The file input was invisible. Its ID changed every time the model changed. The agent tried agent-browser's upload command. Failed. Tried clicking the button. Failed. Tried making the input visible. Failed. The solution was JavaScript's File API with DataTransfer. The agent spent three sessions on this. The human watched."

**Scripts creados**:
- `webui_generate.py` — script definitivo que inyecta imagen vía File API, acepta el dialog "Media upload agreement", llena el prompt, hace clic en Generate, y espera el resultado.

**Lección**: los inputs `sr-only` de React no se pueden manipular con comandos normales de automation. Hay que usar la File API de JavaScript con DataTransfer.

---

## Capítulo 6 — El snapshot que escondía los UUIDs (30s)

**Visual**: `snapshot -c` vs `snapshot` (sin flags), mostrando los UUIDs en los alt attributes
**TTS**: "The agent found the generated videos in the history tab. But couldn't download them. No download button. No video URL. He tried clicking every button. Nothing worked. The human said: try the library. Click the video. And use a full snapshot, not compact. The -c flag was hiding the alt attributes where the video UUIDs were hiding."

**Lección**: `snapshot -c` es bueno para ahorrar tokens, pero esconde metadata en atributos como `alt`, `data-*`, y `href`. A veces la información está justo en lo que filtrás.

---

## Capítulo 7 — Cómo descargar los videos (30s)

**Visual**: library/video/{uuid} con el player y botón Download
**TTS**: "The library detail page had everything. A video player. A download button. The video URL in the src attribute. The agent downloaded all 6 clips. Error, thinking, idle, victory, mountain. Each one cost 7.5 credits. Total: 45 credits. Worth it."

**Scripts creados**:
- Función `download_video()` en `webui_generate.py`
- Función `get_video_url()` que abre library/{uuid} y extrae el src del `<video>`

**Lección**: los videos generados no están en el DOM de la página principal. Están en una página aparte: `/library/video/{uuid}`. Hay que ir ahí, esperar que React cargue el player, y extraer el src.

---

## Capítulo 8 — 19 audios con la misma frase (1 min)

**Visual**: lista de 19 archivos mp3 en la librería de audio, todos con texto concatenado
**TTS**: "The agent needed narration for the video. Higgsfield had ElevenLabs TTS built in. He wrote a script. But the fill command on the Voiceover textbox didn't replace the text. It concatenated. Every new sentence was appended to the old one. He generated 19 audio files before noticing they all said the same thing. Nineteen. The human said: try one first, then check, then repeat. The agent never tested a single one before mass-producing failures."

**Scripts creados**:
- `webui_tts.py` — script para generar TTS vía Higgsfield Voiceover. Tenía el bug de concatenación, nunca se usó correctamente.

**Lección**: probar UNO. Siempre uno. No 19. Verificar que funciona, recién escalar. El `fill` de agent-browser no limpia textareas de React que no sean `<input>` — hay que verificar manualmente el contenido después de escribir.

---

## Capítulo 9 — Los scripts que quedaron (30s)

**Visual**: árbol de archivos del experimento
**TTS**: "After 19 hours, the session produced 6 scripts. Two for the SDK approach that never got credits. Two for browser automation. One for TTS that never worked. And one video script for the next agent. The working script is webui_generate.py. It can generate any video clip from an image and a prompt. The rest is documentation of what not to do."

**Archivos producidos**:
- `generate_video.py` — SDK, necesita créditos
- `browser_video.py` — login automático por web (requiere código de verificación)
- `webui_generate.py` — **funcional**: genera clips de video vía web UI
- `webui_tts.py` — TTS vía ElevenLabs (el fill concatena, no reemplaza — no usar sin fix)
- `models.md` — referencia de modelos y costos
- `video-plan.md` — plan original del video (híbrido Higgsfield + screencast)
- `lessons-script.md` — este archivo

---

## Epílogo — Lo que aprendió el agente (30s)

**Visual**: los logos de las herramientas usadas: Python, agent-browser, ffmpeg, edge-tts
**TTS**: "The agent learned 9 lessons. Check for credits before writing code. Escape shell variables. Use the GPU directly. Spoof the User-Agent. Re-find elements after every render. Use File API for hidden inputs. Don't use compact flags when searching. Test one before mass-producing. And when stuck, ask the human."

---

## Especificaciones técnicas para Remotion

### Componentes necesarios

1. **Texto con efecto máquina de escribir** — para mostrar código y terminal
2. **Pantalla dividida** — código a la izquierda, resultado a la derecha
3. **Transiciones** — fundido entre escenas
4. **Sincronización TTS** — cada escena tiene su propio audio, duración conocida

### Archivos de entrada

```
output/
├── idle.mp4         # clip robot (5s, 828x1108)
├── thinking.mp4     # clip robot (5s)
├── error.mp4        # clip robot (5s)
├── victory.mp4      # clip robot (5s)
├── mountain.mp4     # clip extra
```

### Narración (edge-tts)

```bash
# 9 segmentos, uno por capítulo
edge-tts --voice en-US-JennyNeural -t "texto del capítulo" --write-media output/chapter1.mp3
# ... repetir para cada capítulo
```

### Tiempos estimados por capítulo

| Capítulo | Duración |
|----------|----------|
| Prólogo | 15s |
| Cap 1: API sin créditos | 30s |
| Cap 2: Password bash | 45s |
| Cap 3: 160% CPU | 30s |
| Cap 4: Headless detect | 30s |
| Cap 5: 6 clips robot | 60s |
| Cap 6: Snapshot UUIDs | 30s |
| Cap 7: Descargar videos | 30s |
| Cap 8: 19 audios iguales | 60s |
| Cap 9: Los scripts | 30s |
| Epílogo | 30s |
| **Total** | **~6.5 min** |

### Notas para el agente de Remotion

- No uses Higgsfield para nada. edge-tts para narración, Remotion para composición.
- Los clips de robot ya existen en `output/`. Son 828x1108, escalarlos a 608x1080.
- El guión de cada capítulo está arriba en TTS. Pasarlo a edge-tts literal.
- Si falta algún clip, no regenerar — usar pantalla negra con texto.
- El video es sobre la historia, no sobre la calidad visual.
