#!/usr/bin/env python3
"""Build the audit-preview page: inject our own turn log as the embedded demo.

    python3 preview/build_preview.py [source.jsonl] -> preview/index.html

The page (index.template.html) is the source of truth; this script only replaces the
`__SAMPLE_JSON__` placeholder with our fleet's turn rows so the "use our own 500-turn log"
button works offline. Two rules for what may be embedded:

  * `sessionId` values are replaced with opaque labels (`s1`, `s2`, ...): a session id is a
    handle the local daemon accepts, so it does not leave this machine.
  * only fields the preview reads are kept (`ts`, `model`, `provider`, `turnIndex`,
    `llmDurationMs`, `preResponseMs`, `toolMsTotal`, `turnMsTotal`, `output`, `input`,
    `outcome`); the `tools` array is dropped and so is `sessionName` (a session's human label
    is private). `provider` is what the route split reads.

Default source: /home/vuos/code/p4/.pi-web/tps-turns.jsonl (the live fleet log).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
TEMPLATE = HERE / "index.template.html"
OUT = HERE / "index.html"
DEFAULT_SRC = Path("/home/vuos/code/p4/.pi-web/tps-turns.jsonl")
KEEP = ("ts", "model", "provider", "turnIndex", "llmDurationMs", "preResponseMs", "toolMsTotal",
        "turnMsTotal", "output", "input", "outcome")


def sanitize(rows: list[dict]) -> list[dict]:
    labels: dict[str, str] = {}
    out = []
    for r in rows:
        sid = r.get("sessionId") or "?"
        labels.setdefault(sid, f"s{len(labels) + 1}")
        row = {k: r[k] for k in KEEP if k in r}
        if not {"ts", "model", "turnMsTotal", "llmDurationMs", "toolMsTotal", "output",
                "outcome"} <= set(row):
            continue
        row["sessionId"] = labels[sid]
        out.append(row)
    return out


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    rows = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    clean = sanitize(rows)
    template = TEMPLATE.read_text()
    if "__SAMPLE_JSON__" not in template:
        raise SystemExit("template has no __SAMPLE_JSON__ placeholder")
    payload = json.dumps(clean, separators=(",", ":")).replace("</", "<\\/")
    html = template.replace("__SAMPLE_JSON__", payload)
    OUT.write_text(html)
    print(f"wrote {OUT.name} ({len(html) / 1024:.0f} KB) — demo = {len(clean)} of {len(rows)} "
          f"rows, {len({r['sessionId'] for r in clean})} session labels, session ids replaced")


if __name__ == "__main__":
    main()
