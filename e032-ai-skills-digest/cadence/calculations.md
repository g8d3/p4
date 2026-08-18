# Cadence calculations — audit trail

Format per entry: phase → N_base(phase) × multiplier → N_check; evidence; action.

## 2026-08-18 seed
All four Stage-1 agents DONE (verified done.txt in output/). N_check=600 (done phase, max).
Unsubmitted-Enter fix applied manually to ag-02-products (window 32-2): stranded
instruction "Re-read your AGENTS.md — a new '## Cadence' section..." consumed via
Enter; window back at clean prompt. Clock now flags this class automatically.

## 2026-08-18 06:13 — ag-01..04 (all four)
phase=done N_base=600 mult=4.0 stable=100 → N_check=600×4.0=2400 → clamped 600 (clock max)
evidence: done.txt present in output/ since 23:16-23:29; monitor-state last_status=DONE all, age 6.6-6.9h; no anomalies in ~6.5h
action: wrote interval_s=600 to config.json; multiplier held at max (step-back capped at 4.0, stable well beyond stable_cycles_needed=3)

## 2026-08-18 06:32 — ag-05-synthesis (NEW agent registered)
phase=booting (registered by setup) → detected done.txt at 06:30 → phase=done
N_base=600 mult=1.0 (fresh, stable=0) → N_check=600×1.0=600
evidence: done.txt present 06:30 (synthesis.md 06:29, teaching-plan.md + profit-plan.md 06:30), heartbeat 06:31 "done: ... shipped"
action: wrote phase=done, interval_s=600, multiplier=1.0, stable_cycles=0 to config.json

## 2026-08-18 06:32 — ag-01..04 (unchanged, DONE overnight)
No N change: phase=done N_base=600 mult=4.0 (step-back max) stable=100 → N_check=600
evidence: DONE all night (done.txt ages 6.6-7.4h), zero anomalies since 23:30
action: none (interval_s=600 already correct)

## 2026-08-18 06:42 — ag-06-engine (content engine, registered by setup as booting)
Detected done.txt at 06:38 → phase=done
N_base=600 mult=1.0 (fresh) → N_check=600×1.0=600
evidence: done.txt + episode-1-challenge.md + posts.txt + metrics.json + successor.md all in output/ 06:37-06:38; heartbeat 06:38 status=DONE
action: wrote phase=done, interval_s=600, multiplier=1.0, stable_cycles=0

