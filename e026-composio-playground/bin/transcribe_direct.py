#!/usr/bin/env python
"""Transcribe a public audio URL with Deepgram directly (no Composio)."""
import json
import os
import sys

from urllib.request import Request, urlopen

AUDIO = sys.argv[1] if len(sys.argv) > 1 else (
    "https://res.cloudinary.com/deepgram/video/upload/v1680127025/"
    "dg-audio/nasa-spacewalk-interview_ljjahn.wav"
)

req = Request(
    "https://api.deepgram.com/v1/listen?model=nova-2",
    data=json.dumps({"url": AUDIO}).encode(),
    headers={"Authorization": f"Token {os.environ['DEEPGRAM_API_KEY']}",
             "Content-Type": "application/json"},
)
r = json.load(urlopen(req, timeout=60))
print(r["results"]["channels"][0]["alternatives"][0]["transcript"])
