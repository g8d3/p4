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

#### Parameters

| Parameter | Description |
|---|---|
| `temperature` | Sampling temperature (0–2, default 1) |
| `scene` | Audio environment description, e.g. "A quiet warm room with a fireplace" |
| `sample_context` | Overall tone/style prompt, e.g. "Audiobook style narration. Tone is gentle and inviting." |
| `speakers[]` | Array of speaker configs (see below) |
| `dialogue_turns[]` | Array of `{speaker_id, text}` — the dialogue lines |

#### Per-speaker parameters

| Parameter | Options | Description |
|---|---|---|
| `voice_name` | 30 voices (see below) | Voice identity |
| `accent` | Neutral, American (Gen/Valley/South), British (RP/Brixton), Transatlantic, Australian | Accent |
| `style` | Vocal Smile, Newscaster, Whisper, Empathetic, Promo/Hype, Deadpan | Emotional delivery |
| `pace` | Natural, Rapid Fire, The Drift, Staccato | Speaking speed/rhythm |
| `audio_profile` | Free text | Character description, e.g. "A stern and weary gatekeeper" |

#### Available voices (30)

Achernar, Achird, Algenib, Algieba, Alnilam, Aoede, Autonoe, Callirrhoe, Charon, Despina, Enceladus, Erinome, Fenrir, Gacrux, Iapetus, Kore, Laomedeia, Leda, Orus, Puck, Pulcherrima, Rasalgethi, Sadachbia, Sadaltager, Schedar, Sulafat, Umbriel, Vindemiatrix, Zephyr, Zubenelgenubi

#### Markup tags (inline in dialogue text)

| Tag | Effect |
|---|---|
| `[sigh]` | Inserts a sigh sound |
| `[laughing]` | Inserts a laugh |
| `[uhm]` | Inserts hesitation |
| `[sarcasm]` | Sarcastic tone on subsequent phrase |
| `[whispering]` | Lowers volume |
| `[shouting]` | Increases volume |
| `[robotic]` | Robotic delivery |
| `[short pause]` | ~250ms pause |
| `[medium pause]` | ~500ms pause |
| `[long pause]` | ~1000ms+ pause |

#### Three levers for best results

Google Cloud docs recommend aligning all three for natural output:
1. **sample_context** (style prompt) — sets overall emotional tone
2. **Text content** — use emotionally rich text, not neutral
3. **Markup tags** — for local effects (sighs, pauses, laughter)

A neutral text like "The meeting is at 4 PM" with a scared prompt produces ambiguous results. Use evocative text.

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

### Request (Gemini — optimized with all levers)

```json
{
    "model": "google/gemini-3-1-flash-tts",
    "input": {
        "temperature": 1,
        "scene": "A quiet warm room with a fireplace crackling softly",
        "sample_context": "Audiobook style narration. Tone is gentle and inviting.",
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

## Storyboard & character sheet workflow

This experiment provides the tools for the pre-production phase defined in fundamentals.

### 1. Character sheet

```bash
./ag-01/bin/kie-image.sh "Character description, front view, full body, white background" "3:4" "basic"
```

### 2. Storyboard frames

```bash
./ag-01/bin/kie-image.sh --image-url <char_url> "Scene description with character in environment" "16:9" "basic"
```

Use `--image-url` with the character portrait for consistent characters across scenes.

### 3. Narration (optimized with Gemini TTS levers)

For best results, use all three levers: `sample_context` (tone), `scene` (environment), and markup tags:

```bash
# Generate a JSON payload instead of using the simple script:
cat > /tmp/narration.json << 'JSON'
{
    "model": "google/gemini-3-1-flash-tts",
    "input": {
        "temperature": 1,
        "scene": "Environment description, e.g. A quiet library at night",
        "sample_context": "Tone/style prompt, e.g. Excited but whispering",
        "speakers": [{"speaker_id": "Speaker 1", "voice_name": "Zephyr", "audio_profile": "Character description", "accent": "Neutral", "style": "Whisper", "pace": "Rapid Fire"}],
        "dialogue_turns": [{"speaker_id": "Speaker 1", "text": "Use markup tags like [short pause] [sigh] [laughing] for natural delivery."}]
    }
}
JSON
curl -sS "https://api.kie.ai/api/v1/jobs/createTask" \
  -H "Authorization: Bearer $KIE_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST -d @/tmp/narration.json
```

### 4. Output

- Character images → `output/kie_TIMESTAMP_TAG.jpg`
- Scene images → `output/kie_TIMESTAMP_sceneN_NAME.jpg`  
- TTS → `output/tts_v2/NAME.mp3`
- Final video → `output/storyboard_v2.mp4`

## Learnings — Gemini TTS from Google Cloud docs

Source: https://docs.cloud.google.com/text-to-speech/docs/gemini-tts

### Three levers of speech control

For predictable, natural results, all three must be aligned:

| Lever | Our field | What we did wrong |
|---|---|---|
| Style Prompt | `sample_context` | Left empty. Should describe tone/emotion. |
| Text Content | `dialogue_turns[].text` | Used neutral text. Should use emotionally evocative phrasing. |
| Markup Tags | Inline in text | Not used. Should add `[sigh]`, `[short pause]`, `[laughing]`, etc. |

### What we fixed in v2

| Aspect | v1 (bad) | v2 (good) |
|---|---|---|
| Voice | All "Fenrir" | Charon, Iapetus, Kore, Aoede, Zephyr |
| Accent | None | American (South) for Carl, Neutral for others |
| Style | None | Whisper, Deadpan, Empathetic, Vocal Smile |
| Pace | None | The Drift, Natural, Rapid Fire |
| Scene | `""` (empty) | Described subway, workshop, apartment, patio, library |
| sample_context | `""` (empty) | Described emotional tone per character |
| Markup tags | None | `[sigh]`, `[short pause]`, `[medium pause]`, `[laughing]` |

### Available voices (30)

Achernar, Achird, Algenib, Algieba, Alnilam, Aoede, Autonoe, Callirrhoe, Charon, Despina, Enceladus, Erinome, Fenrir, Gacrux, Iapetus, Kore, Laomedeia, Leda, Orus, Puck, Pulcherrima, Rasalgethi, Sadachbia, Sadaltager, Schedar, Sulafat, Umbriel, Vindemiatrix, Zephyr, Zubenelgenubi

### Available styles

Vocal Smile, Newscaster, Whisper, Empathetic, Promo/Hype, Deadpan

### Available accents

Neutral, American (Gen), American (Valley), American (South), British (RP), British (Brixton), Transatlantic, Australian

### Available paces

Natural, Rapid Fire, The Drift, Staccato

### Known limitations

- Temperature, top_k, top_p generation config params are **ignored** by the API (per Google Cloud docs)
- Max 8,000 bytes total for prompt + text fields
- Max 10,000 characters per dialogue turn (per KIE docs)
- Audio truncated at ~655 seconds
