# ag-01 — Higgsfield Video Generator

Owns `generate_video.py` — a script to generate videos using the Higgsfield API.

## Usage

```bash
export HF_API_KEY="your-api-key"
export HF_API_SECRET="your-api-secret"
python generate_video.py
```

### With the project venv

```bash
source ../../.venv/bin/activate
python generate_video.py
```

## Dependencies

- `higgsfield-client` (v0.1.0) — Python SDK for Higgsfield API
- `httpx` — HTTP client (dependency of higgsfield-client)

## Performance

### Problem

`agent-browser` launches Chrome with `--enable-unsafe-swiftshader` by default,
which emulates GPU in software. This consumes ~160% CPU and heats the machine.

### Solution: manual Chrome with real GPU

Launch Chrome manually with AMD GPU acceleration, then connect agent-browser via `--auto-connect`:

```bash
# Start Chrome once with real GPU
google-chrome \
  --headless=new \
  --no-sandbox \
  --use-gl=angle \
  --use-angle=gl-egl \
  --enable-gpu \
  --disable-software-rasterizer \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/hf-chrome-profile \
  --no-first-run --no-default-browser-check \
  "about:blank" \
  >/dev/null 2>&1 &

# Wait for it to start
sleep 2

# Use agent-browser as usual, connecting via --auto-connect
agent-browser --auto-connect open "https://higgsfield.ai/ai/video"
agent-browser --auto-connect snapshot -i
# ... etc ...
```

**Result**: ~4% CPU instead of ~160%.

### Cleanup

When done, close everything:

```bash
agent-browser close --all        # close agent-browser sessions
pkill -f "remote-debugging-port=9222"  # kill manual Chrome
```

## Trail
- [trail.md](trail.md) — session history

## Inherits
- [../AGENTS.md](../AGENTS.md) — experiment context, endpoints, auth
