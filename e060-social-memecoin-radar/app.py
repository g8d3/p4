#!/usr/bin/env python3
"""e060 v1 — Dexscreener-only rotation radar (FREE tier, no keys, no secrets).

Owner decision 2026-09-12: cheapest way (free) -> Dexscreener-only.
No LunarCrush / X pipe. Social velocity deferred; rotation proxy =
boost attention $ x on-chain velocity (volume/txns) from Dexscreener.

Routes: / -> dashboard, /api/rotation -> JSON, /health -> ok.
Cache: data/rotation.json (5 min TTL), stale-badged when Dexscreener unreachable.
"""
import html
import json, math, os, subprocess as _sp, threading, time, urllib.request
_BASE = os.path.dirname(os.path.abspath(__file__))
_VSTART = int(time.time())
try:
    _VRUN = _sp.run(['git', 'log', '-1', '--format=%h', '--', 'app.py', 'bin/', 'tests/'], capture_output=True,
                    text=True, cwd=_BASE).stdout.strip() or '?'
except Exception:
    _VRUN = '?'
def _version():
    try:
        latest = _sp.run(['git', 'log', '-1', '--format=%h', '--', 'app.py', 'bin/', 'tests/'], capture_output=True,
                         text=True, cwd=_BASE).stdout.strip() or '?'
        dirty = bool(_sp.run(['git', 'status', '--short', '--'] + ['e060-social-memecoin-radar/app.py', 'e060-social-memecoin-radar/bin/', 'e060-social-memecoin-radar/tests/'], capture_output=True,
                             text=True, cwd='/home/vuos/code/p4').stdout.strip())
    except Exception:
        latest, dirty = '?', False
    return {"ok": True, "track": "e060", "running": _VRUN,
            "latest": latest, "stale": _VRUN != latest,
            "dirty": dirty, "started_ts": _VSTART}
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("E060_PORT", "8323"))
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "rotation.json")
TTL = 300
PAPER_DIR = os.path.join(HERE, "paper")
SCORE_FILE = os.path.join(PAPER_DIR, "score.json")

# Worthy-ping rule (strategy WORTHY-1, see STRATEGIES.md). Keep in sync with
# bin/paper_snapshot.py and the dashboard JS `worthy()`.
def is_worthy(r):
    try:
        return (float(r.get("heat") or 0) >= 80 and
                float(r.get("vol_h24") or 0) >= 5e5 and
                float(r.get("txns_h24") or 0) >= 1e4)
    except (TypeError, ValueError):
        return False

BOOSTS_URL = "https://api.dexscreener.com/token-boosts/top/v1"
UA = {"User-Agent": "e060-radar/1.0 (+local)"}

def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def enrich(chain, addr):
    """Best-effort pair stats for one token. Returns dict or {}."""
    url = f"https://api.dexscreener.com/tokens/v1/{chain}/{addr}"
    try:
        pairs = fetch(url, timeout=8)
        if not pairs:
            return {}
        # pick highest-volume pair
        best = max(pairs, key=lambda p: (p.get("volume") or {}).get("h24", 0))
        return {
            "symbol": (best.get("baseToken") or {}).get("symbol", "?"),
            "name": (best.get("baseToken") or {}).get("name", ""),
            "priceUsd": best.get("priceUsd"),
            "vol_h24": (best.get("volume") or {}).get("h24", 0),
            "priceChange_h24": (best.get("priceChange") or {}).get("h24", 0),
            "txns_h24": sum(((best.get("txns") or {}).get("h24") or {}).values()) if isinstance((best.get("txns") or {}).get("h24"), dict) else 0,
            "dex": best.get("dexId", ""),
            "pairUrl": best.get("url", ""),
        }
    except Exception:
        return {}

def build():
    boosts = fetch(BOOSTS_URL, timeout=10)[:15]
    rows = []
    for b in boosts:
        chain, addr = b.get("chainId", "?"), b.get("tokenAddress", "")
        e = enrich(chain, addr) if addr else {}
        amt = b.get("totalAmount", 0) or 0
        vol = e.get("vol_h24", 0) or 0
        score = round(math.log10(amt + 1) * 10 + math.log10(vol + 1) * 5, 1)
        txns = e.get("txns_h24", 0) or 0
        chg = e.get("priceChange_h24") or 0
        # heat: rotation score + trade-speed (log txns) + 24h-move size (capped).
        # txns_h24 was collected but unused — now it powers the ranking.
        heat = round(score + 5 * math.log10(txns + 1) + min(abs(chg), 150) / 10, 1)
        rows.append({
            "symbol": e.get("symbol", "?"), "name": e.get("name", ""),
            "chain": chain, "token": addr,
            "boost_usd": amt, "vol_h24": vol,
            "priceUsd": e.get("priceUsd"),
            "priceChange_h24": e.get("priceChange_h24"),
            "txns_h24": txns,
            "rotation_score": score, "heat": heat,
            "dex": e.get("dex", ""), "pairUrl": e.get("pairUrl") or b.get("url", ""),
            "dsUrl": b.get("url", ""),
        })
    rows.sort(key=lambda r: r["rotation_score"], reverse=True)
    return {"ts": int(time.time()), "source": "dexscreener-free",
            "note": "heat = score + 5*log10(txns+1) + min(|chg24h|,150)/10; social velocity deferred (no X pipe)",
            "stale": False, "rows": rows}

