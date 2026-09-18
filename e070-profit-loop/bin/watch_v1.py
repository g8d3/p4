#!/usr/bin/env python3
"""e070 watcher v1: venue-direct bounty radar. $0 inference (stdlib only, no model calls).

Fetches live listings DIRECTLY from venue pages/APIs (no generic web search):
  - Cantina  https://cantina.xyz/opportunities/competitions (embedded query JSON)
    + sitemap pagination: sitemap-0.xml enumerates ALL /bounties/<uuid> pages;
      detail pages of unknown urls are fetched (cap 50/run) and live ones kept
  - Sherlock https://audits.sherlock.xyz/api/contests (paginated JSON, ?page=N)
  - Superteam Earn https://superteam.fun/api/listings (small fixed-price bounties)
  - Code4rena https://code4rena.com/audits (server-rendered audit tiles)
  - Immunefi https://immunefi.com/bug-bounty/ (embedded program JSON)
  - Algora   https://algora.io/challenges (server-rendered challenge cards)
One GET per venue, 20s timeout, custom UA; any failure -> venue skipped (never hammer).
Appends ONLY genuinely open + paid finds to data/watch.jsonl as
  {"ts":..,"who":"watcher","venue":..,"title":..,"url":..,"bounty":..}
Dedupes against urls already in watch.jsonl.
Usage: python3 bin/watch_v1.py
"""
import datetime
import html as htmllib
import json
import os
import re
import sys
import urllib.request

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCH = os.path.join(DIR, "data", "watch.jsonl")
UA = {"User-Agent": "Mozilla/5.0 (e070 watcher v1 pilot; venue-direct)"}
TIMEOUT = 20


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", errors="replace")


def money(n):
    try:
        f = float(n)
    except (TypeError, ValueError):
        return str(n)
    if f >= 1_000_000:
        s = f"{f / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"${s}M"
    if f >= 1_000:
        s = f"{f / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"${s}k"
    return f"${f:,.0f}"


def venue_cantina():
    """Parse embedded react-query dehydrated state: items with status live."""
    html = fetch("https://cantina.xyz/opportunities/competitions")
    # items are embedded as \"-escaped JSON (react-query dehydrated state);
    # match id/name/url records directly on the full page (never on a slice).
    recs = re.findall(
        r'\\"id\\":\\"([0-9a-f\-]{36})\\",\\"name\\":\\"((?:[^\\"\\\\]|\\\\.)*)\\",'
        r'\\"url\\":\\"(https://cantina\.xyz/bounties/[0-9a-f\-]{36})\\"',
        html)
    # company + status + pot per record: search forward from each url occurrence
    out = []
    for _id, name, url in recs:
        idx = html.find(url.replace("https://cantina.xyz/bounties/", ""))
        ctx = html[idx:idx + 2500] if idx > 0 else ""
        st = re.search(r'\\"status\\":\\"([a-z]+)\\"', ctx)
        status = st.group(1) if st else ""
        if status != "live":
            continue
        co = re.search(r'\\"company\\":\{[^}]*?\\"name\\":\\"((?:[^\\"\\\\]|\\\\.)*)\\"', ctx)
        pot = re.search(r'\\"totalRewardPot\\":\\"([\d.]+)\\"', ctx)
        cur = re.search(r'\\"currencyCode\\":\\"([A-Z]+)\\"', ctx)
        company = co.group(1) if co else ""
        bounty = (money(pot.group(1)) + " " + (cur.group(1) if cur else "")).strip()
        title = f"{name} ({company})" if company else name
        out.append({"venue": "cantina", "title": title[:160],
                    "url": url, "bounty": bounty or "paid"})
    # dedupe within venue (page embeds data twice)
    return list({r["url"]: r for r in out}.values())


