# pdw — Design Philosophy

## Overview

pdw (Puppet Display Wizard) is a CLI tool for managing virtual displays,
windows, and video production on Wayland headless environments.

## Core Principles

1. **Short commands** — agents type fast, minimize characters
2. **Consistent verbs** — every resource uses the same verb set
3. **Nested structure** — operations belong to their parent resource
4. **Two modes** — short (for agents) and full (for humans)

## Resources

```
Short   Full        Description
──────────────────────────────────────
ds      display     Virtual displays (HEADLESS-1, HEADLESS-2, ...)
w       window      Windows running on displays
vp      viewport    What's visible on screen
vnc     vnc         VNC remote access
```

## Verbs

```
Short   Full        CRUD        Description
─────────────────────────────────────────────────────────
new     create      Create      Create a resource
ls      list        Read        List multiple resources
show    show        Read        Show detail of one resource
mv      move        Update      Relocate a resource
set     set         Update      Modify properties
rm      remove      Delete      Delete a resource
start   start       —           Start/recording/activate
stop    stop        —           Stop/deactivate
claim   claim       —           Acquire exclusive access
release release     —           Release exclusive access
```

## Command Tree

```
pdw ds ls                    # list all displays
pdw ds new                   # create new display (reuses free)
pdw ds rm <display>          # remove display
pdw ds claim <display>       # claim display for this agent
pdw ds release <display>     # release claimed display
pdw ds rec <display> [sec]   # record display
pdw ds ss <display>          # screenshot display

pdw w ls                     # list all windows
pdw w new <display> <cmd>    # open window on display
pdw w mv <app> <display>     # move window to display
pdw w rm <app>               # close window

pdw vp read                  # read what's visible (accessibility tree)
pdw vp ss                    # screenshot viewport

pdw vnc ls                   # list VNC servers
pdw vnc new <display> [port] # start VNC server
pdw vnc rm <display>         # stop VNC server
```

## Three-Mode Syntax

### Mode 1: Resource-first (current, for agents)

```bash
pdw ds new H1
pdw ds ls
pdw w mv browser HEADLESS-2
pdw vp read
pdw ds rec HEADLESS-2 30
```

### Mode 2: Verb-first (alternative)

```bash
pdw c ds H1            # create display
pdw r ds               # list displays
pdw u w browser H2     # move window
pdw r vp               # read viewport
pdw s ds H1 30         # record display
```

### Mode 3: Full words (for humans, readable)

```bash
pdw display create H1
pdw display list
pdw window move browser HEADLESS-2
pdw viewport read
pdw display record HEADLESS-2 30
```

### CRUD Single-Letter Mapping

```
Letter  Full        Short       Description
─────────────────────────────────────────────
c       create      new         Create a resource
r       read        ls          List/show resources
u       update      mv/set      Modify properties
d       delete      rm          Delete a resource
s       start       start       Start/record
```

### Mode Detection

First argument determines mode:
- `ds`, `w`, `vp`, `vnc` → resource-first
- `c`, `r`, `u`, `d` → verb-first (Active Record style)
- `display`, `window`, `viewport` → full words

### Active Record Style (recommended)

Two valid formats — ALL positional OR ALL key=value. No mixing:

```bash
# All positional
pdw c ds H1 true              # name=H1, rec=true
pdw c w H2 chrome             # display=H2, cmd=chrome
pdw u ds H1 agent-1           # name=H1, owner=agent-1
pdw u ds H1                   # name=H1, owner= (release)

# All key=value
pdw c ds name=H1 rec=true
pdw c w display=H2 cmd=chrome
pdw u ds name=H1 owner=agent-1
pdw u ds name=H1 owner=
```
```

Benefits:
- Consistent parsing: everything is key=value
- Self-documenting: `name=H1` is clearer than positional `H1`
- Extensible: add new properties without breaking existing commands
- No positional args after resource type

### Mapping Table

```
Resource-first      Verb-first       Full words
──────────────────────────────────────────────────
pdw ds c H1         pdw c ds H1      pdw display create H1
pdw ds r            pdw r ds         pdw display list
pdw ds d H1         pdw d ds H1      pdw display remove H1
pdw ds mv H1 o=x    pdw u ds H1 o=x  pdw display set H1 owner=x
pdw ds rec H1 30    pdw s ds H1 30   pdw display record H1 30

