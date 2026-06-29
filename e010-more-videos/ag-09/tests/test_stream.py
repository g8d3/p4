"""Tests for stream format."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tds.stream import StreamEvent, format_event, parse_event, write_stream, read_stream


def test_format_keyframe():
    ev = StreamEvent(kind="KEYFRAME", timestamp=0.0, channel="*",
                     ops=["  $ ", "  echo hello"])
    text = format_event(ev)
    assert "KEYFRAME" in text
    assert "t=0.0" in text
    assert "$" in text


def test_format_delta():
    ev = StreamEvent(kind="DELTA", timestamp=3.5, channel="term(1)",
                     ops=["+ hello", "- goodbye"])
    text = format_event(ev)
    assert "DELTA" in text
    assert "t=3.5" in text
    assert "ch=term(1)" in text


def test_format_add():
    ev = StreamEvent(kind="ADD", timestamp=2.0, channel="browser(1)",
                     meta={"url": "https://example.com", "title": "Example"})
    text = format_event(ev)
    assert "ADD" in text
    assert "example.com" in text


def test_format_remove():
    ev = StreamEvent(kind="REMOVE", timestamp=10.0, channel="term(1)")
    text = format_event(ev)
    assert "REMOVE" in text


def test_parse_keyframe():
    block = """KEYFRAME t=0.0
  content:
    line 1
    line 2

"""
    ev = parse_event(block)
    assert ev is not None
    assert ev.kind == "KEYFRAME"
    assert abs(ev.timestamp - 0.0) < 0.01


def test_parse_delta():
    block = """DELTA t=2.5 ch=term(1)
  content:
    + new line
    - old line

"""
    ev = parse_event(block)
    assert ev is not None
    assert ev.kind == "DELTA"
    assert ev.channel == "term(1)"
    assert abs(ev.timestamp - 2.5) < 0.01


def test_parse_add():
    block = """ADD ch=browser(1) t=3.0
  url="https://github.com"
  title="GitHub"

"""
    ev = parse_event(block)
    assert ev is not None
    assert ev.kind == "ADD"
    assert ev.meta.get("url") == "https://github.com"


def test_roundtrip():
    """Write events to file, read back, verify they match."""
    original = [
        StreamEvent(kind="KEYFRAME", timestamp=0.0, channel="*",
                    ops=["  $ ", "  echo hello"]),
        StreamEvent(kind="DELTA", timestamp=1.5, channel="term(1)",
                    ops=["+ hello world"]),
        StreamEvent(kind="ADD", timestamp=2.0, channel="browser(1)",
                    meta={"url": "https://x.com", "title": "X"}),
        StreamEvent(kind="DELTA", timestamp=5.0, channel="browser(1)",
                    ops=["+ Trending: AI", "+ New post about LLMs"]),
        StreamEvent(kind="REMOVE", timestamp=10.0, channel="term(1)"),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".tds", delete=False) as f:
        path = f.name
        write_stream(original, path)

    loaded = read_stream(path)
    os.unlink(path)

    assert len(loaded) == len(original)
    for orig, load in zip(original, loaded):
        assert orig.kind == load.kind
        assert abs(orig.timestamp - load.timestamp) < 0.1
        assert orig.channel == load.channel


def test_empty_stream():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tds", delete=False) as f:
        f.write("# TDS v1\n# Empty test\n\n")
        path = f.name

    loaded = read_stream(path)
    os.unlink(path)
    assert loaded == []


def test_large_stream():
    """Stress: 1000 events"""
    events = []
    for i in range(1000):
        ev = StreamEvent(
            kind="DELTA",
            timestamp=i * 0.5,
            channel="term(1)",
            ops=[f"+ line {j}" for j in range(10)],
        )
        events.append(ev)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".tds", delete=False) as f:
        path = f.name
        write_stream(events, path)

    size = os.path.getsize(path)
    loaded = read_stream(path)
    os.unlink(path)

    assert len(loaded) == len(events)
    assert size > 10000  # Should be substantial
    print(f"  Large stream: {len(events)} events, {size} bytes")


def test_unicode_in_stream():
    ev = StreamEvent(kind="DELTA", timestamp=1.0, channel="term(1)",
                     ops=["+ 日本語 한국어 中文 🔥"])
    text = format_event(ev)
    assert "🔥" in text

    parsed = parse_event(text + "\n")
    assert parsed is not None
    assert any("🔥" in op for op in parsed.ops)


def test_meta_with_special_chars():
    ev = StreamEvent(kind="ADD", timestamp=5.0, channel="browser(1)",
                     meta={"url": "https://example.com?a=1&b=2#frag"})
    text = format_event(ev)
    assert "example.com" in text


if __name__ == "__main__":
    test_format_keyframe()
    test_format_delta()
    test_format_add()
    test_format_remove()
    test_parse_keyframe()
    test_parse_delta()
    test_parse_add()
    test_roundtrip()
    test_empty_stream()
    test_large_stream()
    test_unicode_in_stream()
    test_meta_with_special_chars()
    print("All stream tests passed!")
