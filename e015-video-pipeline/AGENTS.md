# e015 — Video Pipeline

**Goal**: Modular video production pipeline: research → scripts → audio → transcription → render → merge. Each step produces files that feed the next, enabling parallel processing and A/B testing.

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles, TTS, GPU encoding

## Pipeline Flow

```
User topic → ag-01 → topics.csv → ag-02 → scripts → ag-03 → audio → ag-04 → transcription → ag-05 → video → ag-06 → FINAL
```

## Agents

| Agent | Role | Reads From | Writes To |
|-------|------|------------|-----------|
| ag-01 | Research topics | `topic_prompt.txt` | `ag-01/output/topics.csv` |
| ag-02 | Write scripts | `ag-01/output/topics.csv` | `ag-02/output/script-*.md` |
| ag-03 | Generate audio | `ag-02/output/scripts-manifest.csv` | `ag-03/output/script-*/audio.*` |
| ag-04 | Transcribe | `ag-03/output/audio-manifest.csv` | `ag-04/output/script-*/transcription.*` |
| ag-05 | Render video | `ag-04/output/transcribe-manifest.csv` | `ag-05/output/script-*/video-*.mp4` |
| ag-06 | Merge audio+video | `ag-05/output/render-manifest.csv` + audio | `ag-06/output/script-*/FINAL.mp4` |

---

## AI Plans & Models

### Overview: 4 Plans Available

| Plan | Binary | Subscription | Best For |
|------|--------|--------------|----------|
| **opencode-go** | `opencode` | Monthly | General agent work |
| **Xiaomi Token Plan** | `opencode` | Token-based | TTS, ASR, vision |
| **ZAI Coding Plan** | `opencode` | 5h rolling window | Coding tasks |
| **Command Code Go** | `cmd` | Monthly credits | Chinese models + deals |

### How to Use Each Plan

#### 1. opencode-go, Xiaomi, ZAI (same binary: `opencode`)

```bash
# Format:
opencode -m <provider>/<model>

# Examples (USE EXACT PROVIDER NAMES):
opencode -m opencode-go/mimo-v2.5
opencode -m xiaomi-token-plan-sgp/mimo-v2.5      # Singapore (recommended)
opencode -m zai-coding-plan/glm-5.1               # Coding plan
```

**Required env vars:**
```bash
export OPENCODE_GO_API_KEY=tp-xxx      # opencode-go
export OPENCODE_GO_BASE_URL=...        # opencode-go
export OPENCODE_GO_MODEL=...           # opencode-go (default)
export XIAOMI_API_KEY=tp-xxx           # Xiaomi
export XIAOMI_BASE_URL=...             # Xiaomi
export ZAI_API_KEY=xxx                 # ZAI
```

**Important**: 
- Xiaomi: Always use `xiaomi-token-plan-sgp/` (Singapore) — lowest latency
- ZAI: Always use `zai-coding-plan/` — this is the coding plan provider

#### 2. Command Code Go (separate binary: `cmd`)

```bash
# Format:
cmd -m <model>

# Examples:
cmd -m deepseek/deepseek-v4-pro
cmd -m xiaomi/mimo-v2.5
cmd -m tencent/Hy3

# List all models:
cmd --list-models
```

**Note**: `cmd` is a completely separate binary with its own API keys and config.

---

## Command Code Deals (Active Promotions)

### Permanent Deals

| Model | Discount | Input (was→now) | Output (was→now) | Multiplier |
|-------|----------|-----------------|------------------|------------|
| **DeepSeek V4 Pro** | 75% off | $1.74→$0.435 | $3.48→$0.87 | 4× |
| **MiniMax M3** | 62.5% off | $0.60→$0.225 | $2.40→$0.90 | 2.7× |
| **MiMo V2.5 Pro** | 86-99% off | $2.00→$0.435 | $6.00→$0.87 | 7× |
| **MiMo V2.5** | 83-98% off | $0.80→$0.14 | $4.00→$0.28 | 14× |

### Temporary Deal

| Model | Discount | Expires | Notes |
|-------|----------|---------|-------|
| **Tencent Hy3** | **100% FREE** | July 21, 2026 | All tokens at $0 |

### Best Value Models (with deals)

1. **Tencent Hy3** — FREE (limited time) → Use aggressively before July 21
2. **MiMo V2.5** — 14× multiplier → Best bang for buck on open tasks
3. **MiMo V2.5 Pro** — 7× multiplier → High capability + great value
4. **DeepSeek V4 Pro** — 4× multiplier → Strong reasoning tasks

---

## Command Code Plans

| Plan | Price/mo | Credits/mo | 5h Limit | Weekly Limit | Models |
|------|----------|------------|----------|--------------|--------|
| Go | $1 | $10 | $3 | $6 | Open-source only |
| Pro | $15 | $30 | $9 | $18 | Open-source + premium |
| Max 10× | $100 | $150 | $45 | $90 | All |
| Max 20× | $200 | $300 | $90 | $180 | All |