def venue_code4rena():
    """Parse server-rendered audit tiles; keep open-for-participation ones."""
    html = fetch("https://code4rena.com/audits")
    OPEN = ("live", "upcoming", "starts", "open for", "join")
    CLOSED = ("completed", "report in progress", "submissions closed")
    tiles = re.findall(
        r'audit-tile__link" href="(/audits/[^"]+)">(.*?)audit-tile__footer__right">([^<]+)<',
        html, re.DOTALL)
    out = []
    for href, body, prize in tiles:
        stm = re.search(r'audit-tile__header__status"[^>]*>([^<]+)<', body)
        status = (stm.group(1).strip().lower() if stm else "")
        if any(c in status for c in CLOSED):
            continue
        if not any(o in status for o in OPEN):
            continue  # unknown status: skip rather than emit noise
        nm = re.search(r'audit-tile__project__name">([^<]+)<', body)
        name = htmllib.unescape(nm.group(1).strip()) if nm else href
        out.append({"venue": "code4rena", "title": f"{name} audit [{status}]"[:160],
                    "url": "https://code4rena.com" + href,
                    "bounty": prize.strip() or "paid"})
    return out


def venue_immunefi():
    """Parse embedded program JSON (slug/url/project/maxBounty)."""
    html = fetch("https://immunefi.com/bug-bounty/")
    recs = re.findall(
        r'\\"slug\\":\\"([a-z0-9\-]+)\\",\\"url\\":\\"(/bug-bounty/[a-z0-9\-/]+/)\\".*?'
        r'\\"maxBounty\\":(\d+|null).*?\\"project\\":\\"((?:[^\\"\\\\]|\\\\.)*)\\"',
        html)
    out = []
    for slug, url, maxb, project in recs:
        if maxb == "null" or int(maxb) <= 0:
            continue
        proj = project.encode().decode("unicode_escape", errors="ignore")
        out.append({"venue": "immunefi", "title": f"{proj} bug bounty"[:160],
                    "url": "https://immunefi.com" + url,
                    "bounty": f"up to {money(maxb)}"})
    return list({r["url"]: r for r in out}.values())


def venue_algora():
    """Parse challenge cards; keep non-Completed ones."""
    html = fetch("https://algora.io/challenges")
    cards = re.findall(
        r'>(Completed|Open|Live|Active)<.*?href="(/challenges/[a-z0-9\-]+)"',
        html, re.DOTALL)
    cards += [(s, h) for h, s in
              re.findall(r'href="(/challenges/[a-z0-9\-]+)".{0,2000}?>(Completed|Open|Live|Active)<',
                         html, re.DOTALL)]
    out = []
    for status, href in cards:
        if status == "Completed":
            continue
        name = href.split("/")[-1].replace("-", " ").title()
        out.append({"venue": "algora", "title": f"{name} challenge [{status}]"[:160],
                    "url": "https://algora.io" + href, "bounty": "paid"})
    return list({r["url"]: r for r in out}.values())


def venue_cantina_sitemap(known):
    """Paginate Cantina beyond the embedded first-10: sitemap-0.xml lists ALL
    /bounties/<uuid> pages (~45). Fetch detail pages for unknown urls only
    (cap 50/run, sequential, same timeout), keep status==live ones."""
    xml = fetch("https://cantina.xyz/sitemap-0.xml")
    urls = sorted(set(re.findall(
        r"https://cantina\.xyz/bounties/[0-9a-f\-]{36}", xml)))
    out = []
    for url in urls:
        if url in known:
            continue
        if len(out) >= 50:
            break
        try:
            html = fetch(url)
        except Exception:
            continue
        i = html.find('\\"bounty\\":\\"id\\"')
        if i < 0:
            i = html.find('\\"bounty\\":{')
        if i < 0:
            known.add(url)
            continue
        seg = html[i:i + 4000]  # full bounty record window
        st = re.search(r'\\"status\\":\\"([a-z]+)\\"', seg)
        if not st or st.group(1) != "live":
            known.add(url)  # judged/closed: remember so we never refetch
            continue  # (live urls are added to seen by main after append)
        nm = re.search(r'\\"name\\":\\"((?:[^\\"\\\\]|\\\\.)*)\\"', seg)
        name = nm.group(1) if nm else url.rsplit("/", 1)[-1]
        co = re.search(r'\\"company\\":\{[^}]*?\\"name\\":\\"((?:[^\\"\\\\]|\\\\.)*)\\"', seg)
        pot = re.search(r'\\"totalRewardPot\\":\\"([\d.]+)\\"', seg)
        cur = re.search(r'\\"currencyCode\\":\\"([A-Z]+)\\"', seg)
        company = co.group(1) if co else ""
        bounty = (money(pot.group(1)) + " " + (cur.group(1) if cur else "")).strip()
        title = f"{name} ({company})" if company else name
        out.append({"venue": "cantina", "title": title[:160],
                    "url": url, "bounty": bounty or "paid"})
    return out


