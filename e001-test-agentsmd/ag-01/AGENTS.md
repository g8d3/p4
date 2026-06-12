# ag-01 — Creador de video

## Objetivo

Crear un video explicativo (9:16 vertical) sobre el sistema multiagente basado en archivos.

## Proceso (lo que funcionó)

### 1. Escribir guion

```
e001-test-agentsmd/ag-01/guion.md
```

Estructura: introducción (~23s), estructura (~37s), comparación (~24s), demo (~14s), cierre (~13s).

### 2. TTS

Usar `edge-tts` con voz colombiana, no espeak-ng:

```
edge-tts --voice es-CO-GonzaloNeural --text "..." --write-media audio.mp3
```

### 3. Preparar entorno

```
xset s off && xset -dpms
xscreensaver-command -exit
```

### 4. Captura de pantalla

```
ffmpeg -f x11grab -video_size 608x1080 -i :0.0+656,0 -framerate 15 ... /tmp/screen.mkv
```

### 5. Abrir terminal en la zona de grabación

```
xterm -geometry 46x45+656+0 -fa "Monospace" -fs 22 -e "bash demo.sh"
```

### 6. Generar subtítulos (estilo TikTok)

- Chunks de 2-4 palabras.
- Colores alternados: #FFFFFF, #FFD700, #00FF88, #FF6B6B, #6BCBFF.
- Posición: inferior (Alignment=2, MarginV=50).

### 7. Combinar

```
ffmpeg -i video.mkv -i audio.mp3 -vf "subtitles=subs.srt:force_style='FontName=Monospace,FontSize=17,MarginV=50,Alignment=2'" -shortest video.mp4
```

### 8. Verificar

- Revisar que no haya cuadros negros.
- Confirmar que el audio se escuche y coincida con la imagen.
- Revisar que los subtítulos se vean correctamente.
