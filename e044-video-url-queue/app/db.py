import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  status TEXT NOT NULL,
  items_json TEXT,
  progress_json TEXT,
  error TEXT,
  output_path TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  started_at REAL,
  finished_at REAL
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
"""


class JobStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        with self._lock:
            self.db.executescript(_SCHEMA)
            self.db.commit()

    def create(self, url: str) -> dict:
        now = time.time()
        job = {
            "id": uuid.uuid4().hex[:12],
            "url": url,
            "status": "queued",
            "items_json": json.dumps([]),
            "progress_json": "{}",
            "error": None,
            "output_path": None,
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "finished_at": None,
        }
        with self._lock:
            self.db.execute(
                "INSERT INTO jobs (id,url,status,items_json,progress_json,error,output_path,"
                "created_at,updated_at,started_at,finished_at) "
                "VALUES (:id,:url,:status,:items_json,:progress_json,:error,:output_path,"
                ":created_at,:updated_at,:started_at,:finished_at)",
                job,
            )
            self.db.commit()
        return job

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            row = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return _row(row)

    def list(self) -> list[dict]:
        with self._lock:
            rows = self.db.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 200"
            ).fetchall()
        return [_row(r) for r in rows]

    def update(self, job_id: str, **fields) -> None:
        fields["updated_at"] = time.time()
        cols = ",".join(f"{k}=?" for k in fields)
        with self._lock:
            self.db.execute(
                f"UPDATE jobs SET {cols} WHERE id=?",
                list(fields.values()) + [job_id],
            )
            self.db.commit()

    def claim_next(self) -> str | None:
        with self._lock:
            now = time.time()
            row = self.db.execute(
                "SELECT id FROM jobs WHERE status='queued' "
                "ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not row:
                return None
            cur = self.db.execute(
                "UPDATE jobs SET status='detecting', started_at=?, updated_at=? "
                "WHERE id=? AND status='queued'",
                (now, now, row[0]),
            )
            self.db.commit()
            if cur.rowcount != 1:
                return None
            return row[0]

    def set_waiting(self) -> int:
        with self._lock:
            now = time.time()
            cur = self.db.execute(
                "UPDATE jobs SET status='waiting_window', updated_at=? "
                "WHERE status='queued'",
                (now,),
            )
            self.db.commit()
            return cur.rowcount

    def release_waiting(self) -> int:
        with self._lock:
            now = time.time()
            cur = self.db.execute(
                "UPDATE jobs SET status='queued', updated_at=? "
                "WHERE status='waiting_window'",
                (now,),
            )
            self.db.commit()
            return cur.rowcount

    def delete(self, job_id: str) -> bool:
        with self._lock:
            cur = self.db.execute("DELETE FROM jobs WHERE id=?", (job_id,))
            self.db.commit()
            return cur.rowcount > 0


def _row(row) -> dict | None:
    if row is None:
        return None
    keys = [
        "id", "url", "status", "items_json", "progress_json", "error",
        "output_path", "created_at", "updated_at", "started_at", "finished_at",
    ]
    job = dict(zip(keys, row))
    job["items"] = json.loads(job.pop("items_json") or "[]")
    job["progress"] = json.loads(job.pop("progress_json") or "{}")
    return job
