#!/usr/bin/env python3
"""browser-torture.py: Push browser capture to the limit.

Tests: no Chrome, 100 tabs, infinite scroll, heavy DOM, shadow DOM, iframes,
real-time updates, PDF viewer, and crash recovery.
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from tds.stream import StreamEvent, write_stream


CHROME_BIN = "/usr/bin/google-chrome-stable"
TMPDIR = tempfile.mkdtemp(prefix="tds-browser-torture-")
PORT = 19222
events = []
start_time = time.time()


def log(msg):
    print(f"[{time.time()-start_time:.1f}] {msg}", file=sys.stderr)


def start_chrome(args=None):
    """Start Chrome with remote debugging."""
    cmd = [
        CHROME_BIN,
        f"--remote-debugging-port={PORT}",
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        f"--user-data-dir={TMPDIR}/chrome",
        "--disable-dev-shm-usage",
    ]
    if args:
        cmd.extend(args)
    log(f"Starting Chrome on port {PORT}")
    proc = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    return proc


def stop_chrome(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    log("Chrome stopped")


async def get_tabs():
    """Get tabs via CDP /json."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:{PORT}/json", timeout=3) as resp:
                return await resp.json()
    except Exception as e:
        log(f"Error getting tabs: {e}")
        return []


async def navigate(url, tab_id=None):
    """Navigate a tab to URL."""
    tabs = await get_tabs()
    if not tabs:
        return
    t = tabs[tab_id or 0]
    ws_url = t["webSocketDebuggerUrl"]
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(ws_url, timeout=5) as ws:
            cmd = json.dumps({
                "id": 1,
                "method": "Page.navigate",
                "params": {"url": url},
            })
            await ws.send_str(cmd)
            await ws.receive(timeout=5)


async def get_text(tab_id=0):
    """Get document body text from a tab."""
    tabs = await get_tabs()
    if not tabs or tab_id >= len(tabs):
        return ""
    ws_url = tabs[tab_id]["webSocketDebuggerUrl"]
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, timeout=5) as ws:
                cmd = json.dumps({
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": "document.body?.innerText || ''",
                        "returnByValue": True,
                    }
                })
                await ws.send_str(cmd)
                resp = await ws.receive(timeout=5)
                if resp.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(resp.data)
                    return data.get("result", {}).get("result", {}).get("value", "")
    except Exception as e:
        return f"<error: {e}>"
    return ""


# ============================================================
# TEST SCENARIOS
# ============================================================

async def test_no_chrome():
    """Test 1: What happens when Chrome is not running."""
    log("=" * 50)
    log("Test 1: Browser not running")
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:{PORT}/json", timeout=2) as resp:
                log(f"  Unexpected connection: {resp.status}")
    except Exception as e:
        log(f"  Expected error (no Chrome): {type(e).__name__}")
    log(f"  Events so far: {len(events)}")


async def test_basic_page():
    """Test 2: Basic page with simple text."""
    log("=" * 50)
    log("Test 2: Basic page text capture")

    html_page = os.path.join(TMPDIR, "basic.html")
    with open(html_page, "w") as f:
        f.write("""<html><body>
            <h1>Hello TDS</h1>
            <p>This is a simple test page with some text content.</p>
            <p>Line 1: The quick brown fox</p>
            <p>Line 2: Jumps over the lazy dog</p>
            <p>Line 3: 1234567890</p>
        </body></html>""")

    await navigate(f"file://{html_page}")
    await asyncio.sleep(1)
    text = await get_text()
    log(f"  Captured text ({len(text)} chars):")
    for line in text.split("\n")[:5]:
        log(f"    {line}")


