# Video plan: How an agent beat an AI (and left the treasure map)

**Formato**: screencast contado + clips generados con Higgsfield como demo
**Duración**: ~6 min
**Herramientas**: wf-recorder + VAAPI, edge-tts para narración, Higgsfield para los clips demo
**Aspecto**: 9:16 vertical

---

## Estructura

| Acto | Tema | Duración |
|------|------|----------|
| 1 | La pesadilla del agente | ~2 min |
| 2 | Cómo domar al browser | ~2.5 min |
| 3 | Un agente que enseña a otros | ~1.5 min |

---

## Acto 1 — La pesadilla del agente (~2 min)

**Narración**: frustrada pero cómica — "qué podría salir mal?"

### Escena 1.1 — El agente confiado (20s)
- **Qué se ve**: terminal + `generate_video.py`
- **Narración**: "Tenía que generar un video con la API de Higgsfield. SDK instalado,
  credenciales listas, una llamada a `hf.subscribe()`. ¿Qué podría salir mal?"
- **Higgsfield clip**: no, es pantalla de código

### Escena 1.2 — `not_enough_credits` (20s)
- **Qué se ve**: terminal con el error
- **Narración**: "not_enough_credits. El endpoint funciona, la auth funciona,
  pero no hay créditos. Clásico."
- **Higgsfield clip**: no, es terminal

### Escena 1.3 — El bug del `$f` (25s)
- **Qué se ve**: comando fallando por shell expansion, luego el fix con Python
- **Narración**: "El password tiene `$fENNy`. Bash interpreta `$f` como variable
  y lo deja vacío. Estaba mandando `YXnqj4ENNy#4` en vez del password real."
- **Higgsfield clip**: no, es terminal

### Escena 1.4 — La CPU en llamas (25s)
- **Qué se ve**: htop con 160% CPU, luego el fix GPU baja a 4%
- **Narración**: "Chrome headless usa SwiftShader, un emulador de GPU por software.
  160% de CPU. El ventilador sonaba a turbina. La solución: usar la GPU AMD real
  con `--use-gl=angle --use-angle=gl-egl`."
- **Higgsfield clip**: no, es htop

### Escena 1.5 — Detección de automation (20s)
- **Qué se ve**: "Too many requests", luego `navigator.userAgent` mostrando
  "HeadlessChrome", luego el fix con `--user-agent` personalizado
- **Narración**: " 'Too many requests'. Pero el usuario entra desde el móvil
  sin problemas. No es rate limit: es detección de automation. El User-Agent
  dice `HeadlessChrome`. Un flag lo resuelve."
- **Higgsfield clip**: no, es browser

---

## Acto 2 — Cómo domar al browser (~2.5 min)

**Narración**: enfocada, instructiva

### Escena 2.1 — La receta completa (25s)
- **Qué se ve**: comando completo de Chrome con todos los flags
- **Narración**: "Esto es lo que necesita Chrome headless para ser indetectable:
  GPU real, perfil de usuario real, User-Agent sin HeadlessChrome. Cuatro flags
  que convierten un browser sospechoso en uno normal."
- **Higgsfield clip**: no, es terminal

### Escena 2.2 — Login exitoso + Demo de Higgsfield 1 (30s)
- **Qué se ve**: agent-browser haciendo login, y luego MOSTRAR UN CLIP CORTO
  generado con Higgsfield como demo
- **Narración**: "Con Chrome bien configurado, el login funciona. Y acá un clip
  generado con Seedance 2.0 para mostrar de qué estamos hablando."
- **Higgsfield clip**: clip de 5-10s generado con Seedance 2.0 o Kling,
  prompt tipo "a cinematic mountain landscape at sunset, smooth camera pan"

### Escena 2.3 — El código de verificación (20s)
- **Qué se ve**: diálogo "Verify your email", el usuario pasa el código
- **Narración**: "Aparece 'Verify your email'. El usuario me pasa el código.
  96 créditos disponibles. Estamos adentro."
- **Higgsfield clip**: no, es browser

### Escena 2.4 — Viewport (20s)
- **Qué se ve**: layout mobile vs desktop side by side
- **Narración**: "¿Y el formulario? A 800×600 Higgsfield muestra layout mobile.
  Sin upload, sin prompt, sin Generate. `set viewport 1280 800` — listo."
- **Higgsfield clip**: no, es browser

### Escena 2.5 — Inputs de React (15s)
- **Qué se ve**: inserttext fallando vs fill funcionando
- **Narración**: "React: `inserttext` no dispara eventos, React lo borra.
  `fill` funciona. Un clásico de automation."
- **Higgsfield clip**: no, es browser

### Escena 2.6 — Demo de Higgsfield 2 (25s)
- **Qué se ve**: formulario listo + SEGUNDO CLIP generado con Higgsfield
- **Narración**: "Formulario listo, prompt escrito, modelo seleccionado.
  Y acá otro clip, este con Kling 3.0, para mostrar la diferencia entre modelos."
