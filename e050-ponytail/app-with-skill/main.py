#!/usr/bin/env python3
"""Voice dictation popup — single-file, stdlib-first.
Built with DietrichGebert/ponytail skill (full): ladder rungs 3-5 applied.
Usage: pip install sounddevice SpeechRecognition pynput && python main.py
  env OPENAI_API_KEY optional | XDG_SESSION_TYPE auto-detected
Hotkey: Ctrl+Alt+V toggle | Drag move | Right-click menu | Ctrl+C/Ctrl+Q/Esc quit
"""
# ponytail: global STATE/TMP lock — per-window state if multi-window needed
import os, sys, signal, subprocess, tempfile, threading, shutil
import tkinter as tk

STATE="idle"  # idle | recording | processing
TMP=tempfile.gettempdir()+"/dictation.wav"  # ponytail: single temp file, unique per-process if parallel rec needed
rec_proc=None; sd_stream=None; sd_frames=[]

# ── optional deps (graceful degrade) ──
try: import pyatspi
except: pyatspi=None
try: import sounddevice as sd, soundfile as sf
except: sd=sf=None
try: import speech_recognition as sr
except: sr=None

def record_audio(start=True):
    global rec_proc, sd_stream, sd_frames
    if start:
        sd_frames=[]
        if sd and sf:
            def cb(indata, frames, time, status): sd_frames.append(indata.copy())
            sd_stream=sd.InputStream(samplerate=16000,channels=1,dtype='int16',callback=cb)
            sd_stream.start(); return True
        # fallback: arecord subprocess (linux)
        if shutil.which("arecord"):
            rec_proc=subprocess.Popen(["arecord","-f","S16_LE","-r","16000","-c","1","-t","wav",TMP])
            return True
        # last resort: pyaudio
        try:
            import pyaudio, wave
            def _rec():
                pa=pyaudio.PyAudio(); s=pa.open(format=pyaudio.paInt16,channels=1,rate=16000,input=True,frames_per_buffer=1024)
                fr=[]
                while STATE=="recording": fr.append(s.read(1024,exception_on_overflow=False))
                s.stop_stream(); s.close(); pa.terminate()
                with wave.open(TMP,'wb') as wf: wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000); wf.writeframes(b''.join(fr))
            threading.Thread(target=_rec,daemon=True).start()
            return True
        except: return False
    else:
        if sd_stream:
            sd_stream.stop(); sd_stream.close(); sd_stream=None
            if sd_frames and sf:
                import numpy as np
                data=np.concatenate(sd_frames,axis=0); sf.write(TMP,data,16000)
            return TMP
        if rec_proc:
            rec_proc.terminate()
            try: rec_proc.wait(timeout=2)
            except: rec_proc.kill()
            rec_proc=None; return TMP
        return TMP if os.path.exists(TMP) else None

def transcribe(wav):
    # 1) OpenAI Whisper API if key
    if os.getenv("OPENAI_API_KEY"):
        try:
            import urllib.request, json
            import uuid
            bnd=uuid.uuid4().hex
            with open(wav,'rb') as f: ad=f.read()
            body=b'--'+bnd.encode()+b'\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\nContent-Type: audio/wav\r\n\r\n'+ad+b'\r\n--'+bnd.encode()+b'\r\nContent-Disposition: form-data; name="model"\r\n\r\nwhisper-1\r\n--'+bnd.encode()+b'--\r\n'
            req=urllib.request.Request("https://api.openai.com/v1/audio/transcriptions",data=body,headers={"Authorization":"Bearer "+os.getenv("OPENAI_API_KEY"),"Content-Type":"multipart/form-data; boundary="+bnd})
            with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read())["text"]
        except Exception as e: print("openai:",e)
    # 2) Google free via SpeechRecognition (default, no key)
    if sr:
        try:
            r=sr.Recognizer()
            with sr.AudioFile(wav) as s: audio=r.record(s)
            return r.recognize_google(audio)
        except Exception as e: print("sr:",e)
    # 3) local faster-whisper
    try:
        from faster_whisper import WhisperModel
        m=WhisperModel("tiny",device="cpu",compute_type="int8")
        segs,_=m.transcribe(wav); return "".join(s.text for s in segs).strip()
    except Exception as e: print("faster-whisper:",e)
    return "[transcription failed: install SpeechRecognition or set OPENAI_API_KEY]"

