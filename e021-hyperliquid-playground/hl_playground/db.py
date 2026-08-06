"""SQLite persistence for the Hyperliquid playground.

Every artifact the playground produces is a SQLite table, so the SAME query
engine and the SAME generic table renderer work for all of them:

  flows   - flow definitions (the playground's admin table)
  runs    - one row per execution of a flow (status, latency, row count)
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
CREATE TABLE IF NOT EXISTS flows (
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
  last_row_count INTEGER,
  last_request TEXT NOT NULL DEFAULT '',
  read_sql TEXT NOT NULL DEFAULT '',
  config TEXT NOT NULL DEFAULT '{}',
  keep_last INTEGER NOT NULL DEFAULT 0,
  keep_group_col TEXT NOT NULL DEFAULT '',
  keep_by TEXT NOT NULL DEFAULT '',
  dedup_cols TEXT NOT NULL DEFAULT '',
  last_t_col TEXT NOT NULL DEFAULT 't',
  backfill_ms INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  flow_id INTEGER NOT NULL,
  ts TEXT NOT NULL,
  status TEXT,
  http_status INTEGER,
  latency_ms INTEGER,
  row_count INTEGER,
  error TEXT,
  request TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_runs_call ON runs(flow_id);
CREATE INDEX IF NOT EXISTS idx_runs_ts ON runs(ts);
"""

_READ_PREFIXES = ("select", "with", "explain")
_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def result_table(call_id):
    return f"r_{call_id}"


