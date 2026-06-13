# ag-03 — TTS segment generator

## Inherits
- `../../e000-fundamentals/AGENTS.md` — principles, no /tmp, timeouts
- `../AGENTS.md` — experiment scope

## Goal

Generate one MP3 audio file per dialogue line from the script.

## Task

Read `../ag-02/script.md`. For each dialogue line, create a separate MP3:

```
seg_001.mp3  — first line (persona A)
seg_002.mp3  — second line (persona B)
seg_003.mp3  — third line (persona A)
...
```

Use Colombian voices matching each persona:

```
edge-tts --voice es-CO-GonzaloNeural --text "..." --write-media seg_001.mp3  # persona A
edge-tts --voice es-CO-SalomeNeural --text "..." --write-media seg_002.mp3    # persona B
```

### Output

- `seg_NNN.mp3` files — one per dialogue line
- `timing.json` — mapping of segment number to speaker, text, and duration

### Completion

When finished, create `done.txt`:

```
touch done.txt
```

This triggers ag-04 via inotifywait.