def type_text(text):
    if not text or text.startswith("["): return
    sess=os.getenv("XDG_SESSION_TYPE","").lower()
    cmds=[]
    if sess=="wayland": cmds=[["wtype",text],["ydotool","type",text]]
    else: cmds=[["xdotool","type","--clearmodifiers",text],["wtype",text],["ydotool","type",text]]
    for c in cmds:
        if shutil.which(c[0]):
            try: subprocess.run(c,timeout=5,check=False); return
            except: pass
    # universal fallback
    try:
        from pynput.keyboard import Controller
        Controller().type(text)
    except Exception as e: print("type failed:",e,"text:",text)

def setup_ui(root):
    global STATE
    root.overrideredirect(True); root.attributes("-topmost",True)
    root.geometry("64x64+40+40"); root.configure(bg="#1a1a1a")
    # draggable
    def drag(e): root.geometry(f"+{e.x_root-32}+{e.y_root-32}")
    def start_drag(e): root._dx=e.x; root._dy=e.y
    root.bind("<B1-Motion>",drag)
    # button
    btn=tk.Label(root,text="🎤",font=("Arial",24),bg="#3a3a3a",fg="white",width=3,height=1)
    btn.pack(expand=True,fill="both",padx=2,pady=2)
    def set_state(s):
        global STATE; STATE=s
        c={"idle":"#3a3a3a","recording":"#e53935","processing":"#fdd835"}[s]
        btn.configure(bg=c,text={"idle":"🎤","recording":"●","processing":"…"}[s])
        if s=="recording": pulse()
    def pulse():
        if STATE!="recording": return
        cur=btn.cget("bg"); nxt="#ff6f60" if cur=="#e53935" else "#e53935"
        btn.configure(bg=nxt); root.after(500,pulse)
    def toggle_recording(e=None):
        if STATE=="recording":
            set_state("processing"); wav=record_audio(False)
            def go():
                t=transcribe(wav) if wav and os.path.exists(wav) else ""
                print(">",t); type_text(t)
                root.after(0,lambda: set_state("idle"))
            threading.Thread(target=go,daemon=True).start()
        elif STATE=="idle":
            if record_audio(True): set_state("recording")
            else: print("no audio backend")
    btn.bind("<Button-1>",toggle_recording)
    root.bind("<Control-Alt-v>",toggle_recording); root.bind("<Control-Alt-V>",toggle_recording)
    # close: Ctrl+C / Ctrl+Q / Escape, and right-click menu
    def quit_app(e=None):
        try: record_audio(False)
        except: pass
        root.destroy(); sys.exit(0)
    root.bind("<Control-c>", quit_app); root.bind("<Control-C>", quit_app)
    root.bind("<Control-q>", quit_app); root.bind("<Control-Q>", quit_app)
    root.bind("<Escape>", quit_app)
    signal.signal(signal.SIGINT, lambda s,f: quit_app())
    signal.signal(signal.SIGTERM, lambda s,f: quit_app())
    # right-click: hide (Ctrl+Alt+h to show) + middle-click quit
    def hide(e=None): root.withdraw()
    def show(e=None): root.deiconify()
    btn.bind("<Button-3>", lambda e: hide())
    btn.bind("<Button-2>", lambda e: quit_app())
    root.bind("<Control-Alt-h>", lambda e: show())
    # tiny context menu on right-click with Quit
    try:
        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="Show (Ctrl+Alt+h)", command=show)
        menu.add_command(label="Quit (Ctrl+Q / Ctrl+C)", command=quit_app)
        btn.bind("<Button-3>", lambda e: (menu.tk_popup(e.x_root, e.y_root), hide()))
    except: pass
    return toggle_recording, set_state

def poll_focus(root):
    if pyatspi is None: return  # ponytail: graceful degrade — always visible, add AT-SPI only if installed
    # ponytail: 500ms dumb poll, event listener if CPU matters
    try:
        desktop=pyatspi.Registry.getDesktop(0)
        for i in range(desktop.childCount):
            app=desktop.getChildAtIndex(i)
            for j in range(app.childCount):
                w=app.getChildAtIndex(j)
                if w.getState().contains(pyatspi.STATE_FOCUSED):
                    # walk to focused descendant
                    f=w
                    while True:
                        try: k=f.getState().contains; break
                        except: break
                    role=f.getRoleName().lower() if hasattr(f,"getRoleName") else ""
                    editable=any(x in role for x in ["text","entry","password","document","terminal","edit"])
                    if editable: root.deiconify()
                    else: root.withdraw()
                    break
    except: pass
    root.after(500,lambda: poll_focus(root))

if __name__=="__main__":
    root=tk.Tk()
    toggle, _ = setup_ui(root)
    if pyatspi: poll_focus(root)
    print("dictation ready — click mic or Ctrl+Alt+V | drag move | right-click menu (Quit) | Ctrl+C/Ctrl+Q/Esc to quit")
    try:
        root.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)
