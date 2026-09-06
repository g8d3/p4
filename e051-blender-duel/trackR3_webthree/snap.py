import json, subprocess, sys, time, shutil
from pathlib import Path

# usage: snap.py <tag> "<notes>"
tag = sys.argv[1]; notes = sys.argv[2] if len(sys.argv) > 2 else ""
base = Path("/home/vuos/code/p4/e051-blender-duel/trackR3_webthree")
t0 = int((base / ".t0").read_text().strip())
now = int(time.time())
el = now - t0
# wait until the checkpoint minute if early
want = {"01m": 60, "02m": 120, "05m": 300, "10m": 600}.get(tag)
if want and el < want:
    time.sleep(want - el)
    el = int(time.time()) - t0
d = base / "checkpoints" / tag
d.mkdir(parents=True, exist_ok=True)
files = []
for f in ["index.html", "shot.py"]:
    src = base / f
    if src.exists():
        shutil.copy(src, d / f); files.append(f)
# proof screenshots: A-talking + B-talking frames
for frame, name in [(36, "proof_A_f036.png"), (108, "proof_B_f108.png")]:
    out = str(d / name)
    r = subprocess.run(["python3", "shot.py", "http://localhost:8765/trackR3_webthree/index.html",
                        out, str(frame)], cwd=base, capture_output=True, text=True, timeout=120)
    print(r.stdout.strip(), r.stderr.strip()[-300:] if r.stderr else "")
    files.append(name)
(d / "status.json").write_text(json.dumps(
    {"elapsed_s": el, "files": files + ["status.json"], "notes": notes}, indent=1))
print(f"checkpoint {tag} @ elapsed={el}s -> {d}")
