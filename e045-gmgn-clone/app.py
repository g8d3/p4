"""
app.py — GMGN-style web app backend (e045).

Flask single-page app over the Hyperliquid client. Serves the screener,
token detail, candles, buy/sell flow, order book, and a read-only SQL endpoint
over the snapshot cache.

Run:
    python3 app.py            # or: bin/run.sh
    Default port 8338, bind 0.0.0.0 (so it works from the phone on LAN).
"""

from __future__ import annotations

import os
import sqlite3
import time
import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request, abort

from hl import Hyperliquid, HLError, INTERVAL_MS
import sol

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "gmgn.sqlite3"

hl = Hyperliquid(ttl=5.0)

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


@app.after_request
def _no_cache(resp):
    # live trading UI: never cache stale market data or stale JS/CSS
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


# --------------------------------------------------------------------------
# SQLite snapshot cache (p4 convention: everything is a SQL table)
# --------------------------------------------------------------------------
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _init_db():
    con = _conn()
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market TEXT NOT NULL,
            ts REAL NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    con.commit()
    con.close()


def _store_snapshot(market: str, rows: list[dict]):
    try:
        con = _conn()
        con.execute(
            "INSERT INTO snapshot(market, ts, payload) VALUES(?,?,?)",
            (market, time.time(), json.dumps(rows)),
        )
        # keep the table bounded
        con.execute(
            "DELETE FROM snapshot WHERE id NOT IN "
            "(SELECT id FROM snapshot ORDER BY id DESC LIMIT 500)"
        )
        con.commit()
        con.close()
    except Exception:  # pragma: no cover - cache must never break the app
        pass


_init_db()


# --------------------------------------------------------------------------
# helpers for screener sorting / filters
# --------------------------------------------------------------------------
SORTABLE = {
    "price": lambda r: r["price"],
    "change": lambda r: r["change_24h"],
    "volume": lambda r: r["volume_24h"],
    "mc": lambda r: r.get("market_cap", 0),
    "fdv": lambda r: r.get("fully_diluted_cap", 0),
    "oi": lambda r: r.get("open_interest", 0),
    "funding": lambda r: r.get("funding", 0),
    "volume_base": lambda r: r.get("volume_base", 0),
    "name": lambda r: r["name"],
}


def _sort_rows(rows, sort="volume", order="desc"):
    key = SORTABLE.get(sort, SORTABLE["volume"])
    return sorted(rows, key=key, reverse=(order == "desc"))


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "ts": time.time(), "source": "hyperliquid"})


@app.route("/api/meta")
def meta():
    market = request.args.get("market", "perp")
    m, _ = hl.meta_and_asset_ctxs(market)
    return jsonify({"market": market, "meta": m})


@app.route("/api/screener")
def screener():
    market = request.args.get("market", "perp")
    sort = request.args.get("sort", "volume")
    order = request.args.get("order", "desc")
    q = (request.args.get("q") or "").strip().lower()
    limit = int(request.args.get("limit", 200))
    try:
        rows = hl.markets(market)
    except HLError as exc:
        return jsonify({"error": str(exc)}), 502
    if q:
        rows = [r for r in rows if q in r["name"].lower()]
    rows = _sort_rows(rows, sort, order)
    _store_snapshot(f"{market}:{sort}:{order}", rows)
    return jsonify({"market": market, "sort": sort, "order": order, "rows": rows[:limit]})


@app.route("/api/trending")
def trending():
    market = request.args.get("market", "perp")
    limit = int(request.args.get("limit", 12))
    try:
        rows = hl.markets(market)
    except HLError as exc:
        return jsonify({"error": str(exc)}), 502
    # blend of volume + abs change => what's hot right now
    for r in rows:
        r["trend_score"] = (r["volume_24h"] or 0) * (1 + abs(r["change_24h"]) / 100 * 3)
    rows = sorted(rows, key=lambda r: r["trend_score"], reverse=True)
    _store_snapshot(f"trending:{market}", rows)
    return jsonify({"market": market, "rows": rows[:limit]})


@app.route("/api/token")
def token():
    name = (request.args.get("name") or "").strip()
    market = request.args.get("market", "perp")
    if not name:
        abort(400, "name required")
    try:
        detail = hl.token_detail(name, market)
    except HLError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(detail)


@app.route("/api/candles")
def candles():
    name = (request.args.get("name") or "").strip()
    interval = request.args.get("interval", "1m")
    limit = int(request.args.get("limit", 200))
    if not name:
        abort(400, "name required")
    try:
        data = hl.candles(name, interval, limit)
    except HLError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify({"name": name, "interval": interval, "candles": data})


def _flow_summary(trades):
    buy_vol = sell_vol = 0.0
    buy_cnt = sell_cnt = 0
    buyer = seller = 0.0
    for t in trades:
        try:
            notional = float(t["px"]) * float(t["sz"])
        except (KeyError, TypeError, ValueError):
            continue
        if t.get("side") == "B":  # taker buy
            buy_vol += notional
            buy_cnt += 1
            buyer += notional
        else:  # "A" taker sell
            sell_vol += notional
            sell_cnt += 1
            seller += notional
    total = buy_vol + sell_vol
    return {
        "buy_volume": round(buy_vol, 4),
        "sell_volume": round(sell_vol, 4),
        "buy_count": buy_cnt,
        "sell_count": sell_cnt,
        "net": round(buy_vol - sell_vol, 4),
        "buy_ratio": round(buy_vol / total, 4) if total else 0.5,
        "sell_ratio": round(sell_vol / total, 4) if total else 0.5,
    }


