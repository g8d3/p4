import json
import re
import shutil

import httpx

DIRECT_EXT_RE = re.compile(r"\.(mp4|webm|mov|mkv|m3u8|mpd|ts)(\?|$)", re.I)
SRC_RE = re.compile(
    r'<(?:video|source|audio)[^>]*?\bsrc=["\']([^"\']+)["\']',
    re.I,
)
META_RE = re.compile(r'<meta[^>]*?content=["\']([^"\']+)["\']', re.I)
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
JSONLD_RE = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.I | re.S)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _is_media(link: str) -> bool:
    return bool(link) and not link.startswith(("data:", "blob:", "about:")) and bool(
        DIRECT_EXT_RE.search(link)
    )


def detect_from_html(url: str, log=lambda *a: None) -> list[str]:
    found: list[str] = []
    try:
        with httpx.Client(follow_redirects=True, timeout=20, headers={"User-Agent": UA}) as client:
            resp = client.get(url)
            html = resp.text
    except Exception as e:
        log("html fetch failed:", e)
        return found

    def add(link: str):
        link = link.strip()
        if _is_media(link):
            if link.startswith("//"):
                link = "https:" + link
            elif link.startswith("/"):
                link = f"{resp.url.scheme}://{resp.url.host}{link}"
            if link not in found:
                found.append(link)

    for m in SRC_RE.finditer(html):
        add(m.group(1))
    for attrs in META_RE.finditer(html):
        tag = attrs.group(0)
        if re.search(r'(?:og:video|video_src|twitter:player:stream|og:video:url)', tag, re.I):
            add(attrs.group(1))
        if re.search(r'(?:og:image|twitter:image)', tag, re.I) and DIRECT_EXT_RE.search(attrs.group(1)):
            add(attrs.group(1))
    for m in HREF_RE.finditer(html):
        add(m.group(1))
    for block in JSONLD_RE.findall(html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        for item in _walk_jsonld(data):
            if isinstance(item, dict):
                for key in ("contentUrl", "embedUrl", "url"):
                    val = item.get(key)
                    if isinstance(val, str) and _is_media(val):
                        add(val)
    return found


def _walk_jsonld(data):
    if isinstance(data, dict):
        yield data
        for v in data.values():
            yield from _walk_jsonld(v)
    elif isinstance(data, list):
        for v in data:
            yield from _walk_jsonld(v)


def detect_ytdlp(url: str, max_entries: int, log=lambda *a: None) -> list[dict]:
    yt = shutil.which("yt-dlp")
    if not yt:
        log("yt-dlp not found")
        return []
    cmd = [
        yt, "-J", "--no-warnings", "--no-progress", "--skip-download",
        "--playlist-items", f"1-{max_entries}", url,
    ]
    try:
        import subprocess
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    except subprocess.TimeoutExpired:
        log("yt-dlp timed out")
        return []
    if proc.returncode != 0:
        log("yt-dlp failed:", proc.stderr.strip()[:200])
        return []
    try:
        info = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []

    entries = info.get("entries") or [info]
    items: list[dict] = []
    for entry in entries:
        if not entry:
            continue
        fmt = _pick_format(entry.get("formats") or [])
        fmt_id = fmt.get("format_id") if fmt else "bestvideo+bestaudio/best"
        items.append({
            "url": entry.get("webpage_url") or entry.get("original_url") or url,
            "kind": "ytdlp",
            "format_id": fmt_id,
            "title": entry.get("title", ""),
        })
    return items


def _pick_format(formats: list[dict]) -> dict | None:
    usable = [f for f in formats if f.get("vcodec") not in (None, "none")]
    if not usable:
        usable = formats
    score = 0.0
    best = None
    for f in usable:
        s = 0.0
        if f.get("acodec") not in (None, "none"):
            s += 2
        ext = (f.get("ext") or "").lower()
        if ext in ("mp4", "m4a", "m4v"):
            s += 1
        if f.get("height"):
            s += min(f["height"], 1080) / 1080
        if s > score:
            score, best = s, f
    return best


def detect_videos(url: str, cfg, log=lambda *a: None) -> list[dict]:
    items: list[dict] = []
    seen: set[tuple] = set()

    def add(i: dict):
        key = (i["url"], i.get("format_id", ""))
        if key not in seen:
            seen.add(key)
            items.append(i)

    for link in detect_from_html(url, log):
        add({"url": link, "kind": "direct", "title": ""})

    from .cdp import Browser, find_chrome

    browser_on = bool(cfg.get("detection.browser")) and find_chrome() is not None

    if not items:
        for entry in detect_ytdlp(url, cfg.get("max_entries_per_url", 50), log):
            add(entry)

    if browser_on:
        try:
            browser = getattr(detect_videos, "_browser", None)
            if browser is None:
                browser = Browser(cfg.data_dir / "browser")
                detect_videos._browser = browser
            timeout = cfg.get("detection.browser_timeout_s", 30)
            links: list[str] = []
            for attempt in range(2):
                try:
                    found = browser.collect_videos(url, timeout)
                except RuntimeError as e:
                    log(f"browser pass {attempt + 1} failed:", e)
                    continue
                log(f"browser pass {attempt + 1}: {len(found)} videos")
                if len(found) > len(links):
                    links = found
            for link in links:
                add({"url": link, "kind": "direct", "title": ""})
        except Exception as e:
            log("browser detect failed:", e)

    if not items:
        log("no videos found for", url)
    return items


def cleanup_browser():
    browser = getattr(detect_videos, "_browser", None)
    if browser is not None:
        try:
            browser.proc and browser.proc.terminate()
        except Exception:
            pass
        detect_videos._browser = None
