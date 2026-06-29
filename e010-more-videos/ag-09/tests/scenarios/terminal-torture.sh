#!/bin/bash
# terminal-torture.sh: extreme edge cases for terminal capture
# Tests: binary output, no-output scenarios, race conditions, stale sessions

set -euo pipefail
cd "$(dirname "$0")/../.."
SESSION="tds-torture-$$"
OUTDIR="tests/output/torture"
mkdir -p "$OUTDIR"

echo "=== TDS Terminal Torture Test ==="

# 1. Non-existent pane
echo "--- Test 1: non-existent pane ---"
python3 -c "
from tds.terminal import TerminalWatcher
w = TerminalWatcher(pane='nonexistent-99999')
lines = w.capture()
print(f'Non-existent pane: {len(lines)} lines')
for l in lines[:3]:
    print(f'  {l}')
" 2>&1 | head -5

# 2. Stale session (pane existed but is gone)
echo ""
echo "--- Test 2: closed tmux session ---"
tmux new-session -d -s "$SESSION-stale" -x 80 -y 24
sleep 0.3
tmux send-keys -t "$SESSION-stale" "echo hello" Enter
sleep 0.3
tmux kill-session -t "$SESSION-stale"
sleep 0.3
python3 -c "
from tds.terminal import TerminalWatcher
w = TerminalWatcher(pane='$SESSION-stale')
lines = w.capture()
print(f'Stale session: {len(lines)} lines, first: {lines[0][:80] if lines else \"(empty)\"}')
" 2>&1

# 3. Extremely rapid capture (every 10ms - simulate race)
echo ""
echo "--- Test 3: rapid capture race (100 captures in 1s) ---"
tmux new-session -d -s "$SESSION-race" -x 80 -y 24
sleep 0.3
python3 -c "
import time
from tds.terminal import TerminalWatcher
from tds.diff import diff_snapshots, snapshot_key

w = TerminalWatcher(pane='$SESSION-race', interval=0.01)
# Manually do rapid captures
last = []
changes = 0
for i in range(100):
    lines = w.capture()
    key = snapshot_key(lines)
    if key != snapshot_key(last):
        changes += 1
    last = lines
    time.sleep(0.01)
print(f'100 rapid captures: {changes} detected changes')
" 2>&1
tmux send-keys -t "$SESSION-race" "for i in {1..100}; do echo \"\$i\"; done" Enter
sleep 2
tmux kill-session -t "$SESSION-race"

# 4. Massive scrollback (>10K lines)
echo ""
echo "--- Test 4: massive scrollback ---"
tmux new-session -d -s "$SESSION-scroll" -x 80 -y 24
sleep 0.3
tmux send-keys -t "$SESSION-scroll" "for i in \$(seq 1 5000); do echo \$i; done" Enter
sleep 4
python3 -c "
from tds.terminal import TerminalWatcher
from tds.diff import trim_to_visible
w = TerminalWatcher(pane='$SESSION-scroll', max_lines=5000)
lines = w.capture()
print(f'Scrollback raw: {len(lines)} lines')
trimmed = trim_to_visible(lines, max_lines=200, max_cols=100)
print(f'Trimmed: {len(trimmed)} lines')
print(f'First: {trimmed[0][:60]}')
print(f'Last: {trimmed[-1][:60]}')
" 2>&1
tmux kill-session -t "$SESSION-scroll"

# 5. Zero output (idle terminal)
echo ""
echo "--- Test 5: idle terminal (no changes) ---"
tmux new-session -d -s "$SESSION-idle" -x 80 -y 24
sleep 0.3
python3 -c "
from tds.terminal import TerminalWatcher
from tds.diff import snapshot_key
w = TerminalWatcher(pane='$SESSION-idle')
c1 = w.capture()
import time; time.sleep(1)
c2 = w.capture()
print(f'Same content: {snapshot_key(c1) == snapshot_key(c2)}')
print(f'Captures equal: {c1 == c2}')
" 2>&1
tmux kill-session -t "$SESSION-idle"

# 6. Unicode / multi-byte characters
echo ""
echo "--- Test 6: unicode stress ---"
tmux new-session -d -s "$SESSION-unicode" -x 80 -y 24
sleep 0.3
tmux send-keys -t "$SESSION-unicode" "echo 'ÁÉÍÓÚ ñ Ñ 日本語 한국어 中文 ✓ 😀🔥🚀'" Enter
sleep 1
tmux send-keys -t "$SESSION-unicode" "echo '盒中有盒中有盒 中 文 测 试'" Enter
sleep 1
python3 -c "
from tds.terminal import TerminalWatcher
from tds.diff import diff_snapshots
w = TerminalWatcher(pane='$SESSION-unicode')
c1 = w.capture()
print('Unicode capture (first 5 lines):')
for l in c1[:5]:
    print(f'  {l[:100]}')
# Count non-ASCII chars
total_chars = sum(len(l) for l in c1)
non_ascii = sum(1 for l in c1 for c in l if ord(c) > 127)
print(f'Total chars: {total_chars}, Non-ASCII: {non_ascii}')
" 2>&1
tmux kill-session -t "$SESSION-unicode"

# 7. Empty lines and whitespace-only lines
echo ""
echo "--- Test 7: whitespace stress ---"
tmux new-session -d -s "$SESSION-ws" -x 80 -y 24
sleep 0.3
tmux send-keys -t "$SESSION-ws" "echo; echo '   '; echo; printf '  \t  \n'; echo 'real content'" Enter
sleep 1
python3 -c "
from tds.terminal import TerminalWatcher
w = TerminalWatcher(pane='$SESSION-ws')
lines = w.capture()
empty = sum(1 for l in lines if l.strip() == '')
print(f'Total lines: {len(lines)}, Whitespace-only: {empty}')
for l in lines[-5:]:
    print(f'  [{repr(l[:40])}]')
" 2>&1
tmux kill-session -t "$SESSION-ws"

echo ""
echo "=== Torture test complete ==="
