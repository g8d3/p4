# pkill -f Hang Diagnostic

## Root Cause

`pkill -f "pattern"` hangs (or kills the parent shell) because `-f` matches against the **full cmdline** of every process in `/proc/*/cmdline`. The parent shell's cmdline contains the entire command being executed — including the `pkill` invocation itself. So `pkill -f` always matches and kills its own parent process.

### Reproduction

```
# This hangs because pkill matches timeout's cmdline:
timeout 5 pkill -9 -f "nonexistent_pattern_xyz_123"

# The parent process cmdline IS the command:
cat /proc/$PPID/cmdline | tr '\0' ' '
# → "timeout 5 pkill -9 -f nonexistent_pattern_xyz_123"
# ^^^ Contains the pattern! pkill kills it.
```

### Why it happens

1. User runs: `pkill -f "some_pattern"`
2. pkill iterates `/proc/*/cmdline` for all 311 processes
3. Parent shell (or `timeout` wrapper) has cmdline: `...pkill -f "some_pattern"`
4. Pattern matches → pkill sends SIGKILL to parent
5. Parent dies → shell hangs or exits with error

### Key observations

| Command | Behavior | Why |
|---------|----------|-----|
| `pkill "bash"` | Exits immediately (code 1) | Name-only match, no cmdline scan |
| `pkill -f "pattern"` | Hangs/kills parent | `-f` scans all cmdlines, matches parent |
| `pgrep -f "pattern"` | Works fine | Same scan, but only prints PIDs, doesn't kill |
| `kill $PID` | Works fine | Explicit PID, no scanning |

## Safe Alternatives

### 1. Kill by PID (Recommended)

```bash
# Find PID first, then kill
PID=$(pgrep -f "exact_process_name")
kill $PID

# Or with signal
kill -9 $PID
```

### 2. pkill without -f (name-only match)

```bash
# Only matches process name (15 char limit), not full cmdline
pkill -9 "processname"
```

### 3. pgrep + kill loop

```bash
# For multiple processes
pgrep -f "exact_pattern" | xargs kill -9
```

### 4. Scoped pkill (extreme precision)

```bash
# Only if you're 100% sure the pattern WON'T match parent shells
pkill -f "Xvfb :99"
```

## Recommended Approach for Agents

Per `e000-fundamentals/AGENTS.md`:

> **Never use pkill without extreme precision**: `pkill -f godot4` kills Godot processes across ALL tmux windows, including other agents. Use `kill $PID` with a specific process ID instead. If you must use pkill, scope it tightly.

### Safe pattern

```bash
# Step 1: Find the PID
PID=$(pgrep -f "exact_process_command")

# Step 2: Kill it
kill $PID

# Step 3: Verify it's gone
kill -0 $PID 2>/dev/null && echo "still alive" || echo "killed"
```

### Dangerous pattern (NEVER do this)

```bash
# WRONG: pkill -f matches parent shell, kills it, hangs
pkill -9 -f "godot4"
pkill -9 -f "opencode"
pkill -9 -f "Xvfb"
```

## Environment

- **procps-ng**: 4.0.4
- **System**: Linux (311 processes)
- **Shell**: zsh (via opencode bash tool)
- **Reproduced**: Sun Jun 14 2026
