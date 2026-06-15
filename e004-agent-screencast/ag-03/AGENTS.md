# ag-03 — Render log aggregator

## Model
`opencode-go/mimo-v2.5`

## Goal

Centralize render metrics from all agents into a single CSV, analyze efficiency, and produce reports.

## Input

All agents append to `/home/vuos/code/p4/e004-agent-screencast/ag-03/render-log.csv` with format:

```
timestamp,agent_id,experiment,step,duration_sec,gpu_busy_pct,output_fps,file_size_mb,notes
```

## Task

### 1. Collect data
Read the shared CSV. If it doesn't exist, create it with headers:
```csv
timestamp,agent_id,experiment,step,duration_sec,gpu_busy_pct,output_fps,file_size_mb,resolution,notes
```

### 2. Check all agent directories
Look for render logs in:
- ag-01/ and ag-02/ (individual logs if they exist)

### 3. Aggregate
Read all entries. For each agent report:
- Total time spent
- GPU avg usage
- FPS achieved
- File sizes

### 4. Report
Write `efficiency-report.md` with:
- Summary table of all renders
- GPU utilization trends
- Comparison: which steps are fastest/slowest
- Recommendations for pipeline optimization

## Self-command
ALL commands: `>/dev/null 2>&1 &`. Self-wake. Never run synchronously.
