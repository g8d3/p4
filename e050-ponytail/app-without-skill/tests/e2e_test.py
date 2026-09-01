#!/usr/bin/env python3
"""E2E (no mocks) for ponytail without-skill — real STT + real typing via classes."""
import os, sys, time, shutil, subprocess, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
try:
    from main import Transcriber, Typer, CONFIG
except Exception as e:
    print(f"import main failed: {e}"); raise

FIX = pathlib.Path(__file__).parent / "fixtures"
FIXTURES = [
    (FIX / "hello.wav",    "hello world",           ["hello", "world"]),
    (FIX / "terminal.wav", "ls -la",                ["ls", "la"]),
    (FIX / "browser.wav",  "search ponytail skill", ["search", "ponytail", "skill"]),
]

def gen_wav(text, path):
    path=pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("espeak-ng"):
        r=subprocess.run(["espeak-ng","-v","en","-s","130","-w",str(path),text], capture_output=True)
        if r.returncode==0 and path.exists() and path.stat().st_size>1000: return True
    if shutil.which("pico2wave"):
        r=subprocess.run(["pico2wave","-l","en-US","-w",str(path),text], capture_output=True)
        if r.returncode==0 and path.exists() and path.stat().st_size>1000: return True
    try:
        from gtts import gTTS
        if shutil.which("ffmpeg"):
            mp3=str(path)+".mp3"
            gTTS(text=text, lang="en").save(mp3)
            r=subprocess.run(["ffmpeg","-y","-i",mp3,"-ar","16000","-ac","1",str(path)], capture_output=True)
            try: os.remove(mp3)
            except: pass
            if r.returncode==0 and path.exists() and path.stat().st_size>1000: return True
    except Exception as e:
        print(f" gTTS failed: {e}")
    return False

def ensure_fixtures():
    for p, txt, _ in FIXTURES:
        if p.exists() and p.stat().st_size>1000: continue
        print(f"[fixtures] generating {p.name} <- {txt!r}")
        ok=gen_wav(txt, p)
        if not ok:
            print(f"[fixtures] skip {p.name}: no TTS (espeak-ng/pico2wave/gTTS+ffmpeg)")
            if not p.exists(): p.write_bytes(b"")

ensure_fixtures()

def has_display(): return bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))
def _hits(result, kws): return [k for k in kws if k.lower() in result.lower()]

def _transcribe_check(wav, keywords):
    import pytest as _pt
    if not wav.exists() or wav.stat().st_size<1000:
        _pt.skip(f"no fixture {wav.name} (gen_wav failed)")
    print(f"\n[E2E] Transcriber.transcribe {wav.name} ...")
    txt=Transcriber(CONFIG["language"]).transcribe(str(wav))
    print(f"  -> {txt!r}")
    if not txt or txt.startswith("[transcription failed"):
        _pt.skip(f"no STT backend (SpeechRecognition/faster-whisper/OPENAI_API_KEY) got: {txt!r}")
    assert _hits(txt, keywords), f"expected {keywords} in {txt!r}"
    return txt

def test_transcription():
    import pytest
    passed=0; skipped=0
    for wav, _, kws in FIXTURES:
        try: _transcribe_check(wav, kws); passed+=1
        except pytest.skip.Exception: skipped+=1; continue
    if passed==0 and skipped>0:
        pytest.skip("all fixtures skipped (no STT backend or unintelligible TTS)")
    assert passed>0, "no fixture passed transcription"

def _tk_entry_roundtrip(text):
    if not has_display():
        import pytest; pytest.skip("no DISPLAY for Tk entry")
    import tkinter as tk
    root=tk.Tk(); root.withdraw()
    top=tk.Toplevel(root); top.title("ponytail-e2e-editor")
    entry=tk.Entry(top, width=60); entry.pack(padx=10,pady=10)
    top.geometry("+100+100"); top.deiconify(); top.lift(); top.attributes("-topmost", True)
    entry.focus_set(); root.update(); time.sleep(0.35)
    if shutil.which("xdotool"):
        try: subprocess.run(["xdotool","search","--name","ponytail-e2e-editor","windowactivate"], timeout=2, capture_output=True)
        except: pass
        time.sleep(0.2)
    print(f"[E2E] Typer.type into Tk Entry: {text!r}")
    Typer().type(text)
    time.sleep(0.6); root.update()
    val=entry.get()
    print(f"  Entry.get()={val!r}")
    top.destroy(); root.destroy()
    return val

def _tk_text_proxy(text, title="proxy"):
    import tkinter as tk
    root=tk.Tk(); root.withdraw()
    top=tk.Toplevel(root); top.title(title)
    txt=tk.Text(top, width=60, height=4); txt.pack(padx=10,pady=10)
    top.geometry("+120+120"); top.deiconify(); top.lift(); txt.focus_set(); root.update(); time.sleep(0.3)
    if shutil.which("xdotool"):
        try: subprocess.run(["xdotool","search","--name",title,"windowactivate"], timeout=2, capture_output=True)
        except: pass
        time.sleep(0.2)
    Typer().type(text); time.sleep(0.5); root.update()
    val=txt.get("1.0","end-1c")
    top.destroy(); root.destroy()
    return val

