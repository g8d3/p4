# ag-08 — Content engine (episode-1 video render + next content)

Stage 4 of e032. You take the locked episode-1 script from ag-07 and RENDER it
into the actual episode-1 faceless explainer video (HyperFrames), verify it,
package post-ready metadata, and keep the always-on loop alive with a successor.

## Inherits
- [../../AGENTS.md](../../AGENTS.md) — experiment scope, operating model (always-on engine, metrics, reproduction)
- [../../../e000-fundamentals/AGENTS.md](../../../e000-fundamentals/AGENTS.md) — principles, quiet caps, self-wake, TTS choices
- [../ag-07-engine/output/episode-1-script.md](../ag-07-engine/output/episode-1-script.md) — the script to render (12 scenes, ~6:45, 9:16, faceless)
- [../ag-06-engine/output/episode-1-challenge.md](../ag-06-engine/output/episode-1-challenge.md) — the guide (source of the 7 days)
- [../ag-05-synthesis/output/teaching-plan.md](../ag-05-synthesis/output/teaching-plan.md) — M1–M5 the video demonstrates
- [../ag-07-engine/output/successor.md](../ag-07-engine/output/successor.md) — this task's exact contract

## The always-on rules (mandatory)
1. Work all the time — render the video, verify it, then leave a successor.
2. Create-and-post — publish-ready `output/posts.txt` with the REAL YouTube
   title/description (AI disclosure line), 2 X posts, 1 Shorts caption.
3. Metrics — `output/metrics.json` reports the ACTUAL cloud cost (TTS +
   transcription + render; likely < $1 — never assume $0).
4. Reproduce — `output/successor.md` for ag-09 before done (next asset:
   day-1 challenge diary Short unless cadence/metrics.csv shows a better angle).

## Your deliverable
Render `videos/reto-7-dias-primer-video/` → `renders/video.mp4`:
- Faceless (typography/abstracts only, NO face/camera), 9:16 (1080x1920).
- ~6:45 min, ONE consistent Spanish voice (KIE Gemini TTS preferred voice or
  Deepgram Aura-2 `aura-2-celeste-es`).
- Word-timed captions always visible (Deepgram Nova-3 timings).
- Keep the day-4 OPEN GAP beat and scene-11 "pasado no es futuro" note verbatim.
- Verify: not black, audio present, narration matches visuals (ffprobe +
  frame extraction), sane file size.

## Cadence
- Agent id: `ag-08-engine`. Heartbeat every milestone:
  `e000-fundamentals/bin/progress-monitor/report.sh ag-08-engine "<step>"`.
- Interval 90s while working (long renders). Inside the quiet cap — ONE heavy
  step at a time, background + self-wake.

## Rules
- Read-only on inputs. Write only to `output/` and `videos/` (your project).
- Cloud-first: KIE/Deepgram for TTS+transcription, HyperFrames render local or
  cloud. If the final encode is too heavy for the cap, ship composition +
  audio + captions and note the resume point (successor contract allows it).
- 90 min hard deadline: stop, ship partial, notify.
- Measurement-based timeouts: background everything + self-wake at mean+4σ.

## Notify
- Finish: `notify.sh done "ag-08: episode-1 video rendered + post-ready"`.
- Failure: `notify.sh error "ag-08 failed: <cause>"`.

## Self-command
- Background everything: `> /dev/null 2>&1 &`
- Self-wake: `(sleep <mean+4σ>; tmux send-keys -t 32-8 "Self-wake: step=N, check" Enter) &`
