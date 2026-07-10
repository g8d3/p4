"""
Generate images via Higgsfield web UI (Nano Banana Pro).

Fully self-contained: sources secrets, starts Chrome, logs in,
generates image, downloads it. Just run it.

Usage:
    python generate_image.py "prompt text" [--output image.png]
"""

import sys
import time
import os

sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    load_secrets, ensure_chrome_ready, ab, ab_eval, find_ref, is_logged_in
)


def generate_image(prompt, output_path="image.png", model="nano-banana-pro"):
    """Generate an image using Higgsfield web UI. Returns True on success."""
    print(f"\n{'='*50}")
    print(f"Generating image: {prompt[:80]}...")
    print(f"{'='*50}")

    # Open image page for the chosen model
    print("1. Opening image page...")
    ab("open", f"https://higgsfield.ai/ai/image?model={model}", timeout=15)
    time.sleep(3)
    ab("set", "viewport", "1280", "800")
    time.sleep(2)

    # Fill prompt
    print("2. Filling prompt...")
    _, snap, _ = ab("snapshot", "-i", timeout=10)
    ref = find_ref(snap, 'textbox "Describe')
    if not ref:
        print("   [error] Prompt textbox not found")
        return False
    ab("fill", f"@{ref}", prompt)
    time.sleep(1)

    # Click Generate
    print("3. Clicking Generate...")
    _, snap, _ = ab("snapshot", "-i", timeout=10)
    ref = find_ref(snap, 'button "Generate')
    if not ref:
        print("   [error] Generate button not found")
        return False
    ab("click", f"@{ref}")
    time.sleep(2)

    # Wait for generation (poll for download button or image URL)
    print("4. Waiting for generation (up to 60s)...")
    deadline = time.time() + 60
    img_url = None
    while time.time() < deadline:
        _, snap, _ = ab("snapshot", "-i", timeout=10)
        if "Download" in snap or "download" in snap.lower():
            print("   [ok] Generation complete!")
            time.sleep(2)
            break
        time.sleep(5)

    # Extract image URL from the page
    print("5. Extracting image URL...")
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
    if not img_url or "cloudfront" not in img_url:
        print("   [error] Could not find generated image URL")
        return False

    print(f"   [ok] Image URL: {img_url[:80]}...")

    # Download
    print("6. Downloading image...")
    try:
        import httpx
        r = httpx.get(img_url, timeout=30)
        if r.status_code != 200:
            print(f"   [error] Download returned HTTP {r.status_code}")
            return False
        with open(output_path, 'wb') as f:
            f.write(r.content)
        size_kb = len(r.content) / 1024
        print(f"   [ok] Saved to {output_path} ({size_kb:.1f} KB)")
        return True
    except Exception as e:
        print(f"   [error] Download failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_image.py 'prompt text' [--output image.png]")
        sys.exit(1)

    prompt = sys.argv[1]
    output = "output/hf_image.png"

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    load_secrets()

    if not ensure_chrome_ready():
        print("[fatal] Cannot proceed: Chrome setup failed")
        sys.exit(1)

    success = generate_image(prompt, output)
    sys.exit(0 if success else 1)
