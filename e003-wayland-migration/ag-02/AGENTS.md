# ag-02 — pkill hang diagnostic

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, self-wake pattern

## Goal

Diagnose why `pkill -9 -f "pattern"` hangs on this system, and determine the correct way to kill processes.

## Task

### 1. Reproduce the hang
```
timeout 5 pkill -9 -f "nonexistent_pattern_xyz_123"
echo "Exit: $?"
```

### 2. Test alternatives
- `timeout 5 kill $PID` with a real PID
- `timeout 5 pkill -f "exact_process_name"`
- `timeout 5 pgrep -f "pattern"` then `kill $PID`

### 3. Check if pkill hangs on specific patterns
- Empty match (no processes)
- Multiple matches
- Zombie processes

### 4. Document findings
Write `pkill-fix.md` with:
- Why pkill hangs
- Safe alternative commands
- Recommended approach for agents

## Self-command
After reading, execute immediately. ALL commands: `>/dev/null 2>&1 &`. Self-wake to continue.
