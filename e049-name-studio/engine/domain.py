"""Domain availability checker via RDAP + DNS fallback. Batched, cached."""
from __future__ import annotations
import asyncio
import json
import time
import os
import socket
from pathlib import Path
from typing import Dict, List, Tuple

CACHE_PATH = Path(__file__).parent.parent / "data" / "domain_cache.json"
TTL = 24 * 3600

# RDAP endpoints per TLD (authoritative). rdap.org is a bootstrap.
RDAP_BOOTSTRAP = "https://rdap.org/domain/{domain}"

# Price hints (standard renewal, non-premium)
TLD_PRICE = {
    "com": "$12", "cc": "$12", "io": "$60", "ai": "$70", "co": "$12",
    "net": "$12", "org": "$12", "app": "$14", "dev": "$12", "studio": "$30",
    "xyz": "$12", "site": "$3", "online": "$4", "tech": "$45", "co": "$12",
    "me": "$15", "sh": "$40", "live": "$25", "pro": "$15", "co": "$12",
    "app": "$14", "dev": "$12", "xyz": "$12", "site": "$3", "online": "$4",
}
# numeric for filtering (cheap = <=15)
TLD_PRICE_NUM = {
    "com": 12, "cc": 12, "co": 12, "net": 12, "org": 12, "app": 14, "dev": 12,
    "xyz": 12, "site": 3, "online": 4, "me": 15, "pro": 15,
    "io": 60, "ai": 70, "sh": 40, "studio": 30, "tech": 45, "live": 25,
}

def _load_cache() -> Dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except: return {}
    return {}

def _save_cache(cache: Dict):
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, indent=2))
    except: pass

async def _check_single(domain: str, client) -> Tuple[str, str, str]:
    """Returns (domain, status, detail) status in available/taken/unknown"""
    cache = _load_cache()
    now = time.time()
    if domain in cache:
        entry = cache[domain]
        if now - entry.get("ts", 0) < TTL:
            return domain, entry["status"], entry.get("detail", "")

    # Try RDAP
    status = "unknown"
    detail = ""
    try:
        url = RDAP_BOOTSTRAP.format(domain=domain)
        resp = await client.get(url, follow_redirects=True, timeout=7)
        # RDAP: 404 = not found = available, 200 = exists = taken
        if resp.status_code == 404:
            status = "available"
            detail = "RDAP 404"
        elif resp.status_code == 200:
            # ensure it's not a error object
            try:
                data = resp.json()
                if "objectClassName" in data or "ldhName" in data:
                    status = "taken"
                    detail = "RDAP 200"
                elif "errorCode" in data and data["errorCode"] == 404:
                    status = "available"
                else:
                    status = "taken"
            except:
                status = "taken"
        elif resp.status_code in (400, 422):
            # malformed maybe
            status = "unknown"
            detail = f"RDAP {resp.status_code}"
        else:
            detail = f"RDAP {resp.status_code}"
            status = "unknown"
    except Exception as e:
        detail = f"RDAP err {str(e)[:60]}"
        status = "unknown"

    # Fallback: DNS lookup if unknown
    if status == "unknown":
        try:
            # quick DNS check: if A record exists, likely taken; if NXDOMAIN, likely available
            # Use socket gethostbyname with timeout via asyncio
            loop = asyncio.get_event_loop()
            def _dns():
                try:
                    socket.gethostbyname(domain)
                    return True
                except socket.gaierror as ex:
                    # [Errno -2] Name or service not known = likely available
                    # [Errno -3] etc
                    return False
                except Exception:
                    return None
            has_dns = await loop.run_in_executor(None, _dns)
            if has_dns is True:
                status = "taken"
                detail += " | DNS exists"
            elif has_dns is False:
                status = "available"
                detail += " | DNS NXDOMAIN"
            else:
                status = "unknown"
        except Exception:
            pass

    # Heuristic fallback for demo: if still unknown, use hash to simulate (so UI not all gray)
    # But mark as unknown, not fake available. We keep unknown so UI shows retry.
    # To avoid complete gray, we can leave as unknown.

    # Save cache if definitive
    if status in ("available", "taken"):
        cache[domain] = {"status": status, "detail": detail, "ts": now}
        _save_cache(cache)
    return domain, status, detail

async def check_domains(names: List[str], tlds: List[str]) -> List[Dict]:
    """Batch check: for each name and each tld, return row."""
    import httpx
    domains = []
    for name in names:
        clean = name.lower().replace(" ", "").replace("-", "")
        if not clean: continue
        for tld in tlds:
            tld = tld.strip().lstrip(".").lower()
            if not tld: continue
            domains.append(f"{clean}.{tld}")

    results: List[Dict] = []
    # limit concurrency
    async with httpx.AsyncClient(headers={"Accept": "application/json"}, timeout=10) as client:
        sem = asyncio.Semaphore(8)
        async def _one(d):
            async with sem:
                dom, status, detail = await _check_single(d, client)
                # price
                tld = d.split(".")[-1]
                return {"domain": d, "name": d.rsplit(".",1)[0], "tld": tld, "status": status, "detail": detail, "price": TLD_PRICE.get(tld, "—")}
        tasks = [asyncio.create_task(_one(d)) for d in domains]
        # gather with timeout per batch
        for coro in asyncio.as_completed(tasks):
            try:
                r = await asyncio.wait_for(coro, timeout=12)
                results.append(r)
            except Exception as e:
                pass
    # sort: available first, then taken, then unknown; then by domain
    order = {"available": 0, "unknown": 1, "taken": 2}
    results.sort(key=lambda x: (order.get(x["status"], 3), x["domain"]))
    return results

def check_domains_sync(names: List[str], tlds: List[str]) -> List[Dict]:
    return asyncio.run(check_domains(names, tlds))

# Single domain quick check
async def check_single_domain(domain: str) -> Dict:
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        d, status, detail = await _check_single(domain.lower(), client)
        tld = d.split(".")[-1]
        return {"domain": d, "tld": tld, "status": status, "detail": detail, "price": TLD_PRICE.get(tld, "—")}
