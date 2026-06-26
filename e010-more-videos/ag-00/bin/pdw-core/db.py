"""Database operations for pdw-core."""
import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

DEFAULT_DB = Path(__file__).parent.parent / "output" / "pdw.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
  key TEXT PRIMARY KEY,
  value TEXT,
  category TEXT
);

CREATE TABLE IF NOT EXISTS displays (
  name TEXT PRIMARY KEY,
  resolution TEXT,
  owner TEXT,
  status TEXT DEFAULT 'active',
  created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS windows (
  id INTEGER PRIMARY KEY,
  app_id TEXT,
  pid INTEGER,
  display TEXT,
  created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (display) REFERENCES displays(name)
);

CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY,
  inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  fin TIMESTAMP,
  status TEXT DEFAULT 'active',
  agent TEXT
);

CREATE TABLE IF NOT EXISTS steps (
  id INTEGER PRIMARY KEY,
  session_id INTEGER,
  tipo TEXT,
  comando TEXT,
  parametros TEXT,
  inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  fin TIMESTAMP,
  duracion_ms INTEGER,
  exit_code INTEGER,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS metrics (
  id INTEGER PRIMARY KEY,
  session_id INTEGER,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  cpu_percent REAL,
  gpu_percent REAL,
  ram_mb REAL,
  dma_active INTEGER,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY,
  session_id INTEGER,
  titulo TEXT,
  archivo TEXT,
  duracion_seg REAL,
  tamanio_bytes INTEGER,
  resolucion TEXT,
  codec TEXT,
  fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY,
  video_id INTEGER,
  orden INTEGER,
  url TEXT,
  seccion TEXT,
  duracion_plan INTEGER,
  duracion_real INTEGER,
  scroll_px INTEGER,
  FOREIGN KEY (video_id) REFERENCES videos(id)
);

CREATE TABLE IF NOT EXISTS ideas (
  id INTEGER PRIMARY KEY,
  tema TEXT,
  urls TEXT,
  chunks_plan TEXT,
  narracion_sketch TEXT,
  tono TEXT,
  status TEXT DEFAULT 'pending',
  creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  procesado TIMESTAMP
);

CREATE TABLE IF NOT EXISTS commands (
  id INTEGER PRIMARY KEY,
  session_id INTEGER,
  binario TEXT,
  comando TEXT,
  duracion_ms INTEGER,
  exit_code INTEGER,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS ast_types (
  id INTEGER PRIMARY KEY,
  code TEXT,
  description TEXT
);

INSERT OR IGNORE INTO ast_types VALUES
(1, 'stmt', 'statement type'),
(2, 'id', 'identifier'),
(3, 'str', 'string literal'),
(4, 'param', 'placeholder parameter');

CREATE TABLE IF NOT EXISTS ast_nodes (
  id INTEGER PRIMARY KEY,
  preset_id INTEGER,
  path TEXT,
  type_id INTEGER,
  value TEXT,
  depth INTEGER DEFAULT 0,
  parent_id INTEGER,
  FOREIGN KEY (type_id) REFERENCES ast_types(id)
);

CREATE TABLE IF NOT EXISTS presets (
  id INTEGER PRIMARY KEY,
  name TEXT,
  verb TEXT,
  resource TEXT,
  description TEXT
);

CREATE VIEW IF NOT EXISTS v_ast_tree AS
SELECT 
  n.id,
  n.preset_id,
  REPEAT('  ', n.depth) || n.path as indent_path,
  t.code as type,
  n.value
FROM ast_nodes n
JOIN ast_types t ON n.type_id = t.id
ORDER BY n.preset_id, n.id;
"""


class Database:
    """SQLite database for pdw state management."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema."""
        self.conn.executescript(SCHEMA)
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # === Display operations ===
    
    def get_displays(self, status: str = "active") -> List[Dict[str, Any]]:
        """Get all displays with given status."""
        cursor = self.conn.execute(
            "SELECT * FROM displays WHERE status = ?", (status,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_display(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific display."""
        cursor = self.conn.execute(
            "SELECT * FROM displays WHERE name = ?", (name,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def add_display(self, name: str, resolution: str = "608x1080") -> bool:
        """Add a display to database."""
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO displays (name, resolution, status) VALUES (?, ?, 'active')",
                (name, resolution)
            )
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def remove_display(self, name: str) -> bool:
        """Mark display as removed."""
        try:
            self.conn.execute(
                "UPDATE displays SET status = 'removed' WHERE name = ?", (name,)
            )
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def update_display(self, name: str, **kwargs) -> bool:
        """Update display properties."""
        if not kwargs:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [name]
        try:
            self.conn.execute(
                f"UPDATE displays SET {set_clause} WHERE name = ?", values
            )
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    # === Window operations ===
    
    def get_windows(self, display: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all windows, optionally filtered by display."""
        if display:
            cursor = self.conn.execute(
                "SELECT * FROM windows WHERE display = ?", (display,)
            )
        else:
            cursor = self.conn.execute("SELECT * FROM windows")
        return [dict(row) for row in cursor.fetchall()]
    
    def add_window(self, app_id: str, pid: int, display: str) -> bool:
        """Add a window to database."""
        try:
            self.conn.execute(
                "INSERT INTO windows (app_id, pid, display) VALUES (?, ?, ?)",
                (app_id, pid, display)
            )
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def remove_window(self, app_id: str, pid: Optional[int] = None) -> bool:
        """Remove a window."""
        try:
            if pid:
                self.conn.execute(
                    "DELETE FROM windows WHERE app_id = ? AND pid = ?", (app_id, pid)
                )
            else:
                self.conn.execute(
                    "DELETE FROM windows WHERE app_id = ?", (app_id,)
                )
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    # === Metrics operations ===
    
    def add_metric(self, session_id: int, cpu: float, gpu: float, ram: float, dma: int) -> bool:
        """Add a metric entry."""
        try:
            self.conn.execute(
                "INSERT INTO metrics (session_id, cpu_percent, gpu_percent, ram_mb, dma_active) VALUES (?, ?, ?, ?, ?)",
                (session_id, cpu, gpu, ram, dma)
            )
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def get_metrics(self, session_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent metrics."""
        if session_id:
            cursor = self.conn.execute(
                "SELECT * FROM metrics WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit)
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM metrics ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
        return [dict(row) for row in cursor.fetchall()]
    
    # === Command operations ===
    
    def add_command(self, session_id: int, binario: str, comando: str, duracion_ms: int, exit_code: int) -> bool:
        """Add a command entry."""
        try:
            self.conn.execute(
                "INSERT INTO commands (session_id, binario, comando, duracion_ms, exit_code) VALUES (?, ?, ?, ?, ?)",
                (session_id, binario, comando, duracion_ms, exit_code)
            )
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def get_command_stats(self) -> List[Dict[str, Any]]:
        """Get command duration statistics."""
        cursor = self.conn.execute("""
            SELECT binario, COUNT(*) as count, 
                   AVG(duracion_ms) as avg_ms,
                   MIN(duracion_ms) as min_ms,
                   MAX(duracion_ms) as max_ms
            FROM commands 
            GROUP BY binario
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    # === Query execution ===
    
    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a query and return results."""
        cursor = self.conn.execute(sql)
        return [dict(row) for row in cursor.fetchall()]
    
    def execute(self, sql: str) -> bool:
        """Execute a statement."""
        try:
            self.conn.execute(sql)
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