@app.route("/api/trades")
def trades():
    name = (request.args.get("name") or "").strip()
    limit = int(request.args.get("limit", 100))
    if not name:
        abort(400, "name required")
    try:
        data = hl.trades(name, limit)
    except HLError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify(
        {"name": name, "trades": data, "flow": _flow_summary(data)}
    )


@app.route("/api/flow")
def flow():
    name = (request.args.get("name") or "").strip()
    if not name:
        abort(400, "name required")
    try:
        data = hl.trades(name, 100)
    except HLError as exc:
        return jsonify({"error": str(exc)}), 502
    summary = _flow_summary(data)
    # whales = largest notional trades
    trades = []
    for t in data:
        try:
            notional = float(t["px"]) * float(t["sz"])
        except (KeyError, TypeError, ValueError):
            continue
        trades.append(
            {
                "price": float(t["px"]),
                "size": float(t["sz"]),
                "notional": round(notional, 4),
                "side": t.get("side"),
                "time": t.get("time"),
                "hash": t.get("hash"),
            }
        )
    whales = sorted(trades, key=lambda x: x["notional"], reverse=True)[:10]
    return jsonify({"name": name, "flow": summary, "whales": whales})


@app.route("/api/orderbook")
def orderbook():
    name = (request.args.get("name") or "").strip()
    if not name:
        abort(400, "name required")
    try:
        data = hl.l2_book(name)
    except HLError as exc:
        return jsonify({"error": str(exc)}), 502
    bids = data.get("levels", [list(), list()])[0][:12]
    asks = data.get("levels", [list(), list()])[1][:12]
    return jsonify({"name": name, "bids": bids, "asks": asks})


@app.route("/api/search")
def search():
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify({"rows": []})
    rows = []
    for market in ("perp", "spot"):
        try:
            rows += hl.markets(market)
        except HLError:
            continue
    hits = [r for r in rows if q in r["name"].lower()][:20]
    return jsonify({"rows": hits})


@app.route("/api/intervals")
def intervals():
    return jsonify({"intervals": sorted(INTERVAL_MS.keys())})


# --------------------------------------------------------------------------
# Solana memecoin surface (the real GMGN clone)
# --------------------------------------------------------------------------
MC_SORT = {
    "price": lambda r: r.get("price") or 0,
    "change": lambda r: r.get("change_24h") or 0,
    "volume": lambda r: r.get("volume_24h") or 0,
    "mc": lambda r: r.get("market_cap") or 0,
    "fdv": lambda r: r.get("fdv") or 0,
    "liquidity": lambda r: r.get("liquidity") or 0,
    "buys": lambda r: r.get("buys_24h") or 0,
    "sells": lambda r: r.get("sells_24h") or 0,
    "name": lambda r: r.get("name") or "",
}


def _mc_sort(rows, sort="volume", order="desc"):
    key = MC_SORT.get(sort, MC_SORT["volume"])
    return sorted(rows, key=key, reverse=(order == "desc"))


def _mc_token_key(row):
    return row.get("mint") or (row.get("pool") or "")


@app.route("/api/memecoins/screener")
def memecoins_screener():
    sort = request.args.get("sort", "volume")
    order = request.args.get("order", "desc")
    q = (request.args.get("q") or "").strip().lower()
    try:
        rows = sol.screener()
    except sol.SOLError as exc:
        return jsonify({"error": str(exc)}), 502
    if q:
        rows = [r for r in rows if q in (r.get("symbol") or "").lower() or q in (r.get("name") or "").lower()]
    rows = _mc_sort(rows, sort, order)
    return jsonify({"rows": rows[:120]})


@app.route("/api/memecoins/trending")
def memecoins_trending():
    try:
        rows = sol.trending()
    except sol.SOLError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify({"rows": rows[:20]})


@app.route("/api/memecoins/token")
def memecoins_token():
    addr = (request.args.get("addr") or "").strip()
    if not addr:
        abort(400, "addr required")
    try:
        detail = sol.token_detail(addr)
    except sol.SOLError as exc:
        return jsonify({"error": str(exc)}), 404
    if not detail.get("pool") and not detail.get("mint"):
        return jsonify({"error": "unknown token"}), 404
    return jsonify(detail)


@app.route("/api/memecoins/candles")
def memecoins_candles():
    pool = (request.args.get("pool") or "").strip()
    interval = request.args.get("interval", "15m")
    if not pool:
        abort(400, "pool required")
    try:
        data = sol.candles(pool, interval)
    except sol.SOLError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify({"pool": pool, "interval": interval, "candles": data})


@app.route("/api/memecoins/holders")
def memecoins_holders():
    addr = (request.args.get("addr") or "").strip()
    if not addr:
        abort(400, "addr required")
    return jsonify({"mint": addr, "holders": sol.holders(addr)})


@app.route("/api/db")
def db():
    """Read-only SQL over the snapshot cache (p4 convention)."""
    sql = (request.args.get("sql") or "").strip()
    if not sql.lower().lstrip().startswith("select"):
        return jsonify({"error": "only SELECT allowed"}), 400
    try:
        con = _conn()
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        con.close()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"columns": cols, "rows": rows, "sql": sql})


def _warm_cache():
    """Pre-load the Solana screener so token details seed from a hot cache."""
    import threading
    def run():
        try:
            sol.screener()
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    port = int(os.environ.get("GMGN_PORT", 8338))
    host = os.environ.get("GMGN_HOST", "0.0.0.0")
    _warm_cache()
    print(f"GMGN clone on http://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)
