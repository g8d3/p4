"""Browser watcher: polls Chrome via CDP and emits deltas."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from .diff import diff_snapshots
from .stream import StreamEvent


OnEvent = Callable[[StreamEvent], None]


@dataclass
class BrowserTab:
    tab_id: str
    url: str = ""
    title: str = ""
    visible_text: str = ""


class BrowserWatcher:
    """Watch a browser via Chrome DevTools Protocol.

    - Filters out extension tabs (chrome-extension://)
    - Creates a new tab on start for real content
    - Polls visible text content via Runtime.evaluate
    - Emits ADD/DELTA/REMOVE events
    """

    def __init__(
        self,
        cdp_port: int = 9222,
        channel_prefix: str = "browser",
        interval: float = 0.5,
        max_text_len: int = 5000,
        initial_url: str = "about:blank",
    ):
        self.cdp_port = cdp_port
        self.channel_prefix = channel_prefix
        self.interval = interval
        self.max_text_len = max_text_len
        self.initial_url = initial_url
        self._tabs: Dict[str, BrowserTab] = {}
        self._last_texts: Dict[str, str] = {}
        self._running = False

    def _cdp_json_url(self) -> str:
        return f"http://localhost:{self.cdp_port}/json"

    async def _http_get_json(self, url: str) -> list:
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=3) as resp:
                    data = await resp.json()
                    return data if isinstance(data, list) else []
        except Exception:
            return []

    async def _ws_send_recv(self, ws_url: str, cmd: dict, timeout: float = 5) -> Optional[dict]:
        """Send a CDP command and receive one response."""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url, timeout=timeout) as ws:
                    await ws.send_str(json.dumps(cmd))
                    resp = await ws.receive(timeout=timeout)
                    if resp.type == aiohttp.WSMsgType.TEXT:
                        return json.loads(resp.data)
        except Exception:
            return None
        return None

    async def _get_tab_info(self, ws_url: str) -> tuple:
        """Get (url, title, body_text) from a tab."""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url, timeout=5) as ws:
                    cmds = [
                        (1, "Runtime.evaluate", {"expression": "window.location.href", "returnByValue": True}),
                        (2, "Runtime.evaluate", {"expression": "document.title", "returnByValue": True}),
                        (3, "Runtime.evaluate", {"expression": "document.body?.innerText || ''", "returnByValue": True}),
                    ]
                    results = {}
                    for cid, method, params in cmds:
                        await ws.send_str(json.dumps({"id": cid, "method": method, "params": params}))
                        resp = await ws.receive(timeout=5)
                        if resp.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(resp.data)
                            if "result" in data and "result" in data["result"]:
                                results[cid] = data["result"]["result"].get("value", "") or ""
                    return (
                        results.get(1, ""),
                        results.get(2, ""),
                        (results.get(3, "") or "")[:self.max_text_len],
                    )
        except Exception:
            return "", "", ""

    async def _create_tab(self, url: str = "about:blank") -> Optional[str]:
        """Create a new tab via CDP Target.createTarget.

        Returns the targetId of the new tab, or None on failure.
        """
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                # First get the browser websocket URL
                async with session.get(
                    f"http://localhost:{self.cdp_port}/json/version", timeout=5
                ) as resp:
                    version = await resp.json()
                    browser_ws = version.get("webSocketDebuggerUrl", "")
                    if not browser_ws:
                        return None

                # Connect to browser endpoint and create target
                async with session.ws_connect(browser_ws, timeout=5) as ws:
                    cmd = json.dumps({
                        "id": 1,
                        "method": "Target.createTarget",
                        "params": {"url": url, "newWindow": False},
                    })
                    await ws.send_str(cmd)
                    resp = await ws.receive(timeout=5)
                    if resp.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(resp.data)
                        return data.get("result", {}).get("targetId")
        except Exception:
            return None
        return None

    def _is_extension(self, url: str) -> bool:
        return url.startswith("chrome-extension://") or url.startswith("chrome://")

    def _is_empty(self, text: str) -> bool:
        return not text or len(text.strip()) < 3

    async def _poll_async(self, on_event: OnEvent, start_time: float) -> None:
        self._running = True
        tab_created = False

        while self._running:
            try:
                tabs = await self._http_get_json(self._cdp_json_url())
                all_tab_ids = set()

                # Create a real content tab on first cycle if initial_url != about:blank
                if not tab_created and self.initial_url != "about:blank":
                    print(f"  [browser] Creating tab: {self.initial_url[:50]}", flush=True)
                    await self._create_tab(self.initial_url)
                    tab_created = True
                    await asyncio.sleep(2)  # wait for tab to appear in listing
                    tabs = await self._http_get_json(self._cdp_json_url())

                for tab in tabs:
                    tab_id = tab.get("id", "")
                    ws_url = tab.get("webSocketDebuggerUrl", "")
                    url = tab.get("url", "")
                    title_from_list = tab.get("title", "")
                    if not ws_url:
                        continue

                    # Skip extension/internal/about:blank/empty tabs
                    if self._is_extension(url) or url in ("about:blank", "chrome://newtab/"):
                        continue

                    all_tab_ids.add(tab_id)

                    # NEW tab discovered
                    if tab_id not in self._tabs:
                        _, _, text = await self._get_tab_info(ws_url)
                        # Only add if it has actual content or is a real URL
                        if not text.strip() and "about:" in url:
                            continue

                        bt = BrowserTab(tab_id=tab_id, url=url, title=title_from_list,
                                        visible_text=text)
                        self._tabs[tab_id] = bt
                        self._last_texts[tab_id] = text

                        idx = len(self._tabs)
                        ch = f"{self.channel_prefix}({idx})"
                        ev = StreamEvent(kind="ADD", timestamp=time.time() - start_time,
                                         channel=ch, meta={"url": url, "title": title_from_list})
                        on_event(ev)

                        if text.strip():
                            lines = text.strip().split("\n")
                            ev2 = StreamEvent(kind="DELTA", timestamp=time.time() - start_time,
                                              channel=ch, ops=[f"+ {l}" for l in lines[:50]])
                            on_event(ev2)

                    # EXISTING tab: check for changes
                    else:
                        url, title, text = await self._get_tab_info(ws_url)
                        last = self._last_texts.get(tab_id, "")
                        if text != last:
                            bt = self._tabs[tab_id]
                            idx = sum(1 for t in self._tabs.values() if t.tab_id <= tab_id)
                            ch = f"{self.channel_prefix}({idx})"

                            # Update metadata if URL/title changed
                            meta = {}
                            if url != bt.url:
                                meta["url"] = url
                                bt.url = url
                            if title != bt.title:
                                meta["title"] = title
                                bt.title = title

                            before = last.split("\n") if last else []
                            after = text.split("\n") if text else []
                            ops = diff_snapshots(before, after)
                            if ops:
                                ev = StreamEvent(kind="DELTA", timestamp=time.time() - start_time,
                                                 channel=ch, meta=meta,
                                                 ops=[f"{o} {l}" for o, l in ops[:50]])
                                on_event(ev)

                            self._last_texts[tab_id] = text or ""
                            bt.visible_text = text

                # Detect closed tabs
                for tab_id in list(self._tabs.keys()):
                    if tab_id not in all_tab_ids:
                        bt = self._tabs[tab_id]
                        idx = sum(1 for t in self._tabs.values() if t.tab_id <= tab_id)
                        ch = f"{self.channel_prefix}({idx})"
                        ev = StreamEvent(kind="REMOVE", timestamp=time.time() - start_time, channel=ch)
                        on_event(ev)
                        del self._tabs[tab_id]
                        del self._last_texts[tab_id]

            except Exception:
                pass

            await asyncio.sleep(self.interval)

    def start(self, on_event: OnEvent, start_time: float) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._poll_async(on_event, start_time))
        finally:
            loop.close()

    def stop(self) -> None:
        self._running = False
