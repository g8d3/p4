"""TDS capture orchestrator: runs terminal and browser watchers, writes .tds file."""

from __future__ import annotations

import argparse
import signal
import sys
import time
import threading
from typing import List, Optional

from .stream import StreamEvent, write_stream
from .terminal import TerminalWatcher
from .browser import BrowserWatcher


class Capture:
    """Orchestrates multiple watchers and collects events into a .tds stream."""

    def __init__(self):
        self.events: List[StreamEvent] = []
        self._start_time: float = 0
        self._lock = threading.Lock()
        self._watchers: list = []

    def _on_event(self, ev: StreamEvent) -> None:
        with self._lock:
            # Truncate ops to prevent unbounded memory
            if len(ev.ops) > 200:
                ev.ops = ev.ops[:200] + [f"... ({len(ev.ops)} total ops, truncated)"]
            self.events.append(ev)

    def add_terminal(self, pane: str, channel_id: str = "term(1)",
                     interval: float = 0.2) -> TerminalWatcher:
        w = TerminalWatcher(pane=pane, channel_id=channel_id, interval=interval)
        self._watchers.append(("term", w))
        return w

    def add_browser(self, cdp_port: int = 9222, channel_prefix: str = "browser",
                    interval: float = 0.5) -> BrowserWatcher:
        w = BrowserWatcher(cdp_port=cdp_port, channel_prefix=channel_prefix, interval=interval)
        self._watchers.append(("browser", w))
        return w

    def run(self, duration: Optional[float] = None) -> List[StreamEvent]:
        """Run all watchers. If duration is None, runs until interrupted."""
        self._start_time = time.time()
        threads = []

        for kind, watcher in self._watchers:
            t = threading.Thread(
                target=watcher.start,
                args=(self._on_event, self._start_time),
                daemon=True,
            )
            t.start()
            threads.append(t)

        print(f"Capture started with {len(self._watchers)} watcher(s)", file=sys.stderr)
        print(f"  Watchers: {[k for k, w in self._watchers]}", file=sys.stderr)

        try:
            if duration:
                time.sleep(duration)
            else:
                # Wait forever until interrupted
                signal.pause()  # type: ignore
        except KeyboardInterrupt:
            print("\nCapture interrupted.", file=sys.stderr)

        self.stop()
        return self.events

    def stop(self) -> None:
        for kind, watcher in self._watchers:
            watcher.stop()
        elapsed = time.time() - self._start_time
        print(f"Capture stopped. {len(self.events)} events in {elapsed:.1f}s", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="TDS - Text Delta Stream capture"
    )
    parser.add_argument("--term-pane", "-t", default=None,
                        help="Tmux pane target for terminal capture")
    parser.add_argument("--browser-port", "-b", type=int, default=None,
                        help="Chrome remote debugging port for browser capture")
    parser.add_argument("--duration", "-d", type=float, default=None,
                        help="Capture duration in seconds (default: until Ctrl+C)")
    parser.add_argument("--term-interval", type=float, default=0.2,
                        help="Terminal poll interval (seconds)")
    parser.add_argument("--browser-interval", type=float, default=0.5,
                        help="Browser poll interval (seconds)")
    parser.add_argument("output", nargs="?", default="capture.tds",
                        help="Output .tds file path")
    args = parser.parse_args()

    cap = Capture()

    if args.term_pane:
        cap.add_terminal(pane=args.term_pane, interval=args.term_interval)
        print(f"  Terminal: pane={args.term_pane}", file=sys.stderr)

    if args.browser_port:
        cap.add_browser(cdp_port=args.browser_port, interval=args.browser_interval)
        print(f"  Browser:   CDP port={args.browser_port}", file=sys.stderr)

    if not args.term_pane and not args.browser_port:
        print("Error: specify at least --term-pane or --browser-port", file=sys.stderr)
        sys.exit(1)

    events = cap.run(duration=args.duration)
    write_stream(events, args.output)
    print(f"Wrote {len(events)} events to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
