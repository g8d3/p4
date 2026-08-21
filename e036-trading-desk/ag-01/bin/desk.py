#!/usr/bin/env python3
"""Trading desk: mobile dashboard for the e025 paper-trading desk.

Read-only. Serves paper trades, open positions, equity curve (live HL marks),
and a price ticker. Flask, port 8088, LAN-accessible for phone access.
"""
import csv
import json
import os
import time
import urllib.request

from flask import Flask, jsonify

P4 = "/home/vuos/code/p4"
MON = os.path.join(P4, "e025-hyperliquid-candle-tails/ag-16-live-monitor/output")
TRADES_CSV = os.path.join(MON, "paper_trades.csv")
STATE_JSON = os.path.join(MON, "paper_state.json")
MONITOR_LOG = os.path.join(MON, "monitor.log")
EXEC_SUMMARY = os.path.join(P4, "e025-hyperliquid-candle-tails/EXECUTIVE_SUMMARY.md")

HL_INFO = "https://api.hyperliquid.xyz/info"
START_EQUITY = 1000.0
FEE_PCT = 0.09

app = Flask(__name__)
_cache = {"mids": {"t": 0, "data": None}}


def _fetch(url: str, body: dict, timeout: float = 6.0):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def get_mids():
    """All Hyperliquid mid prices, cached 5s. Returns dict or None."""
    now = time.time()
    if _cache["mids"]["data"] is None or now - _cache["mids"]["t"] > 5:
        try:
            raw = _fetch(HL_INFO, {"type": "allMids"})
            _cache["mids"] = {"t": now, "data": raw}
        except Exception:
            return _cache["mids"]["data"]  # stale on failure
    return _cache["mids"]["data"]


def read_trades():
    if not os.path.exists(TRADES_CSV):
        return []
    with open(TRADES_CSV) as f:
        return list(csv.DictReader(f))


def read_state():
    if not os.path.exists(STATE_JSON):
        return {"last_day": None, "pending": []}
    with open(STATE_JSON) as f:
        return json.load(f)


def tail_log(n=25):
    if not os.path.exists(MONITOR_LOG):
        return []
    with open(MONITOR_LOG) as f:
        return [l.rstrip() for l in f.readlines()[-n:]]


def day_close(coin: str, day: str, mids: dict | None):
    """Close price for coin on day: live mid for today, else daily candle."""
    today = time.strftime("%Y-%m-%d", time.localtime())
    if day == today and mids:
        v = mids.get(coin)
        return float(v) if v else None
    try:
        start = time.mktime(time.strptime(day, "%Y-%m-%d"))
        candles = _fetch(
            HL_INFO,
            {"type": "candleSnapshot", "req": {"coin": coin, "interval": "1d", "startTime": int(start * 1000)}},
        )
        if candles:
            t0 = int(start)
            match = [c for c in candles if int(c["t"]) // 1000 >= t0 - 86400 and int(c["t"]) // 1000 < t0 + 86400]
            if match:
                return float(match[0]["c"])
    except Exception:
        return None
    return None


def build_data():
    mids = get_mids()
    trades = read_trades()
    state = read_state()
    today = time.strftime("%Y-%m-%d", time.localtime())

    closed = []
    for r in trades:
        if r.get("status") != "closed":
            continue
        closed.append(
            {
                "coin": r["coin"],
                "entry_day": r["entry_day"],
                "exit_day": r["exit_day"],
                "trigger": r["trigger"],
                "net_pct": round(float(r["net_pct"]), 2),
                "ret_pct": round(float(r["ret_pct"]), 2),
            }
        )
    closed.sort(key=lambda x: x["exit_day"], reverse=True)

    # Equity curve: cumulative net % applied to START_EQUITY, chronological.
    eq = []
    cum = 0.0
    for r in sorted(closed, key=lambda x: x["exit_day"]):
        cum += float(r["net_pct"])
        eq.append({"day": r["exit_day"], "equity": round(START_EQUITY * (1 + cum / 100.0), 2)})
    # Mark open positions to market for "current" equity.
    open_pos = []
    unrealized = 0.0
    for p in state.get("pending", []):
        px = day_close(p["coin"], p["entry_day"], mids)
        cur = day_close(p["coin"], today, mids)
        if cur is None and mids:
            v = mids.get(p["coin"])
            cur = float(v) if v else None
        ret = None
        if px and cur:
            ret = round((cur / px - 1) * 100, 2)
            unrealized += ret
        open_pos.append(
            {
                "coin": p["coin"],
                "entry_day": p["entry_day"],
                "exit_day": p["exit_day"],
                "trigger": p.get("trigger", ""),
                "entry_close": p.get("entry_close"),
                "current": cur,
                "unrealized_pct": ret,
            }
        )
    current_equity = round(START_EQUITY * (1 + (cum + unrealized) / 100.0), 2)

    wins = [t for t in closed if t["net_pct"] > 0]
    return {
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "start_equity": START_EQUITY,
        "current_equity": current_equity,
        "closed_count": len(closed),
        "win_rate": round(100 * len(wins) / len(closed), 1) if closed else None,
        "total_net_pct": round(sum(t["net_pct"] for t in closed), 2),
        "unrealized_pct": round(unrealized, 2),
        "closed": closed,
        "open": open_pos,
        "equity": eq,
        "log": tail_log(),
        "stale": mids is None,
    }


@app.get("/api/data")
def api_data():
    return jsonify(build_data())


@app.get("/")
def index():
    with open(os.path.join(os.path.dirname(__file__), "index.html")) as f:
        return f.read()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8088, threaded=True)
