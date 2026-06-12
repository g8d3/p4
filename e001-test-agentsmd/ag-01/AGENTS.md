# ag-01 — Video creator

## Goal

Create an explanatory video (9:16 vertical) about the file-based multi-agent system.

## Process (what worked)

### 1. Write script

```
e001-test-agentsmd/ag-01/script.md
```

Structure: intro (~23s), structure (~37s), comparison (~24s), demo (~14s), closing (~13s).

### 2. TTS

Use `edge-tts` with Colombian voice, not espeak-ng:

```
edge-tts --voice es-CO-GonzaloNeural --text "..." --write-media audio.mp3
```

### 3. Prepare environment

```
xset s off && xset -dpms
xscreensaver-command -exit
```

### 4. Screen capture

```
ffmpeg -f x11grab -video_size 608x1080 -i :0.0+656,0 -framerate 15 ... /tmp/screen.mkv
```

### 5. Open terminal in capture region

```
xterm -geometry 46x45+656+0 -fa "Monospace" -fs 22 -e "bash demo.sh"
```

### 6. Generate subtitles (TikTok style)

- 2-4 word chunks.
- Alternating colors: #FFFFFF, #FFD700, #00FF88, #FF6B6B, #6BCBFF.
- Bottom position (Alignment=2, MarginV=50).

### 7. Combine

```
ffmpeg -i video.mkv -i audio.mp3 -vf "subtitles=subs.srt:force_style='FontName=Monospace,FontSize=17,MarginV=50,Alignment=2'" -shortest video.mp4
```

### 8. Verify

- Check for black frames.
- Confirm audio is audible and matches the image.
- Verify subtitles render correctly.
