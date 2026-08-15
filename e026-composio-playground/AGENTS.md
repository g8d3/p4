# e026 — Audio Transcription Playground

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, env-var conventions

Transcribe audio/video to text via **Deepgram directly** (REST API, no middleware).
This started as a Composio integration test; after comparing, direct API calls win for
this use case (fewer keys, fewer concepts, same result). Composio was removed.

## Setup (already done)

- `DEEPGRAM_API_KEY` lives in `~/.secrets/.env`, sourced by `~/.zshrc`.
  Never print it or commit it.
- No SDK needed — Python standard library only.
- `.venv/` is only for convenience; `transcribe_direct.py` needs no packages.

## Run

```bash
source ~/.zshrc
.venv/bin/python bin/transcribe_direct.py                 # NASA sample
.venv/bin/python bin/transcribe_direct.py <public-audio-url>
```

Even shorter (one-liner for pipelines):

```bash
curl -s -X POST "https://api.deepgram.com/v1/listen?model=nova-2" \
  -H "Authorization: Token $DEEPGRAM_API_KEY" -H "Content-Type: application/json" \
  -d '{"url":"<audio-url>"}' | jq -r '.results.channels[0].alternatives[0].transcript'
```

## How it works

One POST to `https://api.deepgram.com/v1/listen?model=nova-2` with
`Authorization: Token <DEEPGRAM_API_KEY>` and a JSON body `{"url": <public-url>}`.
Transcript lives at `results.channels[0].alternatives[0].transcript`.

For local files: upload bytes as the request body (`?model=nova-2`) instead of `{"url": ...}`.

## Notes

- Requires a **publicly downloadable URL** for the URL mode. For private/local
  audio, send the raw bytes as the POST body.
- Nova-2 model is a good default; `phonecall`, `general`, etc. are available.

## Compared to Composio (reference, removed)

- Composio version needed `COMPOSIO_API_KEY` + `DEEPGRAM_API_KEY`, sessions,
  toolkit versions, custom_connection_data, log IDs (~75 lines).
- Direct version: 1 HTTP call, 1 key, 20 lines, identical transcript (conf 0.998).
- Composio earns its place when scaling to many apps/users with OAuth
  (multi-app agent flows), not for a single fixed integration like this.
