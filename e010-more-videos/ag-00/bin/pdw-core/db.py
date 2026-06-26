"""Thin SQLite wrapper for pdw."""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

DEFAULT_DB = Path(__file__).parent.parent / "output" / "pdw.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT, category TEXT);
CREATE TABLE IF NOT EXISTS displays (name TEXT PRIMARY KEY, resolution TEXT, owner TEXT, status TEXT DEFAULT 'active', created TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS windows (id INTEGER PRIMARY KEY, app_id TEXT, pid INTEGER, display TEXT, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY, inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP, fin TIMESTAMP, status TEXT DEFAULT 'active', agent TEXT);
CREATE TABLE IF NOT EXISTS steps (id INTEGER PRIMARY KEY, session_id INTEGER, tipo TEXT, comando TEXT, inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP, fin TIMESTAMP, duracion_ms INTEGER, exit_code INTEGER);
CREATE TABLE IF NOT EXISTS metrics (id INTEGER PRIMARY KEY, session_id INTEGER, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, cpu_percent REAL, gpu_percent REAL, ram_mb REAL, dma_active INTEGER);
CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY, session_id INTEGER, titulo TEXT, archivo TEXT, duracion_seg REAL, tamanio_bytes INTEGER, resolucion TEXT, codec TEXT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS chunks (id INTEGER PRIMARY KEY, video_id INTEGER, orden INTEGER, url TEXT, seccion TEXT, duracion_plan INTEGER, duracion_real INTEGER, scroll_px INTEGER);
CREATE TABLE IF NOT EXISTS ideas (id INTEGER PRIMARY KEY, tema TEXT, urls TEXT, chunks_plan TEXT, narracion_sketch TEXT, tono TEXT, status TEXT DEFAULT 'pending', creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP, procesado TIMESTAMP);
CREATE TABLE IF NOT EXISTS commands (id INTEGER PRIMARY KEY, session_id INTEGER, binario TEXT, comando TEXT, duracion_ms INTEGER, exit_code INTEGER, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS ast_types (id INTEGER PRIMARY KEY, code TEXT, description TEXT);
INSERT OR IGNORE INTO ast_types VALUES (1, 'stmt', 'statement'), (2, 'id', 'identifier'), (3, 'str', 'string'), (4, 'param', 'parameter');
CREATE TABLE IF NOT EXISTS ast_nodes (id INTEGER PRIMARY KEY, preset_id INTEGER, path TEXT, type_id INTEGER, value TEXT, depth INTEGER DEFAULT 0, parent_id INTEGER);
CREATE TABLE IF NOT EXISTS presets (id INTEGER PRIMARY KEY, name TEXT, verb TEXT, resource TEXT, description TEXT);
"""


class DB:
    """Thin SQLite wrapper."""
    
    def __init__(self, path: Optional[Path] = None):
        self.path = path or DEFAULT_DB
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
    
    def q(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Query rows."""
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]
    
    def x(self, sql: str, params: tuple = ()) -> bool:
        """Execute statement."""
        try:
            self.conn.execute(sql, params)
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False
    
    def close(self):
        self.conn.close()
    
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
