#!/usr/bin/env bash
# Client for transcribe_server.py
# Usage: ./transcribe.sh /path/to/audio.mp3
curl -s -X POST http://127.0.0.1:9877 \
  -H 'Content-Type: application/json' \
  -d "{\"path\":\"$1\"}" | python3 -m json.tool
