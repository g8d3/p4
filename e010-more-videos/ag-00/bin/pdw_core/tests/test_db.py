"""Tests for db module."""
import tempfile
from pathlib import Path
from pdw_core.db import DB


def test_db_init():
    """Test database initialization."""
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db = DB(Path(f.name))
        assert db.path.exists()
        db.close()


def test_db_query():
    """Test query execution."""
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db = DB(Path(f.name))
        result = db.q("SELECT 1 as test")
        assert len(result) == 1
        assert result[0]["test"] == 1
        db.close()


def test_db_execute():
    """Test statement execution."""
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db = DB(Path(f.name))
        assert db.x("INSERT INTO config (key, value) VALUES ('test', 'value')")
        result = db.q("SELECT * FROM config WHERE key='test'")
        assert len(result) == 1
        assert result[0]["value"] == "value"
        db.close()


def test_db_displays():
    """Test display operations."""
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db = DB(Path(f.name))
        
        # Add display
        assert db.x("INSERT INTO displays (name, status) VALUES ('H1', 'active')")
        
        # Query display
        result = db.q("SELECT * FROM displays WHERE name='H1'")
        assert len(result) == 1
        assert result[0]["name"] == "H1"
        assert result[0]["status"] == "active"
        
        # Update display
        assert db.x("UPDATE displays SET owner='agent-1' WHERE name='H1'")
        result = db.q("SELECT owner FROM displays WHERE name='H1'")
        assert result[0]["owner"] == "agent-1"
        
        # Remove display
        assert db.x("UPDATE displays SET status='removed' WHERE name='H1'")
        result = db.q("SELECT status FROM displays WHERE name='H1'")
        assert result[0]["status"] == "removed"
        
        db.close()


def test_db_windows():
    """Test window operations."""
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db = DB(Path(f.name))
        
        # Add window
        assert db.x("INSERT INTO windows (app_id, pid, display) VALUES ('chrome', 1234, 'H1')")
        
        # Query window
        result = db.q("SELECT * FROM windows WHERE app_id='chrome'")
        assert len(result) == 1
        assert result[0]["pid"] == 1234
        
        # Remove window
        assert db.x("DELETE FROM windows WHERE app_id='chrome' AND pid=1234")
        result = db.q("SELECT * FROM windows WHERE app_id='chrome'")
        assert len(result) == 0
        
        db.close()


if __name__ == "__main__":
    test_db_init()
    test_db_query()
    test_db_execute()
    test_db_displays()
    test_db_windows()
    print("All tests passed!")
