import json
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

import httpx

from .detector import detect_videos, cleanup_browser
from .merger import merge_segments

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

YTDLP_PROGRESS_RE = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")


def _cancelled(store, job_id) -> bool:
    job = store.get(job_id)
    return bool(job and job["status"] == "cancelling")


class Worker:
    def __init__(self, store, cfg, log=lambda *a: None):
        self.store = store
        self.cfg = cfg
        self.log = log
        self.stop_flag = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._loop, daemon=True, name="urlqueue-worker")
        self.thread.start()

    def stop(self):
        self.stop_flag.set()

    def _loop(self):
        while not self.stop_flag.is_set():
            try:
                open_now = self.cfg.window_open()
                if not open_now:
                    if self.store.set_waiting() > 0:
                        self.log("window closed, jobs waiting")
                    self.stop_flag.wait(30)
                    continue
                self.store.release_waiting()
                job_id = self.store.claim_next()
                if not job_id:
                    self.stop_flag.wait(3)
                    continue
                self._process(job_id)
            except Exception as e:
                self.log("worker error:", e)
                self.stop_flag.wait(10)

    def _process(self, job_id: str):
        job = self.store.get(job_id)
        if not job:
            return
        job_dir = self.cfg.data_dir / "downloads" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        progress = {"items": []}
        try:
            self.log(f"job {job_id}: detecting")
            items = detect_videos(job["url"], self.cfg, log=self.log)
            if _cancelled(self.store, job_id):
                self._finish_cancel(job_id, job_dir)
                return
            if not items:
                self.store.update(job_id, status="error", error="no videos found")
                return

            kept = []
            for idx, item in enumerate(items):
                if _cancelled(self.store, job_id):
                    self._finish_cancel(job_id, job_dir)
                    return
                ip = {
                    "index": idx,
                    "url": item["url"],
                    "kind": item["kind"],
                    "status": "downloading",
                    "pct": 0.0,
                    "path": None,
                }
                progress["items"].append(ip)
                self._save_progress(job_id, progress)
                try:
                    dest = self._download_item(job_id, idx, item, job_dir, ip, progress)
                    if dest is None:
                        self._finish_cancel(job_id, job_dir)
                        return
                    ip.update(status="done", pct=1.0, path=str(dest))
                    kept.append(dest)
                    self._save_progress(job_id, progress)
                except Exception as e:
                    ip.update(status="error", error=str(e))
                    self.store.update(job_id, status="error", error=f"download {idx}: {e}")
                    self._save_progress(job_id, progress)
                    return

            if _cancelled(self.store, job_id):
                self._finish_cancel(job_id, job_dir)
                return

            out_dir = self.cfg.data_dir / "output"
            out_dir.mkdir(parents=True, exist_ok=True)
            out = out_dir / f"{job_id}.mp4"
            self.store.update(job_id, status="merging")
            merge_segments(kept, out, self.cfg,
                           cancel_check=lambda: _cancelled(self.store, job_id),
                           log=self.log)
            if _cancelled(self.store, job_id):
                self._finish_cancel(job_id, job_dir)
                return
            self.store.update(job_id, status="done", output_path=str(out), error=None,
                              finished_at=time.time())
            self.log(f"job {job_id}: done -> {out}")
        except Exception as e:
            self.log(f"job {job_id}: error", e)
            self.store.update(job_id, status="error", error=str(e)[:500])

    def _finish_cancel(self, job_id, job_dir):
        shutil.rmtree(job_dir, ignore_errors=True)
        self.store.update(job_id, status="cancelled", error=None, finished_at=time.time())
        self.log(f"job {job_id}: cancelled")

    def _save_progress(self, job_id, progress):
        done_pct = 0.0
        for ip in progress["items"]:
            if ip["status"] == "done":
                done_pct += 1.0
            elif ip["status"] == "downloading":
                done_pct += ip.get("pct", 0.0)
        total = len(progress["items"]) or 1
        payload = json.dumps({
            "items": progress["items"],
            "percent": round(100 * done_pct / total, 1),
        })
        self.store.update(job_id, progress_json=payload,
                          items_json=json.dumps(progress["items"]))

    def _download_item(self, job_id, idx, item, job_dir, ip, progress) -> Path | None:
        limit = self.cfg.get("resource.download_speed_limit_kbps", 0)
        if item["kind"] == "ytdlp":
            return self._download_ytdlp(job_id, idx, item, job_dir, ip, progress)
        return self._download_direct(job_id, idx, item, job_dir, ip, progress, limit)

    def _download_direct(self, job_id, idx, item, job_dir, ip, progress, limit) -> Path | None:
        ext = _ext_from_url(item["url"])
        dest = job_dir / f"seg{idx:03d}{ext}"
        part = dest.with_suffix(dest.suffix + ".part")
        headers = {"User-Agent": UA}
        with httpx.Client(follow_redirects=True, timeout=30, headers=headers) as client:
            with client.stream("GET", item["url"]) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("Content-Length") or 0)
                ip["bytes_total"] = total
                done = 0
                with open(part, "wb") as f:
                    for chunk in resp.iter_bytes(1024 * 256):
                        if _cancelled(self.store, job_id):
                            f.close()
                            part.unlink(missing_ok=True)
                            return None
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            ip["pct"] = round(done / total, 3)
                        if limit:
                            ip.setdefault("_start", time.time())
                            target = done / (limit * 1000 / 8)
                            elapsed = time.time() - ip["_start"]
                            if elapsed < target:
                                time.sleep(min(target - elapsed, 2))
                        if time.time() - ip.get("_t", 0) > 1:
                            ip["_t"] = time.time()
                            self._save_progress(job_id, progress)
        part.rename(dest)
        if not _has_video_stream(dest):
            dest.unlink(missing_ok=True)
            raise RuntimeError("downloaded file is not a video")
        return dest

    def _download_ytdlp(self, job_id, idx, item, job_dir, ip, progress) -> Path | None:
        dest_tpl = job_dir / f"seg{idx:03d}.%(ext)s"
        fmt = item.get("format_id", "bestvideo+bestaudio/best")
        cmd = [
            "nice", "-n", str(self.cfg.get("resource.nice", 10)),
            "yt-dlp", "--no-warnings", "--no-progress", "-f", fmt,
            "--no-mtime", "-o", str(dest_tpl), item["url"],
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        while proc.poll() is None:
            if _cancelled(self.store, job_id):
                proc.kill()
                proc.wait(timeout=5)
                shutil.rmtree(job_dir, ignore_errors=True)
                return None
            line = proc.stdout.readline()
            if line:
                m = YTDLP_PROGRESS_RE.search(line)
                if m:
                    ip["pct"] = round(float(m.group(1)) / 100, 3)
                    self._save_progress(job_id, progress)
            else:
                time.sleep(0.3)
        proc.stdout.close()
        if proc.returncode != 0:
            raise RuntimeError(f"yt-dlp failed (rc={proc.returncode})")
        if _cancelled(self.store, job_id):
            return None
        files = sorted(job_dir.glob(f"seg{idx:03d}.*"))
        if not files:
            raise RuntimeError("yt-dlp produced no file")
        return files[-1]


def _ext_from_url(url: str) -> str:
    m = re.search(r"\.(mp4|webm|mov|mkv|m3u8|ts)(\?|$)", url, re.I)
    return "." + m.group(1).lower() if m else ".mp4"


def _has_video_stream(path: Path) -> bool:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=20,
        )
        return "video" in out.stdout
    except Exception:
        return False
