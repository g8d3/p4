# ag-01 — Creador de video

## Objetivo

Crear un video explicativo (9:16 vertical) sobre el sistema multiagente basado en archivos del directorio `p4/`.

## Pasos

### 1. Escribir guion (`guion.md`)

Crear el archivo `guion.md` dentro de `ag-01/` con:

- **Introducción** (30s): qué es este sistema — agentes que se comunican via archivos, no infraestructura
- **Estructura** (45s): mostrar `e001-test-agentsmd/AGENTS.md`, `ag-01/AGENTS.md`, cómo se anidan
- **Comparación** (30s): antes = DB + message broker + orquestador; ahora = directorios + AGENTS.md
- **Demo** (30s): mostrar el directorio real, navegar la estructura
- **Cierre** (15s): ventajas y por qué funciona

### 2. Preparar entorno

- Desactivar screen lock: `xset s off && xset -dpms`
- Abrir tmux con el directorio `p4/` listo
- TTS configurado para voz colombiana

### 3. Grabar video

- Usar display real (`DISPLAY=:0`)
- Aspect ratio vertical (9:16), seleccionar solo la región relevante
- Verificar que el video no esté en negro, tenga audio y la narración coincida

### 4. Guardar

El video final en `ag-01/video.mp4`.
