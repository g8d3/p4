# e026 — Composio Playground

## Inherits
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, env-var conventions

First Composio integration in this repo: connect a real app (Deepgram) through
the **Composio Platform** and run a real transcription tool call.

## Setup (already done)

- `COMPOSIO_API_KEY` (Platform project key, `ak_...`) lives in
  `~/.secrets/.env`, sourced by `~/.zshrc`. Never print, rotate, or commit it.
  Never run `composio dev init` for this key.
- `DEEPGRAM_API_KEY` (also in `~/.secrets/.env`) authenticates Deepgram via a
  Composio custom auth config (API_KEY scheme, `generic_api_key`).
- Local venv: `.venv/` with `composio` SDK (0.19.x).
- No Composio CLI needed — everything goes through the Python SDK.

## Run

```bash
source ~/.zshrc                      # exports COMPOSIO_API_KEY + DEEPGRAM_API_KEY
.venv/bin/python bin/transcribe.py   # transcribe the default NASA sample
.venv/bin/python bin/transcribe.py <public-audio-url>
```

Writes to `output/`: `transcript.txt`, `result.json`, `log_id.txt`.

## How it works

1. `Composio()` reads `COMPOSIO_API_KEY` from the environment (project auth).
2. `composio.create(user_id=..., toolkits=["deepgram"])` makes a **session** —
   the runtime context for one application user. The user id here is
   `COMPOSIO_TEST_USER_ID` or `vuos`.
3. `composio.tools.execute(...)` runs
   `DEEPGRAM_SPEECH_TO_TEXT_PRE_RECORDED` on a public audio URL.
   - `custom_connection_data` supplies the Deepgram API key inline
     (`auth_scheme=API_KEY`, `val.generic_api_key`) — no OAuth / Connect Link
     needed for API-key apps.
   - `version` is required for manual execution: Deepgram toolkit version is
     `20260707_00`. Discover current versions via
     `toolkits.get(slug=...)` → `meta.available_versions`.

## Pitfalls (learned)

- Session object uses `.session_id`, not `.id`.
- `tools.execute` returns a plain `dict` (no `.model_dump()`).
- Toolkit version is mandatory for manual `tools.execute`; "latest" is not
  accepted. Fetch the toolkit to read `meta.available_versions[0]`.
- `logs.tools.list(cursor=0, limit=N)` gives the Composio execution log IDs
  (status, app, entity, execution time). Verify success there.
- `toolkits.get(query=...)` does **not** accept free-text `q`; to search tools
  use `tools.get(user_id=..., search="...")` — returns raw tool schemas.
- Never print the API keys; only ever compare length/prefix.

## What's verified

- Real transcript from a 25.9 s NASA spacewalk interview WAV, confidence
  0.998 (nova-2 model).
- Composio log IDs present and `status: success`
  (e.g. `log_41-HHmzqm9-x`), entity `vuos`, execution ~1 s.
- Discovery works at runtime: `search="transcribe audio"` surfaced Deepgram,
  Eranol (video captioning), AssemblyAI, CastingWords, Gladia, etc.

## What to try next

- **Persistent connection**: create an auth config
  (`auth_configs.create(toolkit="deepgram", {type:"use_custom_auth", auth_scheme:"API_KEY"})`),
  then `connected_accounts.initiate(...)` once and reuse the connected account
  instead of inline `custom_connection_data`.
- **Any toolkit with OAuth** (GitHub, Gmail, Slack, Notion): session meta tools
  `COMPOSIO_MANAGE_CONNECTIONS` return a Connect Link; authorize, wait, then execute.
- **Search-first agent loop**: let an agent call `COMPOSIO_SEARCH_TOOLS`, pick
  a slug, and execute — the runtime-discovery path used by production agents.
- **Video transcription**: try `ERANOL_CAPTION_VIDEO` (burns styled captions,
  produces subtitles) or AssemblyAI/CastingWords for long-form files.
- **Wrap in a CLI/flow**: transcribe a local file by hosting it (e006 filex /
  any public URL) and piping the transcript into a p4 pipeline (e023 narration
  sync, subtitles via the Parakeet stack).
