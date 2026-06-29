"""Tests for diff engine."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tds.diff import diff_snapshots, trim_to_visible, snapshot_key


def test_empty():
    assert diff_snapshots([], []) == []


def test_no_change():
    assert diff_snapshots(["a", "b"], ["a", "b"]) == []
    assert diff_snapshots(["hello"], ["hello"]) == []


def test_addition():
    ops = diff_snapshots(["a"], ["a", "b"])
    assert ("+", "b") in ops


def test_removal():
    ops = diff_snapshots(["a", "b"], ["a"])
    assert ("-", "b") in ops


def test_replacement():
    ops = diff_snapshots(["a"], ["b"])
    assert ("~", "a") in ops or ("+", "b") in ops


def test_complex():
    before = ["$ ", "echo hello", "hello", "$ "]
    after = ["$ ", "echo world", "world", "$ "]
    ops = diff_snapshots(before, after)
    assert len(ops) > 0


def test_trim_to_visible():
    lines = [f"line {i}" for i in range(500)]
    trimmed = trim_to_visible(lines, max_lines=100, max_cols=50)
    assert len(trimmed) == 100
    assert trimmed[-1] == "line 499"


def test_trim_columns():
    lines = ["x" * 500]
    trimmed = trim_to_visible(lines, max_lines=10, max_cols=10)
    assert trimmed[0].endswith("...")


def test_snapshot_key():
    assert snapshot_key(["a", "b"]) == snapshot_key(["a", "b"])
    assert snapshot_key(["a"]) != snapshot_key(["b"])


def test_large_diff():
    """Stress test: diff 10000 lines"""
    before = [f"line {i}" for i in range(10000)]
    after = [f"line {i}" for i in range(10000)]
    after[5000] = "MODIFIED"
    ops = diff_snapshots(before, after)
    assert len(ops) > 0


def test_unicode_diff():
    ops = diff_snapshots(["hola"], ["hola", "mundo 🌍"])
    assert ("+", "mundo 🌍") in ops


def test_all_changed():
    before = ["a", "b", "c"]
    after = ["x", "y", "z"]
    ops = diff_snapshots(before, after)
    # Should detect all as changed (might be ~ or -/+)
    assert len(ops) >= 3


def test_whitespace_sensitive():
    """Whitespace matters in terminal content."""
    before = ["  indented"]
    after = ["indented"]
    ops = diff_snapshots(before, after)
    assert len(ops) > 0


if __name__ == "__main__":
    test_empty()
    test_no_change()
    test_addition()
    test_removal()
    test_replacement()
    test_complex()
    test_trim_to_visible()
    test_trim_columns()
    test_snapshot_key()
    test_large_diff()
    test_unicode_diff()
    test_all_changed()
    test_whitespace_sensitive()
    print("All diff tests passed!")