def now_iso():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def valid_payload_template(s):
    """Payloads may contain templates ({{coins}}/{{coins:N}}, {{last_t}},
    {{now_ms}}) that are only valid JSON after resolution — validate with
    representative values."""
    t = (re.sub(r"\{\{coins(?::\d+)?\}\}", '"X"', s)
          .replace("{{last_t}}", "0")
          .replace("{{now_ms}}", "0"))
    try:
        json.loads(t)
        return True
    except json.JSONDecodeError:
        return False


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
                self._rename_legacy_tables(c)
                c.executescript(SCHEMA)
                self._migrate_flows(c)
                self._migrate_runs(c)
                self._migrate_config(c)
                c.execute("UPDATE flows SET read_sql = 'SELECT * FROM {{table}} ORDER BY _ts DESC LIMIT 100' "
                          "WHERE read_sql = ''")
                c.commit()
            finally:
                c.close()

    def _rename_legacy_tables(self, c):
        """Migrate the pre-Flows/Runs naming (calls/logs/call_id) in place."""
        tables = {r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "flows" not in tables and "calls" in tables:
            c.execute("ALTER TABLE calls RENAME TO flows")
        if "runs" not in tables and "logs" in tables:
            c.execute("ALTER TABLE logs RENAME TO runs")
        runs_cols = {x[1] for x in c.execute("PRAGMA table_info('runs')").fetchall()}
        if "flow_id" not in runs_cols and "call_id" in runs_cols:
            c.execute("ALTER TABLE runs RENAME COLUMN call_id TO flow_id")
        c.execute("DROP INDEX IF EXISTS idx_logs_call")
        c.execute("DROP INDEX IF EXISTS idx_logs_ts")

    def _migrate_flows(self, c):
        """Add columns introduced after the initial schema to existing DBs."""
        existing = {x[1] for x in c.execute("PRAGMA table_info('flows')").fetchall()}
        for col, ddl in {
            "last_request": "TEXT NOT NULL DEFAULT ''",
            "read_sql": "TEXT NOT NULL DEFAULT ''",
            "config": "TEXT NOT NULL DEFAULT '{}'",
            "keep_last": "INTEGER NOT NULL DEFAULT 0",
            "keep_group_col": "TEXT NOT NULL DEFAULT ''",
            "keep_by": "TEXT NOT NULL DEFAULT ''",
            "dedup_cols": "TEXT NOT NULL DEFAULT ''",
            "last_t_col": "TEXT NOT NULL DEFAULT 't'",
            "backfill_ms": "INTEGER NOT NULL DEFAULT 0",
        }.items():
            if col not in existing:
                c.execute(f'ALTER TABLE flows ADD COLUMN "{col}" {ddl}')

    def _migrate_runs(self, c):
        existing = {x[1] for x in c.execute("PRAGMA table_info('runs')").fetchall()}
        if "request" not in existing:
            c.execute("ALTER TABLE runs ADD COLUMN request TEXT NOT NULL DEFAULT ''")
        if "flow_id" not in existing and "call_id" in existing:
            c.execute("ALTER TABLE runs RENAME COLUMN call_id TO flow_id")

    def _migrate_config(self, c):
        """Move the legacy `config` table's watchlist into the markets flow,
        then drop the table entirely."""
        try:
            row = c.execute(
                "SELECT value FROM config WHERE key = 'watchlist'").fetchone()
        except sqlite3.OperationalError:
            row = None
        if row:
            market = self.markets_flow(c)
            if market:
                c.execute("UPDATE flows SET config = ? WHERE id = ?",
                          (row["value"], market["id"]))
        c.execute("DROP TABLE IF EXISTS config")

    def markets_flow(self, c=None):
        """The flow that feeds the ranking/watchlist (metaAndAssetCtxs)."""
        own = c is None
        if own:
            c = self.conn()
        try:
            rows = c.execute(
                "SELECT * FROM flows WHERE payload LIKE '%metaAndAssetCtxs%' "
                "OR name = 'markets' ORDER BY id LIMIT 1").fetchall()
            return dict(rows[0]) if rows else None
        finally:
            if own:
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

    def db_stats(self):
        """Storage stats: DB file size + per-table rows/size/24h growth."""
        import datetime
        import os
        c = self.conn()
        try:
            page_count = c.execute("PRAGMA page_count").fetchone()[0]
            page_size = c.execute("PRAGMA page_size").fetchone()[0]
            per_table = dict(c.execute(
                "SELECT name, SUM(pgsize) FROM dbstat GROUP BY name").fetchall())
            since = (datetime.datetime.now(datetime.timezone.utc)
                     - datetime.timedelta(days=1)).isoformat(timespec="seconds")
            tables = []
            for t in self.list_tables():
                name, grown = t["name"], 0
                if name.startswith("r_"):
                    try:
                        grown = c.execute(
                            f'SELECT COUNT(*) FROM "{name}" WHERE _ts >= ?',
                            (since,)).fetchone()[0]
                    except sqlite3.Error:
                        grown = 0
                tables.append({
                    "name": name, "kind": t["kind"], "rows": t["rows"],
                    "columns": len(t["columns"]),
                    "size_bytes": per_table.get(name, 0), "grown_24h": grown,
                })
            wal = str(self.path) + "-wal"
            return {
                "db_file_bytes": os.path.getsize(self.path) if os.path.exists(self.path) else 0,
                "wal_bytes": os.path.getsize(wal) if os.path.exists(wal) else 0,
                "page_count": page_count,
                "page_size": page_size,
                "db_bytes": page_count * page_size,
                "tables": sorted(tables, key=lambda x: -x["size_bytes"]),
            }
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

    def store_rows(self, call_id, rows, ts, dedup_cols=None):
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
                # skip rows that already exist on the dedup columns (e.g. candle
                # boundary re-fetches: dedup_cols "s,t" avoids duplicates)
                dc = [(o, actual[keymap[o].lower()]) for o in keymap
                      if (dedup_cols and keymap[o] in {d.lower() for d in dedup_cols}
                          and keymap[o].lower() in actual)]
                if dc:
                    dcol_sql = ", ".join(f'"{col}"' for _, col in dc)
                    existing = {tuple(r) for r in c.execute(
                        f'SELECT {dcol_sql} FROM "{table}"').fetchall()}
                    rows = [r for r in rows
                            if tuple(r.get(orig) for orig, _ in dc) not in existing]
                    if not rows:
                        return 0
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

    def max_col(self, call_id, col, where_col=None, where_val=None):
        """Max value of a column in a result table, or None if empty/missing.
        Optional `where_col`/`where_val` restrict to a group (e.g. one coin)."""
        c = self.conn()
        try:
            cols = {x[1].lower() for x in c.execute(
                f"PRAGMA table_info('{result_table(call_id)}')").fetchall()}
            if col.lower() not in cols:
                return None
            sql = f'SELECT MAX("{col}") AS m FROM "{result_table(call_id)}"'
            params = []
            if where_col and where_col.lower() in cols:
                sql += f' WHERE "{where_col}" = ?'
                params.append(where_val)
            r = c.execute(sql, params).fetchone()
            return r["m"]
        except sqlite3.Error:
            return None
        finally:
            c.close()

    def prune_rows(self, call_id, keep_last, group_col="", keep_by=""):
        """Keep only the last `keep_last` rows per group.
        With `keep_by` set, keeps the last `keep_last` distinct values of that
        column per group (e.g. book `keep_last=1` + `keep_by=time` keeps the
        whole latest snapshot — all levels — not just one row)."""
        if not keep_last or keep_last <= 0:
            return
        table = result_table(call_id)
        with self.lock:
            c = self.conn()
            try:
                cols = {x[1].lower() for x in c.execute(
                    f"PRAGMA table_info('{table}')").fetchall()}
                if group_col and group_col.lower() not in cols:
                    group_col = ""
                if keep_by and keep_by.lower() not in cols:
                    keep_by = ""
                if group_col and keep_by:
                    n = int(keep_last)
                    sql = (f'DELETE FROM "{table}" WHERE rowid NOT IN ('
                           f'SELECT rowid FROM "{table}" WHERE '
                           f'("{group_col}", "{keep_by}") IN ('
                           f'SELECT "{group_col}", "{keep_by}" FROM ('
                           f'SELECT "{group_col}", "{keep_by}", ROW_NUMBER() OVER ('
                           f'PARTITION BY "{group_col}" ORDER BY "{keep_by}" DESC) AS rn '
                           f'FROM (SELECT DISTINCT "{group_col}", "{keep_by}" FROM "{table}")'
                           f') WHERE rn <= {n}))')
                elif group_col:
                    sql = (f'DELETE FROM "{table}" WHERE rowid NOT IN ('
                           f'SELECT rowid FROM (SELECT rowid, ROW_NUMBER() OVER ('
                           f'PARTITION BY "{group_col}" ORDER BY rowid DESC) AS rn '
                           f'FROM "{table}") WHERE rn <= {int(keep_last)})')
                else:
                    sql = (f'DELETE FROM "{table}" WHERE rowid NOT IN ('
                           f'SELECT rowid FROM "{table}" ORDER BY rowid DESC '
                           f'LIMIT {int(keep_last)})')
                c.execute(sql)
                c.commit()
            except sqlite3.Error:
                pass
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
        if not valid_payload_template(data["payload"]):
            raise ValueError("payload is not valid JSON (templates may be unquoted)")
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
            "keep_last": int(data.get("keep_last") or 0),
            "keep_group_col": data.get("keep_group_col") or "",
            "keep_by": data.get("keep_by") or "",
            "dedup_cols": data.get("dedup_cols") or "",
            "last_t_col": data.get("last_t_col") or "t",
            "backfill_ms": int(data.get("backfill_ms") or 0),
            "read_sql": data.get("read_sql") or "SELECT * FROM {{table}} ORDER BY _ts DESC LIMIT 100",
        }
        cols = ", ".join(fields.keys())
        ph = ", ".join("?" for _ in fields)
        with self.lock:
            c = self.conn()
            try:
                cur = c.execute(f"INSERT INTO flows ({cols}) VALUES ({ph})", list(fields.values()))
                c.commit()
                return cur.lastrowid
            except sqlite3.IntegrityError:
                raise ValueError(f"call name '{fields['name']}' already exists")
            finally:
                c.close()

    def update_call(self, call_id, data):
        allowed = {"name", "base_url", "path", "method", "payload", "result_shape",
                   "interval_sec", "enabled", "keep_last", "keep_group_col",
                   "keep_by", "dedup_cols", "last_t_col", "backfill_ms", "read_sql",
                   "config"}
        if "payload" in data and not valid_payload_template(data["payload"]):
            raise ValueError("payload is not valid JSON (templates may be unquoted)")
        sets, vals = [], []
        for k, v in data.items():
            if k not in allowed or v is None:
                continue
            if k == "method":
                v = v.upper()
            if k == "enabled":
                v = 1 if v else 0
            if k in ("interval_sec", "keep_last", "backfill_ms"):
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
                c.execute(f"UPDATE flows SET {', '.join(sets)} WHERE id = ?", vals)
                c.commit()
            except sqlite3.IntegrityError:
                raise ValueError("call name already exists")
            finally:
                c.close()

    def delete_call(self, call_id):
        with self.lock:
            c = self.conn()
            try:
                c.execute("DELETE FROM flows WHERE id = ?", (call_id,))
                c.execute("DELETE FROM runs WHERE flow_id = ?", (call_id,))
                c.execute(f'DROP TABLE IF EXISTS "{result_table(call_id)}"')
                c.commit()
            finally:
                c.close()

    def get_call(self, call_id):
        c = self.conn()
        try:
            r = c.execute("SELECT * FROM flows WHERE id = ?", (call_id,)).fetchone()
            return dict(r) if r else None
        finally:
            c.close()

    def list_calls(self, enabled_only=False):
        c = self.conn()
        try:
            sql = "SELECT * FROM flows" + (" WHERE enabled = 1" if enabled_only else "") + " ORDER BY id"
            return [dict(r) for r in c.execute(sql).fetchall()]
        finally:
            c.close()

    # ---- per-flow config (JSON column; e.g. markets flow holds the watchlist) ----

    def get_flow_config(self, call_id):
        c = self.conn()
        try:
            r = c.execute("SELECT config FROM flows WHERE id = ?", (call_id,)).fetchone()
            if not r or not r["config"]:
                return {}
            return json.loads(r["config"])
        except (sqlite3.Error, json.JSONDecodeError):
            return {}
        finally:
            c.close()

    def set_flow_config(self, call_id, obj):
        with self.lock:
            c = self.conn()
            try:
                c.execute("UPDATE flows SET config = ?, updated_at = ? WHERE id = ?",
                          (json.dumps(obj), now_iso(), call_id))
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

    def mark_run(self, call_id, status, error, row_count, last_request=""):
        with self.lock:
            c = self.conn()
            try:
                c.execute(
                    "UPDATE flows SET last_run_at = ?, last_status = ?, last_error = ?, "
                    "last_row_count = ?, last_request = ?, updated_at = ? WHERE id = ?",
                    (now_iso(), status, error, row_count, last_request, now_iso(), call_id),
                )
                c.commit()
            finally:
                c.close()

    def log_run(self, call_id, status, http_status, latency_ms, row_count, error, request=""):
        with self.lock:
            c = self.conn()
            try:
                c.execute(
                    "INSERT INTO runs (flow_id, ts, status, http_status, latency_ms, "
                    "row_count, error, request) VALUES (?,?,?,?,?,?,?,?)",
                    (call_id, now_iso(), status, http_status, latency_ms, row_count, error, request),
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
