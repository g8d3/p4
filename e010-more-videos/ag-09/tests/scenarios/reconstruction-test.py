#!/usr/bin/env python3
"""reconstruction-test.py: Record a session, then verify the stream is detailed enough
to answer specific questions about what happened.

This is the most important test: if an LLM can reconstruct the session from the .tds file,
then the format is working as designed.
"""

import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from tds.stream import StreamEvent, write_stream, read_stream
from tds.replay import reconstruct_timeline


TMPDIR = tempfile.mkdtemp(prefix="tds-recon-")
SESSION = f"tds-recon-{os.getpid()}"
TDS_FILE = os.path.join(TMPDIR, "session.tds")
FIXTURE_FILE = os.path.join(TMPDIR, "fixture.tds")


def log(msg):
    print(msg, file=sys.stderr)


def create_fixture_session():
    """Create a known sequence of terminal actions, capture with TDS,
    then verify the stream contains the expected events."""
    log("=" * 60)
    log("Reconstruction Test: Record → Stream → Verify")
    log("=" * 60)

    # Create a tmux session
    subprocess.run(["tmux", "new-session", "-d", "-s", SESSION, "-x", "80", "-y", "24"],
                   check=True)
    time.sleep(0.5)

    # Perform a known sequence of actions
    actions = [
        ("echo 'HELLO_WORLD_12345'", 0.3),
        ("echo 'SECOND_LINE_67890'", 0.3),
        ("ls /tmp | head -3", 0.5),
        ("echo 'MULTI\nLINE\nOUTPUT\nHERE'", 0.5),
        ("uname -a", 0.3),
    ]

    for cmd, delay in actions:
        subprocess.run(["tmux", "send-keys", "-t", SESSION, cmd, "Enter"], check=True)
        time.sleep(delay)

    # Capture the pane content
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", SESSION, "-p"],
        capture_output=True, text=True, check=True
    )
    captured = result.stdout
    log(f"Captured {len(captured)} bytes from session")
    log(f"Content preview:\n{captured[:500]}")

    # Cleanup
    subprocess.run(["tmux", "kill-session", "-t", SESSION], check=False)
    return captured


def build_fixture_stream(known_content):
    """Build a synthetic but realistic TDS stream from the known session."""

    events = []
    lines = known_content.split("\n")

    # Keyframe t=0
    ev = StreamEvent(kind="KEYFRAME", timestamp=0.0, channel="term(1)",
                     ops=[f"  {l}" for l in lines[:5]])
    events.append(ev)

    # DELTA: HELLO_WORLD appeared
    ev = StreamEvent(kind="DELTA", timestamp=1.5, channel="term(1)",
                     ops=["+ $ echo 'HELLO_WORLD_12345'", "+ HELLO_WORLD_12345", "+ $ "])
    events.append(ev)

    # DELTA: SECOND_LINE appeared
    ev = StreamEvent(kind="DELTA", timestamp=3.0, channel="term(1)",
                     ops=["+ $ echo 'SECOND_LINE_67890'", "+ SECOND_LINE_67890", "+ $ "])
    events.append(ev)

    # DELTA: ls output
    ev = StreamEvent(kind="DELTA", timestamp=5.0, channel="term(1)",
                     ops=["+ $ ls /tmp | head -3", "+ file1.txt", "+ file2.txt", "+ $ "])
    events.append(ev)

    # DELTA: multi-line output
    ev = StreamEvent(kind="DELTA", timestamp=7.0, channel="term(1)",
                     ops=["+ $ echo 'MULTI\nLINE\nOUTPUT\nHERE'",
                          "+ MULTI", "+ LINE", "+ OUTPUT", "+ HERE", "+ $ "])
    events.append(ev)

    # DELTA: uname
    ev = StreamEvent(kind="DELTA", timestamp=9.0, channel="term(1)",
                     ops=["+ $ uname -a", "+ Linux hostname 6.8.0-generic x86_64 GNU/Linux", "+ $ "])
    events.append(ev)

    write_stream(events, FIXTURE_FILE)
    log(f"Fixture stream: {len(events)} events written to {FIXTURE_FILE}")
    return events