pdw w c H2 cmd      pdw c w H2 cmd   pdw window create H2 cmd
pdw w r             pdw r w          pdw window list
pdw w d chrome      pdw d w chrome   pdw window remove chrome
pdw w mv a H2       pdw u w a H2     pdw window move a H2

pdw vp r            pdw r vp         pdw viewport read
pdw vp ss           pdw s vp         pdw viewport screenshot

pdw vnc r           pdw r vnc        pdw vnc list
pdw vnc c H2 5900   pdw c vnc H2 5900 pdw vnc create H2 5900
pdw vnc d H2        pdw d vnc H2     pdw vnc remove H2
```

## Verb Applicability

Not every verb applies to every resource. Empty cells mean "not applicable":

```
Resource    new   ls   mv   rm   read   start   claim
──────────────────────────────────────────────────────
ds          ✓     ✓    -    ✓    ✓      ✓       ✓
w           ✓     ✓    ✓    ✓    -      -       -
vp          -     -    -    -    ✓      -       -
vnc         ✓     ✓    -    ✓    -      ✓       -
```

## Design Decisions

### Why nested under `ds`?

`rec`, `claim`, `release` are operations ON displays, not standalone
resources. They belong under `ds`:

```
pdw ds claim H1      # not: pdw claim H1
pdw ds release H1    # not: pdw release H1
pdw ds rec H1 30     # not: pdw rec H1 30
```

### Why `vp` instead of `viewport`?

Same pattern as `ds` and `w`: short alias for fast typing.
Full name available in full mode.

### Why two modes?

- Agents need speed: `pdw ds new` (7 chars)
- Humans need readability: `pdw display create` (19 chars)
- Both are valid, same behavior

## Escaping Rules

### Positional mode (compact, for agents)
No escaping needed — arguments are already separated by spaces:
```bash
pdw c ds H1 true           # name=H1, rec=true
pdw c w H2 chrome          # display=H2, cmd=chrome
```

### Key=value mode (verbose, for humans)
Values with spaces must be quoted:
```bash
pdw c w H2 cmd="google-chrome --ozone-platform=wayland"
pdw c w H2 title="It's a test"
pdw u ds H1 owner="agent-1"
```

### Empty value (clear)
`key=` means set to empty/clear:
```bash
pdw u ds H1 owner=         # release: clear owner
pdw u ds H1 rec=           # stop recording
```

### No shell expansion
pdw does NOT expand `$`, `` ` ``, `~`, or `!` inside values:
```bash
pdw c w H2 cmd="echo $HOME"     # $HOME is literal, not expanded
pdw c w H2 cmd='echo `date`'    # backticks are literal
pdw c w H2 path="~/file.txt"    # ~ is literal
```

### Nested quotes
Use different quote types:
```bash
pdw c w H2 cmd='echo "hello"'   # single quotes around, double inside
pdw c w H2 title="It's a test"  # double quotes around, single inside
```

### Special characters in URLs
Quote the entire value:
```bash
pdw c w H2 url="https://example.com/path?q=1&r=2&lang=en"
pdw c w H2 url='https://example.com/search?q="hello world"'
```

### Parsing logic (Python)
```python
def parse_args(args):
    positional = []
    kwargs = {}
    for arg in args:
        if '=' in arg:
            k, v = arg.split('=', 1)
            kwargs[k] = v  # empty string if value is empty
        else:
            positional.append(arg)
    return positional, kwargs

# Examples:
parse_args(['ds', 'H1', 'rec=true'])
# → (['ds', 'H1'], {'rec': 'true'})

parse_args(['ds', 'H1', 'owner='])
# → (['ds', 'H1'], {'owner': ''})

parse_args(['w', 'H2', 'cmd=google-chrome --flag'])
# → (['w', 'H2'], {'cmd': 'google-chrome --flag'})
```

## Future: Unified key=value Format

All commands should accept key=value pairs for flexibility:

```bash
# Current
pdw ds claim H1
pdw ds release H1
pdw w new H2 google-chrome --ozone-platform=wayland

# Future (unified key=value)
pdw ds set H1 owner=agent-1          # claim
pdw ds set H1 owner=                 # release
pdw w new H2 cmd=google-chrome ozone=wayland profile="Profile 1"
pdw ds rec H1 duration=30 output=video.mp4
pdw vnc new H2 port=5900 auth=true
```

Benefits:
- Consistent parsing across all commands
- Extensible without adding new verbs
- Self-documenting: `owner=agent-1` is clearer than `claim H1`

