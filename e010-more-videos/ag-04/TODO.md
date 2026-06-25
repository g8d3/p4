# TODO — quality improvements

## pdw (`bin/pdw`)

- [ ] **Refactor into functions**: `init()`, `ls()`, `ds()`, `vnc()`, `w()`, `rec()` instead of flat if/elif chain. Currently 340 lines of sequential logic.
- [ ] **Consistent error handling**: mix of `exit 1`, `|| true`, and silent failures. Standardize: all errors print to stderr and exit non-zero.
- [ ] **Argument validation**: `vnc rm` with no args gives cryptic error. Validate and show usage message before touching system.
- [ ] **Signal handling**: `wayvnc` processes orphaned if pdw exits uncleanly. Add trap or at least log PIDs for manual cleanup.
- [ ] **Sway not running detection**: `sway_alive()` called redundantly in every subcommand. Cache result or restructure flow.
- [ ] **No tests**: critical flows (init, vnc new --auth, w new) have no automated validation.
- [x] **Multi-display recording verified**: 2026-06-25 — two displays (HEADLESS-1 + HEADLESS-2) recorded simultaneously for 15s, both produced valid video content.
- [ ] **Bug: `pdw rec` name collision**: cuando dos procesos corren `pdw rec` sin nombre, ambos usan "recording" y pisan el raw. Fix: nombre único automático.

## filex (`~/code/filex/serve_md.py`)

- [ ] **Split `do_GET`**: 200+ line method handles static files, directories, markdown, CSV, code, video, fallback. Each should be a separate handler.
- [ ] **Streaming for large files**: `f.read()` loads entire file into memory. Use chunked serving for the text fallback too.
- [ ] **Configurable max inline size**: 10MB hardcoded. Move to env var or config file.
- [ ] **Rate limiting / DoS protection**: filex has no request limits.

## record.sh (`bin/record.sh`)

- [ ] **Sway startup reliability**: no retry logic if sway fails to start.
- [ ] **Output existence check**: doesn't verify HEADLESS-N exists before recording.
- [ ] **Lock-free concurrency**: relies on agents not running simultaneously.
