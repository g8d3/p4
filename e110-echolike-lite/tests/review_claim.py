"""Claim review: a device token is issued on the spot, so nothing is pasted.

Real server.py over HTTP, no browser: health advertises the claim mode, a claim
mints a working token, the plaintext is never stored, the device cap holds, and
the token printed at start keeps working. Exit code 1 on any failure.
"""
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
server_dir = tempfile.mkdtemp(prefix="echolike-lite-claim-")
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


PORT = free_port()
srv = subprocess.Popen(
    [sys.executable, "-u", str(ROOT / "server.py"), "--port", str(PORT)],
    cwd=server_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    env=dict(os.environ, ECHO_MAX_DEVICES="3"),
)
BASE = f"http://127.0.0.1:{PORT}"


def call(path, token=None, body=None, method=None):
    req = urllib.request.Request(
        BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        method=method or ("POST" if body is not None else "GET"),
        headers={"content-type": "application/json", **({"authorization": "Bearer " + token} if token else {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


try:
    token = None
    for _ in range(50):
        line = srv.stdout.readline()
        if line.startswith("Token: "):
            token = line.split()[1].strip()
            break
    check("server printed its token", len(token or ""), 32)

    code, health = call("/api/health")
    check("health ok", (code, health.get("ok")), (200, True))
    check("health advertises claim mode", health.get("claim"), "private")

    code, first = call("/api/claim", method="POST")
    check("claim from loopback works", (code, first.get("ok")), (200, True))
    dev = first.get("token") or ""
    check("claim returned a device token", len(dev), 32)
    check("device token differs from the server token", dev != token, True)

    code, r = call("/api/likes", dev, {"items": [{"kind": "like", "id": "1", "handle": "nasa"}]})
    check("device token can post", (code, r.get("received")), (200, 1))

    code, _ = call("/api/likes", "0" * 32, {"items": [{"id": "2"}]})
    check("a wrong token is still refused", code, 401)

    code, r = call("/api/likes", token, {"items": [{"kind": "like", "id": "3", "handle": "esa"}]})
    check("the printed server token still works", (code, r.get("received")), (200, 1))

    # Device cap (ECHO_MAX_DEVICES=3): two more claims fit, the fourth is refused.
    codes = [call("/api/claim", method="POST")[0] for _ in range(3)]
    check("claim stops at the device cap", codes, [200, 200, 409])

    devfile = pathlib.Path(server_dir) / ".devices.json"
    check("devices file written", devfile.exists(), True)
    check("devices file is private", oct(devfile.stat().st_mode & 0o777), "0o600")
    stored = devfile.read_text()
    check("no plaintext token on disk", dev in stored or token in stored, False)
    check("devices recorded", len(json.loads(stored)), 3)

    health = call("/api/health")[1]
    check("health still answers after all that", health.get("ok"), True)
finally:
    srv.terminate()
    try:
        srv.wait(timeout=5)
    except subprocess.TimeoutExpired:
        srv.kill()

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
