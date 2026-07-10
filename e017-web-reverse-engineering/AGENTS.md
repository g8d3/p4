# e017 — Web Reverse Engineering

Generic web page reverse engineering tool using agent-browser.

## What it does

Given a URL, it:
1. Detects open browsers and reuses the best one
2. Searches Google for the site's main features
3. Analyzes DOM structure (frameworks, components, patterns)
4. Intercepts all network traffic (API calls, websockets)
5. Probes every interactive element (click, fill, hover)
6. Generates a complete Markdown report

## Usage

```bash
uv run --with httpx reverse.py https://higgsfield.ai
uv run --with httpx reverse.py https://higgsfield.ai --output report.md
uv run --with httpx reverse.py https://higgsfield.ai --browser 9222  # force specific port
```

## Architecture

```
re.py                      # CLI entry point
core/
  browser_manager.py       # Detect & manage open browsers (CDP ports)
  functionalities.py       # Google search for site features
  analyzer.py              # DOM + network + interaction analysis
  reporter.py              # Markdown report generation
```

## Conventions

- All code in English
- Uses agent-browser CLI (not Playwright)
- Secrets from ~/.secrets/.env
- Output in markdown format
