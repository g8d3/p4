# Parakeet ASR — setup & usage (portable reference)

Word-level speech transcription for the p4 video pipeline. This file is the
authoritative how-to; it lives next to the scripts so any agent can recover the
setup from scratch. **The virtualenv is ephemeral — if it's gone, recreate it
with the commands below. This is the part that was previously undocumented and
cost a session to reverse-engineer.**

## What it is

Two persistent services in `e018-hyprframes-browser-video/ag-02/bin/`:

| File | Role |
|---|---|
| `model_worker.py` | Loads the Parakeet CTC 0.6b model once (~20–30 s), serves via Unix socket `/tmp/transcribe-worker.sock` |
| `transcribe_server.py` | HTTP server on `127.0.0.1:9877`, delegates to the worker, saves `.srt` + `.txt` |

Model (portable): `~/models/parakeet-ctc-0.6b.nemo` (2.4 GB). Never hardcode a
machine path — the worker resolves it via `PARAKEET_MODEL`, defaulting to
`~/models/parakeet-ctc-0.6b.nemo`.

## Step 0 — recreate the venv (only when `/tmp/nemo_venv` is missing)

The venv lives at `/tmp/nemo_venv` (RAM/tmpfs — **wiped on reboot**, and not
backed by a lockfile). Recreate it with `uv` (~4–5 GB download, minutes):

```bash
uv venv /tmp/nemo_venv --python 3.11
uv pip install --python /tmp/nemo_venv/bin/python "nemo_toolkit[asr]>=1.22,<2"
```

Why `<2`: the worker script uses the NeMo 1.x API
(`model.transcribe(..., return_hypotheses=True, timestamps=True)`). NeMo 2.x
removed `return_hypotheses` and changed the timestamps API — do not upgrade.

## Step 1 — start the services (once per session)

```bash
export TMPDIR=/home/vuos/tmp            # model/audio scratch on disk, not tmpfs
source /tmp/nemo_venv/bin/activate
python3 e018-hyprframes-browser-video/ag-02/bin/model_worker.py >/tmp/parakeet-worker.log 2>&1 &
python3 e018-hyprframes-browser-video/ag-02/bin/transcribe_server.py >/tmp/parakeet-server.log 2>&1 &
```

The worker takes ~20–30 s to load the model. Verify it is REALLY up by
transcribing a tiny file — `/health` only checks the socket file exists and can
report healthy after a crash. Check `ps aux | grep model_worker` too.

## Step 2 — transcribe an audio file

Audio must be **mono** (stereo raises a TypeError). Convert first:

```bash
ffmpeg -i in.mp3 -ac 1 -ar 16000 mono.mp3
```

Then:

```bash
curl -s -X POST http://127.0.0.1:9877 -H 'Content-Type: application/json' \
  -d '{"path":"/absolute/path/to/mono.mp3"}' | python3 -m json.tool
```

Response fields: `text` (full transcript), `srt`, `words_raw` (word-level
timestamps: `start`/`end` in seconds, `word`), `transcribe_sec`, `word_count`.

Or the wrapper: `e018-hyprframes-browser-video/ag-02/bin/transcribe.sh <audio.mp3>`

## Step 3 — use the timestamps

`words_raw` gives per-word start/end. For scene timing, locate the first word of
each narration paragraph and use its `start` — that is the frame-accurate scene
boundary. Parakeet writes numbers as words ("five point six") — post-process to
digits if the script uses numerals.

## Pitfalls (hard-won)

- **The venv dies with `/tmp`.** After any reboot, `/tmp/nemo_venv` is gone and
  `python3 -c "import nemo"` fails everywhere. Recreate it (Step 0) — do not
  search the machine for nemo; it exists only in that venv.
- Bad audio does NOT kill the worker (fixed: errors return to the caller). If
  the worker is down, restart it; the model reloads in ~20–30 s.
- The transcribe server is single-threaded and can wedge on a leaked connection
  (CLOSE-WAIT pileup). If it hangs: `kill $(pgrep -f transcribe_server | head -1)`
  and relaunch. The worker keeps running.
- First transcribe after a fresh worker start includes model warmup — budget
  ~1–2 min for the first request.