_REFRESH_LOCK = threading.Lock()
_REFRESHING = False


def maybe_refresh():
    """Serve cache instantly; rebuild in background so the page never hangs."""
    global _REFRESHING
    try:
        if os.path.exists(CACHE) and time.time() - os.path.getmtime(CACHE) < TTL:
            return
    except Exception:
        pass
    with _REFRESH_LOCK:
        if _REFRESHING:
            return
        _REFRESHING = True

    def _run():
        global _REFRESHING
        try:
            data = build()
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            with open(CACHE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass
        finally:
            with _REFRESH_LOCK:
                _REFRESHING = False
    threading.Thread(target=_run, daemon=True).start()


def _auto_refresh_loop():
    """Keep first paint LIVE with no page loads: tick every 60s and rebuild
    when the cache passed its TTL. maybe_refresh() no-ops while fresh and
    skips while a build runs, so this costs ~16 free-tier reqs per 5 min."""
    while True:
        time.sleep(60)
        try:
            maybe_refresh()
        except Exception:
            pass


def get_data():
    maybe_refresh()
    try:
        with open(CACHE) as f:
            d = json.load(f)
        # backfill heat for caches written before heat existed (instant, no fetch)
        for r in d.get("rows", []):
            if "heat" not in r:
                tx = r.get("txns_h24", 0) or 0
                ch = r.get("priceChange_h24") or 0
                r["heat"] = round((r.get("rotation_score", 0) or 0) + 5 * math.log10(tx + 1) + min(abs(ch), 150) / 10, 1)
        try:
            age = time.time() - os.path.getmtime(CACHE)
        except Exception:
            age = 0
        if age >= 3 * TTL:
            d["stale"] = True
            d["stale_reason"] = "cache older than 3x TTL, background refresh pending"
        return d
    except Exception as ex:
        return {"ts": int(time.time()), "source": "dexscreener-free",
                "stale": True, "stale_reason": str(ex), "rows": []}

def fmt_big(n):
    try:
        n = float(n)
    except (TypeError, ValueError):
        return '—'
    if n >= 1e6:
        return f"{n/1e6:.1f}M"
    if n >= 1e3:
        return f"{n/1e3:.1f}K"
    return str(round(n))


def fmt_age(sec):
    try:
        sec = max(0, float(sec))
    except (TypeError, ValueError):
        return '?'
    if sec < 90:
        return f"{sec:.0f}s ago"
    if sec < 5400:
        return f"{sec/60:.0f}m ago"
    return f"{sec/3600:.1f}h ago"


def grade_countdown():
    """Live countdown to first 24h grade (FREE, local files only): oldest
    worthy-with-price snapshot -> 'first grade ~18h'. Empty when none."""
    try:
        oldest = None
        with open(os.path.join(PAPER_DIR, "calls.jsonl")) as f:
            for line in f:
                try:
                    snap = json.loads(line)
                except Exception:
                    continue
                entries = [e for e in (snap.get("top") or []) if e.get("worthy")]
                if any(e.get("priceUsd") and e.get("token") for e in entries):
                    ts = int(snap.get("ts", 0))
                    if ts and (oldest is None or ts < oldest):
                        oldest = ts
        if not oldest:
            return ""
        remain_h = 24 - (time.time() - oldest) / 3600
        if remain_h <= 0:
            return "grading now"
        if remain_h < 1:
            return f"first grade ~{remain_h * 60:.0f}m"
        return f"first grade ~{remain_h:.0f}h"
    except Exception:
        return ""


def grade_src_line():
    """One short line naming HOW 24h grades are priced (DATA PULSE rule).
    Live Dexscreener first, cached GeckoTerminal pool backup second.
    e.g. 'grades via live, backup 9/9' or 'grades 2 live + 1 backup'."""
    try:
        npools = 0
        with open(os.path.join(PAPER_DIR, "pools.json")) as f:
            d = json.load(f)
            npools = sum(1 for k, v in d.items()
                         if not k.startswith("_") and isinstance(v, dict) and v.get("pool_addr"))
    except Exception:
        npools = 0
    try:
        live_n, backup_n = 0, 0
        with open(os.path.join(PAPER_DIR, "outcomes.jsonl")) as f:
            for line in f:
                try:
                    src = (json.loads(line) or {}).get("src", "")
                except Exception:
                    continue
                if src == "dexscreener":
                    live_n += 1
                elif src.startswith("gecko"):
                    backup_n += 1
        if live_n or backup_n:
            parts = []
            if live_n:
                parts.append(f"{live_n} live")
            if backup_n:
                parts.append(f"{backup_n} backup")
            return f"grades {' + '.join(parts)}"
    except Exception:
        pass
    return f"grades via live, backup {npools}/{npools}" if npools else "grades via live"


def pending_calls():
    """Per-call ballot (FREE, local files only): every pending worthy-with-
    price entry grouped by snapshot -> called Xh ago + grades in Yh.
    Fully-resolved snapshots drop out via outcomes.jsonl."""
    try:
        done = set()
        try:
            with open(os.path.join(PAPER_DIR, "outcomes.jsonl")) as f:
                for line in f:
                    try:
                        o = json.loads(line)
                        done.add((o.get("date"), o.get("symbol"), o.get("chain")))
                    except Exception:
                        pass
        except Exception:
            pass
        now = time.time()
        out = []
        try:
            with open(os.path.join(PAPER_DIR, "calls.jsonl")) as f:
                for line in f:
                    try:
                        snap = json.loads(line)
                    except Exception:
                        continue
                    entries = [e for e in (snap.get("top") or [])
                               if e.get("worthy") and e.get("priceUsd") and e.get("token")]
                    open_calls = [e for e in entries
                                  if (snap.get("date"), e.get("symbol"), e.get("chain")) not in done]
                    if not open_calls:
                        unpriced = [e for e in (snap.get("top") or [])
                                    if e.get("worthy") and not (e.get("priceUsd") and e.get("token"))]
                        if unpriced and not any(
                                (snap.get("date"), e.get("symbol"), e.get("chain")) not in done
                                for e in entries):
                            ts = int(snap.get("ts", 0) or 0)
                            out.append({
                                "date": snap.get("date"),
                                "called_ts": ts,
                                "called_ago": "called " + fmt_age(now - ts) if ts else "called ?",
                                "grades_in": "no entry price \u2014 cannot grade",
                                "remain_h": None,
                                "n": 0,
                                "symbols": [e.get("symbol", "?") for e in unpriced],
                            })
                        continue
                    ts = int(snap.get("ts", 0) or 0)
                    remain_h = 24 - (now - ts) / 3600 if ts else 24
                    if remain_h <= 0:
                        grades = "grading now"
                    elif remain_h < 1:
                        grades = f"grades in ~{remain_h * 60:.0f}m"
                    else:
                        grades = f"grades in ~{remain_h:.0f}h"
                    out.append({
                        "date": snap.get("date"),
                        "called_ts": ts,
                        "called_ago": "called " + fmt_age(now - ts) if ts else "called ?",
                        "grades_in": grades,
                        "remain_h": round(remain_h, 1),
                        "n": len(open_calls),
                        "symbols": [e.get("symbol", "?") for e in open_calls],
                    })
        except Exception:
            pass
        out.sort(key=lambda x: x.get("called_ts") or 0)
        return out
    except Exception:
        return []


def ballot_html():
    """Paper ballot expand (LONG TEXT RULE): one line per pending snapshot —
    coins, called Xh ago, grades in Yh. Empty when nothing pending."""
    calls = pending_calls()
    if not calls:
        return ""
    try:
        total = sum(c.get("n", 0) for c in calls)
        summ = (f"Paper ballot: {total} calls resolving \u2014 tap for each call.")
        rows = "".join(
            f"<div>{html.escape(str(c.get('date', '?')))} "
            f"{html.escape(', '.join(c.get('symbols', [])))} "
            f"<small>{html.escape(c.get('called_ago', '?'))}, "
            f"{html.escape(c.get('grades_in', '?'))}</small></div>"
            for c in calls)
        return (f"<details id=\"ballot\" style='margin:.2em 0;font-size:13px;color:#555'>"
                f"<summary>{html.escape(summ)}</summary>"
                f"<div>{rows}</div></details>")
    except Exception:
        return ""


def paper_score():
    """Read paper/score.json (written by bin/paper_resolve.py). Never fetches."""
    try:
        with open(SCORE_FILE) as f:
            s = json.load(f)
        n = int(s.get("resolved") or 0)
        if n > 0:
            return f"worthy hit-rate {s.get('hit_rate_pct')}% ({s.get('hits')}/{n})"
        pend = int(s.get("pending") or 0)
        if pend > 0:
            cd = grade_countdown()
            tail = f" ({cd})" if cd else " (first outcome <24h)"
            return f"{pend} worthy call{'s' if pend != 1 else ''} resolving{tail}"
        return "worthy score: logging first calls"
    except Exception:
        return "worthy score: logging first calls"


def early_read():
    """Intraday early read (FREE, no fetch): latest worthy entries with
    entry priceUsd vs current rotation.json prices. A same-day proxy while
    the canonical 24h resolver waits — never replaces paper_score()."""
    try:
        calls = []
        with open(os.path.join(PAPER_DIR, "calls.jsonl")) as f:
            for line in f:
                try:
                    calls.append(json.loads(line))
                except Exception:
                    pass
        with open(CACHE) as f:
            live = {}
            for r in json.load(f).get("rows", []):
                try:
                    live[r.get("token")] = {
                        "price": r.get("priceUsd"),
                        "pairUrl": r.get("pairUrl") or r.get("dsUrl") or "",
                    }
                except Exception:
                    pass
        now = time.time()
        for snap in reversed(calls):
            entries = [e for e in (snap.get("top") or []) if e.get("worthy")]
            usable = [e for e in entries
                      if e.get("priceUsd") and live.get(e.get("token"))]
            priced = [e for e in entries if e.get("priceUsd")]
            if not usable:
                continue
            ups, moves, detail = 0, [], []
            cup, cmoves = 0, []  # WORTHY-2c shadow: ex-pumped (entry chg24>+200 out)
            for e in usable:
                try:
                    entry = float(e["priceUsd"])
                    lv = live[e["token"]]
                    cur = float(lv["price"] if isinstance(lv, dict) else lv)
                except (TypeError, ValueError, KeyError):
                    continue
                if entry <= 0:
                    continue
                pct = (cur - entry) / entry * 100
                moves.append(pct)
                try:
                    pumped_entry = float(e.get("chg24")) > 200
                except (TypeError, ValueError):
                    pumped_entry = False
                if not pumped_entry:
                    cmoves.append(pct)
                    if pct > 0:
                        cup += 1
                lv = live.get(e["token"], {})
                detail.append({"symbol": e.get("symbol", "?"),
                               "pct": round(pct, 1),
                               "entry": e.get("priceUsd"),
                               "cur": (lv.get("price") if isinstance(lv, dict) else lv),
                               "pairUrl": (lv.get("pairUrl") if isinstance(lv, dict) else "") or "",
                               "src": "dexscreener-live"})
                if pct > 0:
                    ups += 1
            if not moves:
                return None
            detail.sort(key=lambda x: x["pct"], reverse=True)
            age_h = (now - int(snap.get("ts", now))) / 3600
            best = detail[0] if detail else None
            out = {"n": len(moves), "up": ups,
                   "avg_pct": round(sum(moves) / len(moves), 1),
                   "age_h": round(age_h, 1), "date": snap.get("date"),
                   "detail": detail, "best": best,
                   "px_src": "dexscreener-live",
                   "px_age": fmt_age(time.time() - os.path.getmtime(CACHE)),
                   "tracked": f"{len(moves)}/{len(priced)}",
                   "tracked_partial": bool(priced) and len(moves) < len(priced)}
            if len(cmoves) < len(moves) and cmoves:
                out["capped"] = {"n": len(cmoves), "up": cup,
                                  "avg_pct": round(sum(cmoves) / len(cmoves), 1)}
            return out
    except Exception:
        pass
    return None


def early_line():
    e = early_read()
    if not e:
        return ""
    s = (f" · early {e['up']}/{e['n']} up "
         f"(avg {e['avg_pct']:+.1f}%, ~{e['age_h']}h in")
    try:
        b = e.get("best")
        if b and b.get("pct") is not None:
            s += f", best {b.get('symbol')} {b.get('pct'):+.1f}%"
    except Exception:
        pass
    s += " via live)"
    try:
        c = e.get("capped")
        if c and c.get("n") != e.get("n"):
            s += (f" · ex-pumped {c.get('up')}/{c.get('n')} up"
                  f" (avg {c.get('avg_pct'):+.1f}%)")
    except Exception:
        pass
    try:
        if e.get("tracked_partial"):
            s += f" · {e.get('tracked')} still tracked"
    except Exception:
        pass
    return s


def breakout():
    """Intraday winner ping (FREE, local only): best early move >= +20%
    since its call. Surfaced in the one-line verdict; per-call detail
    stays behind the early expand. None when no breakout."""
    try:
        e = early_read()
        b = (e or {}).get("best")
        if b and b.get("pct") is not None and float(b["pct"]) >= 20:
            return b
    except Exception:
        pass
    return None


def early_detail_html():
    """One-line summary + expand for per-call early moves (LONG TEXT RULE)."""
    e = early_read()
    if not e or not e.get("detail"):
        return ""
    try:
        ups = e["up"]
        n = e["n"]
        best = e.get("best") or {}
        summ = (f"Early moves: {ups}/{n} up, best {best.get('symbol', '?')} "
                f"{best.get('pct', 0):+.1f}% via live \u2014 tap for each call.")
        rows = "".join(
            f"<div>{html.escape(str(x.get('symbol','?')))} "
            f"{x.get('pct', 0):+.1f}%"
            f" <small>entry {html.escape(str(x.get('entry') or '?'))} \u2192 now "
            f"{html.escape(str(x.get('cur') or '?'))} via live</small>"
            + (f" <a href=\"{html.escape(x['pairUrl'], quote=True)}\">pair ↗</a>" if x.get('pairUrl') else "")
            + "</div>"
            for x in e["detail"])
        return (f"<details style='margin:.2em 0;font-size:13px;color:#555'>"
                f"<summary>{html.escape(summ)}</summary>"
                f"<div>{rows}</div></details>")
    except Exception:
        return ""


def server_card():
    """Server-rendered first paint: verdict + data pulse. No JS needed."""
    d = get_data()
    rows = d.get("rows") or []
    try:
        age = time.time() - os.path.getmtime(CACHE)
    except Exception:
        age = -1
    live = "LIVE" if not d.get("stale") else "STALE"
    if rows:
        top = max(rows, key=lambda r: r.get("heat") or 0)
        w = is_worthy(top)
        chg = top.get("priceChange_h24")
        chgs = f"{chg}%" if chg is not None else "—"
        br = breakout()
        br_txt = (f". 🔥 {br.get('symbol')} up +{float(br.get('pct')):.1f}% since its call"
                  if br else "")
        try:
            chgf = float(chg)
        except (TypeError, ValueError):
            chgf = None
        if w and chgf is not None and chgf <= -50:
            wtxt = "falling — not a buy, watch only"
        elif w and chgf is not None and chgf >= 200:
            wtxt = "pumped — not a buy, watch only"
        elif w:
            wtxt = "worth a look"
        else:
            wtxt = "quiet, no calls standing out"
        state = "WATCH" if (w or br) else "COLD"
        verdict = (f"{state} \u2014 Top now: {top.get('symbol')} \u2014 {wtxt}"
                   f"{br_txt}{early_line()}")
    else:
        verdict = "COLD \u2014 No rotation data right now \u2014 refresh in a minute"
    pulse = (f"{live} {len(rows)} tokens · sample {fmt_age(age)} (every 5m) | "
             f"{paper_score()} · {grade_src_line()} | v{_VRUN}")
    return html.escape(verdict), html.escape(pulse)


def get_paper():
    """/api/paper payload: score file + today's logged count. Never fetches."""
    out = {"ok": True, "track": "e060", "today": time.strftime("%Y-%m-%d"),
           "today_logged": 0, "resolved": 0, "hits": 0,
           "hit_rate_pct": None, "paper_n_hit": 0, "paper_n": 0,
           "pending": 0}
    try:
        with open(SCORE_FILE) as f:
            s = json.load(f)
        out.update({k: s.get(k) for k in ("resolved", "hits", "hit_rate_pct", "pending", "shadow", "shadow2")
                    if k in s})
        out["paper_n_hit"] = out["hits"]
        out["paper_n"] = out["resolved"]
        out["paper_hit_rate_pct"] = out["hit_rate_pct"]
    except Exception:
        pass
    try:
        e = early_read()
        if e:
            out["early"] = e
    except Exception:
        pass
    try:
        out["grade_cd"] = grade_countdown()
    except Exception:
        pass
    try:
        out["grade_src"] = grade_src_line()
    except Exception:
        pass
    try:
        out["pending_calls"] = pending_calls()
    except Exception:
        pass
    try:
        with open(os.path.join(PAPER_DIR, "calls.jsonl")) as f:
            for line in f:
                try:
                    if json.loads(line).get("date") == out["today"]:
                        out["today_logged"] += 1
                except Exception:
                    pass
    except Exception:
        pass
    return out


PAGE = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>e060 rotation radar (free)</title><style>body{font-family:system-ui,sans-serif;max-width:900px;margin:1em auto 0;padding:0 1em}html.dark body{background:#111418;color:#e6e6e6}html.dark td,html.dark th{border-color:#444}html.dark a{color:#8ab4ff}table{border-collapse:collapse;width:100%;margin:0;min-width:640px}td,th{border:1px solid #ccc;padding:4px 8px;font-size:13px;text-align:right}td:nth-child(1),th:nth-child(1){text-align:left;position:sticky;left:0;background:#fff;z-index:1}html.dark td:nth-child(1),html.dark th:nth-child(1){background:#111418}.badge{background:#dfd;padding:2px 8px;border-radius:8px}.stale{background:#fdd}details{margin:.4em 0;color:#555;font-size:13px}html.dark details{color:#aaa}summary{cursor:pointer}.twrap{max-height:62vh;overflow:auto;border:1px solid #ccc;border-radius:8px}.twrap thead th{position:sticky;top:0;background:#f4f4f4;z-index:1}html.dark .twrap{border-color:#444}html.dark .twrap thead th{background:#1c2127}.twrap thead th:nth-child(1){z-index:2}html.dark .twrap thead th:nth-child(1){background:#1c2127}.twrap thead th:nth-child(1){background:#f4f4f4}.thumbbar{position:sticky;bottom:0;z-index:5;display:flex;gap:8px;padding:10px 0 calc(12px + env(safe-area-inset-bottom));background:#fff}html.dark .thumbbar{background:#111418}.thumbbar button{flex:1;padding:14px 4px;font-size:16px;border-radius:12px;border:1px solid #ccc;background:#f4f4f4}html.dark .thumbbar button{background:#1c2127;color:#e6e6e6;border-color:#444}.thumbbar button.on{background:#222;color:#fff;border-color:#222}html.dark .thumbbar button.on{background:#e6e6e6;color:#111;border-color:#e6e6e6}small{color:#888;font-size:11px}</style></head>
<body><h1>e060 rotation radar <span class=badge>FREE</span></h1>
<div id=s>%%PULSE%%</div>
<div id=v style="margin:.4em 0;font-size:15px">%%TOPONE%%</div>
%%EARLYDETAIL%%
%%BALLOT%%
<details><summary>Your radar sorts with one tap below \u2014 tap for details.</summary>
<p>Your top mover sits on top; tap \U0001f525 \U0001f680 \U0001f4b0 below to re-sort. Details: cheapest free plan, <b>heat</b> = score + trade-speed + 24h-move size; per-row <b>pair ↗</b> opens that pair on Dexscreener (free, no key — their free link lands on the pair page, not the trades tab). <a href=/api/rotation>JSON</a> <a href=/health>health</a> <small id=ver></small></p></details>
<div class=twrap><table id=t></table></div>
<nav class=thumbbar><button data-k=heat class=on>🔥 Heat</button><button data-k=movers>🚀 Movers</button><button data-k=vol>💰 Volume</button><button id=refresh>↻ Refresh</button><button id=copy>📋 Copy</button><button id=dark>🌙</button></nav>
<script>if(localStorage.e60==='d')document.documentElement.classList.add('dark')
let ROWS=[],CUR='heat',SLIP='',PSUFFIX='';const KEYS={heat:(a,b)=>(b.heat||0)-(a.heat||0),score:(a,b)=>b.rotation_score-a.rotation_score,movers:(a,b)=>Math.abs(b.priceChange_h24||0)-Math.abs(a.priceChange_h24||0),vol:(a,b)=>b.vol_h24-a.vol_h24};
const fmt=n=>n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?(n/1e3).toFixed(1)+'K':Math.round(n)+'';
const worthy=r=>(r.heat||0)>=80&&(r.vol_h24||0)>=5e5&&(r.txns_h24||0)>=1e4;
const falling=r=>{const c=parseFloat(r.priceChange_h24);return isFinite(c)&&c<=-50};
const pumped=r=>{const c=parseFloat(r.priceChange_h24);return isFinite(c)&&c>=200};
const verdictFor=t=>{const w=worthy(t);if(w&&falling(t))return 'falling — not a buy, watch only';if(w&&pumped(t))return 'pumped — not a buy, watch only';return w?'worth a look':'quiet, no calls standing out'};
function render(){const rows=[...ROWS].sort(KEYS[CUR]);const top=[...ROWS].sort(KEYS.heat)[0];if(top){const ST=worthy(top)?'WATCH':'COLD';document.getElementById('v').innerHTML='<b>'+ST+' \u2014 Top now: '+top.symbol+'</b> \u2014 '+verdictFor(top)+' <small>heat '+top.heat+' vol '+fmt(top.vol_h24)+' chg '+(top.priceChange_h24??'\u2014')+'%</small>'+(PSUFFIX||'');SLIP='e060 '+ST+' paper: '+top.symbol+' ('+top.chain+') heat '+top.heat+' vol '+fmt(top.vol_h24)+' chg '+(top.priceChange_h24??'?')+'% boost $'+top.boost_usd+' '+(top.pairUrl||top.dsUrl||'')+(falling(top)?' FALLING':(pumped(top)?' PUMPED':''))+' — watch only, not a position';}let h='<thead><tr><th>token</th><th>chain</th><th>heat</th><th>chg24h%</th><th>vol24h</th><th>boost$</th><th>pair</th></tr></thead><tbody>';
for(const r of rows){h+=`<tr><td>${r.symbol}</td><td><small>${r.chain}</small></td><td><b>${r.heat??'—'}</b>${worthy(r)?' ⚡':''}</td><td>${r.priceChange_h24??'—'}${falling(r)?' 📉':(pumped(r)?' ⚠️':'')}</td><td>${fmt(r.vol_h24)}</td><td>${r.boost_usd}</td><td>${r.pairUrl?`<a href="${r.pairUrl}">pair ↗</a>`:'—'}</td></tr>`}
document.getElementById('t').innerHTML=h+'</tbody>'}
fetch('/api/version').then(r=>r.json()).then(v=>{if(v.ok)document.getElementById('ver').textContent='v'+v.running+(v.stale?' STALE—restart':'')+(v.dirty?' *':'')}).catch(()=>{});
function loadAll(){fetch('/api/rotation').then(r=>r.json()).then(d=>{ROWS=d.rows;render();const ageS=Math.max(0,Date.now()/1000-d.ts);const age=ageS<90?Math.round(ageS)+'s ago':ageS<5400?Math.round(ageS/60)+'m ago':(ageS/3600).toFixed(1)+'h ago';Promise.all([fetch('/api/paper').then(r=>r.json()).catch(()=>null),fetch('/api/version').then(r=>r.json()).catch(()=>null)]).then(([p,vv])=>{let sc='worthy score: logging first calls';if(p&&p.ok){if(p.paper_n)sc=`worthy hit-rate ${p.paper_hit_rate_pct}% (${p.paper_n_hit}/${p.paper_n})`+(p.shadow&&p.shadow.n?` · stricter bar ${p.shadow.hit_rate_pct}% (${p.shadow.hits}/${p.shadow.n}, trying)`:'')+(p.shadow2&&p.shadow2.n?` · looser bar ${p.shadow2.hit_rate_pct}% (${p.shadow2.hits}/${p.shadow2.n}, trying)`:'');else if(p.pending)sc=`${p.pending} worthy calls resolving (${(p.grade_cd||'first outcome <24h')})`+(p.grade_src?' · '+p.grade_src:'')}document.getElementById('s').innerHTML=(d.stale?'<span class="badge stale">STALE</span> ':'<span class=badge>LIVE</span> ')+d.rows.length+' tokens · sample '+age+' (every 5m) | '+sc+(vv&&vv.ok?' | v'+vv.running+(vv.stale?' STALE\u2014restart':'')+(vv.dirty?' *':''):'');const v=document.getElementById('v');let t='';if(p&&p.ok){if(p.paper_n)t=` · paper ${p.paper_hit_rate_pct}% (${p.paper_n_hit}/${p.paper_n})`;else if(p.pending)t=` · ${p.pending} calls resolving (${(p.grade_cd||'grading soon')})`}if(p&&p.ok&&p.early&&p.early.n){let b='';if(p.early.best&&p.early.best.pct!=null)b=`, best ${p.early.best.symbol} ${(p.early.best.pct>0?'+':'')+p.early.best.pct}%`;let br='';if(p.early.best&&p.early.best.pct!=null&&p.early.best.pct>=20)br=` · 🔥 ${p.early.best.symbol} +${p.early.best.pct}% since call`;if(br){try{if(v.textContent.indexOf('COLD \u2014')>=0)v.textContent=v.textContent.replace('COLD \u2014','WATCH \u2014')}catch(_){}}t+=`${br} · early ${p.early.up}/${p.early.n} up (avg ${p.early.avg_pct>0?'+':''}${p.early.avg_pct}%, ~${p.early.age_h}h in${b}) via live`};if(p.early.capped&&p.early.capped.n!==p.early.n){t+=` · ex-pumped ${p.early.capped.up}/${p.early.capped.n} up (avg ${p.early.capped.avg_pct>0?'+':''}${p.early.capped.avg_pct}%)`}if(p.early.tracked_partial){t+=' · '+p.early.tracked+' still tracked'}try{const bl=document.getElementById('ballot');if(bl&&p&&p.ok&&Array.isArray(p.pending_calls)&&p.pending_calls.length){const tot=p.pending_calls.reduce((a,c)=>a+(c.n||0),0);bl.querySelector('summary').textContent='Paper ballot: '+tot+' calls resolving \u2014 tap for each call.';bl.querySelector('div').innerHTML=p.pending_calls.map(c=>'<div>'+c.date+' '+c.symbols.join(', ')+' <small>'+c.called_ago+', '+c.grades_in+'</small></div>').join('')}}catch(_){}PSUFFIX=t;if(SLIP&&t&&SLIP.indexOf('resolving')<0&&SLIP.indexOf('hit-rate')<0)SLIP+=t;if(t&&v.textContent.indexOf('paper')<0&&v.textContent.indexOf('resolving')<0&&v.textContent.indexOf('early')<0)v.textContent+=t;try{const ed=document.getElementById('earlydetail');if(ed&&p&&p.ok&&p.early&&p.early.detail){const e=p.early;const bo=(e.best&&e.best.pct!=null&&e.best.pct>=20)?'🔥 ':'';const summ=`${bo}Early moves: ${e.up}/${e.n} up, best ${(e.best||{}).symbol||'?'} ${((e.best||{}).pct>0?'+':'')+((e.best||{}).pct??0)}% via live \u2014 tap for each call.`;ed.querySelector('summary').textContent=summ;ed.querySelector('div').innerHTML=e.detail.map(x=>`<div>${x.symbol} ${(x.pct>0?'+':'')+x.pct}%${x.entry?` <small>entry ${x.entry} → now ${x.cur||'?'} via live</small>`:''}${x.pairUrl?` <a href="${x.pairUrl}">trades</a>`:''}</div>`).join('')}}catch(_){}}) });}
loadAll();
document.getElementById('refresh').onclick=()=>{const b=document.getElementById('refresh');b.textContent='↻…';loadAll();setTimeout(()=>{loadAll();b.textContent='↻ Refresh'},7000)};
document.querySelectorAll('.thumbbar [data-k]').forEach(b=>b.onclick=()=>{CUR=b.dataset.k;document.querySelectorAll('.thumbbar [data-k]').forEach(x=>x.classList.toggle('on',x===b));render()});
document.getElementById('copy').onclick=()=>{if(!SLIP)return;const b=document.getElementById('copy');(navigator.clipboard?navigator.clipboard.writeText(SLIP):Promise.reject()).then(()=>{b.textContent='✓ Copied';setTimeout(()=>b.textContent='📋 Copy',1200)}).catch(()=>{prompt('Copy your slip:',SLIP)})};
document.getElementById('dark').onclick=()=>{document.documentElement.classList.toggle('dark');localStorage.e60=document.documentElement.classList.contains('dark')?'d':'l'};</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"ok": True, "track": "e060"}).encode()
            return self.send(body, "application/json")
        if self.path == "/api/version":
            body = json.dumps(_version()).encode()
            return self.send(body, "application/json")
        if self.path == "/api/rotation":
            body = json.dumps(get_data()).encode()
            return self.send(body, "application/json")
        if self.path == "/api/paper":
            body = json.dumps(get_paper()).encode()
            return self.send(body, "application/json")
        try:
            top, pulse = server_card()
        except Exception:
            top, pulse = "Top pick unavailable", ""
        try:
            _early = early_detail_html().replace("<details", '<details id="earlydetail"', 1)
        except Exception:
            _early = ""
        try:
            _ballot = ballot_html()
        except Exception:
            _ballot = ""
        body = PAGE.replace("%%TOPONE%%", top).replace("%%PULSE%%", pulse).replace("%%EARLYDETAIL%%", _early).replace("%%BALLOT%%", _ballot).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
    def send(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    threading.Thread(target=_auto_refresh_loop, daemon=True).start()
    maybe_refresh()  # warm the cache at boot so first paint is LIVE
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
