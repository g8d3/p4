# Pro feature 1 — voice notes without the 60 s cap, transcription, EN↔ES translation

Plan only (2026-10-25 17:5x Bogotá). No code yet, no spend. Read with the queue item `q21-pro-voice-plan`.

## Where transcription runs today
- Browser, extension: records the note and stores it locally (`datos` in `storage.local`). It leaves the device only when the user turns **sync on**; then the encrypted item goes through ntfy.sh.
- Mini PC, server side: `echolike_receptor.py` decrypts, downloads the audio attachment, writes a temp file and calls `stt.transcribir()` → `stt_worker.py` inside `.venv_stt`.
- Model: **faster-whisper `base`, CPU int8**, language auto-detected but restricted to es/en. Transcript goes to `razones.jsonl` / `notas_voz.guardar()` and appears in the private Today/likes view.
- Nothing is sent back to the extension: the extension has no transcripts today, so searchable transcripts exist only on the private page.

## Cost
- Transcription: **$0 per use**, self-hosted, no API key and no network at inference time. Cost is CPU time on the mini PC.
- Measured on this machine (2026-10-25): 99 s English audio → 8.8 s wall (~**11× realtime**), model cached. A 5-minute note ≈ 27 s CPU.
- Translation: **not implemented anywhere today** (no translate code in e092 besides the private-page builder). Options:
  1. Local NMT (Opus-MT / Argos) in a new isolated venv: $0 per use, model ~0.3–1 GB, CPU seconds; quality must be tested on real notes.
  2. Existing LLM credits (OpenCode Go / Zhipu): per-use credit spend, quality high. **Needs Nova's approval** and a spending decision.
  3. Skip translation at launch, ship transcription only.

## Recommended scope
- Phase 1 (no paid API): Pro removes the 60 s cap (e.g. 300 s), audio stays local; opt-in sync transcribes on the mini PC as today; transcript in the private view. Extension UI gets a local Pro preview toggle.
- Phase 2: local NMT spike for EN↔ES; only if quality is acceptable, ship it. Do not use a paid API without Nova.

## Risks / open questions
- Long audio size vs ntfy attachment limits and the queue retry cap (30 tries); measure a 5-min webm before promising sync.
- 5-min base64 audio in `storage.local` is large but the extension has `unlimitedStorage`; export files grow accordingly.
- Transcripts do not flow back to the browser today; extension-side transcript search would need a new server→extension push.