## SQLite Database

All state, config, and metrics stored in a single SQLite database.

### Location
```
$OUTDIR/pdw.db
```

### Schema

```sql
-- Configuration (separated from logic)
CREATE TABLE config (
  key TEXT PRIMARY KEY,
  value TEXT,
  category TEXT  -- 'display', 'chrome', 'encoding', 'tts'
);

-- Sessions (each production run)
CREATE TABLE sessions (
  id INTEGER PRIMARY KEY,
  inicio TIMESTAMP,
  fin TIMESTAMP,
  status TEXT,  -- 'active', 'completed', 'error'
  agent TEXT    -- 'consumer', 'producer'
);

-- Steps (each command executed)
CREATE TABLE steps (
  id INTEGER PRIMARY KEY,
  session_id INTEGER,
  tipo TEXT,         -- 'open', 'scroll', 'record', 'narrate', 'encode'
  comando TEXT,
  parametros TEXT,
  inicio TIMESTAMP,
  fin TIMESTAMP,
  duracion_ms INTEGER,
  exit_code INTEGER,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Metrics (resource usage, sampled every 2s)
CREATE TABLE metrics (
  id INTEGER PRIMARY KEY,
  session_id INTEGER,
  timestamp TIMESTAMP,
  cpu_percent REAL,
  gpu_percent REAL,
  ram_mb REAL,
  dma_active INTEGER,
  disk_write_mb REAL,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Videos (produced output)
CREATE TABLE videos (
  id INTEGER PRIMARY KEY,
  session_id INTEGER,
  titulo TEXT,
  archivo TEXT,
  duracion_seg REAL,
  tamanio_bytes INTEGER,
  resolucion TEXT,
  codec TEXT,
  fecha TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Chunks (individual segments within a video)
CREATE TABLE chunks (
  id INTEGER PRIMARY KEY,
  video_id INTEGER,
  orden INTEGER,
  url TEXT,
  seccion TEXT,
  duracion_plan INTEGER,
  duracion_real INTEGER,
  scroll_px INTEGER,
  FOREIGN KEY (video_id) REFERENCES videos(id)
);

-- Ideas (consumer → producer queue)
CREATE TABLE ideas (
  id INTEGER PRIMARY KEY,
  tema TEXT,
  urls TEXT,
  chunks_plan TEXT,
  narracion_sketch TEXT,
  tono TEXT,
  status TEXT,        -- 'pending', 'processing', 'completed', 'error'
  creado TIMESTAMP,
  procesado TIMESTAMP
);

-- Commands (analytics)
CREATE TABLE commands (
  id INTEGER PRIMARY KEY,
  session_id INTEGER,
  binario TEXT,
  comando TEXT,
  duracion_ms INTEGER,
  exit_code INTEGER,
  timestamp TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

### CLI Commands

```bash
pdw db init              # create database and tables
pdw db query "SELECT..." # run SQL query
pdw db metrics           # show resource usage
pdw db analytics         # show command duration stats
pdw db export            # export to CSV
pdw db import <file.csv> # import from CSV
```

### Example Queries

```sql
-- Average duration by step type
SELECT tipo, AVG(duracion_ms), MIN(duracion_ms), MAX(duracion_ms)
FROM steps GROUP BY tipo;

-- CPU usage during recording
SELECT timestamp, cpu_percent, gpu_percent, dma_active
FROM metrics WHERE session_id = 1 ORDER BY timestamp;

-- Video production efficiency
SELECT v.titulo, SUM(c.duracion_real), v.duracion_seg,
       ROUND(v.duracion_seg / SUM(c.duracion_real), 2) as ratio
FROM videos v JOIN chunks c ON v.id = c.video_id GROUP BY v.id;

-- Slowest commands
SELECT binario, comando, duracion_ms
FROM commands ORDER BY duracion_ms DESC LIMIT 10;
```

## Presets

Use SQL's native features instead of custom preset system.

### Views (preset for READ)

```sql
-- Create view as preset
CREATE VIEW v_displays_with_windows AS
SELECT d.name, d.resolution, w.app_id, w.pid
FROM displays d
LEFT JOIN windows w ON d.name = w.display;

-- Usage
pdw r ds view=displays_with_windows
pdw r w view=active_windows
```

### SQL Templates (preset for CREATE/UPDATE/DELETE)

Store as path-based relational AST (no JSON):

```sql
CREATE TABLE ast_nodes (
  id INTEGER PRIMARY KEY,
  preset_id INTEGER,
  path TEXT,        -- 'i.t', 'i.c.0', 'i.v.0'
  type TEXT,        -- 'stmt', 'id', 'str', 'param'
  value TEXT
);

