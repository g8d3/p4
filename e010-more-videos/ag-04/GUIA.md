# GUIA — Plataforma unificada: nimbo + pdw + filex + proxy + agentes

## Visión

Un solo servidor web que integre todo:

- Exploración de archivos (filex)
- Gestión de displays virtuales + grabación (pdw)
- Proxy para LLMs (OpenAI, Anthropic, etc.)
- Gestión de agentes de IA con ciclo de vida completo
- Acceso VNC web a displays
- Editor de código + terminal web por agente
- Chat en vivo con agentes vía WebSocket

## Arquitectura

### nimbo — framework base (ya existe)

```
nimbo/
├── __init__.py        # App, Request, Response, Database, WSManager
├── server.py          # Core asyncio HTTP + WS (988 lines)
├── db.py              # SQLite/PostgreSQL con DBPool (159 lines)
├── ws.py              # WebSocket nativo RFC 6455 (137 lines)
├── ws_base.py         # WSManager pub/sub abstracto (53 lines)
├── ws_websockets.py   # Backend WS con librería websockets (105 lines)
├── system.py          # Monitoreo CPU/procesos/logs (129 lines)
├── proxy.py           # Proxy LLM con @app.proxy (~300 lines)
├── actions.py         # Decorador @app.action
└── discovery.py       # Descubrimiento de agentes
```

### Módulos nuevos para nimbo

```diff
nimbo/
+├── filex.py           # Explorador de archivos (port de filex)
+├── display.py         # Gestión de displays virtuales (port de pdw)
```

### App unificada — server.py

```python
from nimbo import App

app = App(__name__)

# ─── Modelos ───

@app.model
class AgentSession:
    name: str
    display: str           # HEADLESS-N asignado
    task: str
    status: str            # idle | recording | processing
    file_root: str         # directorio que explora

@app.model
class Recording:
    agent: str
    display: str
    duration: int
    status: str            # recording | done | failed
    output_path: str

@app.model
class FileEntry:
    name: str
    is_dir: bool
    size: int
    date: str
    agent: str             # opcional — asociado a un agente

# ─── Proxy LLM ───

@app.proxy
class OpenAI: ...

@app.proxy(port=9099)
class Anthropic: ...

# ─── Rutas ───

@app.route("/browse/**path")     # file browser
@app.route("/chat/<agent_id>")   # WebSocket chat con agente
@app.route("/terminal/<agent_id>")# WebSocket terminal

# ─── Dashboard ───
# static/index.html unificado con tabs:
#   Files | Displays | Agents | Recordings | Proxy
```

## Migración por capas

### Capa 1 — filex → nimbo/filex.py

Qué migrar de `serve_md.py` (804 lines):
- `do_GET` con 300 líneas → rutas nimbo separadas
- `render_md()` → mantiene lógica de renderizado
- `render_code()` con highlight.js + Ace editor → mantener
- `_serve_file_range()` para video seeking → mantener
- Operaciones CRUD (PUT/DELETE/MOVE/MKCOL) → migrar a @app.route

Ganancias:
- Autenticación via nimbo (hoy filex no tiene)
- WebSocket para cambios en vivo
- Dashboard unificado

### Capa 2 — pdw → nimbo/display.py

Qué migrar de `pdw` (363 lines bash):
- `init` / `clean` → funciones Python con subprocess
- `ds new` / `ds rm` → `swaymsg create_output` desde Python
- `w new` / `w ls` / `w mv` / `w rm` → gestión de ventanas
- `rec` → `wf-recorder` + `ffmpeg` VAAPI
- `vnc` → `wayvnc`

Ganancias:
- Dashboard visual: tabla de displays con botones
- API REST en vez de CLI
- Eventos WebSocket cuando cambia estado
- Coordinación multi-agente

### Capa 3 — proxy + agentes

Ya existe en nimbo (`@app.proxy`). Mejorar:
- `@app.proxy` con ciclo de vida v3 (discovered → active → standby → error)
- Métricas de eficiencia/eficacia por agente
- Tareas asignables via PUT
- Directions modificables

### Capa 4 — app tipo opencode

Funcionalidades nuevas:
- **Editor de código** en web (Ace editor — ya lo usa filex)
- **Terminal web** (xterm.js) para cada agente
- **Chat en vivo** vía WebSocket con el agente
- **Grabación con un clic** desde la UI
- **Explorador de archivos** por agente
- **VNC web** integrado en el dashboard (no puertos separados)

## Dashboard unificado — estructura de tabs

```
┌──────────────────────────────────────────────────────────┐
│  nimbo ◉           [Files] [Displays] [Agents] [Proxy]   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Cada tab muestra su tabla CRUD con acciones:            │
│                                                          │
│  Files:    navegar, crear, editar, eliminar archivos     │
│  Displays: crear display, abrir app, grabar, VNC         │
│  Agents:   ver estado, asignar tarea, chat, terminal     │
│  Proxy:    ver agentes LLM, métricas, eficiencia         │
│  Recordings: lista de videos, ver, descargar             │
│                                                          │
│  Barra de sistema: CPU | RAM | GPU | DISCO              │
└──────────────────────────────────────────────────────────┘
```

## Orden de implementación

1. **filex → nimbo/filex.py** (menor riesgo, más valor inmediato)
2. **Dashboard unificado** (tabs + navegación)
3. **pdw → nimbo/display.py** (API de displays)
4. **VNC web integrado** (proxy VNC → WebSocket → canvas JS)
5. **Chat + Terminal web** por agente
6. **Editor de código** en el browser
7. **Grabación con un clic** desde UI
