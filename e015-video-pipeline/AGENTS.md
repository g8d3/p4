# e015 — Video Pipeline

Modular video production: research → full pipeline per topic.

## Inherits
- [../e000-fundamentals/AGENTS.md](../e000-fundamentals/AGENTS.md) — principles, TTS, GPU encoding

## Architecture

```
ag-01 (Type 1): Research
  └── output: topics.csv

ag-02 (Type 2, MANY in parallel): Full Pipeline per topic
  ├── Reads 1 topic from topics.csv
  ├── Writes script
  ├── Generates voice over
  ├── Transcribes (SRT with timestamps)
  ├── Renders video
  ├── Merges audio + video
  └── Output: agent-NNN/FINAL.mp4
```

## Agents

| Type | Role | Input | Output | Multiplicity |
|------|------|-------|--------|--------------|
| ag-01 | Research | topic_prompt.txt | topics.csv | 1 agent |
| ag-02 | Full pipeline | 1 topic from topics.csv | agent-NNN/FINAL.mp4 | MANY (1 per topic) |

## How to Run

### 1. Launch ag-01 (Research)
```bash
tmux new-window -n 15-1 -d
tmux send-keys -t 15-1 "cd e015-video-pipeline/ag-01-research && opencode -m opencode-go/deepseek-v4-flash" Enter
# Wait for topics.csv
```

### 2. Launch ag-02 agents (Full Pipeline)
```bash
# For each topic in topics.csv:
tmux new-window -n 15-2-N -d
tmux send-keys -t 15-2-N "cd e015-video-pipeline/ag-02-pipeline && opencode -m opencode-go/deepseek-v4-flash" Enter
# Send: "Topic N assigned to you. Work in agent-NNN/ directory."
```

## Ag-02 Subdirectories

Each ag-02 agent works in its own subdirectory:
```
ag-02-pipeline/
├── agent-001/    # Topic 1
│   ├── script.md
│   ├── audio.mp3
│   ├── subtitles.srt
│   └── FINAL.mp4
├── agent-002/    # Topic 2
│   └── ...
└── agent-00N/    # Topic N
    └── ...
```

## AI Plans

| Agent | Plan | Model |
|-------|------|-------|
| ag-01 | opencode-go | deepseek-v4-flash |
| ag-02 | opencode-go | deepseek-v4-flash |

## Output Formats

- **Vertical (9:16)**: 608x1080 — TikTok, Reels, Shorts
- **Horizontal (16:9)**: 1920x1080 — YouTube
