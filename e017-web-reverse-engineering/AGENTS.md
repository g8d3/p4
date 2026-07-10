# e017 — Web Reverse Engineering

Generic web page reverse engineering tool using agent-browser.

## What it does

Given a URL, it:
1. Detects open browsers and reuses the best one
2. Records HAR per interaction (navigation + form submissions)
3. Extracts auth tokens from browser (Clerk, etc.)
4. Generates a clean report with all endpoints

## Usage

```bash
uv run --with httpx explorer.py <url>
uv run --with httpx explorer.py <url> --output report.md
```

## Architecture

```
explorer.py                # CLI entry point
core/
  explorer.py              # HAR recording + navigation + probing
  browser_manager.py       # Detect open browsers (CDP ports)
  functionalities.py       # Google search for site features (disabled)
  reporter.py              # Markdown report generation
  analyzer.py              # Legacy DOM analysis (unused)
```

## Chrome Wrapper

`/usr/local/bin/google-chrome` overrides Chrome with smart defaults:

- `--ozone-platform=headless` — no display needed
- `--use-gl=swiftshader` — software GL (stable, ~20% CPU)
- `--disable-extensions` — no ad blockers, no background scripts
- `--disable-service-worker` — no SW cache overhead
- `--remote-debugging-port=9222` — agent-browser connects here
- `--remote-allow-origins=*` — allows CDP WebSocket connections
- Profile: `~/profiles/chrome-main` (preserves login sessions)

### CPU benchmarks

| Page | CPU |
|------|-----|
| about:blank | 18% |
| higgsfield.ai | 19% |
| YouTube | 27% |
| Twitter/X | 95% (heavy SPA) |

### Why these flags?

- Extensions (Adblock, Bitwarden) register Service Workers that run in background
- Service Worker cache was 451MB, causing high CPU
- `--disable-extensions` + `--disable-service-worker` reduces CPU from 256% to 18%
- Vulkan was tested but caused 100%+ CPU on AMD Barcelo — SwiftShader is more stable

## Approach: Endpoint Discovery

The real API endpoints are NOT revealed by page loads. They are revealed when:
1. User fills a form (textbox, file upload)
2. User clicks an action button (Generate, Create, Send)
3. The form is submitted to the server

Strategy:
1. Snapshot page → find forms and action buttons (free, no API cost)
2. Record HAR
3. Fill form with minimal test data
4. Click submit
5. Capture the request/response in HAR
6. Analyze offline

This way, one request reveals the endpoint, auth pattern, and response format.

## Conventions

- All code in English
- Uses agent-browser CLI (not Playwright)
- Secrets from ~/.secrets/.env
- Output in markdown format
