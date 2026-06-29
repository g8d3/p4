# ag-09 — TDS: Text Delta Stream

Un streamer de texto que captura cambios en terminal y browser, y los emite como un flujo estructurado de deltas. Analogo a como H.264 usa keyframes + P-frames, pero para contenido textual de pantalla.

## Problema que resuelve

Un agente no multimodal no puede "ver" qué pasa en pantalla. TDS captura **qué cambió** en cada canal (terminal, browser) y **cuándo**, generando un archivo de texto que cualquier LLM puede leer para reconstruir la cronologia completa de una sesion.

De un solo raw capture se pueden generar N narraciones (distintas voces, distinto pacing, distintos angulos).

## Formato: .tds (Text Delta Stream)

```
KEYFRAME t=0.0
  term(1): content=[ "$ " ]

DELTA t=1.2 ch=term(1)
  + "$ pdw init"
  + "HEADLESS-1 created"
  + "$ "

DELTA t=3.0 ch=term(1)
  ~ "HEADLESS-1 created" -> "HEADLESS-2 created"
  + "$ pdw w ls"

ADD ch=browser(1) url="https://github.com/trending"
  title="GitHub Trending"
  text=["Trending repositories", "1. langchain/langchain"]

DELTA t=5.5 ch=browser(1)
  scroll: y=200
  text=["6. openai/whisper", "7. anthropic/claude-code"]
```

### Operaciones

| Op | Significado |
|----|-------------|
| `KEYFRAME` | Estado completo de todos los canales |
| `DELTA` | Cambios en un canal desde el ultimo snapshot |
| `+` | Linea agregada |
| `-` | Linea removida |
| `~` | Linea modificada |
| `ADD` | Nuevo canal (nueva terminal, nueva tab) |
| `REMOVE` | Canal cerrado |

## Fuentes

1. **Terminal**: `tmux capture-pane -p` cada ~200ms, diff contra snapshot anterior
2. **Browser**: Chrome DevTools Protocol (CDP) via websocket, polling `document.body.innerText`

## Uso

```bash
# Vigilar terminal + browser en tiempo real
tds watch

# Grabar video + TDS (auto-descubre todo, Ctrl+C para terminar)
tds record
tds record mi-video        # con nombre personalizado
tds record -D 60           # con duracion fija

# Reconstruir timeline del .tds como texto en pantalla
tds replay session.tds
```

No necesita banderas ni configuracion. Descubre solo:
- La sesion de tmux actual
- Chrome si tiene `--remote-debugging-port`
- Displays virtuales de sway

### Record

Graba video del display virtual + TDS de terminal/browser.
Por defecto **ilimitado** — termina con Ctrl+C.

Output en `output/<nombre>/`:
- `video.mp4` — grabacion de pantalla
- `session.tds` — stream de texto delta
- `metadata.json` — info de la sesion

### Replay (v1 = texto)

`tds replay` lee el .tds y muestra la cronologia como texto en la terminal (stdout).
Util para leer que paso, sin necesidad de ver el video.

### Replay (v2 = en pantalla, idea)

Una version futura podria tomar el .tds y reproducir los comandos en un display
virtual real, abriendo terminales, escribiendo comandos, navegando el browser.
Esto probaria que TDS contiene la informacion completa para reconstruir la sesion.
Pero es complejo de implementar — primero validemos que el formato funciona.

## Tests

Correr tests:
```bash
python3 -m pytest tests/ -v
```

Tests locos:
```bash
bash tests/scenarios/terminal-blitz.sh           # 10000 lineas/segundo + ANSI + TUIs
bash tests/scenarios/terminal-torture.sh         # binario, lineas largas, resize
python3 tests/scenarios/browser-torture.py       # 100 tabs, infinite scroll, shadow DOM
bash tests/scenarios/endurance.sh                # 1 hora mixto
python3 tests/scenarios/reconstruction-test.py   # stream -> preguntas -> verificar
```

## Implementacion

```
tds/
  __init__.py
  capture.py    # Orquestador: inicia fuentes, escribe stream
  terminal.py   # TerminalWatcher: polls tmux capture-pane
  browser.py    # BrowserWatcher: polls CDP
  stream.py     # TDS format reader/writer
  diff.py       # Text diff engine (snapshot A -> snapshot B)
  replay.py     # Replay .tds file

tests/
  test_terminal.py
  test_browser.py
  test_stream.py
  scenarios/     # Crazy stress tests
```
