#!/usr/bin/env python3
"""Daily relative-strength scan (code only, stdlib).

Data: CoinGecko free API (batched, retry/backoff) + DefiLlama fees overview.
Watchlist: fixed CoinGecko ids (resolved once by id/market cap, never symbol
guesses) + top 50 of the solana-ecosystem category by market cap.

Flag rule: token 7d AND 30d return each beat SOL by more than 15 percentage
points, only while SOL 30d return is negative. Every flag is appended as a
paper-trade row in data/rstrength_flags.csv; result_7d / result_30d columns
are backfilled by later runs when the row is 7 / 30 days old.

Rate limits: CoinGecko free ~10-30 calls/min; this script makes 2 calls per
run plus retries with exponential backoff. DefiLlama: 1 call per run.
"""
import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE, "data", "rstrength_flags.csv")
LOG_PATH = os.path.join(BASE, "logs", "rstrength.log")
BOG = timezone(timedelta(hours=-5))
THRESH = 15.0
SOLANA_TOP_N = 50

# symbol -> CoinGecko id, resolved 2026-10-25 by id and largest market cap
# among same-symbol candidates (checked via /coins/list + /coins/markets).
WATCHLIST = {
    "ETH": "ethereum", "BNB": "binancecoin", "SOL": "solana", "NEAR": "near",
    "TAO": "bittensor", "LIT": "lighter", "LINK": "chainlink",
    "HYPE": "hyperliquid", "JUP": "jupiter-exchange-solana", "MET": "meteora",
    "RAY": "raydium", "ORCA": "orca", "PUMP": "pump-fun", "UNI": "uniswap",
    "CAKE": "pancakeswap-token", "STONK": "stonk-3", "PONS": "pons",
    "AERO": "aerodrome-finance", "ORE": "ore",
    # LAUNCH: largest same-symbol candidate (Hyperlauncher, mc ~$166k on 2026-10-25).
    # _LaunchX's LAUNCH (Stonk Fun) was not on CoinGecko yet; both candidates logged.
    "LAUNCH": "hyperlauncher",
}
FIELDS = ["date", "token", "price_usd", "ret_7d", "ret_30d",
          "sol_ret_7d", "sol_ret_30d", "rev_24h", "rev_30d",
          "result_7d_date", "result_7d_price", "result_7d_ret",
          "result_30d_date", "result_30d_price", "result_30d_ret"]


def log(msg):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(f"{datetime.now(BOG).isoformat(timespec='seconds')} {msg}\n")
    print(msg)


def get_json(url, tries=4):
    wait = 20
    for i in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "echolike-rstrength/1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            log(f"HTTP {e.code} on {url.split('?')[0]} (try {i})")
            if e.code == 429 and i < tries:
                time.sleep(wait); wait *= 2; continue
            if e.code >= 500 and i < tries:
                time.sleep(wait); wait *= 2; continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            log(f"network error on {url.split('?')[0]} (try {i}): {e}")
            if i < tries:
                time.sleep(wait); wait *= 2; continue
            raise


def markets(ids=None, category=None):
    q = ["vs_currency=usd", "price_change_percentage=7d,30d",
         "per_page=250", "sparkline=false"]
    if ids:
        q.append("ids=" + ",".join(ids))
    if category:
        q.append(f"category={category}")
        q.append("order=market_cap_desc")
    return get_json("https://api.coingecko.com/api/v3/coins/markets?" + "&".join(q)) or []


def defillama_fees():
    """Map DefiLlama fee rows to our symbols by exact slug/name match only."""
    try:
        d = get_json("https://api.llama.fi/overview/fees?excludeTotalDataChart=true"
                     "&excludeTotalDataChartBreakdown=true")
    except Exception as e:
        log(f"defillama unavailable: {e.__class__.__name__}")
        return {}
    out = {}
    for p in d.get("protocols", []):
        key = (p.get("slug") or "").lower()
        out[key] = (p.get("total24h"), p.get("total30d"))
        if p.get("name"):
            out.setdefault(p["name"].lower(), (p.get("total24h"), p.get("total30d")))
    return out


def rev_for(sym, cg_id, fees):
    for k in (sym.lower(), (cg_id or "").lower()):
        if k in fees and fees[k][0] is not None:
            return fees[k]
    return (None, None)


def load_rows():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH) as f:
        return list(csv.DictReader(f))


def save_rows(rows):
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def pct(a, b):
    if a in (None, "", 0) or b in (None, ""):
        return None
    return round((float(b) / float(a) - 1) * 100, 2)


