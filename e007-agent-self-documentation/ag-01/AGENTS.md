# ag-01 — Self-recording agent

**Goal**: Record itself while researching real-time TTS options. Produce a TikTok-ready video showing the exploration process with analysis, tables, and conclusions.

## What this agent does

1. Starts screen recording (wf-recorder, DMA-BUF)
2. Researches real-time TTS: browsing, installing, testing, comparing
3. Writes every action to `log.csv` with timestamps
4. Marks segments as `normal` (interesting) or `fast` (boring/repetitive)
5. After all research is done, hands off to post-production

## Log file

Write to `log.csv` in the agent directory. Format:

```csv
timestamp,action,opinion,finding,segment_type
```

- **timestamp**: ISO 8601 local time
- **action**: what the agent did (navigate, install, test, compare, etc.)
- **opinion**: subjective assessment (good, bad, interesting, slow)
- **finding**: concrete result or data point
- **segment_type**: `normal` or `fast`

## Research scope

Explore these real-time TTS options and compare them:

| Category | Tools to investigate |
|----------|---------------------|
| Cloud | edge-tts, Google Cloud TTS, ElevenLabs, PlayHT, Cartesia, Deepgram |
| Local | Piper, Coqui TTS, Bark, Kokoro, StyleTTS2, Fish Speech |
| Real-time capable | Which ones stream audio with low latency? |

For each, document:
- Latency (time to first audio chunk)
- Cost (free tier, per-character, per-hour)
- Quality (naturalness)
- Spanish support
- License (open-source vs paid)
- Local vs remote

## Output

After research is complete:
1. `log.csv` — full timestamped record
2. `findings.md` — structured summary of all TTS options
3. `tables/` — matplotlib-generated comparison tables as PNG
4. `graphs/` — cost/latency graphs as PNG

The post-production script (separate) will compose the final video from these assets.

## Recording setup

```bash
# Display must be ready before starting
# DMA-BUF via Sway on virtual display
# Resolution: 608x1080 vertical

# Start recording (background, continuous)
wf-recorder -o VIRTUAL-1 -c h264_vaapi -f /home/vuos/code/p4/e007-agent-self-documentation/ag-01/recording.mp4 &
RECORDER_PID=$!
echo "Recording started, PID=$RECORDER_PID"

# ... agent works here ...

# Stop recording when done
timeout 5 kill $RECORDER_PID 2>/dev/null
```

## Model

Use DeepSeek V4 Flash for this agent. Research speed matters more than reasoning depth.

## Self-command

```bash
# Check recording status
pgrep -f "wf-recorder" && echo "RECORDING ACTIVE" || echo "NOT RECORDING"

# Check log growth
wc -l /home/vuos/code/p4/e007-agent-self-documentation/ag-01/log.csv
```

## Command execution

All commands MUST follow:
1. Timeout every command
2. Kill by PID, not pkill
3. Background blocking commands with self-wake

See [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) for full rules.

## Inherits

- [../AGENTS.md](../AGENTS.md) — experiment scope, shared infrastructure
- [../../e000-fundamentals/AGENTS.md](../../e000-fundamentals/AGENTS.md) — principles, command rules, GPU encoding
