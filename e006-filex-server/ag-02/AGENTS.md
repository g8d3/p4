# ag-02 — CRUD completo en filex (API + GUI)

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules
- [../AGENTS.md](../AGENTS.md) — experiment scope

## Goal

Add full CRUD capabilities to filex: create files/directories, upload files, and delete them, both via API and GUI buttons.

## Motivation

Users need to upload transcriptions (text/JSON files) into new directories directly from the browser. Currently filex only supports:
- `GET` — read files and directories
- `POST` — overwrite existing files (edit)

Missing: creating new files, creating new directories, deleting files/dirs, and GUI buttons for all of these.

## What was implemented

### Backend (`serve_md.py`)

#### `do_PUT(self)` — Create/overwrite files
- Reads request body as raw bytes
- Creates parent directories automatically via `os.makedirs(parent, exist_ok=True)`
- Returns `201 Created` for new files, `200 OK` for overwrites
- Same path traversal protection as `do_GET`/`do_POST`

#### `do_MKCOL(self)` — Create directories (WebDAV standard)
- Creates directory via `os.makedirs`
- Returns `405 Method Not Allowed` if directory already exists
- Returns `201 Created` on success

#### `do_DELETE(self)` — Delete files and directories
- Deletes files via `os.remove`, directories via `shutil.rmtree`
- Returns `404` if not found, `200` on success

#### `?raw=1` query param
- Added to `.md` and text/code file serving paths
- Returns raw file content instead of HTML wrapper, with correct MIME types:
  - `.json` → `application/json`
  - `.csv` → `text/csv`
  - `.md` → `text/markdown`
  - others → `text/plain`

### GUI (`templates/toolbar.html` + `static/filex.js` + `static/style.css`)

#### Toolbar buttons
- **+📁** (`createDir`) — hidden by default, shown on directory pages. Prompts for name, sends MKCOL, refreshes modal.
- **+📄** (`uploadFile`) — hidden by default, shown on directory pages. Triggers file picker, reads as ArrayBuffer, sends PUT, refreshes modal.
- **🗑** (`deleteCurrent`) — always visible. Confirms then sends DELETE on current path, redirects to parent directory.

#### Directory modal
- Each row now has a **🗑** delete button (calls `deleteItem(path)`)
- New "Acción" column in table header
- Delete buttons are semi-transparent by default, fully opaque on hover with red background
- All colspan values updated from 3 → 4

### Files modified
- `~/code/filex/serve_md.py` — added `do_PUT`, `do_MKCOL`, `do_DELETE`, `?raw=1` in md/code paths, `showFileActions()` call in dir page
- `~/code/filex/templates/toolbar.html` — added buttons + file input + Acción column header
- `~/code/filex/static/filex.js` — added `createDir()`, `uploadFile()`, `deleteItem()`, `deleteCurrent()`, `showFileActions()`, `getCurrentDir()`
- `~/code/filex/static/style.css` — added `.action-col`, `.del-btn` styles

## Security
- Same path traversal protection as existing endpoints
- Delete prompts for confirmation before sending request
- Directory create/upload only within root

## Testing
```bash
curl -X MKCOL http://localhost:9090/nueva-carpeta
curl -X PUT -d "contenido" http://localhost:9090/nueva-carpeta/archivo.txt
curl -s "http://localhost:9090/nueva-carpeta/archivo.txt?raw=1"
curl -X DELETE http://localhost:9090/nueva-carpeta/archivo.txt
curl -X DELETE http://localhost:9090/nueva-carpeta
```

## Constraints
- Does not break existing GET/POST functionality
- Server runs via systemd after changes