---

## Available Models by Provider

### opencode-go Models (Provider: `opencode-go/`)
| Model | Provider ID | Best For |
|-------|-------------|----------|
| deepseek-v4-flash | opencode-go/deepseek-v4-flash | Fast reasoning |
| mimo-v2.5 | opencode-go/mimo-v2.5 | Coding |
| glm-5.1 | opencode-go/glm-5.1 | Long-context coding |
| kimi-k2.6 | opencode-go/kimi-k2.6 | Coding |
| minimax-m2.7 | opencode-go/minimax-m2.7 | Software engineering |

### Xiaomi Token Plan Models (Provider: `xiaomi-token-plan-sgp/`)
| Model | Provider ID | Best For |
|-------|-------------|----------|
| mimo-v2.5 | xiaomi-token-plan-sgp/mimo-v2.5 | Coding |
| mimo-v2.5-pro | xiaomi-token-plan-sgp/mimo-v2.5-pro | High capability |
| mimo-v2-tts | xiaomi-token-plan-sgp/mimo-v2-tts | Text-to-speech |
| mimo-v2.5-tts | xiaomi-token-plan-sgp/mimo-v2.5-tts | Text-to-speech |
| mimo-v2.5-tts-voiceclone | xiaomi-token-plan-sgp/mimo-v2.5-tts-voiceclone | Voice cloning |
| mimo-v2.5-tts-voicedesign | xiaomi-token-plan-sgp/mimo-v2.5-tts-voicedesign | Voice design |

### ZAI Coding Plan Models (Provider: `zai-coding-plan/`)
| Model | Provider ID | Best For |
|-------|-------------|----------|
| glm-4.7 | zai-coding-plan/glm-4.7 | Fast coding |
| glm-5-turbo | zai-coding-plan/glm-5-turbo | Fast coding |
| glm-5.1 | zai-coding-plan/glm-5.1 | Complex coding |
| glm-5.2 | zai-coding-plan/glm-5.2 | 1M context |
| glm-5v-turbo | zai-coding-plan/glm-5v-turbo | **Vision** (can see images) |

### Command Code Chinese Models (Recommended)
| Model | cmd ID | Best For | Deal |
|-------|--------|----------|------|
| MiMo V2.5 | xiaomi/mimo-v2.5 | Coding + **Vision** | 14× |
| MiMo V2.5 Pro | xiaomi/mimo-v2.5-pro | High capability + **Vision** | 7× |
| DeepSeek V4 Pro | deepseek/deepseek-v4-pro | Reasoning | 4× |
| DeepSeek V4 Flash | deepseek/deepseek-v4-flash | Fast reasoning | — |
| Kimi K2.7 Code | moonshotai/Kimi-K2.7-Code | **Vision** + coding | — |
| Kimi K2.5 | moonshotai/Kimi-K2.5 | Frontend + **Vision** | — |
| GLM-5.2 | zai-org/GLM-5.2 | 1M context (text only) | — |
| GLM-5.1 | zai-org/GLM-5.1 | Autonomous coding (text only) | — |
| MiniMax M3 | MiniMaxAI/MiniMax-M3 | Agents + multimodal | 2.7× |
| Qwen 3.7 Max | Qwen/Qwen3.7-Max | Frontier coding | — |
| Tencent Hy3 | tencent/Hy3 | FREE (until Jul 21) | ∞ |

### Command Code Premium Models
| Model | cmd ID | Price/M (input/output) |
|-------|--------|------------------------|
| Claude Sonnet 5 | claude-sonnet-5 | $2/$10 |
| Claude Opus 4.8 | claude-opus-4-8 | $5/$25 |
| GPT-5.5 | gpt-5.5 | $5/$30 |
| GPT-5.4 | gpt-5.4 | $2.50/$15 |
| Gemini 3.5 Flash | google/gemini-3.5-flash | $1.50/$9 |

---

## Model Selection for Pipeline Tasks

| Task | Recommended Model | Plan | Why |
|------|-------------------|------|-----|
| **ag-01 Research** | deepseek-v4-flash | opencode-go | Fast, good at search |
| **ag-02 Scripts** | mimo-v2.5 | cmd (14× deal) | Great writing + cheap |
| **ag-03 Audio (TTS)** | mimo-v2-tts | xiaomi-token-plan-sgp | Native TTS |
| **ag-04 Transcription** | whisper.cpp | Local | Free, fast |
| **ag-05 Render** | glm-5v-turbo | zai-coding-plan | Vision for review |
| **ag-06 Merge** | mimo-v2.5 | cmd (14× deal) | Cheap verification |

### What is "Vision" (can see images/videos)?

