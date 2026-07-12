# hf CLI — Design Discussion (2026-07-11)

## Proposed Structure

```
hf create image "<prompt>"                      # basic
hf create image --har "<prompt>"                # with HAR capture
hf create image --har /path/to/file.har "<prompt>"  # custom HAR path
hf create image --model <name> "<prompt>"       # model override (default: seedream_v4_5)
hf create image --cdp <port> "<prompt>"         # explicit CDP port (default: 9222)
hf create image --no-unlimited "<prompt>"       # skip Unlimited toggle
```

## Future Actions

```
hf create video "<prompt>"
hf list jobs
hf status <job-id>
hf create image --batch <n> "<prompt>"          # generate multiple at once
```

## Flags Matrix

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | `seedream_v4_5` | Model name |
| `--cdp` | `9222` | Chrome DevTools Protocol port |
| `--har` | off | HAR file path (auto-path if flag alone) |
| `--no-unlimited` | off | Disable Unlimited toggle |
| `--batch` | 1 | Number of images to generate |
| `--aspect` | `9:16` | Aspect ratio |
| `--quality` | `basic` | Quality preset |

## Implementation Notes

- Reuses `sway-vnc-chrome` / `sway-chrome` for environment
- All tricks discovered during initial automation:
  - prompt: `textarea.value = ''` + `dispatchEvent('input')` + `keyboard type`
  - unlimited: native click on `[role=switch]`
  - generate: native JS `document.getElementById('image-submit-button').click()`

## Next Steps

- [ ] Implement all flags
- [ ] Add job status polling
- [ ] Extract HAR and auto-generate curl commands for API-only usage
