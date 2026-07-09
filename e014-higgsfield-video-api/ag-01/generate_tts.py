"""
WEB UI AUTOMATION - Generate TTS narration via Higgsfield Voiceover (ElevenLabs).

Uses browser automation (agent-browser), NOT API credits.

Usage:
    python generate_tts.py "<text>" [--voice HARPER] [--model "Eleven v3"] [--output file.mp3]

Requires:
    - agent-browser CLI
    - Chrome on CDP port 9231 (or HF_CDP_PORT env)
    - Logged into Higgsfield
"""

import subprocess
import sys
import time
import os
import httpx
import argparse

CDP_PORT = os.environ.get("HF_CDP_PORT", "9231")
CDP = ["--cdp", CDP_PORT]


def ab(*args, timeout=30):
    r = subprocess.run(
        ["agent-browser", *CDP, *args],
        capture_output=True, text=True, timeout=timeout,
    )
    return r.stdout.strip()


def ab_eval(js, timeout=15):
    out = ab("eval", js, timeout=timeout)
    if out.startswith('"') and out.endswith('"'):
        out = out[1:-1]
    return out


def find_ref(snapshot, pattern):
    for line in snapshot.split("\n"):
        if pattern in line and "ref=" in line:
            return line.split("ref=")[1].split("]")[0]
    return None


def generate_tts(text, voice="HARPER", model="Eleven v3", output_path="output/tts.mp3"):
    """Generate TTS using Higgsfield Voiceover and download the result."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    print(f"1. Opening Higgsfield Audio page...")
    ab("open", "https://higgsfield.ai/audio")
    time.sleep(4)
    ab("set", "viewport", "1280", "800")
    time.sleep(2)

    # Find the Voiceover tab and click it
    snap = ab("snapshot", "-i", timeout=10)
    vo_ref = find_ref(snap, 'button "Voiceover"')
    if not vo_ref:
        print("ERROR: Voiceover tab not found")
        return False
    ab("click", f"@{vo_ref}")
    time.sleep(2)

    # Find the textbox and fill it using agent-browser's fill command
    # (handles React controlled inputs correctly via proper events)
    snap = ab("snapshot", "-i", timeout=10)
    tb_ref = find_ref(snap, 'textbox "Describe the sound you imagine')
    if not tb_ref:
        print("ERROR: Textbox not found")
        return False

    ab("click", f"@{tb_ref}")
    time.sleep(0.5)
    ab("fill", f"@{tb_ref}", text)
    time.sleep(1)

    # Find and click GENERATE
    snap = ab("snapshot", "-i", timeout=10)
    gen_ref = find_ref(snap, 'button "GENERATE')
    if not gen_ref:
        print("ERROR: Generate button not found")
        return False

    print(f"2. Clicking Generate (cost in credits)...")
    ab("click", f"@{gen_ref}")
    time.sleep(8)

    # Wait for the audio element to appear (it appears after generation)
    deadline = time.time() + 30
    audio_url = None
    while time.time() < deadline:
        url = ab_eval("document.querySelector('audio')?.src || 'NOPE'", timeout=5)
        if url and url != "NOPE":
            audio_url = url
            break
        time.sleep(3)

    if not audio_url:
        print("ERROR: Audio generation timed out")
        return False

    print(f"3. Downloading audio from CDN...")
    r = httpx.get(audio_url, timeout=120, follow_redirects=True)
    with open(output_path, "wb") as f:
        f.write(r.content)
    print(f"   Saved: {output_path} ({len(r.content)} bytes)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate TTS via Higgsfield Voiceover")
    parser.add_argument("text", help="Text to synthesize")
    parser.add_argument("--voice", default="HARPER", help="Voice preset name")
    parser.add_argument("--output", default="output/tts.mp3", help="Output file path")
    args = parser.parse_args()

    success = generate_tts(args.text, output_path=args.output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
