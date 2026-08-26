import os
import subprocess
import time
from pathlib import Path


def _run(cmd, cancel_check=None, log=lambda *a: None) -> int:
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    while proc.poll() is None:
        if cancel_check and cancel_check():
            proc.kill()
            return -1
        time.sleep(0.4)
    err = proc.stderr.read().decode(errors="replace")[-600:]
    if proc.returncode != 0:
        log("ffmpeg stderr:", err.strip())
    return proc.returncode


def _probe_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=20,
        )
        return float(out.stdout.strip() or 0)
    except Exception:
        return 0.0


def merge_segments(paths: list[Path], out: Path, cfg, cancel_check=None,
                   log=lambda *a: None, use_gpu=True) -> Path:
    if len(paths) == 1:
        tmp = out.with_suffix(".tmp.mp4")
        _run(["cp", "-f", str(paths[0]), str(tmp)], cancel_check)
        if not tmp.exists():
            raise RuntimeError("single segment copy failed")
        tmp.replace(out)
        return out

    list_file = out.parent / f"{out.stem}.list.txt"
    list_file.write_text(
        "".join(f"file '{str(p).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n" for p in paths)
    )

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", "-movflags", "+faststart",
        str(out),
    ]
    rc = _run(cmd, cancel_check, log)
    if rc == 0 and os.path.getsize(out) > 0:
        if _probe_duration(out) > 0:
            list_file.unlink(missing_ok=True)
            return out

    log("copy-concat failed, falling back to re-encode")
    out.unlink(missing_ok=True)
    vaapi = "/dev/dri/renderD128"
    threads = max(1, round((cfg.get("resource.cpu_percent", 50) / 100) * os.cpu_count()))
    nice = str(cfg.get("resource.nice", 10))

    if not (use_gpu and os.path.exists(vaapi)):
        vaapi = None

    segs = []
    for i, p in enumerate(paths):
        seg = out.parent / f"{out.stem}.seg{i}.mp4"
        cmd = ["ffmpeg", "-y", "-i", str(p)]
        if vaapi:
            cmd += [
                "-vaapi_device", vaapi,
                "-vf", "format=nv12,hwupload",
                "-c:v", "h264_vaapi", "-qp", "23", "-threads", str(threads),
            ]
        else:
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-threads", str(threads)]
        cmd += ["-c:a", "aac", "-b:a", "192k", str(seg)]
        rc = _run(["nice", "-n", nice] + cmd, cancel_check, log)
        if rc != 0 or _probe_duration(seg) <= 0:
            for s in segs:
                s.unlink(missing_ok=True)
            raise RuntimeError(f"segment re-encode failed at {i}")
        segs.append(seg)

    seg_list = out.parent / f"{out.stem}.segs.txt"
    seg_list.write_text(
        "".join(f"file '{str(s)}'\n" for s in segs)
    )
    rc = _run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(seg_list),
         "-c", "copy", "-movflags", "+faststart", str(out)],
        cancel_check, log,
    )
    for s in segs:
        s.unlink(missing_ok=True)
    seg_list.unlink(missing_ok=True)
    if rc != 0 or _probe_duration(out) <= 0:
        out.unlink(missing_ok=True)
        raise RuntimeError("merge failed")
    return out
