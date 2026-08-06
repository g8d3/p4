"""Execute a configured API call and persist its result as table rows.

Shared by the background scheduler and the "run now" API endpoint, so manual
and scheduled runs behave identically. Uses only the stdlib (urllib).

Payload templates (resolved before each request):
  {{last_t}}  -> max(last_t_col) in this call's result table; if empty, uses
                 (now - backfill_ms) so the first run does a one-shot backfill
  {{now_ms}}  -> current epoch milliseconds
  {{coins}}   -> the saved watchlist (config `watchlist`); fan-out: one request
                 per coin, all stored in the same result table. Falls back to
                 every coin in the latest markets snapshot if no watchlist set.
"""

import json
import time
import urllib.error
import urllib.request

from . import extract
from .db import result_table

DEFAULT_TIMEOUT = 20


def resolve_coins(db):
    """Watchlist coins, or all coins from the latest markets snapshot."""
    raw = db.get_config("watchlist")
    if raw:
        try:
            coins = json.loads(raw).get("coins")
            if coins:
                return coins
        except Exception:
            pass
    call = next((c for c in db.list_calls() if c["name"] == "markets"), None)
    if call:
        t = result_table(call["id"])
        try:
            _, rows, err = db.run_query(
                f'SELECT DISTINCT name FROM "{t}" '
                f'WHERE _ts = (SELECT max(_ts) FROM "{t}") ORDER BY name')
            if rows:
                return [r[0] for r in rows]
        except Exception:
            pass
    return []


def resolve_templates(db, call, payload_str, group_val=None):
    if "{{last_t}}" in payload_str:
        last_t_col = call.get("last_t_col") or "t"
        group_col = call.get("keep_group_col") or ""
        if group_val is not None and group_col:
            last = db.max_col(call["id"], last_t_col, group_col, group_val)
        else:
            last = db.max_col(call["id"], last_t_col)
        if last is None:
            last = int(time.time() * 1000) - int(call.get("backfill_ms") or 604800000)
        payload_str = payload_str.replace("{{last_t}}", str(int(last)))
    if "{{now_ms}}" in payload_str:
        payload_str = payload_str.replace("{{now_ms}}", str(int(time.time() * 1000)))
    return payload_str


def execute_call(db, call):
    payload_str = call["payload"] or "{}"
    has_coins = "{{coins}}" in payload_str
    if has_coins:
        coins = resolve_coins(db)
        if not coins:
            _finish(db, call, "error", None, 0, 0,
                    "no coins to fan out — run the markets ranking first")
            return {"ok": False, "error": "no coins to fan out", "row_count": 0}
    else:
        coins = [None]

    started = time.monotonic()
    total, last_http, first_err = 0, None, None
    requests = []
    for coin in coins:
        pstr = payload_str.replace("{{coins}}", json.dumps(coin)) if coin is not None else payload_str
        pstr = resolve_templates(db, call, pstr, group_val=coin)
        try:
            requests.append(json.loads(pstr))
        except json.JSONDecodeError:
            requests.append(pstr)
        info = _do_request(db, call, pstr)
        if not info["ok"] and first_err is None:
            first_err = info["error"]
        if info.get("http"):
            last_http = info["http"]
        total += info.get("rows", 0)

    latency = int((time.monotonic() - started) * 1000)
    if call.get("keep_last"):
        db.prune_rows(call["id"], call["keep_last"], call.get("keep_group_col") or "")
    ok = first_err is None
    _finish(db, call, "ok" if ok else "error", last_http, latency, total, first_err, requests)
    return {"ok": ok, "error": first_err, "row_count": total, "latency_ms": latency}


def _do_request(db, call, payload_str):
    """One HTTP request + store. Returns {ok, http, rows, error} (no logging)."""
    url = (call["base_url"] or "https://api.hyperliquid.xyz").rstrip("/") + "/" + (
        call["path"].lstrip("/") or "info")
    method = (call["method"] or "POST").upper()
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        return {"ok": False, "http": None, "rows": 0, "error": f"bad payload: {e}"}

    body, headers = None, {"Accept": "application/json"}
    if method in ("POST", "PUT", "PATCH"):
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()
    else:
        from urllib.parse import urlencode
        url = url + ("&" if "?" in url else "?") + urlencode(payload)

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            http = resp.status
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return {"ok": False, "http": e.code, "rows": 0, "error": f"HTTP {e.code}: {e.read()[:200]!r}"}
    except Exception as e:
        return {"ok": False, "http": None, "rows": 0, "error": str(e)}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"ok": False, "http": http, "rows": 0, "error": f"non-JSON response: {e}"}

    rows = extract.rows_from_response(data, call.get("result_shape") or "auto")
    n = db.store_rows(call["id"], rows, _ts_now(), call.get("dedup_cols") or None)
    return {"ok": True, "http": http, "rows": n, "error": None}


def _finish(db, call, status, http_status, latency_ms, row_count, error, requests=None):
    req_json = json.dumps(requests) if requests else ""
    db.mark_run(call["id"], status, error, row_count, req_json)
    db.log_run(call["id"], status, http_status, latency_ms, row_count, error, req_json)


def _ts_now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


class Scheduler:
    """Background thread that runs enabled calls when their interval elapses."""

    def __init__(self, db):
        self.db = db
        self._stop = False

    def start(self):
        import threading
        self._thread = threading.Thread(target=self._loop, daemon=True, name="hl-scheduler")
        self._thread.start()

    def stop(self):
        self._stop = True

    def _loop(self):
        while not self._stop:
            try:
                now = time.time()
                for call in self.db.due_calls(now):
                    execute_call(self.db, call)
            except Exception as e:  # never let the loop die
                try:
                    self.db.log_run(0, "scheduler_error", None, 0, 0, str(e))
                except Exception:
                    pass
            time.sleep(1)
