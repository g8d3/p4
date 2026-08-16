# TTS research — realistic voices with emotion support (2026-08-15)

Context: e029 used Kokoro (the HyperFrames offline fallback) for Spanish narration —
functional but flat. This document maps the better options and what p4 has keys for.

## What p4 has right now (tested 2026-08-15)

| Provider | Access | Voices | Emotion control | Status |
|---|---|---|---|---|
| **Deepgram Aura-2** | `DEEPGRAM_API_KEY` set | 17 Spanish (incl. **es-co Colombian** `aura-2-celeste-es`), 40+ English, 7 langs | `speed` (0.7–1.5, es ≥0.9) + IPA pronunciation overrides | ✅ Tested — REST works, returns WAV |
| **KIE Gemini TTS** | `KIE_API_KEY` set | 30 voices (preferred: Alnilam, Gacrux, Puck, Sulafat, Umbriel, Vindemiatrix) | `--style` (Vocal Smile / Newscaster / Whisper / Empathetic / Promo / Deadpan), scene, context, accent, pace | ✅ Tested — `kie-tts.sh` works |
| Deepgram Flux | same key | English only at GA (launched 2026-08-12) | None needed — expressive by default, reads conversation | Free through 2026-09-12; **no Spanish yet** |

## Leaderboard leaders (mid-2026)

- **Artificial Analysis Speech Arena**: SpeechifyAI Simba 3.2 (Elo 1239) · Qwen-Audio-3.0-TTS-Plus (1237) · Luna TTS (1219) · **Gemini 3.1 Flash TTS (1212 — this is KIE)** · StepAudio 2.5 (1205). Shifts weekly.
- **HuggingFace TTS Arena** (TTS-AGI/TTS-Arena-V2): community blind voting.
- Deepgram's own July-2026 blind test (naturalness): Flux TTS 73.4% > Cartesia Sonic 3.5 72.0% > Gemini 2.5 Flash 62.4% > Rime Arcana 61.4% > ElevenLabs v3 61.2%.

## Emotion-capable providers (the point of this doc)

| Provider | Model | Emotion mechanism | Price | Notes |
|---|---|---|---|---|
| **Fish Audio** | S2.1 Pro | Free-form `[tag]` inline, 15k+ tags (`[whisper]`, `[excited]`, `[sigh]`, …), 64+ named emotions | $15/1M chars; **free dev tier** `s2.1-pro-free` | #1 TTS-Arena; 80+ langs incl. Spanish; multi-speaker; open weights (research license) |
| **Deepgram Flux** | flux-{voice}-en | None needed — context-aware, expressive default | Free thru Sep 12, 2026 | English-only at GA; built for voice agents |
| **Hume** | Octave 2 | LLM reads meaning, adapts tone automatically (no tags) | ~$7.60/1M chars | Top-6 HF arena; empathy-first |
| **ElevenLabs** | v3 / Flash v2.5 | Style presets + multi-speaker dialogue | credits | Expressiveness leader for narration |
| **Cartesia** | Sonic 3.5 | Real-time emotion/laughter, 42 langs | per-char | ~40–82ms TTFB, agent-focused |
| **MiniMax** | Speech 2.x | Emotion control at competitive price | per-char | Text-to-dialogue, multiple speakers |
| **Inworld** | Realtime TTS-2 | Full voice pipeline | per-char | Sub-250ms |
| **OpenAI** | gpt-4o-mini-tts | Natural-language instructions | token-based | Tight GPT integration |

Open-source with emotion: **Orpheus** (3B, 100k h), **Chatterbox** (Resemble), **IndexTTS-2** (duration control for dubbing), **CosyVoice3**, **Sesame CSM**, **Spark TTS**.

## Recommendation for p4 narration

1. **Spanish video narration** → Deepgram **`aura-2-celeste-es`** (es-co Colombian, energetic/friendly, free credits) or KIE Gemini preferred voice (leaderboard-proven, style control). Deepgram wins on cost; KIE wins on expressiveness dials.
2. **Emotion-heavy / marketing lines** → Fish Audio `s2.1-pro-free` (`[tag]` direction) — sign up for a `FISH_API_KEY`.
3. **Future voice agents** → Deepgram Flux (free window, English).
4. Keep **KIE Gemini TTS** as the p4 primary per e000 AGENTS.md; Deepgram as the economical high-quality alternative for Spanish.

## Reusable wrapper

`../bin/dg-tts.sh` — Deepgram Aura-2 TTS wrapper (reads text, writes WAV; `--voice`, `--speed`, `--out`). Mirrors `kie-tts.sh` ergonomics.
