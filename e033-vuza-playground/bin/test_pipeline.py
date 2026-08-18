"""VUZA pipeline smoke test: edge-tts voiceover + moviepy 2.2 video assembly.

Uses LOCAL placeholder media (no stock API/Pinterest). Proves the script→
sentence→keyword→voiceover→subtitled-video path works; only media sourcing
(Pinterest/Pexels/Pixabay) is external and may be blocked/keyed.
"""
import asyncio
import random
import re
from pathlib import Path

import numpy as np
from PIL import Image

BASE = Path(__file__).resolve().parent.parent
REPO = BASE / "repo"
OUT = BASE / "output" / "pipeline_test"
PROJ = OUT / "project"
TMP = OUT / "temp"

import sys
sys.path.insert(0, str(REPO))
sys.path.insert(1, str(BASE / "venv" / "lib" / "python3.12" / "site-packages"))

from video_engine import VideoEngine

SCRIPT_DATA = [
    {"sentence": "Coins can grow into savings if you let them compound.", "keyword": "coins"},
    {"sentence": "Keep your money building while you sleep.", "keyword": "bank"},
]


def make_placeholder_image(path: Path, w=1080, h=1920, label=""):
    """Vertical gradient placeholder, avoids needing stock footage."""
    rng = np.random.default_rng(abs(hash(label)) % 2**32)
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        arr[y, :, 0] = int(60 + 195 * y / h)
        arr[y, :, 1] = int(20 + (255 - 60) * (y / h))
        arr[y, :, 2] = int(120 + 60 * (y / h))
    arr = arr.astype(np.int16)
    arr += rng.integers(-12, 12, size=arr.shape, dtype=np.int16)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(arr).convert("RGB").save(path)


def setup_media():
    """Two keyword folders, each with 2 images."""
    for kw in ("coins", "bank"):
        d = PROJ / kw
        d.mkdir(parents=True, exist_ok=True)
        for i in range(2):
            make_placeholder_image(d / f"m{i}.jpg", label=f"{kw}{i}")


async def voiceover(engine):
    for i, item in enumerate(SCRIPT_DATA):
        await engine.generate_voiceover(item["sentence"], i, voice="en-US-ChristopherNeural")
        print(f"  voiceover {i} OK")


def main():
    from dataclasses import dataclass

    @dataclass
    class S:
        ratio: str = "9:16"
        subtitles: bool = True
        subtitle_style: str = "default"
        vibe: str = "general"
        filter: str = "none"
        watermark: bool = False

    setup_media()
    engine = VideoEngine(output_dir=OUT)
    asyncio.run(voiceover(engine))
    settings = S()
    out = engine.create_video(SCRIPT_DATA, PROJ, media_type="image", settings=settings)
    print("VIDEO:", out)
    return out


if __name__ == "__main__":
    main()
