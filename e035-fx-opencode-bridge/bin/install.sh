#!/usr/bin/env bash
# Install/unpatch the fx -> opencode bridge (one-liner capable)
# Usage: bash install.sh [patch [BASE_URL API_KEY MODEL]] | bash install.sh unpatch
#   patch uses OPENCODE_GO_* env or literal args; unpatch restores Vercel.
# Replicates 2026-08-20 (2:21 wall, see ../TIMELINE.md). Until fx adds native opencode support.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"
CACHE_LOG="$HOME/.cache/fx-proxy.log"
# Support: bash install.sh patch https://... sk-... model  OR  bash install.sh unpatch
if [ "$1" = "unpatch" ]; then
  echo "=== unpatch fx ==="
  if [ -f "$BIN_DIR/fx.real" ]; then mv "$BIN_DIR/fx.real" "$BIN_DIR/fx"; echo "restored fx.real -> fx"; else echo "no backup"; fi
  rm -f "$BIN_DIR/fx-opencode-proxy.py"
  if ss -tln 2>/dev/null | grep -q 8765; then echo "proxy still running on 8765 (kill \$(ps -o pid,args | grep fx-opencode | awk '{print \$1}')) or keep for other windows"; fi
  echo "Done. fx now uses Vercel. Verify: fx status"
  exit 0
fi
if [ "$1" = "patch" ]; then shift; fi
if [ -n "$1" ]; then export OPENCODE_GO_BASE_URL="$1"; fi
if [ -n "$2" ]; then export OPENCODE_GO_API_KEY="$2"; fi
if [ -n "$3" ]; then export OPENCODE_GO_MODEL="$3"; fi

echo "=== fx-opencode bridge installer ==="
echo "SCRIPT_DIR=$SCRIPT_DIR"
echo "BIN_DIR=$BIN_DIR"

# 1. Check fx exists
if ! command -v fx >/dev/null 2>&1 && [ ! -f "$BIN_DIR/fx.real" ]; then
  echo "fx not found. Install first: curl -fsSL https://fx.sh/setup.sh | bash"
  exit 1
fi

# 2. Backup original fx if not yet backed up
if [ -f "$BIN_DIR/fx" ] && [ ! -f "$BIN_DIR/fx.real" ]; then
  # fx is still the real binary (not wrapper)
  if file "$BIN_DIR/fx" | grep -q "ELF"; then
    echo "Backing up real fx -> fx.real"
    cp "$BIN_DIR/fx" "$BIN_DIR/fx.real"
  fi
elif [ -f "$BIN_DIR/fx.real" ]; then
  echo "Backup exists: $BIN_DIR/fx.real"
fi

# 3. Install wrapper as `fx`
echo "Installing wrapper -> $BIN_DIR/fx"
cp "$SCRIPT_DIR/fx" "$BIN_DIR/fx"
chmod +x "$BIN_DIR/fx"
# Ensure wrapper points to fx.real
sed -i 's|REAL_FX="$HOME/.local/bin/fx"|REAL_FX="$HOME/.local/bin/fx.real"|' "$BIN_DIR/fx" 2>/dev/null || true
grep -q "fx.real" "$BIN_DIR/fx" && echo "wrapper OK" || echo "check wrapper REAL_FX"

# 4. Install proxy
echo "Installing proxy -> $BIN_DIR/fx-opencode-proxy.py"
cp "$SCRIPT_DIR/fx-opencode-proxy.py" "$BIN_DIR/fx-opencode-proxy.py"
chmod +x "$BIN_DIR/fx-opencode-proxy.py"

# 5. Install systemd service (optional)
if [ -f "$SCRIPT_DIR/fx-opencode-proxy.service" ]; then
  mkdir -p "$HOME/.config/systemd/user"
  cp "$SCRIPT_DIR/fx-opencode-proxy.service" "$HOME/.config/systemd/user/"
  echo "systemd service installed (enable with: systemctl --user enable --now fx-opencode-proxy)"
fi

# 6. Check OPENCODE env
echo ""
echo "=== env check ==="
echo "OPENCODE_GO_BASE_URL=${OPENCODE_GO_BASE_URL:-<not set>}"
echo "OPENCODE_GO_MODEL=${OPENCODE_GO_MODEL:-<not set>}"
echo "OPENCODE_GO_API_KEY=${OPENCODE_GO_API_KEY:0:12}..."

if [ -z "$OPENCODE_GO_API_KEY" ]; then
  echo "WARNING: OPENCODE_GO_API_KEY not set. Set it in ~/.hermes/.env or export it."
fi

# 7. Test wrapper
echo ""
echo "=== test ==="
"$BIN_DIR/fx" status 2>&1 | head -n 5
echo ""
echo "Proxy will auto-start on next fx call if OPENCODE_GO_BASE_URL is https (external)."
echo "Check: ss -tln | grep 8765 ; cat $CACHE_LOG | tail"
echo ""
echo "Done. Try: fx ask --yolo 'list files' --no-save"
echo "Or new tmux window: tmux new-window -n fx2 -d; tmux send-keys -t fx2 \"fx\" Enter"
