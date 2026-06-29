"""Terminal watcher: polls tmux capture-pane and emits deltas."""

from __future__ import annotations

import subprocess
import time
from typing import List, Optional, Callable

from .diff import diff_snapshots, trim_to_visible, snapshot_key
from .stream import StreamEvent, ChannelState


OnEvent = Callable[[StreamEvent], None]


class TerminalWatcher:
    """Watch a tmux pane and emit deltas on content change.

    Polls `tmux capture-pane -t <pane> -p` every `interval` seconds.
    On each change, emits a DELTA event with added/removed lines.
    """

    def __init__(
        self,
        pane: str,
        channel_id: str = "term(1)",
        interval: float = 0.2,
        max_lines: int = 200,
        max_cols: int = 200,
    ):
        self.pane = pane
        self.channel_id = channel_id
        self.interval = interval
        self.max_lines = max_lines
        self.max_cols = max_cols
        self._last_snapshot: List[str] = []
        self._last_key: str = ""
        self._running = False

    def capture(self) -> List[str]:
        """Run tmux capture-pane and return lines of visible content."""
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", self.pane, "-p"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.split("\n")
            # Remove trailing empty line from split
            if lines and lines[-1] == "":
                lines = lines[:-1]
            # Strip spinner characters to reduce noise
            spinners = set("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏⠛⠹⠰⠠⢀⡀⠄⠂⠁⠈⠐⠐⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟⠠⠡⠢⠣⠤⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠴⠵⠶⠷⠸⠹⠺⠻⠼⠽⠾⠿⬝■")
            cleaned = []
            for line in lines:
                for c in spinners:
                    line = line.replace(c, " ")
                # Collapse multiple spaces from spinner removal
                while "  " in line:
                    line = line.replace("  ", " ")
                cleaned.append(line.rstrip(" "))
            return trim_to_visible(cleaned, self.max_lines, self.max_cols)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            return [f"<capture error: {e}>"]

    def start(self, on_event: OnEvent, start_time: float) -> None:
        """Start polling. Sends KEYFRAME then DELTAs on each change."""
        self._running = True

        # Initial capture
        lines = self.capture()
        self._last_snapshot = lines
        self._last_key = snapshot_key(lines)

        ev = StreamEvent(
            kind="KEYFRAME",
            timestamp=0.0,
            channel=self.channel_id,
            ops=list(lines),
        )
        on_event(ev)

        # Poll loop
        while self._running:
            time.sleep(self.interval)
            lines = self.capture()
            key = snapshot_key(lines)

            if key != self._last_key:
                ops = diff_snapshots(self._last_snapshot, lines)
                if ops:
                    elapsed = time.time() - start_time
                    formatted_ops = [f"{op} {line}" for op, line in ops]
                    ev = StreamEvent(
                        kind="DELTA",
                        timestamp=elapsed,
                        channel=self.channel_id,
                        ops=formatted_ops,
                    )
                    on_event(ev)

                self._last_snapshot = lines
                self._last_key = key

    def stop(self) -> None:
        self._running = False