-- Short path notation:
-- i = insert, s = select, u = update, d = delete
-- t = table, c = columns, v = values, w = where
-- .0, .1, .2 = array index

-- Chrome window preset
INSERT INTO ast_nodes VALUES
(1, 1, 'i.t', 'id', 'windows'),
(2, 1, 'i.c.0', 'id', 'display'),
(3, 1, 'i.c.1', 'id', 'cmd'),
(4, 1, 'i.c.2', 'id', 'ozone'),
(5, 1, 'i.c.3', 'id', 'port'),
(6, 1, 'i.v.0', 'param', 'display'),
(7, 1, 'i.v.1', 'str', 'chrome'),
(8, 1, 'i.v.2', 'str', 'wayland'),
(9, 1, 'i.v.3', 'str', '9222');

-- Read preset with JOIN
INSERT INTO ast_nodes VALUES
(10, 2, 's.c.0', 'id', 'd.name'),
(11, 2, 's.c.1', 'id', 'd.resolution'),
(12, 2, 's.c.2', 'id', 'w.app_id'),
(13, 2, 's.f', 'id', 'displays d'),
(14, 2, 's.j.0', 'id', 'LEFT JOIN windows w ON d.name = w.display');
```

### Debug improvements

```sql
-- Add depth and parent for tree display
ALTER TABLE ast_nodes ADD COLUMN depth INTEGER DEFAULT 0;
ALTER TABLE ast_nodes ADD COLUMN parent_id INTEGER;

-- View that reconstructs full tree
CREATE VIEW v_ast_tree AS
SELECT 
  n.id,
  n.preset_id,
  REPEAT('  ', n.depth) || n.path as indent_path,
  n.type,
  n.value
FROM ast_nodes n
ORDER BY n.preset_id, n.id;

-- Pretty-print a preset
SELECT * FROM v_ast_tree WHERE preset_id = 1;
```

Output:
```
1  1  i            stmt    INSERT
2  1  i.t          id      windows
3  1  i.c.0        id      display
4  1  i.c.1        id      cmd
5  1  i.v.0        param   {display}
6  1  i.v.1        str     chrome
```

### Storage efficiency improvements

```sql
-- Use integers for types (lookup table)
CREATE TABLE ast_types (
  id INTEGER PRIMARY KEY,
  code TEXT,        -- 'stmt', 'id', 'str', 'param'
  description TEXT
);

INSERT INTO ast_types VALUES
(1, 'stmt', 'statement type'),
(2, 'id', 'identifier'),
(3, 'str', 'string literal'),
(4, 'param', 'placeholder parameter');

-- Reference by integer
ALTER TABLE ast_nodes ADD COLUMN type_id INTEGER;
-- type_id=2 instead of type='id'

-- Use shorter path encoding
-- 'i.t' instead of 'insert.table'
-- 'i.c.0' instead of 'insert.columns.0'
```

### Query examples

```sql
-- Find all INSERT presets that use 'chrome'
SELECT DISTINCT preset_id FROM ast_nodes
WHERE path LIKE 'i.v.%' AND value = 'chrome';

-- List all columns for a preset
SELECT value FROM ast_nodes
WHERE preset_id = 1 AND path LIKE 'i.c.%'
ORDER BY path;

-- Modify a preset value
UPDATE ast_nodes SET value = '9333'
WHERE preset_id = 1 AND path = 'i.v.3';

-- Count presets by operation type
SELECT SUBSTR(path, 1, 1) as op, COUNT(DISTINCT preset_id)
FROM ast_nodes
GROUP BY op;
```

## Verification

Every write operation must be verified.

### Write flow

```
1. Execute command (e.g., create display)
2. Verify it succeeded (check sway)
3. Update database
4. Return success/failure
```

### Verification methods

| Operation | Verification |
|-----------|--------------|
| Create display | `swaymsg -t get_outputs` → check if name exists |
| Delete display | `swaymsg -t get_outputs` → check if name gone |
| Create window | `swaymsg -t get_tree` → check if app_id exists |
| Delete window | `swaymsg -t get_tree` → check if app_id gone |
| Start recording | Check if wf-recorder process exists |
| Stop recording | Check if file exists and size > 0 |
| Start VNC | Check if wayvnc process exists |
| Stop VNC | Check if process gone |

### Error handling

```bash
pdw c ds H1
  │
  ├─1. Execute: swaymsg create_output
  │
  ├─2. Verify: swaymsg -t get_outputs | grep H1
  │     ├─ success → continue
  │     └─ failure → skip DB update, return error
  │
  ├─3. Update DB: INSERT INTO displays VALUES (...)
  │
  └─4. Return: "created H1" or "failed to create H1"
