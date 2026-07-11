#!/usr/bin/env python3
"""
higgsfield.py — Generate images/videos via Higgsfield API (no browser needed).

Usage:
    uv run --with httpx higgsfield.py "a red apple on a white table"
    uv run --with httpx higgsfield.py "a cat" --model seedream_v5_pro
    uv run --with httpx higgsfield.py "a sunset" --model nano-banana-pro --output sunset.png

Models: nano-banana-pro, seedream_v5_pro, gpt_image_2, flux_2, grok_image, etc.
"""

import argparse
import json
import os
import sys
import time
import subprocess
import httpx


API_BASE = "https://fnf-api-gw.higgsfield.ai"


def ab(*args, timeout=30):
    """Run agent-browser command."""
    cmd = ["agent-browser", "--auto-connect"] + [str(a) for a in args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"


def load_token():
    """Load Bearer token from ~/.secrets/.env"""
    env_path = os.path.expanduser("~/.secrets/.env")
    if not os.path.exists(env_path):
        print("[error] ~/.secrets/.env not found", file=sys.stderr)
        sys.exit(1)

    with open(env_path) as f:
        for line in f:
            if line.startswith("export BEARER_TOKEN_HIGGSFIELD_AI="):
                token = line.split("=", 1)[1].strip().strip("'\"")
                return token

    print("[error] BEARER_TOKEN_HIGGSFIELD_AI not found in ~/.secrets/.env", file=sys.stderr)
    print("[hint] Run the explorer to extract the token, or set it manually:", file=sys.stderr)
    print("  export BEARER_TOKEN_HIGGSFIELD_AI='your_token_here'", file=sys.stderr)
    sys.exit(1)


def headers(token, datadome=None):
    h = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": "https://higgsfield.ai",
        "Referer": "https://higgsfield.ai/",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    }
    if datadome:
        h["Cookie"] = f"datadome={datadome}"
    return h


def create_job(prompt, model="nano-banana", token=None, **kwargs):
    """Create an image generation job via browser (bypasses DataDome)."""
    use_unlim = kwargs.get("use_unlim", False)

    body = {
        "params": {
            "width": kwargs.get("width", 1024),
            "height": kwargs.get("height", 1024),
            "prompt": prompt,
            "input_images": kwargs.get("input_images", []),
            "batch_size": kwargs.get("batch_size", 1),
            "use_unlim": use_unlim,
            "aspect_ratio": kwargs.get("aspect_ratio", "1:1"),
        },
        "use_unlim": use_unlim,
        "client_meta": None,
    }

    body_json = json.dumps(body).replace("'", "\\'")

    print(f"[api] Model: {model}")
    print(f"[api] Prompt: {prompt[:60]}...")
    print(f"[api] Unlimited: {use_unlim}")

    # Make request via browser (bypasses DataDome)
    js = f"""
    (async () => {{
        const resp = await fetch('https://fnf-api-gw.higgsfield.ai/fnf/jobs/{model}', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
                'Authorization': 'Bearer {token}',
            }},
            body: JSON.stringify({body_json}),
        }});
        const data = await resp.json();
        return JSON.stringify({{status: resp.status, data: data}});
    }})()
    """

    _, out, _ = ab("eval", js, timeout=30)

    try:
        result = json.loads(out.strip().strip('"'))
        print(f"[api] Status: {result['status']}")

        if result["status"] in (200, 201):
            return result["data"]
        else:
            print(f"[api] Error: {json.dumps(result['data'], indent=2)[:300]}")
            return None
    except Exception as e:
        print(f"[error] {e}")
        print(f"[raw] {out[:200]}")
        return None


def poll_job(job_id, token, max_wait=120):
    """Poll job status until complete."""
    url = f"{API_BASE}/fnf/jobs/{job_id}/status"
    print(f"[poll] Waiting for job {job_id}...")

    start = time.time()
    while time.time() - start < max_wait:
        try:
            r = httpx.get(url, headers=headers(token), timeout=10)
            if r.status_code == 200:
                data = r.json()
                status = data.get("status") or data.get("state")
                print(f"[poll] Status: {status}")

                if status in ("completed", "done", "succeeded"):
                    return data
                elif status in ("failed", "error"):
                    print(f"[error] Job failed: {data}")
                    return None
            else:
                print(f"[poll] HTTP {r.status_code}")
        except Exception as e:
            print(f"[poll] Error: {e}")

        time.sleep(3)

    print(f"[error] Timeout after {max_wait}s")
    return None


