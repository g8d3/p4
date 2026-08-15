#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Install dsh into app/ with npm 12 allowScripts approval for the three
# packages that need native build/install scripts. Without approval,
# node-pty's pty.node is never compiled and dsh fails to boot.

if [[ -d app/node_modules ]]; then
  echo "app/ already installed"
  exit 0
fi

mkdir -p app
cd app
npm init -y >/dev/null
npm install @deepseek-ai/dsh
npm install-scripts approve node-pty koffi @deepseek-ai/dsh-subprocess-local
npm rebuild node-pty

if [[ ! -f node_modules/node-pty/build/Release/pty.node ]]; then
  echo "ERROR: pty.node not built" >&2
  exit 1
fi
echo "OK: app/ ready ($(du -sh node_modules | cut -f1) node_modules)"
