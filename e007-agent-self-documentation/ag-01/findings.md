# Real-Time TTS Research Findings

**Agent**: ag-01 (self-recording)
**Date**: 2026-06-17
**Task**: Investigate real-time TTS options for video narration

## Summary

Researched 9 TTS solutions across cloud and local categories. Evaluated on latency, cost, quality, Spanish support, license, and real-time streaming capability.

## Recommendations

### Primary: edge-tts
- Free, no API key, Colombian Spanish voices (es-CO-SalomeNeural / es-CO-GonzaloNeural)
- Streaming capable, good quality, GPL-3.0
- Already used in our pipeline (e004, e005, e006)

### Local fallback: Kokoro
- 82M params, Apache-2.0, very fast inference
- Spanish support (lang_code='e')
- Lightweight, runs anywhere

## Cloud TTS Options

### edge-tts
- **Latency**: Low (streaming via websocket)
- **Cost**: Free (no API key needed)
- **Quality**: Good (Microsoft neural voices)
- **Spanish**: es-CO-SalomeNeural, es-CO-GonzaloNeural
- **License**: GPL-3.0
- **GitHub**: 11.3k stars
- **Streaming**: Yes
- **Note**: Uses Microsoft Edge's online TTS service

### ElevenLabs
- **Latency**: Very low (~200ms TTFB via WebSocket)
- **Cost**: Free tier 10k credits/mo, Starter $6/mo, Creator $11/mo, Pro $99/mo
- **Quality**: Excellent (industry leading)
- **Spanish**: Multilingual v2/v2.5 models
- **License**: Proprietary
- **Streaming**: Yes (WebSocket with chunk_length_schedule)
- **Note**: Best quality but expensive at scale

### Cartesia
- **Latency**: Ultra-low (streaming TTS API)
- **Cost**: Free tier available, paid plans
- **Quality**: Excellent (sonic-3, sonic-3.5 models)
- **Spanish**: Yes (es in supported languages)
- **License**: Proprietary
- **Streaming**: Yes
- **Note**: Emotion control (volume, speed, 50+ emotions)

### Deepgram
- **Latency**: Low (streaming)
- **Cost**: Free tier, pay-as-you-go
- **Quality**: Good (aura-2 models)
- **Spanish**: Limited (primarily English)
- **License**: Proprietary
- **Streaming**: Yes
- **Note**: Max 2000 chars per request

## Local TTS Options

### Piper (piper1-gpl)
- **Latency**: Very low (local C++ inference)
- **Cost**: Free
- **Quality**: Good (fast, lightweight)
- **Spanish**: Community voices available
- **License**: GPL-3.0
- **GitHub**: 4.5k stars (piper1-gpl), 11.1k (original, archived)
- **Streaming**: Yes (local, near-instant)
- **Note**: Original repo archived, moved to piper1-gpl under Open Home Foundation

### Coqui TTS
- **Latency**: Medium-High (depends on model/GPU)
- **Cost**: Free
- **Quality**: Excellent (XTTS v2, state-of-the-art)
- **Spanish**: Yes (XTTS v2, 16 languages)
- **License**: MPL-2.0
- **GitHub**: 45.6k stars
- **Streaming**: XTTS v2 can stream <200ms
- **Note**: Company shut down Dec 2023, project open-sourced

### Kokoro
- **Latency**: Very low (82M params, fast inference)
- **Cost**: Free
- **Quality**: Good (comparable to larger models)
- **Spanish**: Yes (lang_code='e')
- **License**: Apache-2.0
- **GitHub**: 7.5k stars
- **Streaming**: Yes (fast local)
- **Note**: Lightweight, based on StyleTTS2 architecture

### Fish Speech (S2 Pro)
- **Latency**: Ultra-low (~100ms TTFA on H200)
- **Cost**: Free (research license)
- **Quality**: State-of-the-art (4B params, 80+ languages)
- **Spanish**: Yes (Tier 2 language)
- **License**: Fish Audio Research License (NOT fully open source)
- **GitHub**: 30.9k stars
- **Streaming**: Yes (RTF 0.195 on H200)
- **Note**: Requires significant GPU (4B model), research-only license

### StyleTTS2
- **Latency**: Medium (diffusion-based)
- **Cost**: Free
- **Quality**: Human-level (surpasses human recordings on LJSpeech)
- **Spanish**: Limited (English-focused, multilingual PL-BERT available)
- **License**: MIT (code), custom (pre-trained models)
- **GitHub**: 6.3k stars
- **Streaming**: Experimental (GPL fork has streaming API)
- **Note**: Best quality for English, needs fine-tuning for other languages

## Comparison Matrix

| Tool | Latency | Cost | Quality | Spanish | License | Real-time | GitHub Stars |
|------|---------|------|---------|---------|---------|-----------|-------------|
| edge-tts | Low | Free | Good | es-CO | GPL-3.0 | Yes | 11.3k |
| ElevenLabs | Very Low | $0-999/mo | Excellent | Yes | Proprietary | Yes | N/A |
| Cartesia | Ultra Low | Free/Paid | Excellent | Yes | Proprietary | Yes | N/A |
| Deepgram | Low | Free/Paid | Good | Limited | Proprietary | Yes | N/A |
| Piper | Very Low | Free | Good | Community | GPL-3.0 | Yes | 4.5k |
| Coqui TTS | Medium | Free | Excellent | Yes (XTTS) | MPL-2.0 | Yes | 45.6k |
| Kokoro | Very Low | Free | Good | Yes | Apache-2.0 | Yes | 7.5k |
| Fish Speech | Ultra Low | Free* | SOTA | Yes | Research* | Yes | 30.9k |
| StyleTTS2 | Medium | Free | Human-level | Limited | MIT | Experimental | 6.3k |

*Fish Speech: Research license, not commercially friendly

## Real-Time Streaming Comparison

| Tool | Streaming Method | TTFB | Chunked |
|------|-----------------|------|---------|
| edge-tts | WebSocket | ~100ms | Yes |
| ElevenLabs | WebSocket | ~200ms | Yes (configurable) |
| Cartesia | HTTP/WS | Ultra-low | Yes |
| Deepgram | HTTP streaming | Low | Yes |
| Piper | Local | Instant | N/A |
| Coqui XTTS | Local streaming | <200ms | Yes |
| Kokoro | Local | Instant | N/A |
| Fish Speech | Local (SGLang) | ~100ms | Yes |
| StyleTTS2 | Local | Medium | Experimental |

## Decision

For our video pipeline (e004/e007):
1. **edge-tts** remains the primary choice (free, Colombian voices, proven)
2. **Kokoro** as local fallback (Apache-2.0, fast, Spanish support)
3. **ElevenLabs** for highest quality when budget allows
4. **Coqui XTTS** for voice cloning needs
