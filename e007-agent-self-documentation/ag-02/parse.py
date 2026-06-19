#!/usr/bin/env python3
"""Step 1: Parse OpenCode SQLite database into session timeline."""

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

DB_PATH = Path.home() / ".local/share/opencode/opencode.db"


@dataclass
class Part:
    id: str
    type: str  # text, reasoning, tool, patch, step-start, step-finish, file
    text: str
    tool_name: str
    tool_input: str
    tool_output: str
    file_path: str
    time_created: int
    message_id: str

    @property
    def time_seconds(self):
        return self.time_created / 1000


@dataclass
class Session:
    id: str
    title: str
    directory: str
    model: str
    time_created: int
    parts: list[Part] = field(default_factory=list)


def get_session(session_id: str, db_path: str = None) -> Session:
    """Load a session and all its parts from the database."""
    db = db_path or str(DB_PATH)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        "SELECT id, title, directory, model, time_created FROM session WHERE id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Session {session_id} not found")

    session = Session(
        id=row["id"],
        title=row["title"],
        directory=row["directory"],
        model=row["model"],
        time_created=row["time_created"],
    )

    parts = conn.execute(
        "SELECT id, data, time_created, message_id FROM part WHERE session_id = ? ORDER BY time_created",
        (session_id,),
    ).fetchall()

    for p in parts:
        data = json.loads(p["data"])
        ptype = data.get("type", "unknown")

        text = ""
        tool_name = ""
        tool_input = ""
        tool_output = ""
        file_path = ""

        if ptype == "text":
            text = data.get("text", "")
        elif ptype == "reasoning":
            text = data.get("text", "")
        elif ptype == "tool":
            tool_name = data.get("tool", "")
            state = data.get("state", {})
            inp = state.get("input", {})
            if isinstance(inp, dict):
                tool_input = json.dumps(inp, ensure_ascii=False)[:500]
            else:
                tool_input = str(inp)[:500]
            tool_output = str(state.get("output", ""))[:500]
        elif ptype == "patch":
            file_path = data.get("file", "")
            text = f"edit: {file_path}"
        elif ptype in ("step-start", "step-finish"):
            pass
        elif ptype == "file":
            file_path = data.get("file", "")
            text = str(data.get("content", ""))[:200]

        session.parts.append(Part(
            id=p["id"],
            type=ptype,
            text=text,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            file_path=file_path,
            time_created=p["time_created"],
            message_id=p["message_id"],
        ))

    conn.close()
    return session


def list_sessions(directory: str = None, limit: int = 20, db_path: str = None) -> list[dict]:
    """List sessions, optionally filtered by directory."""
    db = db_path or str(DB_PATH)
    conn = sqlite3.connect(db)

    if directory:
        rows = conn.execute(
            """SELECT s.id, s.title, s.directory, s.time_created,
                      (SELECT COUNT(*) FROM part p WHERE p.session_id = s.id) as parts
               FROM session s
               WHERE s.directory = ?
               ORDER BY s.time_created DESC LIMIT ?""",
            (directory, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT s.id, s.title, s.directory, s.time_created,
                      (SELECT COUNT(*) FROM part p WHERE p.session_id = s.id) as parts
               FROM session s
               ORDER BY s.time_created DESC LIMIT ?""",
            (limit,),
        ).fetchall()

    conn.close()
    return [
        {"id": r[0], "title": r[1], "directory": r[2], "time_created": r[3], "parts": r[4]}
        for r in rows
    ]


def export_session_json(session: Session, output_path: str):
    """Export session to JSON file."""
    data = {
        "id": session.id,
        "title": session.title,
        "directory": session.directory,
        "model": session.model,
        "time_created": session.time_created,
        "parts": [
            {
                "id": p.id,
                "type": p.type,
                "text": p.text,
                "tool_name": p.tool_name,
                "tool_input": p.tool_input,
                "tool_output": p.tool_output,
                "file_path": p.file_path,
                "time_created": p.time_created,
                "message_id": p.message_id,
            }
            for p in session.parts
        ],
    }
    Path(output_path).write_text(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 parse.py <session_id> [output.json]")
        print("       python3 parse.py --list [directory]")
        sys.exit(1)

    if sys.argv[1] == "--list":
        directory = sys.argv[2] if len(sys.argv) > 2 else None
        sessions = list_sessions(directory)
        for s in sessions:
            print(f"{s['id']} | {s['parts']:4d} parts | {s['title'][:60]}")
    else:
        session = get_session(sys.argv[1])
        print(f"Session: {session.title}")
        print(f"Parts: {len(session.parts)}")

        if len(sys.argv) > 2:
            export_session_json(session, sys.argv[2])
            print(f"Exported to: {sys.argv[2]}")
        else:
            for p in session.parts[:20]:
                detail = p.text[:60] if p.text else p.tool_name or p.type
                print(f"  {p.type:12s} | {detail}")
