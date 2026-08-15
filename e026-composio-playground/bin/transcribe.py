#!/usr/bin/env python
"""Transcribe a public audio file via Composio + Deepgram.

Product: Composio Platform (COMPOSIO_API_KEY from ~/.secrets/.env via .zshrc).
Path: session create -> execute DEEPGRAM_SPEECH_TO_TEXT_PRE_RECORDED with
custom_connection_data (API_KEY) on a public NASA spacewalk interview WAV.

Success: a real provider transcript + a non-empty Composio log ID.
Writes: output/transcript.txt, output/result.json, output/log_id.txt

Usage:
    source ~/.zshrc
    .venv/bin/python bin/transcribe.py [audio_url]
"""
import json
import os
import sys
from pathlib import Path

from composio import Composio

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "output"
USER_ID = os.environ.get("COMPOSIO_TEST_USER_ID", "vuos")
DEEPGRAM_VERSION = "20260707_00"
DEFAULT_AUDIO_URL = (
    "https://res.cloudinary.com/deepgram/video/upload/v1680127025/"
    "dg-audio/nasa-spacewalk-interview_ljjahn.wav"
)


def main():
    api_key = os.environ.get("DEEPGRAM_API_KEY")
    if not api_key:
        raise SystemExit("DEEPGRAM_API_KEY not set (source ~/.zshrc / ~/.secrets/.env)")

    audio_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_AUDIO_URL

    composio = Composio()
    session = composio.create(
        user_id=USER_ID,
        toolkits=["deepgram"],
        manage_connections=True,
    )
    print(f"[1/3] session ready: {session.session_id}")

    result = composio.tools.execute(
        "DEEPGRAM_SPEECH_TO_TEXT_PRE_RECORDED",
        arguments={
            "audio_url": audio_url,
            "content_type": "audio/wav",
            "model": "nova-2",
        },
        user_id=USER_ID,
        version=DEEPGRAM_VERSION,
        custom_connection_data={
            "auth_scheme": "API_KEY",
            "toolkit_slug": "deepgram",
            "val": {"generic_api_key": api_key},
        },
    )

    if not result.get("successful"):
        raise SystemExit(f"tool call failed: {json.dumps(result)[:500]}")

    payload = result["data"]["results"]["channels"][0]["alternatives"][0]
    transcript = payload["transcript"]
    log_id = _fetch_latest_log_id(composio)
    print(f"[2/3] transcript ({len(transcript)} chars), confidence {payload['confidence']:.3f}")
    print(f"[3/3] log id: {log_id}")
    print()
    print(transcript)

    OUT.mkdir(exist_ok=True)
    (OUT / "transcript.txt").write_text(transcript + "\n")
    (OUT / "log_id.txt").write_text(log_id + "\n")
    (OUT / "result.json").write_text(
        json.dumps(
            {
                "session_id": session.session_id,
                "audio_url": audio_url,
                "tool": "DEEPGRAM_SPEECH_TO_TEXT_PRE_RECORDED",
                "log_id": log_id,
                "confidence": payload["confidence"],
                "duration_sec": result["data"]["metadata"]["duration"],
                "model": result["data"]["metadata"]["models"],
            },
            indent=2,
        )
    )
    print(f"\noutputs written to {OUT}")


def _fetch_latest_log_id(composio: Composio) -> str:
    logs = composio.client.logs.tools.list(cursor=0, limit=1)
    items = logs.model_dump()["data"]
    return items[0]["id"] if items else "unknown"


if __name__ == "__main__":
    main()