## 2026-08-18 06:42 — metrics aggregation (Job 1b)
appended cadence/metrics.csv: 2026-08-18,ag-06-engine,1,0,0,0,,0,0.5,0
articles_written=1 (<2 target), posts_made=0 (<10) — DAY 1, no 2-day miss flag yet. root cause = no create-and-post service (audit-candidate #10), flagged honestly in agent's metrics.json.

## 2026-08-18 06:55 — ag-07-engine (auto-reproduction registered)
phase=booting (spawn-agent.sh registered it) → set N_check
N_base(booting)=30 mult=1.0 stable=0 → N_check=30×1.0=30
evidence: successor.md from ag-06-engine → ag-07; window 32-7 live Build mode, no output/heartbeat yet (booting)
action: wrote interval_s=30, multiplier=1.0, stable_cycles=0 to config.json

## 2026-08-18 07:00 — ag-07-engine (wrong-deliverable → corrective message, N reset)
phase=booting→done prematurely (DONE 06:54 with WRONG deliverable: re-produced guide, not video script). This is a HEALTH FINDING for ag-07 → per step-back rule, multiplier resets to 1.0, stable=0.
Corrective message sent 07:00 to 32-7 to produce episode-1-script.md + delete wrong guide + fix done.txt.
N: stays 600 (DONE detected) but will re-evaluate next cycle; if agent re-ships → verify episode-1-script.md exists.
action: no interval change this cycle; observation logged.

## 2026-08-18 07:00 — quiet transition (Job 2.5)
quiet_hours=FALSE, quiet_override=off → schedule SUSPENDED, caps stay 600%/14GiB. Per USER RULE: no re-cap, no lowering, regardless of clock hour. NO set-caps.sh call made. Verified via audit 06:57-06:58 + set-caps.sh status.

## 2026-08-18 07:04 — ag-07-engine (recovered, DONE verified)
Corrective message cycle 22 → agent deleted wrong guide, shipped episode-1-script.md + posts + metrics + successor (06:59). DONE confirmed (done.txt 06:59). N stays 600 (done). multiplier reset to 1.0 (step-back: health finding on 06:54 wrong deliverable) → stays 1.0, stable=0 for now.

## 2026-08-18 07:04 — ag-08-engine (auto-launched via spawn-agent.sh)
Job 1b reproduction: ag-07 successor.md → ag-08. spawn-agent.sh ag-08-engine 32-8 launched, registered booting.
phase=booting N_base=30 mult=1.0 → N_check=30. action: wrote interval_s=30.

## 2026-08-18 07:06 — ag-08-engine (booting, no N change yet)
phase=booting N_base=30 mult=1.0 → N_check=30 (unchanged)
evidence: launched 07:00, window 32-8 working (tokens rising, planning render), no output/heartbeat yet → NOT_STARTED is booting-expected, not a stall
action: sent report.sh nudge; no config change (interval_s=30 already)

## 2026-08-18 07:09 — ag-08-engine (STUCK false-positive → retuned for long-step)
STUCK flag at 07:07-07:08 (N=30, >4×30=120s no evidence) was FALSE: window moving (111K→114.7K tokens), heartbeat 07:04:54, generating TTS audio for 12 scenes = long-step render.
phase=booting→long-step: N_base(long-step)=300 mult=1.0 → N_check=300×1.0=300
evidence: timings/step = TTS+render (multi-minute); window moving; heartbeat present
action: wrote phase=long-step, interval_s=300 to config.json (was 30)

## 2026-08-18 07:14 — ag-08-engine (WORKING, N=300 confirmed)
phase=long-step N_base=300 mult=1.0 → N_check=300. Status WORKING (age 277s < idle*N=600).
evidence: heartbeat 07:10:59 "TTS gen (6/13), storyboard+script done, building frames"; window moving
action: none (interval_s=300 correct for long-step render)

## 2026-08-18 07:16 — ag-08-engine (WORKING, render halfway)
phase=long-step N_base=300 mult=1.0 → N_check=300. Status WORKING (age 219s < idle*N=600).
evidence: heartbeat 07:15:12 "audio+meta done (5:54), durations synced, frames 00-05 built, writing 06-12"
action: none (interval_s=300 correct)

## 2026-08-18 07:21 — ag-08-engine (WORKING, render frames done)
phase=long-step N_base=300 mult=1.0 → N_check=300. Status WORKING (age 267s < 600).
evidence: pane moving (197K tokens); 12 HTML frame compositions written in ag-08-engine/videos/reto-7-dias-primer-video/compositions/frames/; heartbeat 07:15:12
action: none (interval_s=300 correct; will step-back to 600 on DONE)

## 2026-08-18 07:30 — ag-08-engine (WORKING, encoding; VAAPI reminder)
phase=long-step N_base=300 → N_check=300. Status WORKING (age 571s < 600).
evidence: heartbeat 07:25:41 "launching render"; libx264 intermediate encode (HyperFrames frames→video-only.mp4, ALLOWED); FINAL must be h264_vaapi
action: none on N; sent VAAPI reminder for final assembly; verify final encoder tag next cycle

## 2026-08-18 07:31 — ag-08-engine (WORKING, encoding)
phase=long-step N_base=300 → N_check=300. Status WORKING (age 150s).
evidence: heartbeat 07:25:41, encode active (libx264 intermediate), 224K tokens
action: none (N=300 correct)

## 2026-08-18 07:36 — ag-08-engine (DONE, GPU rule verified)
phase=long-step→done. N_check 300→600 (done). mult=1.0 stable=0.
evidence: done.txt 07:34; video.mp4 5:54 1080x1920 24.4MB; ffprobe encoder tag = h264_vaapi (GPU rule HONORED after cycle-25 reminder); successor.md → ag-09
action: wrote phase=done, interval_s=600

## 2026-08-18 07:36 — ag-09-engine (auto-launched via spawn-agent.sh)
Job 1b reproduction: ag-08 successor.md → ag-09 (day-1 diary Short). spawn-agent.sh ag-09-engine 32-9.
phase=booting N_base=30 mult=1.0 → N_check=30.

## 2026-08-18 07:41 — ag-09-engine (STUCK false-positive → long-step retune)
STUCK at N=30 (no evidence 158s > 4×30=120) was FALSE: heartbeat 07:37:57, 125.7K tokens rising, video project work.
phase=booting→long-step: N_base(long-step)=300 mult=1.0 → N_check=300
evidence: video agent (same as ag-08); heartbeat present; window moving
action: wrote phase=long-step, interval_s=300

## 2026-08-18 07:42 — ag-09-engine (WORKING, N=300 confirmed)
phase=long-step N_base=300 mult=1.0 → N_check=300. Status WORKING (age 193s < 600).
evidence: retune took effect 07:41:10; pane moving; heartbeat 07:37:57
action: none (interval_s=300 correct)

## 2026-08-18 07:48 — ag-09-engine (WORKING, progress)
phase=long-step N_base=300 → N_check=300. Status WORKING (age 498s < 600).
evidence: day-1-short.md written 07:47; 141.9K tokens; pane moving
action: none

## 2026-08-18 07:57 — ag-09-engine (DONE verified, GPU rule honored)
phase=long-step→done. N_check 300→600. mult=1.0 stable=0.
evidence: done.txt 07:48; day-1 video 0:49 1080x1920 3.5MB; ffprobe tag h264_vaapi; successor → ag-10
action: wrote phase=done, interval_s=600

## 2026-08-18 07:57 — ag-10-engine (auto-launched, long-step from start)
Job 1b: ag-09 → ag-10 (day-2 diary Short). spawn-agent.sh ag-10-engine 32-10.
phase=long-step (video agent — pre-empted the ag-08/09 tight-N lesson) N_base=300 → N_check=300.

## 2026-08-18 08:03 — ag-10-engine (WORKING, N=300 correct)
phase=long-step N_base=300 → N_check=300. Heartbeats 07:58:55 + 08:01:14 (TTS gen). NOT_STARTED in state is stale-clock lag; evidence proves WORKING.
action: none

## 2026-08-18 08:13 — ag-10-engine (DONE verified, GPU honored)
phase=long-step→done. N_check 300→600. mult=1.0.
evidence: done.txt 08:10; day-2 video 0:48 1080x1920 3.3MB; ffprobe h264_vaapi; successor → ag-11
action: wrote phase=done, interval_s=600

## 2026-08-18 08:13 — ag-11-engine (auto-launched, long-step)
Job 1b: ag-10 → ag-11 (day-3 diary Short). spawn-agent.sh ag-11-engine 32-11.
phase=long-step N_base=300 → N_check=300 (video-agent pattern).
