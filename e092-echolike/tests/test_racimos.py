import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout

import importlib

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(D, "operador"))
import racimos_topicos as R

assert R.LIVE_TOPICS, "must import TOPICS from the live alerta_topicos.py"


def like(iid, day, text, url=""):
    return {"id": iid, "t": R.dt.datetime(2026, 10, day, 12, 0, tzinfo=R.BOG),
            "text": text, "url": url, "handle": "@x"}


def run(rows, days, desde, *flags):
    R.cargar = lambda *_: (rows, [])
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert R.main(["--days", str(days), "--desde", desde, *flags]) == 0
    return buf.getvalue()


rows = [like(f"l{i}", 20, "pump.fun launchpad TGE " + str(i), f"https://x.com/a/status/{i}") for i in range(5)]
rows += [like(f"m{i}", 21, "ai agent trading bot prompts " + str(i),
              "" if i == 5 else f"https://x.com/b/status/{i}") for i in range(6)]
rows += [like(f"s{i}", 22, "quiet post " + str(i), f"https://x.com/c/status/{i}") for i in range(4)]

# default: only the live alerter's topics are evaluated
out = run(rows, 3, "2026-10-22")
assert "2026-10-20: FIRE fairer launchpads: 5 likes, 5 unique links" in out, out
assert "ai-trading-bots" not in out, out
assert "2026-10-22: 4 likes, no topic hits" in out, out

# --extra: exploratory topics evaluated too
out = run(rows, 3, "2026-10-22", "--extra")
assert "2026-10-21: FIRE ai-trading-bots: 6 likes, 5 unique links" in out, out
assert "(1 without stored/duplicate link, not shown)" in out, out

# same URL under different ids (jsonl mirror in x_items) counts once
r2, v2 = [], set()
t0 = R.dt.datetime(2026, 10, 20, 12, 0, tzinfo=R.BOG)
R._agregar(r2, v2, {"url": "https://x.com/a/1", "text": "x", "handle": "h"}, "id1", t0)
R._agregar(r2, v2, {"url": "https://x.com/a/1", "text": "x", "handle": "h"}, "id2", t0)
R._agregar(r2, v2, {"url": "", "text": "x", "handle": "h"}, "id3", t0)
R._agregar(r2, v2, {"url": "", "text": "x", "handle": "h"}, "id3", t0)
assert len(r2) == 2, r2

# missing estado files warn instead of silently loading 0 likes
importlib.reload(R)  # drop the cargar monkeypatch above; use real loader
buf, err = io.StringIO(), io.StringIO()
with redirect_stdout(buf), redirect_stderr(err):
    assert R.main(["--days", "1", "--estado", tempfile.mkdtemp()]) == 0
assert "warning: missing" in err.getvalue() and "likes_extension.jsonl" in err.getvalue()
assert "0 likes loaded" in buf.getvalue()
print("OK racimos")
