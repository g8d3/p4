# e015 — Video Pipeline

Modular video production: research → scripts → audio → transcription → render → merge.

## Quick Start

```bash
# 1. Create topic prompt
echo "How AI coding works" > topic_prompt.txt

# 2. Run each agent sequentially
cd ag-01-research && opencode -m opencode-go/deepseek-v4-flash
cd ag-02-scripts && cmd -m xiaomi/mimo-v2.5
cd ag-03-audio && opencode -m opencode-go/deepseek-v4-flash
cd ag-04-transcribe && opencode -m opencode-go/deepseek-v4-flash
cd ag-05-render && opencode -m zai-coding-plan/glm-5v-turbo
cd ag-06-merge && cmd -m xiaomi/mimo-v2.5
```

## Directory Structure

```
e015-video-pipeline/
├── AGENTS.md              # Main pipeline documentation
├── topic_prompt.txt       # Your input (create this)
├── ag-01-research/        # Research topics
│   ├── AGENTS.md
│   ├── bin/
│   └── output/            # topics.csv
├── ag-02-scripts/         # Write scripts
│   ├── AGENTS.md
│   ├── bin/
│   └── output/            # script-*.md, scripts-manifest.csv
├── ag-03-audio/           # Generate audio
│   ├── AGENTS.md
│   ├── bin/
│   └── output/            # script-*/audio.*, audio-manifest.csv
├── ag-04-transcribe/      # Transcribe audio
│   ├── AGENTS.md
│   ├── bin/
│   └── output/            # script-*/transcription.*, transcribe-manifest.csv
├── ag-05-render/          # Render video
│   ├── AGENTS.md
│   ├── bin/
│   ├── templates/
│   └── output/            # script-*/video-*.mp4, render-manifest.csv
├── ag-06-merge/           # Merge audio + video
│   ├── AGENTS.md
│   ├── bin/
│   └── output/            # script-*/FINAL.mp4, merge-manifest.csv
└── bin/                   # Shared tools
```

## AI Plans Used

| Agent | Plan | Model | Why |
|-------|------|-------|-----|
| ag-01 | opencode-go | deepseek-v4-flash | Fast reasoning |
| ag-02 | cmd | xiaomi/mimo-v2.5 | 14× deal, writing |
| ag-03 | opencode-go | deepseek-v4-flash | Orchestration |
| ag-04 | opencode-go | deepseek-v4-flash | Orchestration |
| ag-05 | zai-coding-plan | glm-5v-turbo | Vision review |
| ag-06 | cmd | xiaomi/mimo-v2.5 | 14× deal, verification |

## Output Formats

- **Vertical (9:16)**: 608x1080 — TikTok, Reels, Shorts
- **Horizontal (16:9)**: 1920x1080 — YouTube, presentations

## Deals Active

- **Tencent Hy3**: FREE until July 21, 2026
- **MiMo V2.5**: 14× multiplier (permanent)
- **MiMo V2.5 Pro**: 7× multiplier (permanent)
- **DeepSeek V4 Pro**: 4× multiplier (permanent)