Models with **vision** can analyze images and videos. In this pipeline, we use them to:
- **Review video output**: Check if the video looks correct, subtitles are readable, etc.
- **Verify quality**: Ensure the final video meets standards

**Models with vision:**
- `cmd`: Kimi K2.5/K2.6/K2.7-Code, MiMo V2.5/V2.5 Pro
- `opencode`: xiaomi-token-plan-sgp/mimo-v2.5 (if it has vision)
- `zai-coding-plan`: glm-5v-turbo (the "v" means vision)

**Models WITHOUT vision (text only):**
- `zai-coding-plan`: glm-4.7, glm-5.1, glm-5.2, glm-5-turbo
- `cmd`: GLM-5.1, GLM-5.2, DeepSeek models

---

## Tools by Step

### ag-01: Research
- `agent-browser` (CDP CLI) — browse, scrape, extract
- `edge-tts` — test voice availability

### ag-02: Scripts
- LLM via API (Mimo 2.5, DeepSeek)
- Template: `script-template.md`

### ag-03: Audio (Multi-TTS)

#### edge-tts (Microsoft, free)
```bash
# List voices
edge-tts --list-voices | grep en-US

# Generate audio
edge-tts --text "Hello world" --voice en-US-JennyNeural --write-media output.mp3

# With subtitles
edge-tts --text "Hello world" --voice en-US-JennyNeural --write-media output.mp3 --write-subtitles output.vtt
```

**Available voices:**
- `en-US-JennyNeural` (female)
- `en-US-GuyNeural` (male)
- `en-US-EmmaMultilingualNeural` (default)

#### Xiaomi mimo-v2-tts (Token Plan)
```bash
# Prerequisites
export XIAOMI_API_KEY=tp-xxx
export XIAOMI_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1

# List available models
curl -s -k "$XIAOMI_BASE_URL/models" -H "Authorization: Bearer $XIAOMI_API_KEY"

# Generate TTS (WAV)
curl -s -k "$XIAOMI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $XIAOMI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mimo-v2.5-tts",
    "messages": [
      {"role": "user", "content": "Di esto: Hello world"},
      {"role": "assistant", "content": "Hello world"}
    ],
    "modalities": ["audio"],
    "audio": {"voice": "Mia", "format": "wav"}
  }' | python3 -c "import sys,json,base64; r=json.load(sys.stdin); open('output.wav','wb').write(base64.b64decode(r['choices'][0]['message']['audio']['data']))"
```

**Available voices:** Mia, Chloe, Milo, Dean, 冰糖, 茉莉, 苏打, 白桃, mimo_default

**Styles:** voiceclone, voicedesign (use `--style` flag)

#### Xiaomi mimo-v2.5-asr (Speech-to-Text)
```bash
# Transcribe audio
base64_audio=$(base64 -w0 audio.wav)
curl -s -k "$XIAOMI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $XIAOMI_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"mimo-v2.5-asr\",
    \"messages\": [
      {\"role\": \"user\", \"content\": [
        {\"type\": \"input_audio\", \"input_audio\": {\"data\": \"data:audio/wav;base64,$base64_audio\", \"format\": \"wav\"}}
      ]}
    ]
  }" | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

#### kokoro (Chutes API)
```bash
# Requires API key from Chutes
export CHUTES_API_KEY=xxx

# Generate TTS (documentation pending)
```

### ag-04: Transcription
| Tool | Command | Notes |
|------|---------|-------|
| whisper.cpp | `./main -m models/ggml-base.en.bin` | Local, fast |
| MIMO ASR | Xiaomi API | Cloud, accurate |

### ag-05: Render
- `ffmpeg` — composition, VAAPI encoding
- `Godot` — motion graphics (optional)
- Templates in `ag-05/templates/`

### ag-06: Merge
- `ffmpeg -i video.mp4 -i audio.mp3 -c:v copy -c:a aac output.mp4`

---

## Render Parameters (ag-05)

Each video can vary:
- **VFX**: particles, glitch, zoom, pan, fade, color_grade
- **SFX**: typing, notification, ambient, none
- **Subtitles**: size (24-72), color, highlight_color, animation (fade/slide/pop), font
- **Scenes**: intro_duration, content_style, outro_duration
- **Cadence**: slow (0.8x), normal (1.0x), fast (1.2x)

## Output Formats

- **Vertical (9:16)**: 608x1080 — TikTok, Reels, Shorts
- **Horizontal (16:9)**: 1920x1080 — YouTube, presentations

## Self-Command

Agents use background commands + self-wake:
```bash
ffmpeg ... &
CMD_PID=$!
(sleep 10; tmux send-keys -t 15-X "Self-wake: PID=$CMD_PID, check output." Enter) &
```

## Verification

After each step, verify:
1. Output files exist and are non-empty
2. Manifests are valid CSV
3. Audio/video files are playable (`ffprobe`)
4. Transcription timestamps align with audio
