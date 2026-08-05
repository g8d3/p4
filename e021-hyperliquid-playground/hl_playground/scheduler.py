"""Execute a configured API call and persist its result as table rows.

Shared by the background scheduler and the "run now" API endpoint, so manual
and scheduled runs behave identically. Uses only the stdlib (urllib).
"""

import json
import time
import urllib.error
import urllib.request

from . import extract
from .db import result_table

DEFAULT_TIMEOUT = 20


def execute_call(db, call):
    """Run one call config. Returns a dict describing the outcome."""
    started = time.monotonic()
    url = (call["base_url"] or "https://api.hyperliquid.xyz").rstrip("/") + "/" + (
        call["path"].lstrip("/") or "info"
    )
    method = (call["method"] or "POST").upper()
    try:
        payload = json.loads(call["payload"] or "{}")
    except json.JSONDecodeError as e:
        _finish(db, call, "error", None, 0, 0, f"bad payload: {e}")
        return {"ok": False, "error": f"bad payload: {e}", "row_count": 0}

    body = None
    headers = {"Accept": "application/json"}
    if method in ("POST", "PUT", "PATCH"):
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()
    else:
        from urllib.parse import urlencode
        qs = urlencode(payload)
        url = url + ("&" if "?" in url else "?") + qs

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            latency = int((time.monotonic() - started) * 1000)
            http_status = resp.status
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        latency = int((time.monotonic() - started) * 1000)
        _finish(db, call, "error", e.code, latency, 0, f"HTTP {e.code}: {e.read()[:300]!r}")
        return {"ok": False, "error": f"HTTP {e.code}", "row_count": 0}
    except Exception as e:
        latency = int((time.monotonic() - started) * 1000)
        _finish(db, call, "error", None, latency, 0, str(e))
        return {"ok": False, "error": str(e), "row_count": 0}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        _finish(db, call, "error", http_status, latency, 0, f"non-JSON response: {e}")
        return {"ok": False, "error": "non-JSON response", "row_count": 0}

    rows = extract.rows_from_response(data, call.get("result_shape") or "auto")
    n = db.store_rows(call["id"], rows, _ts_now())
    _finish(db, call, "ok", http_status, latency, n, None)
    return {"ok": True, "row_count": n, "http_status": http_status, "latency_ms": latency}


def _finish(db, call, status, http_status, latency_ms, row_count, error):
    db.mark_run(call["id"], status, error, row_count)
    db.log_run(call["id"], status, http_status, latency_ms, row_count, error)


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
