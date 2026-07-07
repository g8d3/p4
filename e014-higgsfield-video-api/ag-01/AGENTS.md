# ag-01 — Higgsfield Video Generator

Owns `generate_video.py` — a script to generate videos using the Higgsfield API.

## Usage

```bash
export HF_API_KEY="your-api-key"
export HF_API_SECRET="your-api-secret"
python generate_video.py
```

## Dependencies

- `higgsfield-client` (v0.1.0) — Python SDK for Higgsfield API
- `httpx` — HTTP client (dependency of higgsfield-client)

## Inherits
- [../AGENTS.md](../AGENTS.md) — experiment context, endpoints, auth
