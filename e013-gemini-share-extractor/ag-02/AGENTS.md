# ag-02 — Video generation

Generates video variations from the extracted Gemini conversation.

## Formats

| Composition | Duration | Description |
|---|---|---|
| `talking-head` | 30s | Avatar explaining the debugging journey |
| `podcast` | 45s | Two-hosts podcast discussing lessons learned |
| `code-review` | 25s | Before/after code comparison |
| `timeline` | 20s | Animated timeline of events |

## Usage

```bash
./scripts/generate_videos.py              # generate all
./scripts/generate_videos.py talking-head # generate one
```

## Output

Videos in `./output/<name>.mp4` with audio narration (English TTS).

## Timing (actual benchmark)

| Composition | Render time | Size |
|---|---|---|
| talking-head | 29.3s | 2.6 MB |
| podcast | 58.4s | 2.8 MB |
| code-review | 20.7s | 1.3 MB |
| timeline | 30.1s | 1.0 MB |
| **Total** | **~2.3 min** | **7.7 MB** |

## Dependencies

- `remotion` (global npm package)
- `edge-tts` (pip install edge-tts)
- `ffmpeg`
