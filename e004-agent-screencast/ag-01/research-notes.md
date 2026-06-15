# TTS Research Notes — June 2026

## Top Models by Downloads (Hugging Face)

### 1. Kokoro-82M (11.7M downloads) — hexgrad
- **82M params**, Apache-2.0 license
- StyleTTS 2 architecture + iSTFTNet
- 8 languages, 54 voices
- Trained on permissive/non-copyrighted audio only
- Cost: ~$1/M characters, ~$0.06/hour audio
- Training cost: ~$1000 on A100 80GB
- Very fast, lightweight, production-ready
- **Best for**: cost-efficient, permissive licensing, quick deployment

### 2. XTTS-v2 (6.9M downloads) — Coqui
- **Voice cloning** with just 6-second audio clip
- 17 languages (EN, ES, FR, DE, IT, PT, PL, TR, RU, NL, CS, AR, ZH, JA, HU, KO, HI)
- Emotion/style transfer, cross-language cloning
- 24kHz sampling rate
- Coqui Public Model License (not fully open)
- **Best for**: multilingual voice cloning, quick reference-based synthesis

### 3. OmniVoice (1.69M downloads) — k2-fsa
- 0.6B params
- 600+ languages
- High-quality voice cloning TTS
- **Best for**: extreme multilingual coverage

### 4. Qwen3-TTS (1.45M downloads) — Alibaba/Qwen
- **2B params**, Apache-2.0 license
- 10 major languages + dialects
- Custom voice, voice design, voice cloning
- Streaming support (97ms latency)
- Instruction-controlled tone/emotion
- State-of-the-art on Seed-TTS benchmarks
- **Best for**: quality, streaming, instruction control

### 5. Chatterbox (1.28M downloads) — Resemble AI
- **0.5B params**, MIT license
- 23 languages (V3 multilingual)
- Emotion exaggeration control
- Watermarked outputs (Perth)
- Outperforms ElevenLabs in benchmarks
- 0.5M hours training data
- **Best for**: production-grade, emotion control, responsible AI

### 6. F5-TTS (395K downloads) — SWivid
- Flow matching architecture
- CC-BY-NC-4.0 license (non-commercial)
- Trained on Emilia dataset
- **Best for**: research, high-quality synthesis

### 7. VoxCPM2 (251K downloads) — OpenBMB
- **2B params**, Apache-2.0
- 30 languages, 48kHz output
- Tokenizer-free diffusion autoregressive
- Voice design, controllable cloning, ultimate cloning
- Streaming (RTF ~0.3 on RTX 4090)
- 2M+ hours training data
- **Best for**: multilingual, high fidelity, streaming

### 8. CSM 1B (194K downloads) — Sesame
- **1B params**, Apache-2.0
- Conversational Speech Model
- Llama backbone + Mimi audio codes
- Best with context (multi-turn)
- Supports batched inference
- English only
- **Best for**: conversational AI, multi-turn dialogue

## Other Notable Models

- **microsoft/VibeVoice-Realtime-0.5B** (509K downloads) — Real-time, 1B params
- **OpenMOSS-Team/MOSS-TTS** (353K downloads) — 8B params, voice cloning
- **microsoft/speecht5_tts** (75K downloads) — Lightweight, 36.3M params
- **myshell-ai/MeloTTS** (92K downloads) — English, Korean, Spanish variants

## Key Trends

1. **Voice cloning is table stakes**: Most top models support zero-shot voice cloning from short audio clips
2. **Multilingual explosion**: 10-30 languages is now standard, with 600+ for some
3. **Streaming/real-time**: Low-latency streaming is critical for interactive applications
4. **Apache-2.0 licensing**: Open models winning over proprietary (Kokoro, Qwen3, VoxCPM2, CSM)
5. **Instruction control**: Natural language instructions to control tone, emotion, pace
6. **Flow matching / diffusion**: New architectures replacing pure autoregressive approaches
7. **Quality convergence**: Open models matching or beating ElevenLabs in benchmarks

## Licensing Summary

| Model | License | Commercial Use |
|-------|---------|----------------|
| Kokoro-82M | Apache-2.0 | Yes |
| XTTS-v2 | Coqui Public | Limited |
| Qwen3-TTS | Apache-2.0 | Yes |
| Chatterbox | MIT | Yes |
| VoxCPM2 | Apache-2.0 | Yes |
| CSM 1B | Apache-2.0 | Yes |
| F5-TTS | CC-BY-NC-4.0 | No |
