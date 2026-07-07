# Design trail

## 2026-07-06 — Initial session

### Context

User asked to generate a test video using the Higgsfield API from https://github.com/higgsfield-ai/higgsfield-client.

### Process

1. Installed `higgsfield-client` v0.1.0 via `uv pip install`
2. Read the SDK source code to understand the API (sync/async client, auth, submit/subscribe patterns)
3. Discovered `agent-browser` CLI was already installed — used it to explore:
   - The Higgsfield GitHub repo (README showed only image examples: `bytedance/seedream/v4/text-to-image`)
   - The Higgsfield web app at `higgsfield.ai` (found video generation UI using Seedance 2.0)
   - GitHub issues (issue #1 asking about motion presets — unanswered)
   - The Higgsfield API docs at `docs.higgsfield.ai/docs` — found the actual video endpoints
4. Verified auth works: `POST /files/generate-upload-url` returned 200
5. Tested image endpoint `bytedance/seedream/v4/text-to-image` → 404 "Model not found" (outdated)
6. Found correct endpoints from docs:
   - `higgsfield-ai/dop/standard` → `not_enough_credits` (endpoint exists, needs credits)
   - `kling-video/v2.1/pro/image-to-video` → `not_enough_credits`
   - `bytedance/seedance/v1/pro/image-to-video` → Model not found

### Key findings

- The SDK v0.1.0 is functional but its documented examples are outdated
- The correct API endpoint format is `https://platform.higgsfield.ai/{application}`
- Auth format: `Authorization: Key {api_key}:{api_secret}`
- Video generation requires sufficient credits on the account
- `agent-browser` is a powerful CLI tool for web automation available in this environment

### Performance: Chrome + SwiftShader CPU drain

`agent-browser` headless Chrome uses SwiftShader (software GPU), consuming ~160% CPU.
Fix: always run `agent-browser close --all` when the browser is not actively needed.

### Pending

- Get credits on the Higgsfield account to actually generate a video
- Find the correct endpoint name for seedance models
- Test image generation endpoints
