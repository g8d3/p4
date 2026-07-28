# e019 — KIE Image API (Seedream 4.5)

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, media generation APIs

Experiments with the [KIE API](https://kie.ai) for image generation (Seedream) and text-to-speech (ElevenLabs, Gemini).

## Environment

| Variable | Description |
|---|---|
| `KIE_API_KEY` | API key for KIE (Bearer token) |
| `KIE_API_BASE_URL` | Base URL (default: `https://api.kie.ai`) |

## Scripts

### `ag-01/bin/kie-image.sh` — Text-to-image

CLI wrapper for Seedream 4.5 text-to-image API.

```bash
export KIE_API_KEY="your-key"
./ag-01/bin/kie-image.sh "prompt" [aspect_ratio] [quality]
```

Supported aspect ratios: `1:1`, `4:3`, `3:4`, `16:9`, `9:16`, `2:3`, `3:2`, `21:9`
Supported qualities: `basic` (2K), `high` (4K)

### `ag-01/bin/kie-tts.sh` — Text-to-speech

CLI wrapper for KIE TTS models (ElevenLabs & Gemini).

```bash
./ag-01/bin/kie-tts.sh "<text>" [model] [voice]
```

Output: WAV + auto-converted MP3, saved to `ag-01/output/`.

## API reference

- Docs: https://docs.kie.ai
- Base: `https://api.kie.ai`
- Auth: `Authorization: Bearer <KIE_API_KEY>`

### Generic task pattern (all models)

1. **POST** `/api/v1/jobs/createTask` — submit a generation job
2. **GET** `/api/v1/jobs/recordInfo?taskId=<id>` — poll for result

Poll response fields:
- `state`: `waiting` / `generating` / `success` / `fail`
- `resultJson`: stringified JSON with `resultUrls` array
- `creditsConsumed`: cost in credits
- `costTime`: processing time in seconds

### Other endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/chat/credit` | GET | Get remaining credits |
| `/api/v1/jobs/createTask` | POST | Create any generation task |
| `/api/v1/jobs/recordInfo` | GET | Query task result |

## Image models (Seedream)

### Available models

| Model ID | Type | Notes |
|---|---|---|
| `seedream/4.5-text-to-image` | Text-to-image | Tested, works |
| `seedream/4.5-edit` | Edit (image-to-image) | Takes `image_urls` |
| `seedream/5-lite-text-to-image` | Text-to-image (lite) | Not tested |
| `seedream/5-lite-image-to-image` | Image-to-image (lite) | Not tested |
| `seedream/5-pro-text-to-image` | Text-to-image (pro) | Not tested |
| `seedream/5-pro-image-to-image` | Image-to-image (pro) | Plus `output_format` param |

Older models (v3, v4) use `bytedance/seedream-v4-*` naming with params: `image_size`, `image_resolution`, `max_images`, `seed`.

### Request (4.5 text-to-image)

```json
{
    "model": "seedream/4.5-text-to-image",
    "input": {
        "prompt": "...",
        "aspect_ratio": "1:1",
        "quality": "basic",
        "nsfw_checker": false
    }
}
```

### Request (4.5 edit / 5-pro image-to-image)

```json
{
    "model": "seedream/4.5-edit",
    "input": {
        "prompt": "Modification description...",
        "image_urls": ["https://...source.jpg"],
        "aspect_ratio": "1:1",
        "quality": "basic",
        "nsfw_checker": true
    }
}
```

## TTS models

### ElevenLabs

| Model ID | Type | Status |
|---|---|---|
| `elevenlabs/text-to-speech-turbo-2-5` | TTS, 60+ voices | **Fails on KIE** (internal error) |
| `elevenlabs/text-to-speech-multilingual-v2` | TTS multilingual | Not tested |
| `elevenlabs/text-to-dialogue-v3` | Dialogue TTS (array of `{text, voice}`) | Not tested |
| `elevenlabs/audio-isolation` | Audio isolation (not TTS) | Not tested |

ElevenLabs voices (sample IDs): `N2lVS1w4EtoT3dr4eOWO` (Callum), `EkK5I93UQWFDigLMpZcX` (James), `Z3R5wn05IrDiVCyEkUrK` (Arabella), and 60+ more. Preview at `https://static.aiquickdraw.com/elevenlabs/voice/<voice_id>.mp3`.

### Gemini

| Model ID | Type | Status |
|---|---|---|
| `google/gemini-3-1-flash-tts` | Multi-speaker TTS | **Tested, works** |
| `google/gemini-2-5-pro-tts` | Multi-speaker TTS | Not tested |

Gemini TTS supports:
- Multiple speakers with distinct `voice_name`, `accent`, `pace`, `style`
- `scene` description for audio environment
- `dialogue_turns` array for multi-turn conversations
- Auto-inserts `dialogue_mode: "single"` for single speaker

### Request (ElevenLabs)

```json
{
    "model": "elevenlabs/text-to-speech-turbo-2-5",
    "input": {
        "text": "Hello world",
        "voice": "N2lVS1w4EtoT3dr4eOWO",
        "stability": 0.5,
        "similarity_boost": 0.75
    }
}
```

### Request (Gemini multi-speaker)

```json
{
    "model": "google/gemini-3-1-flash-tts",
    "input": {
        "temperature": 1,
        "scene": "A dark dungeon",
        "speakers": [
            {
                "speaker_id": "Speaker 1",
                "voice_name": "Fenrir",
                "audio_profile": "A stern gatekeeper",
                "accent": "British (RP)",
                "style": "Deadpan",
                "pace": "Natural"
            }
        ],
        "dialogue_turns": [
            { "speaker_id": "Speaker 1", "text": "Halt, traveler!" }
        ]
    }
}
```

## Pricing

### Verified costs (from actual API calls)

| Model | Credits consumed | Cost (1 credit = $0.005) | Notes |
|---|---|---|---|
| `seedream/4.5-text-to-image` | 6.5 | $0.0325 | ~40s, 2K image |
| `google/gemini-3-1-flash-tts` | 0.6 | $0.003 | ~10s, short sentence |
| `elevenlabs/text-to-speech-turbo-2-5` | 0.0 (failed) | — | Always fails on KIE |

**⚠️ Prices need reverification.** The values above are from single test calls and may not reflect official pricing. The pricing page (`https://kie.ai/pricing`) shows different rates (e.g., Gemini TTS: 2800 credits per million output tokens). Actual cost depends on output length, quality tier, and model. Check `creditsConsumed` in each `recordInfo` response.

### From pricing page (kie.ai/pricing)

| Model | Metric | Price |
|---|---|---|
| Gemini 2.5 Pro TTS | Audio Output | 2800 cr/1M tokens ($14) |
| Gemini 3.1 Flash TTS | Audio Output | 2800 cr/1M tokens ($14) |
| Gemini TTS (both) | Input | 140 cr/1M tokens ($0.70) |
| Seedream 5 Pro | text-to-image 2K | 14 cr/image ($0.07) |

### Notes

- **1 credit ≈ $0.005 USD** (per KIE billing page)
- Generated files at `tempfile.aiquickdraw.com` / `file.aiquickdraw.com` expire after ~20 minutes. Download immediately.
- Rate limit: 20 new generation requests per 10 seconds per account.
- Model prices may change as upstream providers adjust costs — always refer to `kie.ai/pricing` for latest.

## Cost reduction

- **Lite models**: `seedream/5-lite-*` should be cheaper (not tested)
- **Gemini TTS is ~10× cheaper than ElevenLabs** per request (and actually works)
- **No "derived image" discount** documented — image-to-image costs are not advertised as lower than text-to-image
- **No seed caching discount** for image generation
- **Prompt caching exists for chat models only** (Anthropic-style, not applicable to image/audio)

## Agents

- `ag-01/` — owns `bin/kie-image.sh` and `bin/kie-tts.sh`
- Agent output dir: `ag-01/output/` (by convention)
