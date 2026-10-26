import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(D, "operador"))
import racimos_topicos as R


def like(iid, day, text, url=""):
    return {"id": iid, "t": R.dt.datetime(2026, 10, day, 12, 0, tzinfo=R.BOG),
            "text": text, "url": url, "handle": "@x"}


def run(rows, days, desde):
    R.cargar = lambda *_: (rows, [])
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert R.main(["--days", str(days), "--desde", desde]) == 0
    return buf.getvalue()


base = ("launchpad presale", "https://x.com/a/status/1")
rows = [like(f"l{i}", 20, "pump.fun launchpad TGE " + str(i), f"https://x.com/a/status/{i}") for i in range(5)]
rows += [like(f"m{i}", 21, "ai agent trading bot prompts " + str(i),
              "" if i == 5 else f"https://x.com/b/status/{i}") for i in range(6)]
rows += [like(f"s{i}", 22, "quiet post " + str(i), f"https://x.com/c/status/{i}") for i in range(4)]
out = run(rows, 3, "2026-10-22")
assert "2026-10-20: FIRE launchpads: 5 likes" in out, out
assert "2026-10-21: FIRE ai-trading-bots: 6 likes" in out, out
assert "(1 without stored/duplicate link, not shown)" in out, out
assert "2026-10-22: 4 likes, no topic hits" in out, out
assert "https://x.com/a/status/0" in out and "https://x.com/b/status/0" in out
assert "invent" not in out.lower()

# missing estado files warn instead of silently loading 0 likes
import tempfile
from contextlib import redirect_stderr
import importlib
importlib.reload(R)  # drop the cargar monkeypatch above; use real loader
buf, err = io.StringIO(), io.StringIO()
with redirect_stdout(buf), redirect_stderr(err):
    assert R.main(["--days", "1", "--estado", tempfile.mkdtemp()]) == 0
assert "warning: missing" in err.getvalue() and "likes_extension.jsonl" in err.getvalue()
assert "0 likes loaded" in buf.getvalue()
print("OK racimos")
