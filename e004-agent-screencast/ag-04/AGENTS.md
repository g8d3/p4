# ag-04 — FileX CSV/table renderer

## Model
`opencode-go/deepseek-v4-flash`

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, self-wake, sudo in separate window

## Goal

Add CSV rendering as HTML tables to FileX (`~/code/filex/`), and improve handling of more file types.

## Context

FileX is a Python HTTP server (`serve_md.py`) serving `~/code/` on port 9090. It uses:
- highlight.js for code
- marked.js for markdown
- TEXT_EXTENSIONS set for code view
- Fallback to `application/octet-stream` (download) for unknown types

Current problem: clicking a `.csv` file triggers download instead of showing the table inline.

## Task

### 1. Read the codebase
Read `~/code/filex/serve_md.py`, `~/code/filex/templates/`, and `~/code/filex/AGENTS.md` to understand the architecture.

### 2. Add CSV rendering
- Add `.csv` to `TEXT_EXTENSIONS` in `serve_md.py`
- Create `templates/csv.html` that uses **PapaParse** CDN (`https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.4.1/papaparse.min.js`) to parse CSV client-side and render as an HTML table
- Add a `render_csv()` function in `serve_md.py` that passes the raw CSV text to the template
- Add `.csv` → `"csv"` mapping in `LANG_MAP` (use plaintext or csv)
- Add routing in `do_GET()` for `.csv` before the TEXT_EXTENSIONS fallback

### 3. Add more file types to render inline
Add these to TEXT_EXTENSIONS and LANG_MAP:
- `.csv` → csv (PapaParse table)
- `.json` → json (highlight.js supports it)
- `.toml` → plaintext
- `.yaml` / `.yml` → yaml
- `.xml` → xml
- `.log` → plaintext
- `.env` → plaintext
- `.gitignore` → plaintext (already should work)

### 4. Test
```bash
# Verify CSV renders as HTML (not download)
curl -s -o /dev/null -w "%{http_code} %{content_type}" http://localhost:9090/path/to/test.csv
# Should return 200 text/html, not application/octet-stream
```

### 5. Restart FileX
```bash
systemctl --user restart filex
```

### 6. Document
Update `~/code/filex/AGENTS.md` with the new CSV template and extensions added.

## Self-command
ALL commands: `>/dev/null 2>&1 &`. Self-wake. Never synchronous.
