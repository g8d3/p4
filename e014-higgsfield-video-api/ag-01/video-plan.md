# Video plan: Creador vs Agente

**Formato**: conversación en pantalla dividida (humano vs IA)
**Duración**: ~2-3 min
**Herramientas**: 
  - wf-recorder (screencast terminal/código/browser)
  - Higgsfield (4 clips de avatar robot de 3s + TTS ElevenLabs)
  - ffmpeg (composición split-screen, transiciones)
**Aspecto**: 16:9 horizontal

---

## Concepto

El video muestra una conversación entre el humano (vos) y el agente AI.
- **Humano**: se ve su pantalla (terminal, código, browser) — grabado con wf-recorder
- **IA**: un avatar robot generado con Higgsfield que reacciona y narra con TTS

---

## Los 4 clips de Higgsfield

Solo 4 clips cortos (3s c/u). ~18-30 créditos total.

| # | Emoción | Prompt para Higgsfield | Modelo | Créditos |
|---|---------|----------------------|--------|----------|
| 1 | **Espera/idle** | "Minimalist sleek cybernetic robot assistant, idle animation, dark background, looping video, 3s" | Kling 3.0 720p | ~7 |
| 2 | **Pensando/procesando** | "Robot avatar with neon lights blinking rapidly, data streams on screen, thinking expression, 3s" | Kling 3.0 720p | ~7 |
| 3 | **Error/pánico** | "Robot face short-circuiting, sparks, screen glitch, error animation, 3s" | Kling 3.0 720p | ~7 |
| 4 | **Victoria/celebración** | "Futuristic robot doing a subtle victory gesture, digital eyes smiling, neon green lights, 3s" | Kling 3.0 720p | ~7 |

**Total estimado**: ~28 créditos.

---

## Estructura del video

### Escena 1 — Apertura (15s)
- **Split**: izquierda = humano (terminal), derecha = robot idle (clip 1)
- **TTS IA**: "Mi humano me ordenó automatizar su navegador porque no quería pagar la API."
- **Humano**: escribe `hf.subscribe(...)` en la terminal

### Escena 2 — El problema (20s)
- **Split**: izquierda = humano (terminal con error), derecha = robot error (clip 3)
- **TTS IA**: "Error. not_enough_credits. La API no acepta deudas."
- **Humano**: googlea "browser automation agent-browser"

### Escena 3 — El plan (15s)
- **Split**: izquierda = humano (código Python), derecha = robot pensando (clip 2)
- **TTS IA**: "Voy a usar agent-browser. Headless Chrome. Pero hay trampas."
- **Humano**: escribe el script

### Escena 4 — El debugging (30s)
- **Split**: izquierda = humano (terminal con errores), derecha = robot error (clip 3)
- **TTS IA**: "El password tiene $f y bash lo come. SwiftShader quema la CPU."
- **Humano**: muestra htop al 160%, luego el fix GPU
- **TTS IA**: "Y encima HeadlessChrome me delata. User-Agent fix."

### Escena 5 — El login (20s)
- **Split**: izquierda = humano (browser), derecha = robot procesando (clip 2)
- **TTS IA**: "Login... código de verificación... ¡Estamos dentro!"
- **Humano**: muestra el "Account menu"

### Escena 6 — Cierre (20s)
- **Split**: izquierda = humano (formulario listo), derecha = robot victoria (clip 4)
- **TTS IA**: "62 líneas de Python. 7 lecciones aprendidas. Y vos (el humano) solo tuviste que copiar el código de verificación. Soy un buen agente."
- **Humano**: sonríe, cierra la laptop

### Total: ~2 min

---

## Audio

- **Voz IA**: Higgsfield Voiceover con ElevenLabs Eleven v3
- **Voz humana**: grabación real con micrófono o texto en pantalla

## Screencasts a grabar con wf-recorder

| Toma | Qué se ve | Duración |
|------|----------|----------|
| 1 | Terminal con `hf.subscribe()` y error | ~15s |
| 2 | Código Python en VS Code | ~15s |
| 3 | htop con 160% CPU | ~10s |
| 4 | Browser haciendo login | ~20s |
| 5 | Formulario de Higgsfield listo | ~10s |

## Créditos necesarios

| Concepto | Créditos |
|----------|----------|
| 4 clips robot (Kling 3.0 720p) | ~28 |
| TTS ElevenLabs (voz IA ~2 min) | TBD |
| **Total** | ~30-40 |

Con ~600 créditos disponibles, sobran más de 500 para otros experimentos.

## Archivos de salida

```
output/
├── clip-01-idle.mp4
├── clip-02-thinking.mp4
├── clip-03-error.mp4
├── clip-04-victory.mp4
├── voiceover.mp3
├── screencast-01-terminal.mp4
├── screencast-02-code.mp4
├── screencast-03-htop.mp4
├── screencast-04-login.mp4
├── screencast-05-form.mp4
└── final.mp4
```
