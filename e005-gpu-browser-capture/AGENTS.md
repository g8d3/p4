# e005 — GPU browser capture

**Goal**: Record an agent browsing the web while maximizing GPU usage and minimizing CPU/disk I/O. A 10-second video with hardware encoding and real-time resource monitoring.

## Pipeline

```
Kill sddm (free DRM master)
  → Start Sway as root on AMD GPU (HDMI output)
  → wf-recorder captures with VAAPI (GPU encoding)
  → Epiphany browser loads WebGL stress page (GPU rendering)
  → vkcube adds parallel Vulkan load (GPU compute)
  → Log GPU/CPU/disk metrics every second
  → Self-review with Mimo 2.5 (vision)
```

## Why this approach

| Goal | Mechanism |
|------|-----------|
| **GPU max** | Sway compositing + Epiphany WebGL + vkcube Vulkan + VAAPI encode — all GPU-bound |
| **CPU min** | wf-recorder writes VAAPI frames directly, zero CPU for encoding |
| **Disk min** | Output to tmpfs (RAM). 10s at 4Mbps ≈ 5MB. |
| **Measured** | GPU busy%, CPU% per process, disk writes/sec logged to CSV |

## Agents

- **ag-01**: GPU stress test — WebGL + vkcube + VAAPI encoding benchmark
- **ag-02**: AI dynamic browsing — agent decides what to browse, interacts via ydotool, narrates in real-time
- **ag-03**: Autonomous content recording — each agent gets its own Xvfb display, records vertical video with VAAPI, narrates with edge-tts, explores AI topics independently

## Infrastructure

- Sway (wlroots) on real AMD GPU (card1, HDMI-A-1)
- wf-recorder + VAAPI for GPU capture
- epiphany browser with WebGL
- vkcube for supplemental Vulkan GPU load
- ydotool for keyboard automation (Wayland input injection)
- All commands run via sudo (Sway needs root for DRM/TTY access; ydotool needs root for /dev/uinput)

## Metrics

Two log files:

**`ag-01/metrics.csv`** per-second resource telemetry:
```csv
timestamp,gpu_busy_pct,cpu_pct,disk_write_kbps,memory_mb
```

**`ag-01/pipeline-log.csv`** accumulative pipeline log (appended each run):
```csv
timestamp,run_id,experiment,agent_id,step,tool,action,display_type,display_id,gpu_device,gpu_busy_pct,duration_sec,status,notes
```
