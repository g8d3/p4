"""
WEB UI AUTOMATION - Generate video via Higgsfield (Kling 3.0).

Auto-detects Chrome and login status. Just run it.

Usage:
    python generate_video.py "prompt text" [--output video.mp4]

Requires:
    - agent-browser CLI
    - Google Chrome
    - Higgsfield account
"""

import subprocess
import sys
import time
import os

# Add parent to path for utils
sys.path.insert(0, os.path.dirname(__file__))
from utils import ensure_chrome_ready, ab, ab_eval, find_ref


def generate_video(prompt, output_path="video.mp4", model="kling-3.0-turbo"):
    """Generate a video using Higgsfield web UI."""
    print(f"\n{'='*50}")
    print(f"Generating video: {prompt[:60]}...")
    print(f"Model: {model}")
    print(f"{'='*50}")

    # Open video page
    print("1. Opening video page...")
    ab("open", "https://higgsfield.ai/ai/video")
    time.sleep(3)
    ab("set", "viewport", "1280", "800")
    time.sleep(2)

    # Fill prompt
    print("2. Filling prompt...")
    snap = ab("snapshot", "-i", timeout=10)
    ref = find_ref(snap, 'textbox "Describe')
    if ref:
        ab("fill", f"@{ref}", prompt)
        time.sleep(1)
    else:
        print("   [error] Prompt textbox not found")
        return False

    # Click Generate
    print("3. Clicking Generate...")
    snap = ab("snapshot", "-i", timeout=10)
    ref = find_ref(snap, 'button "Generate')
    if ref:
        ab("click", f"@{ref}")
        time.sleep(2)
    else:
        print("   [error] Generate button not found")
        return False

    # Wait for generation
    print("4. Waiting for generation (up to 120s)...")
    deadline = time.time() + 120
    while time.time() < deadline:
        snap = ab("snapshot", "-i", timeout=10)
        if "Rerun" in snap or "Download" in snap:
            print("   [ok] Video generated!")
            break
        time.sleep(5)

    # Try to download
    print("5. Downloading video...")
    js = """
    (() => {
        const imgs = document.querySelectorAll('img[alt*="media asset by id of"]');
        if (imgs.length > 0) {
            const alt = imgs[imgs.length - 1].alt;
            const match = alt.match(/id of ([a-f0-9-]+)/);
            return match ? match[1] : null;
        }
        return null;
    })()
    """
    uuid = ab_eval(js, timeout=10)
    if uuid:
        print(f"   [ok] Video UUID: {uuid}")
        ab("open", f"https://higgsfield.ai/library/video/{uuid}")
        time.sleep(5)
        js_video = "document.querySelector('video')?.src"
        video_url = ab_eval(js_video, timeout=10)
        if video_url and "cloudfront" in video_url:
            print(f"   [ok] Video URL found")
            subprocess.run(["curl", "-s", "-o", output_path, video_url], timeout=120)
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                print(f"   [ok] Saved to {output_path} ({size} bytes)")
                return True
    else:
        print("   [error] Could not find video UUID")

    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_video.py 'prompt text' [--output video.mp4]")
        sys.exit(1)

    prompt = sys.argv[1]
    output = "video.mp4"

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]

    # Ensure Chrome is ready
    if not ensure_chrome_ready():
        print("[fatal] Could not prepare Chrome")
        sys.exit(1)

    success = generate_video(prompt, output)
    sys.exit(0 if success else 1)