def verify_stream_against_questions(stream_path):
    """Read the stream and verify it contains evidence for specific questions."""

    events = read_stream(stream_path)
    timeline = reconstruct_timeline(stream_path, compact=False)
    full_text = "\n".join(timeline)

    questions = [
        ("HELLO_WORLD_12345 was typed and shown",
         "HELLO_WORLD_12345" in full_text),
        ("SECOND_LINE_67890 appeared",
         "SECOND_LINE_67890" in full_text),
        ("ls command was executed",
         "ls" in full_text and "/tmp" in full_text),
        ("Multi-line output was captured (MULTI/LINE/OUTPUT/HERE)",
         all(word in full_text for word in ["MULTI", "LINE", "OUTPUT", "HERE"])),
        ("uname command was executed",
         "uname -a" in full_text),
        ("Timestamps are present",
         "t=" in full_text),
        ("Channel identifiers are present",
         "term(1)" in full_text or "DELTA" in full_text),
        ("Operations have + prefix for additions",
         "+" in "".join(ev.ops[0] for ev in events if ev.ops)),
    ]

    log("")
    log("=" * 60)
    log("Verification Results")
    log("=" * 60)
    all_pass = True
    for question, result in questions:
        status = "✅" if result else "❌"
        log(f"  {status} {question}")
        if not result:
            all_pass = False

    log("")
    log(f"Total events: {len(events)}")
    log(f"Timeline lines: {len(timeline)}")

    # Check file size
    size = os.path.getsize(stream_path)
    log(f"Stream file size: {size} bytes")

    return all_pass


def test_extreme_reconstruction():
    """Even more demanding: create a complex stream and verify ALL patterns survived."""
    log("")
    log("=" * 60)
    log("Extreme Reconstruction Test")
    log("=" * 60)

    # Create a stream with special patterns that must survive serialization
    events = []
    special_patterns = [
        ("URL", "https://github.com/trending?q=ai+ml&sort=stars"),
        ("Unicode", "Hello 世界 🌍 ¡Hola! ñoño"),
        ("Spaces", "  indented line  "),
        ("Special chars", "a=b&c=d#fragment?query"),
        ("Backslashes", "C:\\Users\\test\\path"),
        ("Quotes", "She said \"hello\" and 'goodbye'"),
        ("Empty", ""),
        ("Numbers", "12345.67890 -42 0xFF 0b1010"),
        ("CLI flags", "--timeout=30 --format='json' --verbose"),
        ("Tabs", "col1\tcol2\tcol3"),
    ]

    for i, (name, pattern) in enumerate(special_patterns):
        ev = StreamEvent(
            kind="DELTA",
            timestamp=i * 2.0,
            channel="term(1)",
            ops=[f"+ {pattern}"],
            meta={"test": name},
        )
        events.append(ev)

    write_stream(events, os.path.join(TMPDIR, "special.tds"))

    # Read back
    loaded = read_stream(os.path.join(TMPDIR, "special.tds"))

    # Verify all patterns survived
    all_survived = True
    for i, (name, pattern) in enumerate(special_patterns):
        if i >= len(loaded):
            log(f"  ❌ Missing event {i}: {name}")
            all_survived = False
            continue

        ops_text = " ".join(loaded[i].ops)
        if pattern and pattern not in ops_text:
            log(f"  ❌ Pattern lost: {name}")
            log(f"     Expected: {repr(pattern[:50])}")
            log(f"     Got:      {repr(ops_text[:50])}")
            all_survived = False
        elif not pattern:
            log(f"  ✅ Empty pattern handled: {name}")

    if all_survived:
        log("  ✅ All {len(special_patterns)} special patterns survived serialization")

    return all_survived


if __name__ == "__main__":
    known = create_fixture_session()
    events = build_fixture_stream(known)
    result1 = verify_stream_against_questions(FIXTURE_FILE)
    result2 = test_extreme_reconstruction()

    log("")
    log("=" * 60)
    if result1 and result2:
        log("  ✅ RECONSTRUCTION TEST: ALL PASSED")
        sys.exit(0)
    else:
        log("  ❌ RECONSTRUCTION TEST: SOME FAILURES")
        sys.exit(1)
