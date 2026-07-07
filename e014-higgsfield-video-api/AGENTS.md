# e014 — Higgsfield Video API

Experiments with the [higgsfield-client](https://github.com/higgsfield-ai/higgsfield-client) Python SDK for video generation via the Higgsfield AI platform.

## Learnings

- SDK `higgsfield-client` v0.1.0 is installed in the project venv (`.venv/`)
- Auth uses `HF_API_KEY` + `HF_API_SECRET` env vars, combined as `Key {key}:{secret}`
- SDK base URL: `https://platform.higgsfield.ai`
- `agent-browser` CLI is available for navigating web pages programmatically

### Video application endpoints (confirmed working)

| Application | Status |
|---|---|
| `higgsfield-ai/dop/standard` | Recognized, returns `not_enough_credits` |
| `kling-video/v2.1/pro/image-to-video` | Recognized, returns `not_enough_credits` |
| `bytedance/seedance/v1/pro/image-to-video` | Not found (may need different path) |

### Image application endpoints

| Application | Status |
|---|---|
| `bytedance/seedream/v4/text-to-image` | Returns 404 "Model not found" (outdated) |

### API call format

```python
import higgsfield_client as hf

result = hf.subscribe(
    'higgsfield-ai/dop/standard',
    arguments={
        'image_url': 'https://example.com/image.jpg',
        'prompt': 'A cinematic camera pan across a scene',
        'duration': 5,
    }
)
```

### Auth

```bash
export HF_API_KEY="your-api-key"
export HF_API_SECRET="your-api-secret"
```

The SDK combines them as `{key}:{secret}` and sends `Authorization: Key {combined}`.

### Credits

The current API key lacks credits for video generation (error: `not_enough_credits`). File uploads work without credits.

## API Documentation

Official docs: https://docs.higgsfield.ai/docs

Relevant pages:
- Generate Videos from Images: https://docs.higgsfield.ai/docs/guides/video
- Client Libraries: https://docs.higgsfield.ai/docs/api/client-libraries
- Available models gallery linked from the guides.

## Agents

- `ag-01/` — owns the generate_video.py script
