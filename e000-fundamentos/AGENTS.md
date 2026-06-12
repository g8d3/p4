# e000 — Fundamentos

Este experimento define las convenciones y configuraciones compartidas que otros experimentos pueden heredar o ignorar.

## Convención de directorios

Cada experimento vive en un subdirectorio con el formato:

```
e<NNN>-<nombre-breve>/
```

Ejemplo:
```
e000-fundamentos/
e001-test-agentsmd/
e002-...
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

Los niveles de abstracción son infinitos. Un experimento puede contener sub-experimentos, y cada agente puede tener sub-agentes. Cada nivel hereda el contexto del nivel superior.

## AGENTS.md anidados

- **`<experimento>/AGENTS.md`**: explica qué hace ese experimento, qué archivos contiene, cómo ejecutarlo.
- **`<experimento>/ag-<N>/AGENTS.md`**: (opcional) documentación específica de ese agente dentro del experimento.

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

## Principios para agentes

- **Calidad sobre velocidad**: no se trata solo de terminar rápido. Explora con libertad, pero busca un balance — no agregues código innecesariamente. Prioriza soluciones simples y bien hechas.
- **No asumas, verifica**: antes de cambiar algo, lee el estado actual. Luego piensa cómo modificarlo, actúa, y finalmente verifica que el resultado sea el esperado. Nunca asumas que algo funciona sin confirmarlo.
- **Usa tu directorio de trabajo**: no utilices `/tmp` ni directorios externos. Trabaja dentro de tu propio directorio y mantenlo organizado como mejor te parezca.
- **Timeouts en comandos**: todo comando debe ejecutarse con un timeout estimado. Si no sabes cuánto puede tardar, pon un margen amplio. Nunca dejes un comando sin timeout.
- **Comandos bloqueantes al fondo**: si un comando está diseñado para bloquear la terminal (servidores, procesos largos), ejecútalo en segundo plano.

## Grabación de video

- **Verifica el resultado**: revisa que el video no esté en negro, que tenga audio, y que la narración coincida con lo que ocurre en pantalla.
- **Captura de pantalla**: usar el display real (`DISPLAY=:0` o similar), nada de renderizado por CPU.
- **Sin screen lock**: antes de grabar, desactivar el bloqueo de pantalla para evitar videos en negro. Intentar en orden:
  1. `xset s off && xset -dpms` (desactivar blanking y ahorro de energía)
  2. `xscreensaver-command -exit` (detener xscreensaver si está corriendo)
  3. Si lo anterior no funciona, probar alternativas como `xdg-screensaver suspend` o `gsettings set org.gnome.desktop.screensaver idle-activation-enabled false`.
- **TTS**: voz colombiana (Español Latinoamérica, acento Colombia). Usar `edge-tts` con voz `es-CO-SalomeNeural` o `es-CO-GonzaloNeural`. No usar espeak-ng ni voces genéricas.
- **Formato móvil**: grabar en aspect ratio vertical (9:16). Para lograrlo:
  1. Seleccionar solo la ventana o región relevante (no el monitor completo).
  2. Redimensionar y reubicar las ventanas para que llenen eficientemente el área de grabación, sin dejar espacios vacíos.
  3. Asegurar que el contenido sea legible en una pantalla vertical.
- **Tipos de video**:
  - **Con script**: el agente sigue un guion predefinido y lo narra tal cual.
  - **Exploratorio**: el agente narra en vivo lo que va haciendo — lo que planea, los problemas que encuentra, cómo los resuelve, sus decisiones en el momento. Sin guion, reactivo.