def download_image(url, output_path):
    """Download generated image."""
    print(f"[download] {url[:60]}...")
    try:
        r = httpx.get(url, timeout=30)
        if r.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(r.content)
            size_kb = len(r.content) / 1024
            print(f"[download] Saved: {output_path} ({size_kb:.1f} KB)")
            return True
        else:
            print(f"[error] Download failed: HTTP {r.status_code}")
            return False
    except Exception as e:
        print(f"[error] Download failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate images via Higgsfield API")
    parser.add_argument("prompt", help="Text prompt for image generation")
    parser.add_argument("--model", "-m", default="nano-banana",
                       help="Model ID (default: nano-banana, unlimited)")
    parser.add_argument("--output", "-o", default="output.png",
                       help="Output file path (default: output.png)")
    parser.add_argument("--aspect-ratio", default="1:1",
                       help="Aspect ratio (1:1, 3:4, 16:9, etc.)")
    parser.add_argument("--width", type=int, default=1024,
                       help="Image width (default: 1024)")
    parser.add_argument("--height", type=int, default=1024,
                       help="Image height (default: 1024)")
    parser.add_argument("--batch-size", type=int, default=1,
                       help="Number of images (1-4)")
    parser.add_argument("--unlimited", action="store_true", default=True,
                       help="Use unlimited mode (no credits)")
    parser.add_argument("--no-unlimited", action="store_true",
                       help="Disable unlimited mode (uses credits)")
    parser.add_argument("--datadome", default=None,
                       help="DataDome session cookie (auto-extracted from browser if not set)")
    parser.add_argument("--no-poll", action="store_true",
                       help="Create job but don't wait for result")
    args = parser.parse_args()

    # Load token
    token = load_token()
    print(f"[auth] Token loaded ({len(token)} chars)")

    # Get DataDome from browser if not provided
    datadome = args.datadome
    if not datadome:
        print("[auth] Extracting DataDome from browser...")
        try:
            r = subprocess.run(
                ["agent-browser", "--auto-connect", "eval",
                 "document.cookie.split(';').map(c=>c.trim()).find(c=>c.startsWith('datadome='))?.split('=').slice(1).join('=')||''"],
                capture_output=True, text=True, timeout=10
            )
            datadome = r.stdout.strip().strip('"')
            if datadome:
                print(f"[auth] DataDome: {datadome[:30]}...")
            else:
                print("[warn] No DataDome cookie found, request may fail")
        except Exception as e:
            print(f"[warn] Could not extract DataDome: {e}")

    print()

    # Create job
    use_unlim = args.unlimited and not args.no_unlimited
    result = create_job(
        args.prompt, args.model, token,
        width=args.width, height=args.height,
        batch_size=args.batch_size, aspect_ratio=args.aspect_ratio,
        use_unlim=use_unlim,
    )

    if not result:
        sys.exit(1)

    if args.no_poll:
        print(f"\n[done] Job created. Use --no-poll to skip waiting.")
        print(json.dumps(result, indent=2, default=str)[:500])
        return

    # Poll for completion
    job_id = result.get("id") or result.get("job_id") or result.get("data", {}).get("id")
    if not job_id:
        print("[error] No job ID in response")
        print(json.dumps(result, indent=2, default=str)[:500])
        sys.exit(1)

    final = poll_job(job_id, token)

    if not final:
        sys.exit(1)

    # Extract image URL from response
    image_url = None
    if "output" in final:
        image_url = final["output"].get("url") or final["output"].get("image_url")
    elif "result" in final:
        image_url = final["result"].get("url") or final["result"].get("image_url")
    elif "images" in final:
        image_url = final["images"][0].get("url") if final["images"] else None

    if image_url:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        download_image(image_url, args.output)
    else:
        print("[warn] No image URL in response")
        print(json.dumps(final, indent=2, default=str)[:500])

    print(f"\n[done]")


if __name__ == "__main__":
    main()
