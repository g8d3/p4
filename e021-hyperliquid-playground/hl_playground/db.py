"""SQLite persistence for the Hyperliquid playground.

Every artifact the playground produces is a SQLite table, so the SAME query
engine and the SAME generic table renderer work for all of them:

  calls   - scheduled API call configs (also the playground's admin table)
  logs    - one row per executed call (status, latency, row count)
  r_<id>  - one table per call holding the flattened response rows

Dynamic result columns are declared with NUMERIC affinity so SQLite coerces
numeric strings into real numbers: ORDER BY markPx works numerically while
non-numeric values (coin names, hashes) stay text.
"""

import json
import re
import sqlite3
import threading
import uuid

SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  base_url TEXT NOT NULL DEFAULT 'https://api.hyperliquid.xyz',
  path TEXT NOT NULL DEFAULT '/info',
  method TEXT NOT NULL DEFAULT 'POST',
  payload TEXT NOT NULL DEFAULT '{}',
  result_shape TEXT NOT NULL DEFAULT 'auto',
  interval_sec INTEGER NOT NULL DEFAULT 60,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT,
  updated_at TEXT,
  last_run_at TEXT,
  last_status TEXT,
  last_error TEXT,
  last_row_count INTEGER
);
CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  call_id INTEGER NOT NULL,
  ts TEXT NOT NULL,
  status TEXT,
  http_status INTEGER,
  latency_ms INTEGER,
  row_count INTEGER,
  error TEXT
);
CREATE INDEX IF NOT EXISTS idx_logs_call ON logs(call_id);
CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(ts);
CREATE TABLE IF NOT EXISTS config (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TEXT
);
"""

_READ_PREFIXES = ("select", "with", "explain")
_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def result_table(call_id):
    return f"r_{call_id}"


def now_iso():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


class DB:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        self._init_schema()

    def conn(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _init_schema(self):
        with self.lock:
            c = self.conn()
            try:
                c.executescript(SCHEMA)
                c.commit()
            finally:
                c.close()

    # ---- generic query engine (used for EVERY table in the UI) ----

    def run_query(self, sql, limit=2000):
        """Execute a read-only query. Returns (columns, rows, error)."""
        stmt = sql.strip().rstrip(";").strip()
        if not stmt:
            return [], [], "empty query"
        if ";" in stmt:
            return [], [], "only one statement allowed"
        head = stmt.split(None, 1)[0].lower() if stmt else ""
        if head not in _READ_PREFIXES:
            return [], [], "only SELECT / WITH / EXPLAIN queries are allowed"
        c = self.conn()
        try:
            cur = c.execute(stmt)
            if cur.description is None:
                return [], [], "query produced no result set"
            columns = [d[0] for d in cur.description]
            rows = [list(r) for r in cur.fetchmany(limit + 1)]
            truncated = len(rows) > limit
            return columns, rows[:limit], None
        except sqlite3.Error as e:
            return [], [], str(e)
        finally:
            c.close()

    def list_tables(self):
        c = self.conn()
        try:
            rows = c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            tables = []
            for r in rows:
                name = r[0]
                cnt = c.execute(f"SELECT COUNT(*) FROM '{name}'").fetchone()[0]
                cols = [x[1] for x in c.execute(f"PRAGMA table_info('{name}')").fetchall()]
                kind = "result" if name.startswith("r_") else "system"
                tables.append({"name": name, "kind": kind, "rows": cnt, "columns": cols})
            return tables
        finally:
            c.close()

    # ---- result tables ----

    def _create_result_table(self, call_id, columns):
        cols = ", ".join(f'"{_safe_col(c)}" NUMERIC' for c in columns)
        with self.lock:
            c = self.conn()
            try:
                c.execute(f'CREATE TABLE IF NOT EXISTS "{result_table(call_id)}" '
                          f'("_ts" TEXT, {cols})')
                c.commit()
            finally:
                c.close()

    def _ensure_columns(self, call_id, columns):
        c = self.conn()
        try:
            existing = {x[1].lower() for x in c.execute(
                f"PRAGMA table_info('{result_table(call_id)}')").fetchall()}
            for col in columns:
                if col.lower() not in existing:
                    c.execute(f'ALTER TABLE "{result_table(call_id)}" '
                              f'ADD COLUMN "{col}" NUMERIC')
            c.commit()
        finally:
            c.close()

    def store_rows(self, call_id, rows, ts):
        if not rows:
            return 0
        # SQLite identifiers are case-insensitive: dedupe column names so a
        # candle row (has both `t` and `T`) maps to distinct columns.
        cols, keymap, seen = [], {}, set()
        for k in dict.fromkeys(k for r in rows for k in r):
            base = _safe_col(k).lower()
            name, n = base, 1
            while name in seen:
                name = f"{base}_{n}"
                n += 1
            seen.add(name)
            cols.append(name)
            keymap[k] = name
        self._create_result_table(call_id, cols)
        self._ensure_columns(call_id, cols)
        table = result_table(call_id)
        with self.lock:
            c = self.conn()
            try:
                # use the table's actual column names (may differ in case from
                # the ones computed if the table pre-dates a code change)
                actual = {x[1].lower(): x[1] for x in c.execute(
                    f"PRAGMA table_info('{table}')").fetchall()}
                pairs = [(orig, actual[k.lower()]) for orig, k in keymap.items()
                         if k.lower() in actual]
                col_sql = ", ".join(f'"{col}"' for _, col in pairs)
                placeholders = ", ".join("?" for _ in pairs)
                cur = c.executemany(
                    f'INSERT INTO "{table}" ("_ts", {col_sql}) VALUES (?, {placeholders})',
                    [[ts] + [r.get(orig) for orig, _ in pairs] for r in rows],
                )
                c.commit()
                return cur.rowcount or 0
            finally:
                c.close()

    def clear_results(self, call_id):
        with self.lock:
            c = self.conn()
            try:
                c.execute(f'DELETE FROM "{result_table(call_id)}"')
                c.commit()
            except sqlite3.Error:
                pass
            finally:
                c.close()

    # ---- calls CRUD ----

    def create_call(self, data):
        required = ["name", "payload"]
        if not all(data.get(k) for k in required):
            raise ValueError("name and payload are required")
        try:
            json.loads(data["payload"])
        except json.JSONDecodeError as e:
            raise ValueError(f"payload is not valid JSON: {e}")
        ts = now_iso()
        fields = {
            "name": data["name"],
            "base_url": data.get("base_url") or "https://api.hyperliquid.xyz",
            "path": data.get("path") or "/info",
            "method": (data.get("method") or "POST").upper(),
            "payload": data["payload"],
            "result_shape": data.get("result_shape") or "auto",
            "interval_sec": int(data.get("interval_sec") or 60),
            "enabled": 1 if data.get("enabled", True) else 0,
            "created_at": ts,
            "updated_at": ts,
        }
        cols = ", ".join(fields.keys())
        ph = ", ".join("?" for _ in fields)
        with self.lock:
            c = self.conn()
            try:
                cur = c.execute(f"INSERT INTO calls ({cols}) VALUES ({ph})", list(fields.values()))
                c.commit()
                return cur.lastrowid
            except sqlite3.IntegrityError:
                raise ValueError(f"call name '{fields['name']}' already exists")
            finally:
                c.close()

    def update_call(self, call_id, data):
        allowed = {"name", "base_url", "path", "method", "payload", "result_shape",
                   "interval_sec", "enabled"}
        if "payload" in data:
            try:
                json.loads(data["payload"])
            except json.JSONDecodeError as e:
                raise ValueError(f"payload is not valid JSON: {e}")
        sets, vals = [], []
        for k, v in data.items():
            if k not in allowed or v is None:
                continue
            if k == "method":
                v = v.upper()
            if k == "enabled":
                v = 1 if v else 0
            if k == "interval_sec":
                v = int(v)
            sets.append(f"{k} = ?")
            vals.append(v)
        if not sets:
            return
        sets.append("updated_at = ?")
        vals.append(now_iso())
        vals.append(call_id)
        with self.lock:
            c = self.conn()
            try:
                c.execute(f"UPDATE calls SET {', '.join(sets)} WHERE id = ?", vals)
                c.commit()
            except sqlite3.IntegrityError:
                raise ValueError("call name already exists")
            finally:
                c.close()

    def delete_call(self, call_id):
        with self.lock:
            c = self.conn()
            try:
                c.execute("DELETE FROM calls WHERE id = ?", (call_id,))
                c.execute("DELETE FROM logs WHERE call_id = ?", (call_id,))
                c.execute(f'DROP TABLE IF EXISTS "{result_table(call_id)}"')
                c.commit()
            finally:
                c.close()

    def get_call(self, call_id):
        c = self.conn()
        try:
            r = c.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
            return dict(r) if r else None
        finally:
            c.close()

    def list_calls(self, enabled_only=False):
        c = self.conn()
        try:
            sql = "SELECT * FROM calls" + (" WHERE enabled = 1" if enabled_only else "") + " ORDER BY id"
            return [dict(r) for r in c.execute(sql).fetchall()]
        finally:
            c.close()

    # ---- config (persisted UI/user settings) ----

    def get_config(self, key, default=None):
        c = self.conn()
        try:
            r = c.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
            return r["value"] if r else default
        finally:
            c.close()

    def set_config(self, key, value):
        with self.lock:
            c = self.conn()
            try:
                c.execute(
                    "INSERT INTO config (key, value, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                    "updated_at = excluded.updated_at",
                    (key, value, now_iso()),
                )
                c.commit()
            finally:
                c.close()

    def due_calls(self, now_epoch):
        """Calls that are enabled and have an interval that has elapsed."""
        calls = self.list_calls(enabled_only=True)
        due = []
        for call in calls:
            last = call.get("last_run_at")
            if last is None:
                due.append(call)
                continue
            import datetime
            try:
                last_epoch = datetime.datetime.fromisoformat(last).timestamp()
            except ValueError:
                due.append(call)
                continue
            if now_epoch - last_epoch >= call["interval_sec"]:
                due.append(call)
        return due

    def mark_run(self, call_id, status, error, row_count):
        with self.lock:
            c = self.conn()
            try:
                c.execute(
                    "UPDATE calls SET last_run_at = ?, last_status = ?, last_error = ?, "
                    "last_row_count = ?, updated_at = ? WHERE id = ?",
                    (now_iso(), status, error, row_count, now_iso(), call_id),
                )
                c.commit()
            finally:
                c.close()

    def log_run(self, call_id, status, http_status, latency_ms, row_count, error):
        with self.lock:
            c = self.conn()
            try:
                c.execute(
                    "INSERT INTO logs (call_id, ts, status, http_status, latency_ms, "
                    "row_count, error) VALUES (?,?,?,?,?,?,?)",
                    (call_id, now_iso(), status, http_status, latency_ms, row_count, error),
                )
                c.commit()
            finally:
                c.close()


def _safe_col(col):
    """Sanitize a dynamic column name for use in a quoted identifier."""
    s = re.sub(r"[^A-Za-z0-9_]", "_", str(col))
    if not s or s[0].isdigit():
        s = "c_" + s
    if s in ("_ts",) or s.lower() in ("rowid",):
        s = "col_" + s
    return s
