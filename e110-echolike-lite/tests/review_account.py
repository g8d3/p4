"""Accounts: email login (dev code), tenant linking and the wrapped key backup.

Runs against a LOCAL worker (`wrangler dev --local`) because the production one
mails real codes and must never hand one back. The dev deployment sets
ECHO_DEV_CODE=1, so `POST /api/account/start` returns the code instead of mailing
it — that flag is never set in production.

    cd inbox-worker && wrangler dev --port 8788 --local --compatibility-date 2026-10-30
    python3 tests/review_account.py

Exit code 1 on any failure.
"""
import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8788").rstrip("/")
failures = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ": " + repr(got))
    if not ok:
        failures.append(name)


def call(path, token=None, body=None, method=None):
    h = {"content-type": "application/json"}
    if token:
        h["authorization"] = "Bearer " + token
    req = urllib.request.Request(
        BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        method=method or ("POST" if body is not None else "GET"),
        headers=h,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


b64u = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")

# A device first, as the extension has: claim a tenant, then attach an account to it.
code, claim = call("/api/claim", method="POST")
check("device claimed", (code, claim.get("ok")), (200, True))
device = claim["token"]

EMAIL = "owner+%d@example.com" % int.from_bytes(os.urandom(2), "big")
code, r = call("/api/account/start", body={"email": "not an email"})
check("a bad address is refused", (code, r.get("ok")), (400, False))
code, r = call("/api/account/start", body={"email": EMAIL})
check("a code is issued", (code, r.get("ok")), (200, True))
otp = r.get("code") or ""
check("the dev deployment returns a 6-digit code", len(otp), 6)
check("no account token before verifying", call("/api/account")[0], 401)

code, r = call("/api/account/verify", body={"email": EMAIL, "code": "000000"})
check("a wrong code is refused", (code, r.get("ok")), (401, False))

code, r = call("/api/account/verify", device, {"email": EMAIL, "code": otp})
check("the right code signs in and links this device", (code, r.get("ok")), (200, True))
atoken = r.get("atoken") or ""
check("an account token comes back", len(atoken), 32)
check("the same code cannot be reused", call("/api/account/verify", device, {"email": EMAIL, "code": otp})[0], 401)

code, r = call("/api/account", atoken)
check("the account lists its tenant", (code, claim["user"] in (r.get("tenants") or [])), (200, True))
check("no key backup yet", r.get("has_key"), False)
check("captures counted", isinstance(r.get("captures"), int), True)

# The key backup: wrapped with a passphrase here, so the server can only store it.
key = os.urandom(32)
passphrase = "correct horse battery"
salt = os.urandom(16)
iterations = 210000
wrap_key = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, iterations, 32)
iv = os.urandom(12)
backup = {
    "salt": b64u(salt),
    "iterations": iterations,
    "iv": b64u(iv),
    "ct": b64u(AESGCM(wrap_key).encrypt(iv, b64u(key).encode(), None)),
}
code, r = call("/api/account/key", atoken, {"salt": "x"})
check("an unwrapped key is refused", (code, r.get("ok")), (400, False))
code, r = call("/api/account/key", atoken, backup)
check("the wrapped key is stored", (code, r.get("ok")), (200, True))
code, r = call("/api/account", atoken)
check("the account reports a backup", r.get("has_key"), True)

code, r = call("/api/account/key", atoken)
check("the backup comes back", code, 200)
got = r.get("backup") or {}
check("the server holds no plaintext key", b64u(key) in json.dumps(got), False)
check("nor the passphrase", passphrase in json.dumps(got), False)
plain = AESGCM(hashlib.pbkdf2_hmac("sha256", passphrase.encode(), base64.urlsafe_b64decode(got["salt"] + "=="), got["iterations"], 32)).decrypt(
    base64.urlsafe_b64decode(got["iv"] + "=="), base64.urlsafe_b64decode(got["ct"] + "=="), None
)
check("the passphrase opens it on the client", plain.decode(), b64u(key))
try:
    AESGCM(hashlib.pbkdf2_hmac("sha256", b"wrong passphrase", base64.urlsafe_b64decode(got["salt"] + "=="), got["iterations"], 32)).decrypt(
        base64.urlsafe_b64decode(got["iv"] + "=="), base64.urlsafe_b64decode(got["ct"] + "=="), None
    )
    check("a wrong passphrase fails", "opened", "refused")
except Exception:
    check("a wrong passphrase fails", "refused", "refused")

check("no token, no access to a backup", call("/api/account/key")[0], 401)
check("a bogus account token is refused", call("/api/account", "0" * 32)[0], 401)

print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
