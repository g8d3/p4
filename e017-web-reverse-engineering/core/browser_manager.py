"""
Browser Manager — Detect and manage open Chrome instances via CDP.

Scans common CDP ports, identifies browser type, user agent, profile,
and whether there's an active session. Picks the best browser to reuse.
"""

import subprocess
import json
import re
import os
import socket
import httpx
from dataclasses import dataclass, field


CDP_PORTS = [9222, 9223, 9224, 9225, 9226, 9227, 9228, 9229, 9230]


@dataclass
class BrowserInfo:
    port: int
    user_agent: str = ""
    browser_type: str = "unknown"       # chrome, chromium, edge, other
    is_headless: bool = False
    has_profile: bool = False
    profile_name: str = ""
    current_url: str = ""
    cookies_count: int = 0
    ws_url: str = ""
    pid: int = 0

    @property
    def is_usable(self) -> bool:
        return self.port > 0 and not self.is_headless

    @property
    def summary(self) -> str:
        flags = []
        if self.is_headless:
            flags.append("HEADLESS")
        if self.has_profile:
            flags.append(f"profile={self.profile_name}")
        if self.cookies_count > 0:
            flags.append(f"{self.cookies_count} cookies")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        return f"port={self.port} {self.browser_type}{flag_str} {self.user_agent[:50]}"


def port_is_open(port: int) -> bool:
    """Check if a TCP port is open."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


def cdp_get_json(port: int, path: str) -> dict | list | None:
    """GET JSON from Chrome DevTools Protocol HTTP endpoint."""
    try:
        r = httpx.get(f"http://127.0.0.1:{port}{path}", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def cdp_get_text(port: int, path: str) -> str:
    """GET text from CDP endpoint."""
    try:
        r = httpx.get(f"http://127.0.0.1:{port}{path}", timeout=3)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return ""


def discover_browsers() -> list[BrowserInfo]:
    """Scan CDP ports and return info for each running browser."""
    browsers = []

    for port in CDP_PORTS:
        if not port_is_open(port):
            continue

        info = BrowserInfo(port=port)

        # Get WebSocket debug URL
        version = cdp_get_json(port, "/json/version")
        if version:
            info.ws_url = version.get("webSocketDebuggerUrl", "")
            ua = version.get("User-Agent", "")
            info.user_agent = ua

            # Detect browser type
            ua_lower = ua.lower()
            if "headlesschrome" in ua_lower:
                info.is_headless = True
                info.browser_type = "chrome-headless"
            elif "chrome" in ua_lower:
                info.browser_type = "chrome"
            elif "firefox" in ua_lower:
                info.browser_type = "firefox"
            elif "webkit" in ua_lower or "safari" in ua_lower:
                info.browser_type = "webkit"
            else:
                info.browser_type = "other"

        # Get list of tabs
        tabs = cdp_get_json(port, "/json/list")
        if tabs and len(tabs) > 0:
            # Use first tab for current URL
            for tab in tabs:
                if tab.get("type") == "page":
                    info.current_url = tab.get("url", "")
                    break

        # Try to detect profile via cookies
        cookies = cdp_get_json(port, "/json/protocol")
        # Count cookies via JS eval — but we need a tab for that
        # For now, just check if profile dir exists in common locations
        profile_dirs = [
            os.path.expanduser("~/profiles/chrome-main"),
            os.path.expanduser("~/.config/google-chrome/Default"),
            os.path.expanduser("~/.config/chromium/Default"),
        ]
        for pdir in profile_dirs:
            if os.path.isdir(pdir):
                info.has_profile = True
                info.profile_name = os.path.basename(os.path.dirname(pdir))
                break

        browsers.append(info)

    return browsers


def pick_best_browser(browsers: list[BrowserInfo], target_domain: str = "") -> BrowserInfo | None:
    """Pick the best browser to reuse.

    Priority:
    1. Non-headless with profile and cookies (logged in session)
    2. Non-headless with profile (may be logged in)
    3. Non-headless without profile (fresh but usable)
    4. Headless (last resort)
    """
    if not browsers:
        return None

    # Score each browser
    scored = []
    for b in browsers:
        score = 0
        if not b.is_headless:
            score += 100
        if b.has_profile:
            score += 50
        if b.cookies_count > 0:
            score += 30
        if target_domain and target_domain in b.current_url:
            score += 200  # Already on the target domain!
        scored.append((score, b))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def get_browser_summary(browsers: list[BrowserInfo]) -> str:
    """Return a human-readable summary of all detected browsers."""
    if not browsers:
        return "No browsers detected on CDP ports 9222-9230"

    lines = [f"Detected {len(browsers)} browser(s):\n"]
    for b in browsers:
        lines.append(f"  - {b.summary}")
        if b.current_url:
            lines.append(f"    current URL: {b.current_url[:80]}")
    return "\n".join(lines)


def connect_to_browser(port: int) -> dict:
    """Return connection info for agent-browser --cdp <port>."""
    return {
        "port": port,
        "flag": f"--cdp {port}",
        "auto_connect": port == 9222,  # --auto-connect works for default port
    }


if __name__ == "__main__":
    print("Scanning for browsers...\n")
    browsers = discover_browsers()
    print(get_browser_summary(browsers))

    if browsers:
        best = pick_best_browser(browsers)
        print(f"\nBest choice: port {best.port}")
