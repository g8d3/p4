# Video script: How an agent failed upwards

**Para nuevo agente con Remotion + edge-tts**
**Duración**: ~3 min
**Formato**: 9:16 vertical (608×1080)
**Sin Higgsfield** — edge-tts para narración, Remotion para composición, screenshots reales.

---

## Resumen de errores cometidos (para que el nuevo agente no los repita)

### 1. Asumir que el SDK resolvía todo
Intenté usar la API key directo → `not_enough_credits`. En vez de probar otra ruta, me quedé intentando lo mismo. **Lección**: cuando algo no funciona, cambiar de estrategia, no insistir.

### 2. No verificar el password antes de usarlo
El password tenía `$fENNy`. Bash lo interpretó como variable vacía. Mandé `YXnqj4ENNy#4` en vez del password real. Los rate limits que vinieron después fueron culpa mía. **Lección**: variables de entorno con caracteres especiales necesitan Python subprocess, no shell directo.

### 3. Ignorar el User-Agent
"Too many requests" no era rate limit — era detección de automation. El User-Agent decía `HeadlessChrome/149.0.0.0`. No se me ocurrió mirarlo hasta que el usuario lo sugirió. **Lección**: cuando un sitio bloquea, lo primero es verificar qué fingerprint estamos dejando.

### 4. SwiftShader y CPU al 160%
Chrome headless usa SwiftShader (emulación de GPU por software). Lo dejé así hasta que el usuario se quejó del ruido del ventilador. **Lección**: `--use-gl=angle --use-angle=gl-egl` usa la GPU real, baja a ~4% CPU.

### 5. React re-renders y refs inválidas
Cada vez que hacía clic o fill, React re-renderizaba la página y cambiaba todos los IDs. No lo entendí hasta la 5ta vez que un `@e30` dejó de funcionar. **Lección**: después de cada acción, re-obtener los refs con un nuevo snapshot.

### 6. Subir imagen al form de video
El file input tiene `class=sr-only` (invisible) y `id` dinámico. Intenté 5 enfoques distintos antes de encontrar el correcto: JavaScript File API + DataTransfer. **Lección**: no subestimar un `<input type=file>` oculto por React.

### 7. El snapshot -c escondía los UUIDs
Usaba `snapshot -c` para ahorrar tokens, pero eso quitaba los `alt` attributes donde estaban los UUIDs de los videos. El usuario me dijo "sacá la bandera c" y aparecieron. **Lección**: -c es útil para resumir, pero a veces la información está justo en lo que filtra.

### 8. Generar 19 audios sin probar
El `fill` en el textbox de Voiceover concatena, no reemplaza. Generé 19 audios con el mismo texto antes de darme cuenta. El usuario me dijo "probá con uno solo primero" — debí escucharlo antes. **Lección**: probar UNO, verificar, recién escalar.

### 9. Proponer soluciones sin pensar
"Descarguemos los audios aunque tengan el mismo texto", "usemos edge-tts" — propuestas incoherentes que no arreglaban el problema de base. **Lección**: antes de proponer algo, preguntarse si realmente resuelve el problema o solo lo esconde.

---

## Estructura del video

### Escena 1 — Apertura (15s)
**Visual**: texto "How an agent failed upwards" sobre fondo negro
**TTS**: "This is the story of how an AI agent tried to automate a web app, failed 19 times, and needed a human to show him the obvious."

### Escena 2 — El password (20s)
**Visual**: terminal con `echo $PASSWORD` mostrando resultado truncado
**TTS**: "First mistake. The password had a dollar sign. Bash ate it. The agent typed the wrong password for hours. Rate limits piled up. And he blamed the website."

### Escena 3 — Headless detection (15s)
**Visual**: browser console mostrando `navigator.userAgent`
**TTS**: "The website wasn't rate-limiting. It was detecting automation. The User-Agent literally said HeadlessChrome. And the agent never checked."

### Escena 4 — CPU on fire (15s)
**Visual**: htop con 160% CPU, luego comando con `--use-gl=angle`
**TTS**: "The fan was screaming. 160 percent CPU just to render a login page. A couple of flags fixed it. The agent just hadn't read the docs."

### Escena 5 — React re-renders (20s)
**Visual**: snapshot antes y después de un clic, mostrando refs cambiadas
**TTS**: "React re-renders. Every click. Every fill. Every breath. The agent kept using stale refs and wondering why clicks missed. Re-find everything, every time."

### Escena 6 — 19 audios iguales (20s)
**Visual**: lista de 19 archivos mp3, todos con el mismo MD5
**TTS**: "Nineteen audio files. All identical. The agent never tested the first one before generating the other eighteen. The human said: try one first. One."

### Escena 7 — Cierre (15s)
**Visual**: el script `webui_generate.py` funcionando correctamente
**TTS**: "In the end, the agent did make something work. A script that generates video clips. A tool that downloads them. But the real lesson was learning how to learn: test one, verify, then repeat."

---

## Archivos que necesita el nuevo agente

- `e014-higgsfield-video-api/ag-01/output/` — clips de robot (error, idle, thinking, victory)
- `e014-higgsfield-video-api/ag-01/webui_generate.py` — script funcional (si aplica)
- `e014-higgsfield-video-api/ag-01/AGENTS.md` — learnings documentados
- `e014-higgsfield-video-api/ag-01/trail.md` — historia completa

## TTS a generar con edge-tts

```bash
edge-tts --voice en-US-JennyNeural -f script.txt --write-media output/tts.mp3
```

7 segmentos de narración, cada uno de 15-20 segundos.
Componer con Remotion: texto + clip visual + TTS sincronizado.

## Notas para el agente

- No uses Higgsfield. edge-tts funciona siempre, no gasta créditos.
- Remotion para la composición (texto + video clips + audio).
- Los clips de robot están en `output/` y ya funcionan.
- El valor del video no es técnico — es la historia de un agente que necesitó un humano para aprender lo obvio.
