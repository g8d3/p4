# e006 — Filex server improvements

**Goal**: Improve the filex web server's UI and functionality.

**Filex location**: `~/code/filex/`

## Agents

- **ag-01**: Fix checkbox grid layout in CSV viewer — checkboxes currently take full row width instead of being displayed in a compact grid

## Infrastructure

- Python Flask server (`serve_md.py`)
- Jinja2 templates in `templates/`
- Static files in `static/`
- Systemd service: `filex.service`
