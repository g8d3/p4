# Estructura de Experimentos

Este directorio (`p4`) contiene experimentos organizados por código y nombre.

## Convención de directorios

Cada experimento vive en un subdirectorio con el formato:

```
e<NNN>-<nombre-breve>/
```

Ejemplo:
```
e001-latencia/
e002-benchmark-gpu/
e003-prueba-cache/
```

## Subdirectorios de agentes

Dentro de cada experimento, cada agente tiene su propio directorio:

```
e001-latencia/
├── AGENTS.md
├── ag-01/
├── ag-02/
└── ag-03/
```

Cada agente define su propia estructura interna y puede tener su propio `AGENTS.md`.

## AGENTS.md anidados

- **`p4/AGENTS.md`** (este archivo): explica la estructura global y las convenciones del repositorio.
- **`p4/<experimento>/AGENTS.md`**: explica qué hace ese experimento, qué archivos contiene, cómo ejecutarlo, y cualquier contexto necesario.
- **`p4/<experimento>/ag-<N>/AGENTS.md`**: (opcional) documentación específica de ese agente dentro del experimento.

## Reglas

1. Crear un subdirectorio `e<NNN>-<nombre>` para cada nuevo experimento.
2. Cada experimento debe tener su propio `AGENTS.md`.
3. Cada experimento puede tener uno o más subdirectorios de agentes (`ag-01`, `ag-02`, ...).
4. El `AGENTS.md` raíz solo describe la estructura; nunca contiene detalles de experimentos individuales.

## Entorno de trabajo

- **Dispositivo**: Android con Termux → SSH a Linux (zsh + tmux).
- **Entrada**: Google Keyboard (dictado por voz).
- **Agente**: Open Code CLI.
- **Proveedor principal**: opencode-go.
- **Proveedor alternativo**: Z.AI (coding plan Pro, no pay-as-you-go).
- **Modelos principales**: DeepSeek V4 Flash y MiniMax 2.5 (no Pro). MiniMax 2.5 soporta visión/multimodal, ideal para tareas con video.
- **tmux**: se usan ventanas, no paneles.
- **Mobile-first**: toda interfaz (terminal o web) debe ser amigable con móvil.

### Variables de entorno

| Variable | Descripción |
|---|---|
| `OPENCODE_GO_API_KEY` | API key para opencode-go |
| `OPENCODE_GO_BASE_URL` | Base URL del proveedor opencode-go |
| `OPENCODE_GO_MODEL` | Modelo activo para opencode-go |
| `OPENCODE_API_KEY` | Alias que apunta a `OPENCODE_GO_API_KEY` |
| `ZAI_API_KEY` | API key para Z.AI (coding plan Pro) |