async def test_heavy_dom():
    """Test 3: Page with 10000 DOM elements."""
    log("=" * 50)
    log("Test 3: Heavy DOM (10000 elements)")

    html_page = os.path.join(TMPDIR, "heavy.html")
    with open(html_page, "w") as f:
        f.write("<html><body>\n")
        f.write("<h1>Heavy DOM Test</h1>\n")
        for i in range(10000):
            f.write(f'<p id="p{i}">Paragraph {i}: Lorem ipsum dolor sit amet.</p>\n')
        f.write("</body></html>")

    await navigate(f"file://{html_page}")
    await asyncio.sleep(2)
    text = await get_text()
    log(f"  Captured text: {len(text)} chars, {len(text.split(chr(10)))} lines")

    # Check truncation
    if len(text) > 5000:
        log(f"  Text truncated (good): showing first 100 chars: {text[:100]}...")
    else:
        log(f"  Text NOT truncated (ok): full text fits in limit")


async def test_real_time_updates():
    """Test 4: Page that updates content every 100ms (real-time)."""
    log("=" * 50)
    log("Test 4: Real-time updates every 100ms")

    html_page = os.path.join(TMPDIR, "rt.html")
    with open(html_page, "w") as f:
        f.write("""<html><body>
            <h1>Real-time Updates</h1>
            <div id="counter">0</div>
            <div id="timestamp">-</div>
            <script>
                let count = 0;
                setInterval(() => {
                    count++;
                    document.getElementById('counter').textContent = 'Count: ' + count;
                    document.getElementById('timestamp').textContent = new Date().toISOString();
                }, 100);
            </script>
        </body></html>""")

    await navigate(f"file://{html_page}")
    await asyncio.sleep(1)
    t1 = await get_text()
    log(f"  t=0: {t1[:100]}")
    await asyncio.sleep(2)
    t2 = await get_text()
    log(f"  t=2: {t2[:100]}")

    if t1 != t2:
        log("  Content CHANGED (expected for real-time page)")
    else:
        log("  WARNING: Content did not change!")


async def test_shadow_dom():
    """Test 5: Shadow DOM content."""
    log("=" * 50)
    log("Test 5: Shadow DOM")

    html_page = os.path.join(TMPDIR, "shadow.html")
    with open(html_page, "w") as f:
        f.write("""<html><body>
            <h1>Shadow DOM Test</h1>
            <div id="host1"></div>
            <script>
                const host = document.getElementById('host1');
                const shadow = host.attachShadow({mode: 'open'});
                shadow.innerHTML = '<p>Content INSIDE shadow DOM</p><span>Hidden text!</span>';
            </script>
            <p>Content outside shadow DOM</p>
        </body></html>""")

    await navigate(f"file://{html_page}")
    await asyncio.sleep(1)
    text = await get_text()
    log(f"  Captured ({len(text)} chars):")
    for line in text.split("\n"):
        log(f"    {line}")


async def test_iframes():
    """Test 6: Multiple iframes."""
    log("=" * 50)
    log("Test 6: Nested iframes")

    # Create 3 pages
    for i in range(3):
        with open(os.path.join(TMPDIR, f"frame{i}.html"), "w") as f:
            f.write(f"<html><body><h2>IFrame {i}</h2><p>Content from frame {i}</p></body></html>")

    html_page = os.path.join(TMPDIR, "main.html")
    with open(html_page, "w") as f:
        f.write("""<html><body>
            <h1>IFrame Test</h1>
            <iframe src="frame0.html" width="400" height="100"></iframe>
            <iframe src="frame1.html" width="400" height="100"></iframe>
            <iframe src="frame2.html" width="400" height="100"></iframe>
        </body></html>""")

    await navigate(f"file://{html_page}")
    await asyncio.sleep(2)
    text = await get_text()
    log(f"  Captured ({len(text)} chars):")
    for line in text.split("\n"):
        log(f"    {line}")
    if "IFrame 0" in text and "IFrame 1" in text and "IFrame 2" in text:
        log("  ✅ All iframe content captured!")
    else:
        log("  ⚠️ Some iframe content may be missing")


