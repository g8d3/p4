#!/usr/bin/env bash
set -euo pipefail

DISPLAY_NUM="${1:-1}"

pkill -f "Xvfb :${DISPLAY_NUM}" 2>/dev/null || true
pkill -f "x11vnc.*:${DISPLAY_NUM}" 2>/dev/null || true
pkill openbox 2>/dev/null || true
