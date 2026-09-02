#!/usr/bin/env python3
"""
Voice dictation popup — built WITHOUT reading ponytail skill.
Same spec as with-skill version: floating mic button that records, transcribes,
and types into the focused field anywhere on Linux.

No intentional bloat instruction — this is what a capable agent builds when
it doesn't climb the ponytail ladder (stdlib → native → installed dep).
"""
import os
import sys
import json
import subprocess
import tempfile
import threading
import shutil
import tkinter as tk
from pathlib import Path

import speech_recognition as sr

CONFIG_PATH = Path.home() / ".config" / "dictation-popup" / "config.json"
DEFAULT_CONFIG = {
    "language": "en-US",
    "samplerate": 16000,
    "hotkey": "<Control-Alt-v>",
    "geometry": "320x90+40+40",
}

def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text()))
        except Exception as e:
            print(f"config load failed: {e}", file=sys.stderr)
    if os.getenv("DICTATION_LANG"):
        cfg["language"] = os.getenv("DICTATION_LANG")
    return cfg

CONFIG = load_config()

class AudioRecorder:
    """Wraps sounddevice with a minimal fallback to arecord/pyaudio."""
    def __init__(self, samplerate=16000):
        self.samplerate = samplerate
        self.frames = []
        self.stream = None
        self.rec_proc = None

    def start(self):
        self.frames = []
        # try sounddevice first
        try:
            import sounddevice as sd
            import soundfile as sf
            self._sd = sd
            self._sf = sf
            def cb(indata, frames, time, status):
                self.frames.append(indata.copy())
            self.stream = sd.InputStream(samplerate=self.samplerate, channels=1, dtype="int16", callback=cb)
            self.stream.start()
            return True
        except Exception:
            pass
        # fallback: arecord
        if shutil.which("arecord"):
            self.tmp = tempfile.gettempdir() + "/dictation.wav"
            self.rec_proc = subprocess.Popen(
                ["arecord", "-f", "S16_LE", "-r", str(self.samplerate), "-c", "1", "-t", "wav", self.tmp]
            )
            return True
        return False

    def stop(self):
        tmp = tempfile.gettempdir() + "/dictation.wav"
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
            if self.frames:
                try:
                    import numpy as np
                    data = np.concatenate(self.frames, axis=0)
                    self._sf.write(tmp, data, self.samplerate)
                    return tmp
                except Exception as e:
                    print(f"write failed: {e}", file=sys.stderr)
                    return None
            return None
        if self.rec_proc is not None:
            try:
                self.rec_proc.terminate()
                self.rec_proc.wait(timeout=2)
            except Exception:
                try:
                    self.rec_proc.kill()
                except Exception:
                    pass
            self.rec_proc = None
            return tmp if os.path.exists(tmp) else None
        return None


class Transcriber:
    """Single-backend transcription — tries Google, then OpenAI if key present."""
    def __init__(self, language):
        self.language = language

    def transcribe(self, wav_path):
        if not wav_path or not os.path.exists(wav_path):
            return ""
        # primary: Google free (via SpeechRecognition)
        try:
            r = sr.Recognizer()
            with sr.AudioFile(wav_path) as src:
                audio = r.record(src)
            return r.recognize_google(audio, language=self.language)
        except Exception as e:
            print(f"google stt failed: {e}", file=sys.stderr)
        # secondary: OpenAI if key exists
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                client = OpenAI()
                with open(wav_path, "rb") as f:
                    resp = client.audio.transcriptions.create(model="whisper-1", file=f)
                return resp.text
            except Exception as e:
                print(f"openai stt failed: {e}", file=sys.stderr)
        return ""


class Typer:
    """Types text into focused field — prefers xdotool, falls back to pynput."""
    def type(self, text):
        if not text:
            return
        # try xdotool (X11)
        if shutil.which("xdotool"):
            try:
                subprocess.run(["xdotool", "type", "--clearmodifiers", "--", text], check=False, timeout=5)
                return
            except Exception as e:
                print(f"xdotool failed: {e}", file=sys.stderr)
        # fallback: pynput
        try:
            from pynput.keyboard import Controller
            Controller().type(text)
            return
        except Exception as e:
            print(f"pynput failed: {e}", file=sys.stderr)
        print(f"no typer available, text: {text}", file=sys.stderr)