def venue_sherlock():
    """Sherlock audit contests (open to all, no track record): paginated JSON
    API (?page=N, has_next flag). Keep non-finished contests ending in future."""
    import time as _t
    out, page = [], 1
    now = int(_t.time())
    import os as _os
    maxpages = int(_os.environ.get("SHERLOCK_PAGES", "5"))
    CLOSED = ("FINISHED", "COMPLETED", "CANCELLED", "ARCHIVED")
    while page <= maxpages:
        raw = fetch(f"https://audits.sherlock.xyz/api/contests?page={page}")
        try:
            data = json.loads(raw)
        except ValueError:
            break
        items = data.get("items", [])
        if not items:
            break
        for it in items:
            if it.get("status") in CLOSED or it.get("private"):
                continue
            ends = it.get("ends_at") or 0
            if ends and ends < now:
                continue
            prize = it.get("prize_pool") or it.get("rewards") or 0
            tok = it.get("token", "")
            out.append({
                "venue": "sherlock",
                "title": f"{it.get('title', 'contest')} [{(it.get('status') or 'open').lower()}]"[:160],
                "url": f"https://audits.sherlock.xyz/contests/{it.get('id')}",
                "bounty": f"{money(prize)} {tok}".strip() or "paid"})
        if not data.get("has_next"):
            break
        page += 1
    return list({r["url"]: r for r in out}.values())


def venue_superteam():
    """Superteam Earn: small fixed-price bounties, open to all (first-win
    friendly). Single JSON API; keep OPEN, winners unannounced, deadline future."""
    raw = fetch("https://superteam.fun/api/listings")
    try:
        items = json.loads(raw)
    except ValueError:
        return []
    if isinstance(items, dict):
        items = items.get("listings", items.get("items", []))
    now = datetime.datetime.now(datetime.timezone.utc)
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("isWinnersAnnounced") or it.get("winnersAnnouncedAt"):
            continue
        if (it.get("status") or "").upper() not in ("OPEN", "ACTIVE", "LIVE", ""):
            continue
        dl = (it.get("deadline") or "")[:10]
        try:
            dend = datetime.datetime.strptime(dl, "%Y-%m-%d").replace(
                tzinfo=datetime.timezone.utc)
            if dend < now - datetime.timedelta(days=1):
                continue
        except ValueError:
            pass
        slug = it.get("slug", "")
        amt, tok = it.get("rewardAmount"), it.get("token", "")
        out.append({
            "venue": "superteam",
            "title": f"{it.get('title', slug)} [{it.get('type', 'bounty')}]"[:160],
            "url": f"https://superteam.fun/earn/listing/{slug}",
            "bounty": f"{money(amt)} {tok}".strip() or "paid"})
    return list({r["url"]: r for r in out}.values())


def known_urls():
    try:
        return {json.loads(l).get("url") for l in open(WATCH) if l.strip()}
    except FileNotFoundError:
        return set()


def main():
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%FT%TZ")
    seen = known_urls()
    venues = [("cantina", venue_cantina), ("cantina-sitemap",
              lambda: venue_cantina_sitemap(seen)),
              ("code4rena", venue_code4rena),
              ("immunefi", venue_immunefi), ("algora", venue_algora),
              ("sherlock", venue_sherlock), ("superteam", venue_superteam)]
    working, fresh, detail = [], [], {}
    for name, fn in venues:
        try:
            items = fn()
            working.append(name)
            new = [r for r in items if r["url"] not in seen]
            # bound per-run growth: newest/second-pass order kept, cap 100
            for r in new[:100]:
                row = {"ts": ts, "who": "watcher", **r}
                fresh.append(row)
                seen.add(r["url"])
            detail[name] = {"parsed": len(items), "new": len(new[:100])}
        except Exception as e:  # noqa: BLE001 - one try, skip on failure
            detail[name] = {"error": type(e).__name__}
    if fresh:
        with open(WATCH, "a") as f:
            for row in fresh:
                f.write(json.dumps(row) + "\n")
    print(json.dumps({"ts": ts, "venues_working": working,
                      "fresh": len(fresh), "detail": detail,
                      "sample": fresh[:5]}, indent=1), flush=True)


if __name__ == "__main__":
    sys.exit(main())
