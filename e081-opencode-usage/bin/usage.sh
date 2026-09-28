#!/bin/bash
# One-command OpenCode Go quota check. See AGENTS.md.
exec python3 "$(cd "$(dirname "$0")" && pwd)/usage.py" "$@"
