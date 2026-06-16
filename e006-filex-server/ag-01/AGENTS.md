# ag-01 — Fix CSV checkbox grid layout

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Goal

Fix the CSV viewer in filex so checkboxes are displayed in a compact grid instead of taking full row width.

## Problem

The CSV view (`templates/csv.html`) shows a table with checkboxes. Each checkbox is in its own row, taking the full width. This wastes screen space, especially on mobile. Checkboxes should be organized in a grid (e.g., 3-4 columns) so the user can select rows quickly.

## Filex location

All files are at `~/code/filex/`.

## What to do

1. Read `templates/csv.html` and `static/style.css` and `static/filex.js`
2. Understand how the checkbox table is rendered
3. Modify the HTML/CSS to display checkboxes in a CSS grid (not a table row per checkbox)
4. Test by running the filex server: `python3 ~/code/filex/serve_md.py`
5. Verify the grid layout works on desktop and mobile

## Constraints

- Do not break existing functionality (file browsing, markdown rendering, etc.)
- Keep the filex server running as a systemd service
- Only modify files in `~/code/filex/`

## Success criteria

- Checkboxes appear in a grid (3-4 columns)
- Row selection still works
- Page is usable on mobile
- No layout breaks on other pages (dir.html, md.html, code.html)
