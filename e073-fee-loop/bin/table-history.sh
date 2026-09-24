#!/usr/bin/env bash
# Table time-travel: show exactly how a table looked at every moment.
# Usage: bash bin/table-history.sh seeds/agent-worlds.csv
set -uo pipefail
cd "$(dirname "$0")/.."
F="${1:?usage: table-history.sh <csv path>}"
git log --oneline --follow -- "$F" | head -20
echo ===
echo "diff last two versions:"
git diff HEAD~1 HEAD -- "$F" 2>/dev/null | head -60 || echo "(only one version committed so far)"
