#!/usr/bin/env python3
"""Headless UI-logic tests for app-without-skill — no display needed.
Stubs tkinter/speech_recognition before importing main so PopupApp runs without X.
Verifies: no 2nd recording mid-transcription, Esc hides to taskbar (restorable),
and the "Typed: …" status survives the idle reset.
"""
import os, sys, types, pathlib, time, importlib.util

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

_tk = types.ModuleType("tkinter")

class _Widget:
    def __init__(self, *a, **k):
        self.kwargs = k; self.text = k.get("text", ""); self._packed = False
    def pack(self, *a, **k): self._packed = True
    def pack_forget(self): self._packed = False
    def configure(self, **k): self.kwargs.update(k); self.text = k.get("text", self.text)
    def config(self, **k): self.configure(**k)
    def cget(self, key): return self.kwargs.get(key, "")
    def bind(self, *a, **k): pass
_tk.Label = _Widget; _tk.Button = _Widget; _tk.Tk = object
sys.modules["tkinter"] = _tk
_sr = types.ModuleType("speech_recognition")
_sr.Recognizer = lambda: None
sys.modules["speech_recognition"] = _sr

# load main as a dedicated module object (not the cached "main") so stubs apply
# even when e2e_test.py imported the real thing first in the same pytest session
_spec = importlib.util.spec_from_file_location(
    "main_under_test", str(pathlib.Path(__file__).parent.parent / "main.py"))
main = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = main
_spec.loader.exec_module(main)


class _Root:
    def __init__(self):
        self.geom = "320x90+40+40"; self.afters = []; self.bindings = {}; self.calls = []
    def title(self, *a): pass
    def geometry(self, g=None):
        if g is None: return self.geom
        self.geom = g
    def attributes(self, *a): pass
    def configure(self, **k): pass
    def bind(self, seq, fn): self.bindings[seq] = fn
    def protocol(self, *a): pass
    def after(self, ms, fn):
        self.afters.append((ms, fn))
        if ms == 0: fn()  # mimic event-loop dispatch of after(0)
        return len(self.afters)
    def winfo_x(self): return 40
    def winfo_y(self): return 40
    def iconify(self): self.calls.append("iconify")
    def deiconify(self): self.calls.append("deiconify")
    def withdraw(self): self.calls.append("withdraw")
    def destroy(self): pass


class _Rec:
    def __init__(self):
        self.starts = 0; self.stops = 0; self.wav = "/tmp/fake.wav"
    def start(self): self.starts += 1; return True
    def stop(self): self.stops += 1; return self.wav


def make_app():
    app = main.PopupApp(_Root())
    app.recorder = _Rec()
    app.transcriber.transcribe = lambda wav: ""
    app.typer.type = lambda t: None
    return app


def test_click_during_processing_is_ignored():
    app = make_app()
    app.state = "processing"
    app.toggle()
    assert app.state == "processing", "state changed on ignored click"
    assert app.recorder.starts == 0, "a 2nd recording started mid-transcription"


def test_escape_hides_to_taskbar_not_withdraw():
    app = make_app()
    app.root.bindings["<Escape>"](None)
    assert app.root.calls == ["iconify"], app.root.calls


def test_record_stop_transcribe_status_survives():
    app = make_app()
    app.transcriber.transcribe = lambda wav: "hello world"
    app.toggle()  # idle -> recording
    assert app.state == "recording" and app.recorder.starts == 1
    app.toggle()  # recording -> processing (thread)
    time.sleep(0.2)
    assert app.state == "idle"
    assert app.status.text == "Typed: hello world", app.status.text


def test_no_transcription_status():
    app = make_app()
    app.toggle(); app.toggle()
    time.sleep(0.2)
    assert app.state == "idle"
    assert app.status.text == "No transcription"


def test_no_audio_backend_status():
    app = make_app()

    class _Bad:
        def start(self): return False

    app.recorder = _Bad()
    app.toggle()
    assert "No audio backend" in app.status.text


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print(f"PASS {name}")
            except Exception as e:
                fails += 1; print(f"FAIL {name}: {e}")
    sys.exit(fails)
