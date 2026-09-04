#!/usr/bin/env python3
"""Headless UI-logic tests for app-with-skill — no display needed.
Stubs tkinter/pyatspi before importing main so setup_ui runs without X.
Verifies the feedback papercuts: silent failures now surface in the popup.
"""
import os, sys, types, pathlib, time, importlib.util

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

_all_widgets = []
_tk = types.ModuleType("tkinter")
class _Widget:
    def __init__(self, *a, **k):
        self.kwargs = k; self.text = k.get("text", ""); self._packed = False
        _all_widgets.append(self)
    def pack(self, *a, **k): self._packed = True
    def pack_forget(self): self._packed = False
    def configure(self, **k): self.kwargs.update(k); self.text = k.get("text", self.text)
    def config(self, **k): self.configure(**k)
    def cget(self, key): return self.kwargs.get(key, "")
    def bind(self, *a, **k): pass
class _Menu(_Widget):
    def add_command(self, **k): pass
    def tk_popup(self, *a): pass
class _Root:
    def __init__(self):
        self.geom = "64x64+40+40"; self.afters = []; self._focus = None
    def overrideredirect(self, *a): pass
    def attributes(self, *a): pass
    def configure(self, **k): pass
    def geometry(self, g=None):
        if g is None: return self.geom
        self.geom = g
    def bind(self, *a, **k): pass
    def after(self, ms, fn):
        self.afters.append((ms, fn))
        if ms == 0: fn()  # mimic event-loop dispatch of after(0)
        return len(self.afters)
    def focus_get(self): return self._focus
    def winfo_x(self): return 40
    def winfo_y(self): return 40
    def destroy(self): pass
_tk.Label = _Widget; _tk.Button = _Widget; _tk.Menu = _Menu; _tk.Tk = _Root
sys.modules["tkinter"] = _tk
sys.modules["pyatspi"] = types.ModuleType("pyatspi")  # truthy so poll_focus guard path runs

# load main as a dedicated module object (not the cached "main") so stubs apply
# even when e2e_test.py imported the real thing first in the same pytest session
_spec = importlib.util.spec_from_file_location(
    "main_under_test", str(pathlib.Path(__file__).parent.parent / "main.py"))
main = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = main
_spec.loader.exec_module(main)

_ORIG = dict(record_audio=main.record_audio, transcribe=main.transcribe,
             type_text=main.type_text, STATE=main.STATE)
_which_orig, _run_orig = main.shutil.which, main.subprocess.run


def restore():
    for k, v in _ORIG.items(): setattr(main, k, v if k != "STATE" else "idle")
    main.STATE = "idle"
    main.shutil.which, main.subprocess.run = _which_orig, _run_orig


def build():
    _all_widgets.clear()
    root = _Root()
    toggle, _ = main.setup_ui(root)
    return root, toggle


def err_widget():
    return [w for w in _all_widgets if w.kwargs.get("wraplength")]


def test_no_audio_backend_shows_error():
    root, toggle = build()
    main.record_audio = lambda start=True: False
    toggle()
    err = err_widget()
    assert err and err[0]._packed, "error banner not shown"
    assert "no audio backend" in err[0].text
    assert root.geom.startswith("300x70"), root.geom
    assert main.STATE == "idle"
    restore()


def test_transcription_failure_shows_error():
    root, toggle = build()
    main.record_audio = lambda start=True: True
    main.transcribe = lambda wav: "[transcription failed: nope]"
    main.type_text = lambda t: False
    toggle(); toggle()  # record -> stop -> transcribe (thread)
    time.sleep(0.2)
    err = err_widget()
    assert err and err[0]._packed and "transcription failed" in err[0].text
    assert main.STATE == "idle"
    restore()


def test_typing_failure_shows_error():
    root, toggle = build()
    main.record_audio = lambda start=True: True
    main.transcribe = lambda wav: "hello world"
    main.type_text = lambda t: False
    toggle(); toggle()
    time.sleep(0.2)
    err = err_widget()
    assert err and err[0]._packed and "typing failed" in err[0].text
    restore()


def test_success_returns_idle_without_error():
    root, toggle = build()
    main.record_audio = lambda start=True: True
    main.transcribe = lambda wav: "hello world"
    main.type_text = lambda t: True
    toggle(); toggle()
    time.sleep(0.2)
    err = err_widget()
    assert not (err and err[0]._packed), "no error banner on success"
    assert main.STATE == "idle"
    restore()


def test_type_text_true_with_backend():
    main.shutil.which = lambda name: "/usr/bin/xdotool"
    main.subprocess.run = lambda *a, **k: None
    try:
        assert main.type_text("hi") is True
    finally:
        restore()


def test_type_text_false_without_backend():
    main.shutil.which = lambda name: None
    try:
        assert main.type_text("hi") is False  # pynput not installed -> fallback fails
    finally:
        restore()


def test_poll_focus_keeps_visible_while_recording():
    root = _Root()
    main.STATE = "recording"
    main.poll_focus(root)  # guard returns before any withdraw/AT-SPI call
    assert any(ms == 500 for ms, _ in root.afters), "poll loop must continue"
    restore()


def test_poll_focus_keeps_visible_when_popup_focused():
    root = _Root(); root._focus = object()
    main.STATE = "idle"
    main.poll_focus(root)
    assert any(ms == 500 for ms, _ in root.afters)
    restore()


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print(f"PASS {name}")
            except Exception as e:
                fails += 1; print(f"FAIL {name}: {e}")
    sys.exit(fails)