```

### Retry logic

```bash
pdw c ds H1
  │
  ├─ attempt 1: create output → verify → failed
  │
  ├─ wait 1s
  │
  ├─ attempt 2: create output → verify → success
  │
  └─ update DB
```

## State Synchronization

The database must stay in sync with actual system state. Three strategies:

### Strategy 1: On-demand (lazy sync)

Check reality when a command is executed:

```bash
pdw r ds
# → first: query sway for actual displays
# → then: compare with database
# → update database if different
# → return results
```

Pros:
- Simple to implement
- No background processes
- Database always correct when queried

Cons:
- Drift between queries
- First query after drift is slower

### Strategy 2: Periodic (polling)

Background process checks every N seconds:

```bash
pdw sync start --interval 5    # check every 5 seconds
pdw sync stop
pdw sync status                # last sync time, drift count
```

Pros:
- Database always fresh
- Can detect drift even when no commands running

Cons:
- Wastes resources (CPU, I/O)
- Still has drift between polls
- Background process to manage

### Strategy 3: Event-driven (reactive)

Listen to sway events, update DB immediately:

```bash
pdw sync start --watch         # listen to sway events
pdw sync stop
```

Sway events:
```
output created    → INSERT INTO displays
output removed    → DELETE FROM displays
window created    → INSERT INTO windows
window moved      → UPDATE windows SET display=...
window closed     → DELETE FROM windows
```

Pros:
- Database always in sync
- No polling waste
- Immediate reaction to changes

Cons:
- More complex to implement
- Need to handle event reconnection
- May miss events if connection drops

### Recommended: Hybrid approach

```
On-demand (primary):
  Every pdw command checks reality first
  → simple, reliable, no background process

Event-driven (optional):
  If user wants real-time sync, enable watcher
  → pdw sync start --watch
  → runs in background, updates DB on sway events

Periodic (fallback):
  If event-driven fails, fall back to polling
  → pdw sync start --interval 10
```

### Sync Direction

User decides which is source of truth:

**DB → System (push)**: Database is truth, system conforms
```bash
pdw sync push
# DB says H1 should exist → create H1 in sway
# DB says H2 should not exist → delete H2 from sway
# DB says chrome on H1 → launch chrome on H1
```

**System → DB (pull)**: System is truth, database conforms
```bash
pdw sync pull
# System has H1, H2, H3 → update DB to match
# System has chrome on H2 → update DB
# DB had H4 which no longer exists → remove from DB
```

**Auto (default)**: Detect which changed, sync accordingly
```bash
pdw sync auto
# Compare DB vs system
# If DB has more → push (create missing in system)
# If system has more → pull (add missing to DB)
# If both changed → conflict, ask user
```

### Sync flow

```bash
pdw r ds
  │
  ├─1. Query sway: swaymsg -t get_outputs
  │
  ├─2. Query DB: SELECT * FROM displays
  │
  ├─3. Compare:
  │     - In sway but not in DB → INSERT
  │     - In DB but not in sway → DELETE (or mark stale)
  │     - In both → verify properties match
  │
  ├─4. Update DB if different
  │
  └─5. Return results
```

### Drift detection

```sql
-- Find displays in DB but not in system
SELECT d.name FROM displays d
LEFT JOIN actual_displays a ON d.name = a.name
WHERE a.name IS NULL;

-- Find displays in system but not in DB
SELECT a.name FROM actual_displays a
LEFT JOIN displays d ON a.name = d.name
WHERE d.name IS NULL;
```

## Future: REPL Mode

```bash
pdw                     # start interactive mode
pdw> ds new
HEADLESS-3
pdw> w ls
  APP        PID    OUTPUT
  google-chrome  1234  HEADLESS-2
pdw> vp read
  [accessibility tree]
pdw> exit
```

## Future: Backend + Frontend

```
pdw serve               # start API server (port 8080)
pdw tui                 # start TUI interface
pdw web                 # start web interface
```
