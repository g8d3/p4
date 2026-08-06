"""Hyperliquid API playground — FastAPI app.

Serves a mobile-first single page, a generic SQL query engine over all
stored tables, and a CRUD API for the scheduled calls.
"""

import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import scheduler
from .db import DB

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("HL_DATA_DIR", ROOT.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "playground.db"

db = DB(DB_PATH)
sched = scheduler.Scheduler(db)
START = time.monotonic()

app = FastAPI(title="Hyperliquid Playground", version="0.1.0")


@app.on_event("startup")
def _startup():
    sched.start()


@app.on_event("shutdown")
def _shutdown():
    sched.stop()


# ---- models ---------------------------------------------------------------

class QueryBody(BaseModel):
    sql: str
    limit: int = 2000


class CallBody(BaseModel):
    name: str | None = None
    base_url: str | None = None
    path: str | None = None
    method: str | None = None
    payload: str | None = None
    result_shape: str | None = None
    interval_sec: int | None = None
    enabled: bool | None = None
    keep_last: int | None = None
    keep_group_col: str | None = None
    dedup_cols: str | None = None
    last_t_col: str | None = None
    backfill_ms: int | None = None
    read_sql: str | None = None


# ---- static ---------------------------------------------------------------

app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


# ---- status / discovery ----------------------------------------------------

@app.get("/api/status")
def status():
    calls = db.list_calls()
    tables = db.list_tables()
    return {
        "server_time": scheduler._ts_now(),
        "uptime_sec": int(time.monotonic() - START),
        "db": str(DB_PATH),
        "calls_total": len(calls),
        "calls_enabled": sum(1 for c in calls if c["enabled"]),
        "tables": len(tables),
        "scheduler": "running",
    }


@app.get("/api/endpoints")
def endpoints():
    return {
        "base_urls": [
            "https://api.hyperliquid.xyz",
            "https://api.hyperliquid-testnet.xyz",
        ],
        "info": [
            {"label": "allMids", "payload": {"type": "allMids"}},
            {"label": "meta", "payload": {"type": "meta"}},
            {"label": "metaAndAssetCtxs", "payload": {"type": "metaAndAssetCtxs"}},
            {"label": "spotMeta", "payload": {"type": "spotMeta"}},
            {"label": "spotMetaAndAssetCtxs", "payload": {"type": "spotMetaAndAssetCtxs"}},
            {"label": "l2Book", "payload": {"type": "l2Book", "coin": "BTC"}},
            {"label": "l1Book", "payload": {"type": "l1Book", "coin": "BTC"}},
            {"label": "recentTrades", "payload": {"type": "recentTrades", "coin": "BTC"}},
            {"label": "candleSnapshot", "payload": {"type": "candleSnapshot", "req": {"coin": "BTC", "interval": "1h", "startTime": 0, "endTime": 0}}},
            {"label": "candles 15m (watchlist, incremental)", "payload": '{"type":"candleSnapshot","req":{"coin":{{coins}},"interval":"15m","startTime":{{last_t}},"endTime":{{now_ms}}}}'},
            {"label": "candles 1h (watchlist, incremental)", "payload": '{"type":"candleSnapshot","req":{"coin":{{coins}},"interval":"1h","startTime":{{last_t}},"endTime":{{now_ms}}}}'},
            {"label": "candles 4h (watchlist, incremental)", "payload": '{"type":"candleSnapshot","req":{"coin":{{coins}},"interval":"4h","startTime":{{last_t}},"endTime":{{now_ms}}}}'},
            {"label": "candles 1w (watchlist, incremental)", "payload": '{"type":"candleSnapshot","req":{"coin":{{coins}},"interval":"1w","startTime":{{last_t}},"endTime":{{now_ms}}}}'},
            {"label": "fundingHistory", "payload": {"type": "fundingHistory", "coin": "BTC", "startTime": 0}},
            {"label": "fundingRateHistory", "payload": {"type": "fundingRateHistory", "coin": "BTC", "startTime": 0}},
            {"label": "recentFunding", "payload": {"type": "recentFunding"}},
            {"label": "funding", "payload": {"type": "funding", "coin": "BTC"}},
            {"label": "times", "payload": {"type": "times"}},
            {"label": "exchangeInfo", "payload": {"type": "exchangeInfo"}},
            {"label": "perpVolume", "payload": {"type": "perpVolume"}},
            {"label": "userFills", "payload": {"type": "userFills", "user": "0x..."}},
            {"label": "userFunding", "payload": {"type": "userFunding", "user": "0x...", "startTime": 0}},
            {"label": "userNonFundingLedgerUpdates", "payload": {"type": "userNonFundingLedgerUpdates", "user": "0x...", "startTime": 0}},
            {"label": "clearinghouseState", "payload": {"type": "clearinghouseState", "user": "0x..."}},
            {"label": "clearinghouseStateWithPnl", "payload": {"type": "clearinghouseStateWithPnl", "user": "0x..."}},
            {"label": "portfolio", "payload": {"type": "portfolio", "user": "0x..."}},
            {"label": "userFees", "payload": {"type": "userFees", "user": "0x..."}},
            {"label": "userFeesByTime", "payload": {"type": "userFeesByTime", "user": "0x...", "startTime": 0}},
            {"label": "spotUserFills", "payload": {"type": "spotUserFills", "user": "0x..."}},
            {"label": "orderStatus", "payload": {"type": "orderStatus", "oid": 0}},
            {"label": "topTraders", "payload": {"type": "topTraders", "coin": "BTC", "timeWindow": "7d"}},
            {"label": "userNonFundingLedgerUpdates", "payload": {"type": "userNonFundingLedgerUpdates", "user": "0x...", "startTime": 0}},
        ],
    }


@app.get("/api/tables")
def tables():
    return {"tables": db.list_tables()}


# ---- ranking / coin filter ------------------------------------------------
# Step 1 of the guided flow: fetch markets once, rank coins by 24h volume and
# open interest, and let the user pick a *coverage percentage* per metric.
# The slider computes the top-N automatically and the chosen watchlist is
# persisted in `config` so later steps (candle/book fan-out) can consume it.

RANKING_SQL = """
WITH latest AS (
  -- openInterest is in coin units (BTC = ~35k BTC): convert to USD notional
  SELECT name, dayntlvlm, openinterest * markpx AS oi_usd FROM {table}
  WHERE _ts = (SELECT max(_ts) FROM {table})
),
tot AS (
  SELECT SUM(dayntlvlm) AS tv, SUM(oi_usd) AS toi FROM latest
)
SELECT
  ROW_NUMBER() OVER (ORDER BY dayntlvlm DESC)     AS rank_vol,
  name,
  dayntlvlm,
  ROUND(SUM(dayntlvlm) OVER (ORDER BY dayntlvlm DESC) / tot.tv, 4) AS cum_vol,
  ROW_NUMBER() OVER (ORDER BY oi_usd DESC)        AS rank_oi,
  oi_usd,
  ROUND(SUM(oi_usd) OVER (ORDER BY oi_usd DESC) / tot.toi, 4) AS cum_oi
FROM latest CROSS JOIN tot
ORDER BY rank_vol
"""


def _ranking_rows():
    call = next((c for c in db.list_calls() if c["name"] == "markets"), None)
    if not call:
        return None
    table = f"r_{call['id']}"
    sql = RANKING_SQL.format(table=table)
    cols, rows, err = db.run_query(sql)
    if err or not rows:
        return None
    return [dict(zip(cols, r)) for r in rows]


def _resolve_watchlist(vol_pct, oi_pct, rows):
    """Smallest top-N whose cumulative coverage reaches each threshold."""
    vol_n = min((r["rank_vol"] for r in rows
                 if r["cum_vol"] is not None and r["cum_vol"] >= vol_pct), default=len(rows))
    oi_n = min((r["rank_oi"] for r in rows
                if r["cum_oi"] is not None and r["cum_oi"] >= oi_pct), default=len(rows))
    coins = [r["name"] for r in rows if r["rank_vol"] <= vol_n or r["rank_oi"] <= oi_n]
    return {"vol_pct": vol_pct, "oi_pct": oi_pct, "vol_n": vol_n, "oi_n": oi_n,
            "union_n": len(coins), "coins": coins}


@app.get("/api/ranking")
def ranking():
    rows = _ranking_rows()
    if rows is None:
        return {"available": False, "rows": [], "sql": None}
    tv = sum(r["dayntlvlm"] or 0 for r in rows)
    toi = sum(r["oi_usd"] or 0 for r in rows)
    call = next((c for c in db.list_calls() if c["name"] == "markets"), None)
    sql = RANKING_SQL.format(table=f"r_{call['id']}") if call else None
    return {"available": True, "n_coins": len(rows), "total_vol": tv, "total_oi": toi,
            "sql": sql, "rows": rows}


@app.post("/api/ranking/setup")
def ranking_setup():
    """Create (if needed) and run the markets feed that powers the ranking."""
    call = next((c for c in db.list_calls() if c["name"] == "markets"), None)
    if not call:
        call_id = db.create_call({
            "name": "markets",
            "payload": '{"type":"metaAndAssetCtxs"}',
            "interval_sec": 86400,
            "enabled": True,
        })
        call = db.get_call(call_id)
    result = scheduler.execute_call(db, call)
    return {"ok": result["ok"], "call_id": call["id"],
            "error": result.get("error"), "row_count": result.get("row_count")}


@app.get("/api/watchlist")
def get_watchlist():
    raw = db.get_config("watchlist")
    if not raw:
        return {"set": False}
    return {"set": True, **json.loads(raw)}


class WatchlistBody(BaseModel):
    vol_pct: float = 0.95
    oi_pct: float = 0.95


@app.put("/api/watchlist")
def put_watchlist(body: WatchlistBody):
    rows = _ranking_rows()
    if rows is None:
        raise HTTPException(400, "no markets data yet — run /api/ranking/setup first")
    wl = _resolve_watchlist(body.vol_pct, body.oi_pct, rows)
    db.set_config("watchlist", json.dumps(wl))
    return {"ok": True, **wl}


@app.post("/api/query")
def query(body: QueryBody):
    started = time.monotonic()
    columns, rows, error = db.run_query(body.sql, limit=body.limit)
    elapsed = int((time.monotonic() - started) * 1000)
    return {
        "ok": error is None,
        "columns": columns,
        "rows": rows,
        "rowcount": len(rows),
        "truncated": len(rows) >= body.limit,
        "elapsed_ms": elapsed,
        "error": error,
    }


# ---- calls CRUD + execution ------------------------------------------------

@app.get("/api/calls")
def list_calls():
    return {"calls": db.list_calls()}


@app.post("/api/calls")
def create_call(body: CallBody):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if "enabled" not in data:
        data["enabled"] = True
    try:
        call_id = db.create_call(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "id": call_id}


@app.put("/api/calls/{call_id}")
def update_call(call_id: int, body: CallBody):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        db.update_call(call_id, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.delete("/api/calls/{call_id}")
def delete_call(call_id: int):
    db.delete_call(call_id)
    return {"ok": True}


@app.post("/api/calls/{call_id}/run")
def run_now(call_id: int):
    call = db.get_call(call_id)
    if not call:
        raise HTTPException(404, "call not found")
    result = scheduler.execute_call(db, call)
    return {"ok": result["ok"], "call": call["name"], **result}


@app.post("/api/calls/{call_id}/clear")
def clear_results(call_id: int):
    db.clear_results(call_id)
    return {"ok": True}


@app.post("/api/calls/run_all")
def run_all():
    results = []
    for call in db.list_calls():
        results.append({"name": call["name"], **scheduler.execute_call(db, call)})
    return {"ok": True, "results": results}


@app.exception_handler(Exception)
def _catch_all(req, exc):
    return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})
