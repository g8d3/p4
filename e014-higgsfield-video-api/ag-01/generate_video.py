"""
Generate a video using the Higgsfield API.

Requires HF_API_KEY and HF_API_SECRET environment variables.
"""

import os

import higgsfield_client as hf

API_KEY = os.environ.get("HF_API_KEY")
API_SECRET = os.environ.get("HF_API_SECRET")

if not API_KEY or not API_SECRET:
    raise SystemExit(
        "Set HF_API_KEY and HF_API_SECRET environment variables first."
    )

# Available video endpoints (confirmed working, but require credits):
# - higgsfield-ai/dop/standard
# - kling-video/v2.1/pro/image-to-video

APPLICATION = "higgsfield-ai/dop/standard"
ARGUMENTS = {
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/"
    "PNG_transparency_demonstration_1.png/300px-"
    "PNG_transparency_demonstration_1.png",
    "prompt": "A serene lake at sunset with mountains, "
    "smooth cinematic camera pan from left to right",
    "duration": 5,
}


def main():
    print(f"Submitting to {APPLICATION} ...")
    print(f"Arguments: {ARGUMENTS}")

    result = hf.subscribe(APPLICATION, arguments=ARGUMENTS)

    print("Result:")
    print(result)


if __name__ == "__main__":
    main()