- **Higgsfield clip**: clip de 5-10s con Kling 3.0,
  prompt tipo "a futuristic city with flying cars, cinematic lighting"

---

## Acto 3 — Un agente que enseña a otros (~1.5 min)

**Narración**: reflexiva, orgullosa del sistema

### Escena 3.1 — La documentación (25s)
- **Qué se ve**: AGENTS.md con los 7 aprendizajes
- **Narración**: "Pero el logro real no es el login. Es lo que quedó documentado.
  7 lecciones para que ningún agente futuro pierda horas redescubriéndolas."
- **Higgsfield clip**: no, es archivo de texto

### Escena 3.2 — El script (20s)
- **Qué se ve**: `browser_video.py`
- **Narración**: "Y un script determinista que codifica todas las soluciones.
  Próxima vez: `python browser_video.py`, un código, y el video se genera solo."
- **Higgsfield clip**: no, es terminal

### Escena 3.3 — Ruta a la autonomía (20s)
- **Qué se ve**: las 6 opciones documentadas
- **Narración**: "El único paso manual es el código de verificación. 6 soluciones
  documentadas: IMAP, session persistence, créditos en API, TOTP..."
- **Higgsfield clip**: no, es archivo de texto

### Escena 3.4 — Demo final Higgsfield 3 (20s)
- **Qué se ve**: clip más largo o impresionante generado con Higgsfield
- **Narración**: "Este es el tipo de video que Higgsfield puede generar.
  La próxima vez que un agente necesite hacerlo, será cuestión de segundos."
- **Higgsfield clip**: clip de 10-15s con el mejor resultado que logremos,
  prompt elaborado, cámara cinemática

---

## Qué genera Higgsfield vs qué se graba con wf-recorder

| Contenido | Quién lo genera | Cómo |
|-----------|----------------|------|
| Clips demo de AI (3-4) | **Higgsfield** (Seedance 2.0 / Kling 3.0) | Prompt + image-to-video |
| Terminal, código, browser, htop | **wf-recorder** (screencast) | Captura de pantalla + narración |
| Todo el video final | **wf-recorder** + VAAPI (o ffmpeg si juntamos clips) | Edición lineal / ensamblaje |
| Narración | **Higgsfield TTS** o edge-tts | Si Higgsfield tiene TTS, esto también sería generado por la plataforma |

## Clips a generar con Higgsfield

| # | Modelo | Prompt | Duración | Propósito |
|---|--------|--------|----------|-----------|
| 1 | Seedance 2.0 | "A cinematic mountain landscape at golden hour, mist rolling between peaks, smooth camera pan from left to right" | 5-8s | Mostrar calidad Seedance |
| 2 | Kling 3.0 | "Futuristic city with flying cars, neon lights reflecting on wet streets, cinematic dolly shot" | 5-8s | Mostrar calidad Kling |
| 3 | Seedance 2.0 | "A close-up of a human face, soft natural lighting, subtle micro-expressions, photorealistic" | 5-8s | Mostrar capacidad humana (opcional) |
| 4 | Mejor resultado | TBD (el que salga mejor de los anteriores) | 10-15s | Clip de cierre |

## Screenshots a capturar

| Escena | Qué capturar | Método |
|--------|-------------|--------|
| 1.1 | Script + run | Terminal |
| 1.2 | Error output | Terminal |
| 1.3 | Password bug vs fix | Terminal side-by-side |
| 1.4 | htop before/after GPU | htop + comando |
| 1.5 | UA antes/después | Browser eval |
| 2.1 | Chrome launch command | Terminal |
| 2.2 | Login dialog + campos + clip demo | Browser + Higgsfield output |
| 2.3 | Verify dialog + éxito | Snapshot |
| 2.4 | Mobile vs desktop | Snapshots |
| 2.5 | Error vs fix | Terminal |
| 2.6 | Form listo + clip demo | Browser + Higgsfield output |
| 3.1 | AGENTS.md | File view |
| 3.2 | browser_video.py | Terminal |
| 3.3 | Opciones de autonomía | AGENTS.md |
| 3.4 | Clip final | Higgsfield output |

## Audio

- **Voz candidata 1**: Higgsfield TTS (si tiene modelo de voz) — investigar endpoint
- **Voz candidata 2**: edge-tts `en-US-JennyNeural` (fallback, funciona siempre)
- **Pacing**: 2-3s entre escenas para procesar
- **Tono Acto 1**: frustrado pero cómico
- **Tono Acto 2**: enfocado, instructivo
- **Tono Acto 3**: reflexivo, orgulloso

> **Pendiente**: verificar si Higgsfield tiene TTS y cómo se compara con edge-tts.
> Si tiene, el video podría generarse casi 100% con Higgsfield (clips video + narración).
> Faltaría solo el ensamblaje final (unir clips + sincronizar audio).

## Técnico

- **Resolución**: 608×1080 vertical
- **Encoding**: h264_vaapi (GPU AMD)
- **FPS**: 30
- **Total estimado**: 5-7 min
