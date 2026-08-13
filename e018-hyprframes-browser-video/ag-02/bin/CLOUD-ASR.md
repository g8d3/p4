# Cloud transcription options (research, 2026-08-12)

Local Parakeet (NeMo) breaks on this machine: the venv lives in `/tmp` and gets
wiped, and the `nemo_toolkit` install is fragile (old `youtokentome` package
fails to build on Python 3.11; heavy RAM use). This file documents the cloud
alternatives researched as a replacement. Prices verified from APIScout's STT
comparison (2026-03) unless noted — re-check the provider page before relying
on them.

## What p4 actually needs

Our videos have 2–4 minutes of narration. At these volumes the cost difference
between providers is noise — everything is fractions of a cent per video. Pick
based on: free tier, existing API key, and how easy the API is.

## Verified pricing table

| Provider | Model | Price | Free tier | Notes |
|---|---|---|---|---|
| OpenAI | `gpt-4o-mini-transcribe` | $0.003/min ($0.18/h) | none | Cheapest managed; word timestamps; 25 MB/file limit |
| OpenAI | `whisper-1` (legacy) | $0.006/min | none | Batch only, no longer recommended |
| OpenAI | `gpt-4o-transcribe` | $0.006/min | none | ~35% better WER than whisper-1, streaming |
| Deepgram | `nova-3` | $0.0077/min ($0.46/h) | **$200 credit ≈ 433 h free** | Best batch accuracy (5.26% WER) |
| AssemblyAI | `universal` (batch) | $0.0062/min ($0.37/h) | $50 credit ≈ 185 h free | Rich features (chapters, diarization, LeMUR) |
| Google | `chirp-3` Dynamic Batch | $0.004/min ($0.24/h) | **60 min/month permanent** | Best multilingual; 24 h async SLA |
| Groq | `whisper-large-v3(-turbo)` | free (rate-limited) | free | Fast LPU inference; ~20 req/min dev tier; no word timestamps? (verify) |
| NVIDIA NIM | `parakeet-tdt-0.6b-v2` | free tier (verify) | free research tier | **Same Parakeet family p4 uses locally**, hosted; account + API key |

## Recommendation for p4

1. **If you want zero setup + a free tier that lasts years: Deepgram**
   `$200` credit ≈ 433 hours of transcription. Our whole p4 video catalog is
   well under that. Batch API, word timestamps via `utterances`/`words`.
2. **If you want the same model we already know: NVIDIA NIM Parakeet**
   hosted `parakeet-tdt-0.6b-v2` — no local RAM, no venv, no youtokentome.
   Requires an NVIDIA account + API key (free tier).
3. **If you already have an OpenAI key: `gpt-4o-mini-transcribe`**
   $0.003/min, word timestamps in `verbose_json`, dead-simple curl.
4. **Google Chirp 3 Dynamic Batch** if you want a permanent small free tier
   (60 min/month) and don't need instant results.

## Cost for a typical p4 video (3.5 min narration)

| Provider | Cost per video |
|---|---|
| OpenAI gpt-4o-mini-transcribe | $0.0105 |
| Deepgram nova-3 | $0.027 |
| Google Chirp 3 dynamic batch | $0.014 |
| Groq / NVIDIA NIM (free tier) | $0.00 |

## How to wire it in (once a key exists)

Add a small wrapper script in `e018-hyprframes-browser-video/ag-02/bin/`
(e.g. `transcribe_cloud.sh`) that uploads the audio, polls the job, and writes
`<audio>.srt` + `<audio>.txt` + `words_raw.json` in the same shape as the local
Parakeet server (`text`, `srt`, `words_raw` with word `start`/`end`). Then the
rest of the p4 pipeline (`compute_timing.py`, caption scenes) works unchanged.

## Why local Parakeet kept breaking (so we don't repeat it)

- The venv `/tmp/nemo_venv` is on tmpfs — wiped on reboot, no lockfile.
- `nemo_toolkit[asr]` pulls `youtokentome` (2019, no cp311 wheel) which fails to
  build from source (needs Cython + Rust).
- NeMo + torch in RAM on a 15 GB machine competes with the editor/browser for
  memory → the user's "RAM problems".
- If local ASR is ever needed again, prefer `faster-whisper` (CTranslate2,
  prebuilt wheels, ~2–4 GB RAM) over nemo — but the cloud options above are the
  intended path.
