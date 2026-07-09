"""
WEB UI AUTOMATION - Generate images via Higgsfield (Nano Banana Pro).

Auto-detects Chrome and login status. Just run it.

Usage:
    python generate_image.py "prompt text" [--output image.png]

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


def generate_image(prompt, output_path="image.png", model="nano-banana-pro"):
    """Generate an image using Higgsfield web UI."""
    print(f"\n{'='*50}")
    print(f"Generating image: {prompt[:60]}...")
    print(f"{'='*50}")

    # Open image page
    print("1. Opening image page...")
    ab("open", f"https://higgsfield.ai/ai/image?model={model}")
    time.sleep(3)
    ab("set", "viewport", "1280", "800")
    time.sleep(2)

    # Fill prompt
    print("2. Filling prompt...")
    _, snap, _ = ab("snapshot", "-i", timeout=10)
    ref = find_ref(snap, 'textbox "Describe')
    if ref:
        ab("fill", f"@{ref}", prompt)
        time.sleep(1)
    else:
        print("   [error] Prompt textbox not found")
        return False

    # Click Generate
    print("3. Clicking Generate...")
    _, snap, _ = ab("snapshot", "-i", timeout=10)
    ref = find_ref(snap, 'button "Generate')
    if ref:
        ab("click", f"@{ref}")
        time.sleep(2)
    else:
        print("   [error] Generate button not found")
        return False

    # Wait for generation
    print("4. Waiting for generation (up to 60s)...")
    deadline = time.time() + 60
    while time.time() < deadline:
        _, snap, _ = ab("snapshot", "-i", timeout=10)
        if "Download" in snap or "download" in snap.lower():
            print("   [ok] Image generated!")
            break
        time.sleep(5)

    # Try to download
    print("5. Downloading image...")
    js = """
    (() => {
        const imgs = document.querySelectorAll('img[src*="cloudfront"]');
        if (imgs.length > 0) {
            return imgs[imgs.length - 1].src;
        }
        return null;
    })()
    """
    img_url = ab_eval(js, timeout=10)
    if img_url and "cloudfront" in img_url:
        print(f"   [ok] Image URL found")
        try:
            import httpx
            r = httpx.get(img_url, timeout=30)
            if r.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(r.content)
                size = len(r.content)
                print(f"   [ok] Saved to {output_path} ({size} bytes)")
                return True
        except Exception as e:
            print(f"   [error] Download failed: {e}")
    else:
        print("   [error] Could not find generated image URL")

    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_image.py 'prompt text' [--output image.png]")
        sys.exit(1)

    prompt = sys.argv[1]
    output = "image.png"

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]

    # Ensure Chrome is ready
    if not ensure_chrome_ready():
        print("[fatal] Could not prepare Chrome")
        sys.exit(1)

    success = generate_image(prompt, output)
    sys.exit(0 if success else 1)