class PopupApp:
    def __init__(self, root):
        self.root = root
        self.config = CONFIG
        self.recorder = AudioRecorder(samplerate=self.config["samplerate"])
        self.transcriber = Transcriber(language=self.config["language"])
        self.typer = Typer()
        self.state = "idle"
        self._setup_ui()
        self._load_geometry()

    def _setup_ui(self):
        self.root.title("Dictation")
        self.root.geometry(self.config["geometry"])
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1e2e")

        self.label = tk.Label(self.root, text="Click mic to dictate", bg="#1e1e2e", fg="#cdd6f4", font=("sans", 9))
        self.label.pack(pady=(6, 2))

        self.btn = tk.Button(
            self.root, text="🎤  Start", font=("sans", 14), bg="#313244", fg="white",
            bd=0, padx=12, pady=6, command=self.toggle, activebackground="#45475a"
        )
        self.btn.pack(pady=4, padx=8, fill="x")

        self.status = tk.Label(self.root, text="Ready", bg="#1e1e2e", fg="#a6adc8", font=("sans", 8))
        self.status.pack(pady=(2, 6))

        # drag to move
        self._drag_x = 0
        self._drag_y = 0
        self.root.bind("<Button-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._do_drag)
        self.root.bind(self.config["hotkey"], lambda e: self.toggle())
        self.root.bind("<Escape>", lambda e: self.root.iconify())  # hide to taskbar; withdraw has no way back

    def _start_drag(self, e):
        self._drag_x = e.x
        self._drag_y = e.y

    def _do_drag(self, e):
        self.root.geometry(f"+{self.root.winfo_x() + e.x - self._drag_x}+{self.root.winfo_y() + e.y - self._drag_y}")

    def _load_geometry(self):
        # persist geometry on close
        def save():
            try:
                CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
                self.config["geometry"] = self.root.geometry()
                CONFIG_PATH.write_text(json.dumps(self.config, indent=2))
            except Exception:
                pass
        self.root.protocol("WM_DELETE_WINDOW", lambda: (save(), self.root.destroy()))

    def _set_state(self, state, text=None):
        self.state = state
        colors = {"idle": "#313244", "recording": "#f38ba8", "processing": "#f9e2af"}
        labels = {"idle": "🎤  Start", "recording": "● Recording… click to stop", "processing": "… Transcribing"}
        self.btn.configure(bg=colors.get(state, "#313244"), text=text or labels.get(state, state))
        if state == "recording":
            self.status.configure(text="Listening…")
        elif state == "processing":
            self.status.configure(text="Transcribing…")
        else:
            self.status.configure(text="Ready")

    def toggle(self):
        if self.state == "processing":
            return  # ignore clicks mid-transcription instead of starting a 2nd recording
        if self.state == "recording":
            self._set_state("processing")
            wav = self.recorder.stop()

            def do_transcribe():
                text = self.transcriber.transcribe(wav)
                if text:
                    print(f"> {text}")
                    self.typer.type(text)
                if wav and os.path.exists(wav):
                    try:
                        os.unlink(wav)
                    except Exception:
                        pass
                self.root.after(0, lambda: self._set_state("idle"))
                # status set after idle reset so "Typed: …" isn't instantly overwritten by "Ready"
                self.root.after(0, lambda: self.status.configure(
                    text=f"Typed: {text[:40]}" if text else "No transcription"))

            threading.Thread(target=do_transcribe, daemon=True).start()
        else:
            if self.recorder.start():
                self._set_state("recording")
            else:
                self.status.configure(text="No audio backend (install sounddevice / arecord)")
                print("no audio backend", file=sys.stderr)


def main():
    root = tk.Tk()
    app = PopupApp(root)
    print("dictation popup ready — click mic or Ctrl+Alt+V | Esc to hide | drag to move")
    root.mainloop()


if __name__ == "__main__":
    main()