def main():
    now = datetime.now(BOG)
    # Watchlist + Solana top N. SOL's numbers come from the watchlist row.
    wl = markets(ids=set(WATCHLIST.values()))
    top_sol = markets(category="solana-ecosystem")[:SOLANA_TOP_N]
    by_id = {}
    for c in wl + top_sol:
        if c.get("id") and c["id"] not in by_id:
            by_id[c["id"]] = c
    missing = [s for s, i in WATCHLIST.items() if i not in by_id]
    for s in missing:
        log(f"NOT FOUND on CoinGecko: {s} (id {WATCHLIST[s]})")
    # LAUNCH stand-in watch: when the real Stonk Fun LAUNCH lists on CoinGecko,
    # say so in the log so the id gets swapped (never auto-swapped by code).
    try:
        hits = get_json("https://api.coingecko.com/api/v3/search?query=launch").get("coins", [])
        for c in hits:
            name = (c.get("name") or "").lower()
            if ("stonk" in name or "launchx" in name or "uselaunch" in name) and c.get("id") != "hyperlauncher":
                log(f"NOTE: possible Stonk Fun LAUNCH now on CoinGecko: {c.get('id')} "
                    f"({c.get('name')}) - swap WATCHLIST['LAUNCH'] if confirmed")
                break
    except Exception as e:
        log(f"LAUNCH watch search failed: {e.__class__.__name__}")

    vol_floor = float(os.environ.get("RS_MIN_VOL24", 10000))
    skip = {}
    for cid, c in by_id.items():
        if cid != "solana" and (c.get("total_volume") or 0) < vol_floor:
            sym = (c.get("symbol") or "").upper()
            skip[sym] = c.get("total_volume")
    for sym, v in sorted(skip.items()):
        log(f"SKIPPED near-zero-volume coin: {sym} 24h vol ${v:,.0f} < ${vol_floor:,.0f} (no fake signals)")

    sol = by_id.get("solana")
    if not sol or sol.get("price_change_percentage_30d_in_currency") is None:
        log("SOL data unavailable; scan aborted this run")
        return 1
    sol7 = sol["price_change_percentage_7d_in_currency"]
    sol30 = sol["price_change_percentage_30d_in_currency"]

    fees = defillama_fees()
    rows = load_rows()
    known = {(r["date"], r["token"]) for r in rows}

    flags = []
    for cid, c in sorted(by_id.items(), key=lambda kv: -(kv[1].get("market_cap") or 0)):
        if cid == "solana":
            continue
        sym = (c.get("symbol") or "").upper()
        if sym in skip:
            continue
        p = c.get("current_price")
        r7 = c.get("price_change_percentage_7d_in_currency")
        r30 = c.get("price_change_percentage_30d_in_currency")
        if None in (p, r7, r30):
            continue
        rev24, rev30 = rev_for(sym, cid, fees)
        hit = (sol30 is not None and sol30 < 0
               and (r7 - sol7) > THRESH and (r30 - sol30) > THRESH)
        if hit and (now.strftime("%Y-%m-%d"), sym) not in known:
            flags.append({
                "date": now.strftime("%Y-%m-%d"), "token": sym,
                "price_usd": p, "ret_7d": round(r7, 2), "ret_30d": round(r30, 2),
                "sol_ret_7d": round(sol7, 2), "sol_ret_30d": round(sol30, 2),
                "rev_24h": rev24 if rev24 is not None else "",
                "rev_30d": rev30 if rev30 is not None else "",
                "result_7d_date": "", "result_7d_price": "", "result_7d_ret": "",
                "result_30d_date": "", "result_30d_price": "", "result_30d_ret": "",
            })

    # Backfill +7d / +30d results from today's prices.
    today_p = {cid: c.get("current_price") for cid, c in by_id.items()}
    sym2id = {}
    for cid, c in by_id.items():
        sym2id[(c.get("symbol") or "").upper()] = cid
    changed = False
    for r in rows:
        d0 = datetime.strptime(r["date"], "%Y-%m-%d").replace(tzinfo=BOG)
        cid = sym2id.get(r["token"])
        px = today_p.get(cid)
        if px in (None, 0):
            continue
        if not r["result_7d_date"] and now - d0 >= timedelta(days=7):
            r["result_7d_date"] = now.strftime("%Y-%m-%d")
            r["result_7d_price"] = px
            r["result_7d_ret"] = pct(r["price_usd"], px)
            changed = True
        if not r["result_30d_date"] and now - d0 >= timedelta(days=30):
            r["result_30d_date"] = now.strftime("%Y-%m-%d")
            r["result_30d_price"] = px
            r["result_30d_ret"] = pct(r["price_usd"], px)
            changed = True

    if flags:
        rows.extend(flags)
        changed = True
    if changed or not os.path.exists(CSV_PATH):
        save_rows(rows)

    for f in flags:
        log(f"FLAG {f['token']} 7d={f['ret_7d']}% 30d={f['ret_30d']}% "
            f"(SOL {f['sol_ret_7d']}%/{f['sol_ret_30d']}%)")
    log(f"scan done: watchlist={len(wl)} solana_top={len(top_sol)} "
        f"new_flags={len(flags)} open_rows={sum(1 for r in rows if not r['result_30d_date'])}")

    if flags:
        lines = [f"{f['date']} {f['token']}: 7d {f['ret_7d']}% vs SOL {f['sol_ret_7d']}%, "
                 f"30d {f['ret_30d']}% vs SOL {f['sol_ret_30d']}% (paper trade row saved)" for f in flags]
        print("PINGS:" + "\n" + "\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
