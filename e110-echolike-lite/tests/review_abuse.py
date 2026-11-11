"""Abuse test: the inbox must survive everything a browser (and a phone) does.

Reproduces the ways a Python http.server process usually dies in the wild:
client hangs up mid-response, garbage request line, huge Content-Length with no
body, wrong token, and a burst of parallel requests. After every step the
server must answer /api/health and the captures on disk must be intact.
"""
import json
import pathlib
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 8933
work = tempfile.mkdtemp(prefix="echolike-abuse-")
srv = subprocess.Popen(
    [sys.executable, "-u", str(ROOT / "server.py"), "--port", str(PORT)],
    cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


def health():
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/health" % PORT, timeout=3) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


try:
    token = None
    for _ in range(50):
        line = srv.stdout.readline()
        if line.startswith("Token: "):
            token = line.split()[1].strip()
            break
    check("server up", health().get("ok"), True)

    # 1. client hangs up mid-response (the classic BrokenPipe)
    for _ in range(20):
        s = socket.create_connection(("127.0.0.1", PORT), timeout=3)
        s.sendall(b"GET / HTTP/1.0\r\n\r\n")
        s.close()  # never read the response
    time.sleep(0.3)
    check("survives clients hanging up", health().get("ok"), True)

    # 2. garbage request line
    for junk in (b"\x00\x01\x02\r\n\r\n", b"GET\r\n\r\n", b"NONSENSE / HTTP/9.9\r\n\r\n"):
        try:
            s = socket.create_connection(("127.0.0.1", PORT), timeout=3)
            s.sendall(junk)
            s.settimeout(2)
            try:
                s.recv(100)
            except socket.timeout:
                pass
            s.close()
        except OSError:
            pass
    check("survives garbage requests", health().get("ok"), True)

    # 3. Content-Length promising a body that never arrives, then hang up
    for _ in range(5):
        s = socket.create_connection(("127.0.0.1", PORT), timeout=3)
        s.sendall(
            b"POST /api/likes HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer " + token.encode()
            + b"\r\nContent-Type: application/json\r\nContent-Length: 999999\r\n\r\n{\"items\":["
        )
        s.close()
    time.sleep(0.3)
    check("survives truncated bodies", health().get("ok"), True)

    # 4. wrong token and bad JSON are 4xx, not a crash
    def post(body, auth):
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/likes" % PORT, data=body,
            headers={"authorization": "Bearer " + auth, "content-type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception as e:
            return str(e)

    check("wrong token -> 401", post(b'{"items":[]}', "0" * 32), 401)
    check("bad json -> 400", post(b"not json", token), 400)
    check("items not a list -> 400", post(b'{"items":"nope"}', token), 400)

    # 5. burst of 40 parallel posts, one item each: every line must survive
    def one(i):
        post(json.dumps({"items": [{"kind": "like", "id": str(i), "handle": "h", "text": "t"}]}).encode(), token)

    ts = [threading.Thread(target=one, args=(i,)) for i in range(40)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    check("survives parallel posts", health().get("ok"), True)
    log = pathlib.Path(work) / "likes.jsonl"
    lines = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
    check("40 items stored, none lost", len(lines), 40)
    check("no interleaved lines", all(isinstance(x.get("id"), str) for x in lines), True)

    # 6. still alive at the end
    check("alive at the end", health().get("ok"), True)
    check("process still running", srv.poll(), None)
finally:
    srv.terminate()
    try:
        srv.wait(timeout=5)
    except subprocess.TimeoutExpired:
        srv.kill()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
