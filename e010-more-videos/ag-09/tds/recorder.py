#!/usr/bin/env python3
"""tds-record: graba video + TDS simultaneamente.

Uso:
  python3 -m tds.recorder --display HEADLESS-1 --duration 30 --name demo
  python3 -m tds.recorder --display HEADLESS-1 --term-pane my-session --duration 60
  python3 -m tds.recorder --display HEADLESS-1 --browser-port 9222 --duration 45

Genera en output/<name>/:
  video.mp4        — grabacion de pantalla
  session.tds      — stream TDS (texto delta)
  metadata.json    — info de la sesion
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import threading
import time

from .stream import StreamEvent, write_stream
from .terminal import TerminalWatcher
from .browser import BrowserWatcher


class CombinedRecorder:
    """Record video + TDS simultaneously."""

    def __init__(self, display: str, name: str, duration: float,
                 term_pane: str = None, browser_port: int = None,
                 browser_url: str = None, output_dir: str = None):
        self.display = display
        self.name = name
        self.duration = duration
        self.term_pane = term_pane
        self.browser_port = browser_port
        self.browser_url = browser_url

        if output_dir:
            self.outdir = output_dir
        else:
            self.outdir = os.path.join(
                os.path.dirname(__file__), "..", "output", name
            )
        os.makedirs(self.outdir, exist_ok=True)

        self.events: list = []
        self._lock = threading.Lock()
        self._watchers: list = []
        self._rec_process = None
        self._start_time = 0

    def _on_event(self, ev: StreamEvent) -> None:
        with self._lock:
            if len(ev.ops) > 200:
                ev.ops = ev.ops[:200] + [f"... (truncated {len(ev.ops)} total)"]
            self.events.append(ev)

    def _start_video_recording(self) -> None:
        """Start wf-recorder on the given display."""
        raw_path = os.path.join(self.outdir, "raw.mp4")
        env = os.environ.copy()
        env["WAYLAND_DISPLAY"] = "wayland-1"

        cmd = [
            "wf-recorder", "-f", raw_path, "-o", self.display,
            "--no-dmabuf", "--no-damage", "-c", "libx264", "-r", "25"
        ]
        self._rec_process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env
        )
        print(f"  Video recording started (PID {self._rec_process.pid}) on {self.display}",
              file=sys.stderr)

    def _stop_video_recording(self) -> dict:
        """Stop wf-recorder and VAAPI-encode the final video."""
        if self._rec_process:
            self._rec_process.terminate()
            try:
                self._rec_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._rec_process.kill()

        raw_path = os.path.join(self.outdir, "raw.mp4")
        final_path = os.path.join(self.outdir, "video.mp4")

        if not os.path.exists(raw_path):
            return {"error": "raw recording not found"}

        # VAAPI encode
        print("  Encoding with VAAPI...", file=sys.stderr)
        result = subprocess.run([
            "ffmpeg", "-y", "-i", raw_path,
            "-vaapi_device", "/dev/dri/renderD128",
            "-vf", "format=nv12,hwupload",
            "-c:v", "h264_vaapi", "-b:v", "2M", final_path
        ], capture_output=True, text=True, timeout=30)
        os.remove(raw_path)

        # Get metadata
        duration = self._get_video_duration(final_path)
        size = os.path.getsize(final_path)

        meta = {
            "duration_sec": duration,
            "file_size": size,
            "display": self.display,
            "name": self.name,
        }
        print(f"  Video: {duration:.1f}s, {size // 1024}KB", file=sys.stderr)
        return meta

    def _get_video_duration(self, path: str) -> float:
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path
            ], capture_output=True, text=True, timeout=5)
            return float(result.stdout.strip())
        except Exception:
            return self.duration

    def run(self) -> str:
        """Run recording: start video + watchers, wait, stop, write outputs."""
        self._start_time = time.time()
        threads = []

        # Start video recording
        self._start_video_recording()

        # Start TDS watchers
        if self.term_pane:
            w = TerminalWatcher(pane=self.term_pane, interval=0.2)
            self._watchers.append(("term", w))
            t = threading.Thread(target=w.start, args=(self._on_event, self._start_time), daemon=True)
            t.start()
            threads.append(t)
            print(f"  Terminal watcher: pane={self.term_pane}", file=sys.stderr)

        if self.browser_port:
            initial_url = self.browser_url or "about:blank"
            w = BrowserWatcher(cdp_port=self.browser_port, interval=0.5, initial_url=initial_url)
            self._watchers.append(("browser", w))
            t = threading.Thread(target=w.start, args=(self._on_event, self._start_time), daemon=True)
            t.start()
            threads.append(t)
            print(f"  Browser watcher: CDP port={self.browser_port}", file=sys.stderr)

        if self.duration:
            print(f"  Recording for {self.duration}s...", file=sys.stderr)
            time.sleep(self.duration)
        else:
            print(f"  Recording until Ctrl+C...", file=sys.stderr)
            try:
                signal.pause()
            except AttributeError:
                while True:
                    time.sleep(1)

        # Stop everything
        for kind, w in self._watchers:
            w.stop()

        video_meta = self._stop_video_recording()

        # Write TDS file
        tds_path = os.path.join(self.outdir, "session.tds")
        write_stream(self.events, tds_path)
        print(f"  TDS: {len(self.events)} events, {os.path.getsize(tds_path)} bytes",
              file=sys.stderr)

        # Write metadata
        meta = {
            **video_meta,
            "tds_events": len(self.events),
            "tds_file": "session.tds",
            "watchers": [k for k, w in self._watchers],
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        meta_path = os.path.join(self.outdir, "metadata.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        print(f"\n  Output: {self.outdir}/", file=sys.stderr)
        print(f"    video.mp4  — grabacion de pantalla", file=sys.stderr)
        print(f"    session.tds — stream de texto delta", file=sys.stderr)
        print(f"    metadata.json — info de la sesion", file=sys.stderr)

        return self.outdir


def main():
    parser = argparse.ArgumentParser(description="Grabar video + TDS simultaneamente")
    parser.add_argument("--display", "-d", default="HEADLESS-1",
                        help="Display virtual a grabar (default: HEADLESS-1)")
    parser.add_argument("--term-pane", "-t", default=None,
                        help="Pane de tmux para captura de terminal")
    parser.add_argument("--browser-port", "-b", type=int, default=None,
                        help="Puerto de remote debugging de Chrome")
    parser.add_argument("--browser-url", "-u", default=None,
                        help="URL inicial para el browser (default: about:blank)")
    parser.add_argument("--duration", "-D", type=float, default=30,
                        help="Duracion en segundos")
    parser.add_argument("--name", "-n", default=None,
                        help="Nombre de la sesion (default: tds-rec-<timestamp>)")
    parser.add_argument("--output", "-o", default=None,
                        help="Directorio de salida")
    args = parser.parse_args()

    if not args.name:
        args.name = f"tds-rec-{int(time.time())}"

    if not args.term_pane and not args.browser_port:
        print("Error: especifica al menos --term-pane o --browser-port", file=sys.stderr)
        sys.exit(1)

    rec = CombinedRecorder(
        display=args.display,
        name=args.name,
        duration=args.duration,
        term_pane=args.term_pane,
        browser_port=args.browser_port,
        browser_url=args.browser_url,
        output_dir=args.output,
    )
    rec.run()


if __name__ == "__main__":
    main()
