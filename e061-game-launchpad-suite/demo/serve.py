#!/usr/bin/env python3
"""e061 demo server: static files + server-logged visit counter (day-2 metric).

Replaces `python3 -m http.server`: same static serving plus
  POST /api/visit  {cid, ev}  -> appends one JSONL row to visits.jsonl
  GET  /api/stats             -> DATA PULSE: rows + last-sample age + cadence
No secrets, no funds, no chain. Stdlib only.
"""
import json
import os
import time
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "visits.jsonl")
EVENTS = ("visit", "win", "slip")

# MIDNIGHT-CROSSER GUARD (run #120): test/health probes must never count
# as players or returning players. visits still logs them (traffic),
# but players/day2 only count real device cids.
PROBE_PREFIXES = ("e2e-", "probe", "test-", "health")


def _is_probe(cid):
    c = str(cid or "")
    return c == "e2e-probe" or c.startswith(PROBE_PREFIXES)


def stats():
    # DATA PULSE: is it sampling (rows), how fresh (last-sample age), cadence.
    # Never raises: unknown -> zeros, like the e062/e063 card pattern.
    out = {"visits": 0, "wins": 0, "slips": 0, "players": 0, "day2": 0,
           "rows": 0, "last": None, "lastAgeMin": None, "every": "each page load",
           "wins24": 0, "due": 0, "dueAt": None}
    try:
        days = {}
        last = None
        with open(LOG) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("ev") not in EVENTS:
                    continue
                out["rows"] += 1
                if r.get("ev") == "visit":
                    out["visits"] += 1
                elif r.get("ev") == "win":
                    out["wins"] += 1
                elif r.get("ev") == "slip":
                    out["slips"] += 1
                c, d = r.get("cid"), r.get("day")
                if c and d and not _is_probe(c):
                    days.setdefault(c, set()).add(d)
                if r.get("ts") and (last is None or r["ts"] > last):
                    last = r["ts"]
        out["players"] = len(days)
        out["day2"] = sum(1 for ds in days.values() if len(ds) >= 2)
        # WIN+24H REMINDER (run #86): which wins are due back in the next
        # 4h window, so the card can name the day-2 check without asking.
        try:
            now = datetime.now(timezone.utc)
            win_ts = {}
            for line in open(LOG):
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("ev") == "win" and r.get("cid") and r.get("ts"):
                    if _is_probe(r.get("cid")):
                        continue
                    try:
                        t = datetime.fromisoformat(r["ts"])
                    except Exception:
                        continue
                    c = r["cid"]
                    if c not in win_ts or t < win_ts[c]:
                        win_ts[c] = t
            due_at = None
            for c, t in win_ts.items():
                age_h = (now - t).total_seconds() / 3600
                if 0 <= age_h <= 24:
                    out["wins24"] += 1
                if len(days.get(c, set())) < 2 and 20 <= age_h <= 28:
                    out["due"] += 1
                    if due_at is None or t > due_at:
                        due_at = t
            if due_at is not None:
                out["dueAt"] = due_at.isoformat()
        except Exception:
            pass
        out["last"] = last
        if last:
            try:
                dt = (datetime.now(timezone.utc)
                      - datetime.fromisoformat(last)).total_seconds()
                out["lastAgeMin"] = round(max(dt, 0) / 60, 1)
            except Exception:
                pass
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return out


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=HERE, **k)

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.split("?")[0] != "/api/visit":
            return self._json({"ok": False, "err": "not found"}, 404)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(min(n, 4096)).decode() or "{}")
        except Exception:
            return self._json({"ok": False, "err": "bad json"}, 400)
        cid = str(body.get("cid") or "")[:64]
        ev = str(body.get("ev") or "")
        if not cid or ev not in EVENTS:
            return self._json({"ok": False, "err": "bad fields"}, 400)
        now = datetime.now(timezone.utc)
        try:
            with open(LOG, "a") as f:
                f.write(json.dumps({"ts": now.isoformat(),
                                    "day": now.date().isoformat(),
                                    "cid": cid, "ev": ev}) + "\n")
        except Exception:
            return self._json({"ok": False, "err": "store"}, 500)
        return self._json({"ok": True})

    def do_GET(self):
        if self.path.split("?")[0] == "/api/stats":
            return self._json(stats())
        if self.path.split("?")[0] in ("/", "/index.html"):
            # BAKED PULSE (run #144): slow phones saw `players (server): …`
            # until the JS fetch landed. Server bakes current counts into
            # the HTML; refreshPulse() still upgrades it live after load.
            try:
                s = stats()
                html = open(os.path.join(HERE, "index.html")).read()
                baked = ("players (server): %d visits \u00b7 %d players \u00b7 "
                         "%d back day-2 \u00b7 wins %d" %
                         (s["visits"], s["players"], s["day2"], s["wins"]))
                html = html.replace("players (server): \u2026", baked)
                body = html.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            except Exception:
                pass
        return super().do_GET()


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8321), H).serve_forever()
