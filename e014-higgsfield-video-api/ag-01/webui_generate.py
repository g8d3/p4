"""
Generate a Higgsfield video via the web UI using agent-browser.

This script encapsulates everything learned about automating the Higgsfield
web UI: finding the hidden file input, injecting an image via the File API,
handling the "Media upload agreement" dialog, and clicking Generate.

Usage:
    python webui_generate.py <image_path> "<prompt>" [--model MODEL] [--duration 5]

Requires:
    - agent-browser CLI installed
    - Chrome running on port 9222 with real profile
    - Logged into Higgsfield

Pitfalls documented:
    - The file input has a dynamic id (changes with model) → use querySelector
    - The file input is `sr-only` (hidden) → must use File API via JS
    - React re-renders after every action → re-find elements each time
    - "Media upload agreement" dialog appears on first upload → accept it
    - Refs in agent-browser snapshots change between commands → find dynamically
"""

import subprocess
import sys
import time
import os
import json

CDP_PORT = os.environ.get("HF_CDP_PORT", "9222")
CDP = ["--cdp", CDP_PORT]

# Image URL (pre-uploaded via SDK, hardcoded from previous session)
DEFAULT_IMAGE_URL = (
    "https://d8j0ntlcm91z4.cloudfront.net/user_3G9cFtcuob3yn40SgvSpGjwEvg2/"
    "hf_20260707_050330_18f8c40c-daa2-445f-b8f7-824cdd337c10_min.webp"
)

PROMPTS = {
    "idle": "Minimalist sleek cybernetic robot assistant, idle animation, dark background, neon blue lights, subtle breathing motion",
    "thinking": "Robot avatar with neon lights blinking rapidly, data streams on screen, thinking expression, subtle head tilt",
    "error": "Robot face short-circuiting, sparks, screen glitch, error animation, red warning lights flashing",
    "victory": "Futuristic robot doing a subtle victory gesture, digital eyes smiling, neon green lights, celebration sparkles",
}


def ab(*args, timeout=30):
    """Run agent-browser command, return stdout."""
    r = subprocess.run(
        ["agent-browser", *CDP, *args],
        capture_output=True, text=True, timeout=timeout
    )
    return r.stdout.strip()


def ab_eval(js, timeout=15):
    """Run JavaScript via agent-browser eval. Strip surrounding quotes."""
    out = ab("eval", js, timeout=timeout)
    if out.startswith('"') and out.endswith('"'):
        out = out[1:-1]
    return out


def find_ref(snapshot, pattern):
    """Find the ref of an element matching a pattern in the snapshot text."""
    for line in snapshot.split("\n"):
        if pattern in line and "ref=" in line:
            return line.split("ref=")[1].split("]")[0]
    return None


def inject_image(image_url):
    """Inject an image into the video form via the hidden file input.

    The file input has dynamic id and is `sr-only`. We use JavaScript's
    File API to set it via DataTransfer, which triggers React's onChange.
    """
    js = """
    (async () => {
      try {
        const inp = document.querySelector('input[type=file]');
        if (!inp) return 'ERR:no file input found';

        const resp = await fetch('""" + image_url + """');
        const blob = await resp.blob();
        const ext = blob.type.split('/')[1] || 'webp';
        const file = new File([blob], 'image.' + ext, {type: blob.type});

        const dt = new DataTransfer();
        dt.items.add(file);
        inp.files = dt.files;

        inp.dispatchEvent(new Event('input', {bubbles: true}));
        inp.dispatchEvent(new Event('change', {bubbles: true}));

        return 'OK:' + file.size + ':' + file.type;
      } catch(e) {
        return 'ERR:' + e.message;
      }
    })();
    """
    return ab_eval(js, timeout=20)


def accept_media_agreement():
    """Accept the 'Media upload agreement' dialog if it appears."""
    snap = ab("snapshot", "-i", timeout=10)
    if "Media upload agreement" in snap:
        ref = find_ref(snap, 'button "I agree, continue"')
        if ref:
            print("   [ui] Accepting media agreement...")
            ab("click", f"@{ref}")
            time.sleep(2)
            return True
    return False


def fill_prompt(text):
    """Find the prompt textbox and fill it. Refs change between renders."""
    snap = ab("snapshot", "-i", timeout=10)
    ref = find_ref(snap, 'textbox "Prompt"')
    if ref:
        ab("fill", f"@{ref}", text)
        time.sleep(1)
        return True
    print("   [ui] Prompt textbox not found")
    return False


def click_generate():
    """Find and click the Generate button."""
    snap = ab("snapshot", "-i", timeout=10)
    ref = find_ref(snap, 'button "Generate')
    if ref:
        ab("click", f"@{ref}")
        time.sleep(2)
        return True
    print("   [ui] Generate button not found")
    return False


def wait_for_generation(timeout_sec=60):
    """Wait for the generation to complete (detect via page text changes)."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        text = ab("get", "text", "body", timeout=5)
        if "Rerun" in text:
            return True
        time.sleep(5)
    return False


def check_page_loaded():
    """Verify the page is loaded and we're logged in."""
    title = ab("get", "title", timeout=10)
    if "Create AI Videos" not in title:
        print(f"   [check] Unexpected page: {title}")
        return False
    snap = ab("snapshot", "-i", timeout=10)
    if "Account menu" in snap:
        return True
    print("   [check] Not logged in")
    return False


def generate_clip(clip_name, prompt, image_url=None):
    """Generate one video clip."""
    print(f"\n{'='*50}")
    print(f"Generating: {clip_name}")
    print(f"Prompt: {prompt[:60]}...")
    print(f"{'='*50}")

    # Open video page
    print("1. Opening video page...")
    ab("open", "https://higgsfield.ai/ai/video")
    time.sleep(3)
    ab("set", "viewport", "1280", "800")
    time.sleep(2)

    if not check_page_loaded():
        return False

    # Inject image
    print("2. Injecting image...")
    result = inject_image(image_url or DEFAULT_IMAGE_URL)
    if not result.startswith("OK"):
        print(f"   Failed: {result}")
        return False
    print(f"   Image injected ({result})")
    time.sleep(3)

    # Accept media agreement if needed
    accept_media_agreement()

    # Fill prompt
    print("3. Filling prompt...")
    if not fill_prompt(prompt):
        return False
    print("   Prompt filled")

    # Click Generate
    print("4. Clicking Generate...")
    if not click_generate():
        return False
    print("   Generate clicked!")

    # Wait for completion
    print("5. Waiting for generation...")
    if wait_for_generation():
        print(f"   ✓ {clip_name} generated successfully!")
        return True
    else:
        print(f"   ✗ Generation timed out or failed")
        return False


def download_video(url, output_path):
    """Download a video from a Higgsfield CDN URL."""
    import httpx
    r = httpx.get(url, timeout=120, follow_redirects=True)
    with open(output_path, "wb") as f:
        f.write(r.content)
    return len(r.content)


def main():


def main():
    # Generate all 4 clips
    results = {}
    for name, prompt in PROMPTS.items():
        ok = generate_clip(name, prompt)
        results[name] = "✓" if ok else "✗"

    print(f"\n{'='*50}")
    print("Results:")
    for name, status in results.items():
        print(f"  {status} {name}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
