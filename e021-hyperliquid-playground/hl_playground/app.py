"""Hyperliquid API playground — FastAPI app.

Serves a mobile-first single page, a generic SQL query engine over all
stored tables, and a CRUD API for the scheduled calls.
"""

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
