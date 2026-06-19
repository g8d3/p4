# ag-02: Interaction-to-Video Pipeline — Plan

## Goal

Convert OpenCode chat sessions into narrated vertical videos (608x1080, TikTok-ready).
Supports batch processing of 116+ sessions (22K+ message parts).

## Data Source

**SQLite database**: `~/.local/share/opencode/opencode.db` (1.1 GB)
- 793 sessions, 35,721 messages, 142,670 parts
- Query with `sqlite3` or `opencode db` command

**Tables**:
- `session`: id, title, directory, timestamps, cost, tokens
- `message`: id, session_id, timestamps, data (JSON)
- `part`: id, message_id, session_id, timestamps, data (JSON)

**Export command**: `opencode export <sessionID>` → clean JSON export

**Part types in data JSON**: `text`, `reasoning`, `tool`, `patch`, `step-start`, `step-finish`, `file`, `compaction`

**Audio format**: MP3 (edge-tts native format, not WAV)
```bash
edge-tts --voice es-CO-SalomeNeural --text "..." --write-media segment_01.mp3
```

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────┐
│  1. PARSE                                           │
│  Read all JSON parts → group by session → order by  │
│  messageID → extract type/text/timestamps           │
│  Output: session.json per session                   │
└──────────────────────┬──────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│  2. SCORE & SELECT                                  │
│  Rate each segment for "watchability":              │
│  - User question → score 10 (hook)                  │
│  - Tool execution + result → score 8 (action)       │
│  - Agent text response → score 7 (content)          │
│  - Patch/file edit → score 6 (code change)          │
│  - Reasoning → score 3 (show as indicator only)     │
│  - Step markers → score 1 (navigation)              │
│  Select top segments that fit target duration       │
│  Output: segments.json per session                  │
└──────────────────────┬──────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│  3. RENDER (3 modes for comparison)                 │
│                                                     │
│  Mode A: STYLED TERMINAL                            │
│  - Dark background (#1a1a2e)                        │
│  - Monospace font, syntax colors                    │
│  - User messages in blue, agent in green            │
│  - Tool commands with prompt $ prefix               │
│  - Reasoning as dimmed "thinking..." indicator      │
│  - Generated with Pillow → PNG → ffmpeg             │
│                                                     │
│  Mode B: TMUX CAPTURE                               │
│  - Capture actual terminal scrollback               │
│  - Requires tmux recording during session           │
│  - Most authentic look                              │
│                                                     │
│  Mode C: SIMPLE TEXT (current, improved)            │
│  - Text on solid color background                   │
│  - Less visual, but fast to generate                │
│                                                     │
│  All modes: 608x1080, 30fps, h264_vaapi             │
│  Duration per segment = TTS audio duration          │
└──────────────────────┬──────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│  4. NARRATE                                         │
│  For each segment, generate Spanish narration:      │
│  - "El usuario pregunta: [summary]"                 │
│  - "El agente encuentra [finding]"                  │
│  - "Ejecutando comando: [tool summary]"             │
│  - "Agent pensando..." (for reasoning, 1-2s)        │
│  Voice: es-CO-SalomeNeural (edge-tts)               │
│  Output: segment_N.wav per segment                  │
└──────────────────────┬──────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│  5. COMPOSE                                         │
│  ffmpeg concat all segment videos + narration       │
│  - Concat demuxer for video segments                │
│  - Mux with combined narration audio                │
│  - h264_vaapi encoding, AAC audio                   │
│  Output: final.mp4 per session                      │
└─────────────────────────────────────────────────────┘
```

## File Structure

```
ag-02/
├── AGENTS.md
├── PLAN.md                    # this file
├── parse.py                   # Step 1: Query SQLite, export session
├── score.py                   # Step 2: Score & select segments
├── render_terminal.py         # Step 3A: Styled terminal frames
├── render_simple.py           # Step 3C: Simple text frames
├── narrate.py                 # Step 4: TTS narration (MP3)
├── compose.py                 # Step 5: Video composition
├── pipeline.py                # Orchestrator: runs all steps
├── output/
│   └── {session_id}/
│       ├── session.json       # exported session data
│       ├── segments.json      # selected segments
│       ├── frames/            # rendered frame videos
│       ├── audio/             # TTS audio per segment (MP3)
│       ├── script.md          # narration script
│       └── final.mp4          # composed video
└── sample/                    # test data
```

## Rendering Details (Mode A: Styled Terminal)

Each frame shows:
```
┌──────────────────────────────────────┐
│  ● ● ●  OpenCode Session            │  ← header bar
├──────────────────────────────────────┤
│                                      │
│  $ user message here                 │  ← user (blue)
│                                      │
│  Agent: response text here           │  ← agent (green)
│                                      │
│  $ git status                        │  ← tool command (yellow)
│  On branch main                      │  ← tool output (gray)
│  nothing to commit                   │
│                                      │
│  ▸ Agent thinking... (258ms)         │  ← reasoning (dimmed)
│                                      │
└──────────────────────────────────────┘
```

Font: DejaVu Sans Mono (available at /usr/share/fonts/truetype/dejavu/)
Colors: user=#5b9bd5, agent=#70ad47, tool=#ffc000, reasoning=#666666

## Narration Script Style

Spanish, conversational, 60-90 seconds total:

```
[Hook - 5s]
"Hoy vemos cómo [user question summary]"

[Exploration - 30-40s]
"El agente revisa [finding 1], luego descubre [finding 2]"
"Ejecuta [tool command] y obtiene [result]"

[Analysis - 15-20s]
"Compara [option A] con [option B]"
"La diferencia clave es [insight]"

[Conclusion - 10s]
"La conclusión: [takeaway]"
```

## Model

DeepSeek V4 Flash for narration script generation (creative writing).
edge-tts es-CO-SalomeNeural for audio.

## Batch Processing

```bash
# Process one session
python3 pipeline.py --session ses_xxxx -o output/

# Process all sessions
python3 pipeline.py --all -o output/

# Process with specific render mode
python3 pipeline.py --session ses_xxxx --render terminal
python3 pipeline.py --session ses_xxxx --render simple
```

## Next Steps

1. Implement `parse.py` — read JSON parts, build session timeline
2. Implement `score.py` — rate segments, select top N
3. Implement `render_terminal.py` — styled terminal frames with Pillow
4. Implement `narrate.py` — generate narration script + TTS
5. Implement `compose.py` — ffmpeg concat + mux
6. Test with one small session end-to-end
7. Test with one large session
8. Batch process all 116 sessions
