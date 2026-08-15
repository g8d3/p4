#!/usr/bin/env python3
"""Live viewer for Open Design daemon run SSE streams.

Usage: od-live.py <runId> [daemonUrl]
Streams events from /api/runs/<runId>/events and prints a readable
one-line-per-event log (tool calls, agent text, status transitions).

Cursor keys / q not needed: Ctrl-C to stop.
"""
import json
import sys
import urllib.request
import time

run_id = sys.argv[1]
daemon = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:37463"
url = f"{daemon}/api/runs/{run_id}/events"

print(f"Streaming run {run_id} from {daemon}  (Ctrl-C to stop)\n")
req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
try:
    with urllib.request.urlopen(req, timeout=3600) as resp:
        buf = ""
        while True:
            chunk = resp.read(4096).decode("utf-8", "replace")
            if not chunk:
                break
            buf += chunk
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if line.startswith("id: "):
                    ts = time.strftime("%H:%M:%S")
                    print(f"\n--- {ts} event {line[4:]} ---")
                elif line.startswith("data: "):
                    try:
                        d = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    t = d.get("type")
                    if t == "text_delta":
                        delta = d.get("delta", "")
                        for para in delta.splitlines():
                            if para.strip():
                                print(f"  OD-AGENT> {para}")
                    elif t == "tool_use":
                        name = d.get("name", "")
                        inp = d.get("input", {})
                        if isinstance(inp, dict):
                            cmd = inp.get("command") or inp.get("filePath") or inp.get("pattern") or inp.get("query") or ""
                        else:
                            cmd = str(inp)
                        print(f"  [tool] {name}: {str(cmd)[:220]}")
                    elif t == "status":
                        print(f"  [status] {d.get('label')}")
                    elif t == "end":
                        print(f"  [END] {d.get('status')} code={d.get('code')} artifacts={d.get('artifactCount')}")
                    elif t == "usage":
                        u = d.get("usage", {})
                        print(f"  [usage] in={u.get('input_tokens')} out={u.get('output_tokens')} $={u.get('costUsd', 0):.4f}")
                    elif t == "diagnostic":
                        pass  # noise
                elif line.startswith(": "):
                    pass  # keepalive
except KeyboardInterrupt:
    print("\nstopped.")
except Exception as e:
    print(f"error: {e}", file=sys.stderr)
