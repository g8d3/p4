# ag-02 — Interaction-to-video agent

**Goal**: Convert human-agent chat logs into narrated video content. Takes conversation logs, extracts key moments, structures them into a narrative, and produces a TikTok-ready video.

## What this agent does

1. Reads a chat log (from opencode, terminal, or exported conversation)
2. Parses: timestamps, speakers, messages, decisions, conclusions
3. Structures into narrative arc: intro → development → conclusion
4. Generates narration with edge-tts
5. Produces final video with text overlays and narration

## Input formats

The agent should handle these log formats:

### OpenCode chat log
```
[2026-06-17 10:00:00] User: necesitamos un TTS en tiempo real
[2026-06-17 10:00:15] Agent: déjame revisar qué tenemos disponible...
[2026-06-17 10:01:00] Agent: edge-tts ya está instalado, version 7.2.8
```

### Terminal session log
```bash
script -t 2>timing.log -f output.log
# ... session ...
exit
```

### Manual transcript
```markdown
## Conversation: 2026-06-17
- User: [question]
- Agent: [response with findings]
```

## Narrative structure

Split the conversation into segments:

| Segment | Content | Visual |
|---------|---------|--------|
| **Hook** (0-5s) | The problem/question | Text on screen |
| **Exploration** (5-60s) | Research process, findings | Screen recording + narration |
| **Analysis** (60-90s) | Comparison, tables, graphs | matplotlib PNGs + narration |
| **Conclusion** (90-120s) | Key takeaway | Summary text + narration |

## Output

1. `narration.mp3` — edge-tts audio (MP3 is edge-tts native format)
2. `script.md` — the narration script with timestamps
3. `segments/` — individual segment clips
4. `final.mp4` — composed video (audio muxed as AAC)

## Narration generation

Read the conversation, extract key insights, write a script in Spanish:

```bash
# edge-tts outputs MP3 natively — no WAV intermediate needed
edge-tts --voice es-CO-SalomeNeural --text "Hoy vamos a explorar..." --write-media segment_01.mp3
```

## Video composition

```bash
# Combine segments with narration (MP3→AAC automatic in MP4 mux)
ffmpeg \
  -i segment_01.mp4 -i segment_02.mp4 -i segment_03.mp4 \
  -i narration.mp3 \
  -filter_complex "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]" \
  -map "[v]" -map 3:a \
  -c:v h264_vaapi -c:a aac \
  final.mp4
```

## Text overlays

```bash
# Add text to video frames
ffmpeg -i input.mp4 \
  -vf "drawtext=text='TTS Comparison':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=50" \
  output.mp4
```

## Model

Use DeepSeek V4 Flash. This agent needs speed and creative writing, not deep reasoning.

## Inherits

- [../AGENTS.md](../AGENTS.md) — experiment scope, shared infrastructure
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, GPU encoding