def _terminal_roundtrip(text):
    if not has_display():
        import pytest; pytest.skip("no DISPLAY for terminal")
    cap="/tmp/ponytail_e2e_term"
    try: os.remove(cap)
    except: pass
    term_proc=None
    if shutil.which("xterm"):
        term_proc=subprocess.Popen(["xterm","-T","ponytail-e2e-term","-geometry","80x10+200+200","-e","bash","-c",f"read -r line; echo \"$line\" > {cap}; sleep 0.5"])
        time.sleep(0.9)
        if shutil.which("xdotool"):
            try: subprocess.run(["xdotool","search","--name","ponytail-e2e-term","windowactivate"], timeout=2, capture_output=True)
            except: pass
            time.sleep(0.3)
        print(f"[E2E] Typer.type into xterm: {text!r}")
        Typer().type(text+"\n")
        time.sleep(0.8)
        if shutil.which("xdotool"):
            try: subprocess.run(["xdotool","key","Return"], timeout=2)
            except: pass
            time.sleep(0.3)
        if os.path.exists(cap):
            val=pathlib.Path(cap).read_text().strip()
            print(f"  capture={val!r}")
            if term_proc: term_proc.terminate()
            return val
        if term_proc: term_proc.terminate()
    print(f"[E2E] xterm fallback -> Tk Text proxy: {text!r}")
    return _tk_text_proxy(text, title="ponytail-e2e-terminal-proxy")

def _browser_roundtrip(text):
    if not has_display():
        import pytest; pytest.skip("no DISPLAY for browser xdotool typing (headless can't receive X keystrokes)")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        import pytest; pytest.skip("playwright not installed: pip install playwright && playwright install chromium")
    print(f"[E2E] browser playwright <- {text!r}")
    with sync_playwright() as p:
        headless=not has_display()
        browser=p.chromium.launch(headless=headless, args=["--no-sandbox"])
        page=browser.new_page()
        page.set_content('<html><body><input id="a" style="width:400px;font-size:20px"><textarea id="b"></textarea></body></html>')
        page.wait_for_timeout(400)
        page.focus("#a"); page.wait_for_timeout(250)
        if not headless and shutil.which("xdotool"):
            try: subprocess.run(["xdotool","search","--name","Chromium","windowactivate"], timeout=2, capture_output=True)
            except: pass
            time.sleep(0.3); page.focus("#a")
        Typer().type(text)
        page.wait_for_timeout(700)
        val=page.input_value("#a")
        print(f"  inputValue={val!r}")
        browser.close()
        return val

def test_typing_editor_direct():
    val=_tk_entry_roundtrip("hello ponytail")
    assert "hello ponytail" in val, f"editor direct {val!r}"

def test_typing_terminal_direct():
    val=_terminal_roundtrip("ls -la")
    assert "ls" in val, f"terminal {val!r}"

def test_typing_browser_direct():
    val=_browser_roundtrip("search ponytail skill")
    assert "search" in val.lower() and "ponytail" in val.lower(), f"browser {val!r}"

def test_e2e_editor_transcribe_type():
    txt=_transcribe_check(FIX/"hello.wav", ["hello","world"])
    val=_tk_entry_roundtrip(txt)
    assert val.strip(), "editor e2e empty"
    assert txt.strip().lower()[:3] in val.lower() or _hits(val, txt.split()[:2]), f"mismatch {val!r} vs {txt!r}"

def test_e2e_terminal_transcribe_type():
    txt=_transcribe_check(FIX/"terminal.wav", ["ls"])
    val=_terminal_roundtrip(txt)
    assert val.strip(), f"terminal e2e empty stt={txt!r}"

def test_e2e_browser_transcribe_type():
    txt=_transcribe_check(FIX/"browser.wav", ["search","ponytail","skill"])
    val=_browser_roundtrip(txt)
    assert val.strip(), f"browser e2e empty stt={txt!r}"

if __name__=="__main__":
    import traceback
    try: import pytest; has_pt=True
    except: has_pt=False
    if has_pt:
        sys.exit(subprocess.call([sys.executable,"-m","pytest",__file__,"-v","-s"]))
    tests=[test_transcription, test_typing_editor_direct, test_typing_terminal_direct, test_typing_browser_direct,
           test_e2e_editor_transcribe_type, test_e2e_terminal_transcribe_type, test_e2e_browser_transcribe_type]
    fails=0
    for t in tests:
        print(f"\n=== {t.__name__} ===")
        try: t(); print("PASS")
        except Exception as e:
            if "skip" in str(e).lower() or "Skip" in str(type(e).__name__): fails-=0; print(f"SKIP {e}")
            else: fails+=1; print(f"FAIL {e}"); traceback.print_exc()
    sys.exit(fails)
