#!/usr/bin/env bash
# Apply e107 local patches onto upstream/ (idempotent; safe to re-run).
# Needed after bin/fetch.sh re-clones the pinned upstream commit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/upstream"
for p in ../patches/*.patch; do
  name="$(basename "$p")"
  if git apply --check "$p" 2>/dev/null; then
    git apply "$p" && echo "applied $name"
  else
    echo "skipped $name (already applied or diverged — check by hand)"
  fi
done
echo "rebuild with: cd upstream && pnpm build"
