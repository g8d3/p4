# ag-01 — Gemini Share Extractor

Owns and runs `bin/extract_gemini_share.py`.

## Usage

```bash
./bin/extract_gemini_share.py https://share.gemini.google/<id>
```

Outputs clean conversation text to stdout. Timing stats on stderr.

## Dependencies

- `agent-browser` (Node.js CLI) — handles headless Chrome automation

## Timing (benchmark)

| Method | Time |
|--------|------|
| Raw Chrome `--dump-dom` | ~30s |
| agent-browser (`open` + `wait --load networkidle` + `get text body`) | **~3.5s** |

## Inherits
- [../../AGENTS.md](../../AGENTS.md) — experiment scope