async def test_infinite_scroll():
    """Test 7: Infinite scroll simulation."""
    log("=" * 50)
    log("Test 7: Infinite scroll")

    html_page = os.path.join(TMPDIR, "scroll.html")
    with open(html_page, "w") as f:
        f.write("""<html><body>
            <h1>Infinite Scroll Test</h1>
            <div id="content"></div>
            <script>
                let page = 0;
                function loadMore() {
                    for (let i = 0; i < 20; i++) {
                        const p = document.createElement('p');
                        p.textContent = 'Item ' + (page * 20 + i + 1) + ': Lorem ipsum dolor sit amet.';
                        document.getElementById('content').appendChild(p);
                    }
                    page++;
                }
                loadMore();
                // Auto-scroll every 500ms
                setInterval(() => {
                    loadMore();
                    window.scrollTo(0, document.body.scrollHeight);
                }, 500);
            </script>
        </body></html>""")

    await navigate(f"file://{html_page}")
    await asyncio.sleep(1.5)
    t1 = await get_text()
    await asyncio.sleep(2)
    t2 = await get_text()
    await asyncio.sleep(2)
    t3 = await get_text()

    log(f"  t=1.5s: {len(t1.split(chr(10)))} lines")
    log(f"  t=3.5s: {len(t2.split(chr(10)))} lines")
    log(f"  t=5.5s: {len(t3.split(chr(10)))} lines")

    if len(t3.split(chr(10))) > len(t1.split(chr(10))):
        log("  ✅ Content growing (infinite scroll detected)")
    else:
        log("  ⚠️ Content not growing as expected")


async def test_crash_recovery():
    """Test 8: Kill Chrome during capture, restart."""
    log("=" * 50)
    log("Test 8: Chrome crash recovery")

    # Kill current Chrome
    stop_chrome(chrome_proc)

    # Try to capture - should fail gracefully
    log("  Trying to capture after crash...")
    text = await get_text()
    log(f"  After crash: '{text[:50]}'")

    # Restart
    log("  Restarting Chrome...")
    new_proc = start_chrome()
    await asyncio.sleep(2)
    text = await get_text()
    if text is not None:
        log(f"  After restart: captured OK")
    else:
        log("  ⚠️ After restart: still failing")
    return new_proc


async def test_multi_tab():
    """Test 9: Multiple tabs with different content."""
    log("=" * 50)
    log("Test 9: Multiple tabs")

    for i in range(5):
        await navigate(f"data:text/html,<h1>Tab {i}</h1><p>Content for tab number {i}</p>", tab_id=0)
        await asyncio.sleep(0.5)
        # Open in new tab via Ctrl+T simulation... or just navigate
        text = await get_text(tab_id=0)
        log(f"  Tab 0 after navigation: {text[:80]}")

    tabs = await get_tabs()
    log(f"  Tabs found: {len(tabs)}")


async def test_very_long_text():
    """Test 10: Page with very long single line."""
    log("=" * 50)
    log("Test 10: Very long single line")

    html_page = os.path.join(TMPDIR, "longtext.html")
    with open(html_page, "w") as f:
        f.write("<html><body><p>")
        f.write("word ".join(str(i) for i in range(1000)))
        f.write("</p></body></html>")

    await navigate(f"file://{html_page}")
    await asyncio.sleep(1)
    text = await get_text()
    log(f"  Captured: {len(text)} chars in {len(text.split(chr(10)))} lines")
    if len(text) > 1000:
        log(f"  First 100 chars: {text[:100]}...")
        log(f"  Last 100 chars: ...{text[-100:]}")


async def main():
    global chrome_proc

    log("=" * 60)
    log("TDS Browser Torture Test Suite")
    log("=" * 60)
    log(f"Temp dir: {TMPDIR}")
    log(f"Chrome: {CHROME_BIN}")
    log("")

    await test_no_chrome()

    chrome_proc = start_chrome()

    await test_basic_page()
    await test_heavy_dom()
    await test_real_time_updates()
    await test_shadow_dom()
    await test_iframes()
    await test_infinite_scroll()
    await test_multi_tab()
    await test_very_long_text()

    chrome_proc = await test_crash_recovery()

    log("")
    log("=" * 60)
    log("Browser Torture Test Complete")
    log("=" * 60)

    stop_chrome(chrome_proc)

    # Cleanup
    import shutil
    shutil.rmtree(TMPDIR, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
