# ag-03 — TTS generator

## Goal

Generate TTS audio for both personas (A and B) using the script from ag-02.

## Task

Read `script.md` from `../ag-02/script.md`. Split the dialogue into two audio files:
- `persona_a.mp3` — all lines from persona A
- `persona_b.mp3` — all lines from persona B

Use `edge-tts` with Colombian voices:

```
edge-tts --voice es-CO-GonzaloNeural --text "..." --write-media persona_a.mp3
edge-tts --voice es-CO-SalomeNeural --text "..." --write-media persona_b.mp3
```

### Rules

- Generate full audio for each persona in one call (concatenate all A lines together, all B lines together).
- Keep track of the timing: note the total duration of each persona's audio.
- Write the timing info to `timing.md` for ag-04 to use.

### Files

- `persona_a.mp3` — TTS audio for persona A
- `persona_b.mp3` — TTS audio for persona B
- `timing.md` — duration and sequence notes

### Dependencies

ag-04 needs your audio files and timing info.
