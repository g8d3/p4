# e001 — Test AGENTS.md

**Objetivo**: Probar y validar el sistema de AGENTS.md anidados creando un video que explique el concepto.

## Qué hace

Este experimento produjo un video (9:16 vertical) que explica el sistema multiagente basado en archivos:
- Sistema multiagente sin base de datos ni buses de mensaje
- Comunicación entre agentes vía AGENTS.md anidados y estructura de directorios
- Comparación con enfoques tradicionales

## Estructura

```
e001-test-agentsmd/
├── AGENTS.md      ← este archivo
└── ag-01/
    ├── AGENTS.md      ← proceso del agente
    ├── guion.md       ← guion narrativo
    ├── subtitles.srt  ← subtítulos estilo TikTok
    └── video.mp4      ← resultado final
```

## Lecciones aprendidas

- Los pasos son secuenciales (guion → demo → grabación → subtítulos), no paralelizables con múltiples agentes.
- `edge-tts` con voz colombiana da mejor calidad que espeak-ng.
- La fuente del terminal debe ser grande (~22pt) para verse bien en 9:16.
- Los subtítulos funcionan mejor en chunks cortos con colores alternados (estilo TikTok).
- Usar `ffmpeg -f x11grab -video_size 608x1080 -i :0.0+656,0` para captura 9:16.
- Desactivar screen lock antes de grabar (xset + xscreensaver).
- Verificar que el video no esté en negro, tenga audio y narración sincronizada.
