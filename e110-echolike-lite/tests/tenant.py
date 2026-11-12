"""A tenant for a live test, with a failure that explains itself.

The hosted inbox caps claims per hour and devices per IP, so a suite that has run all
afternoon eventually gets a 409 where it expected a token — and the traceback
(`KeyError: 'token'`) says nothing about the cause. This helper claims one tenant and,
when the cap answers, stops with the exact command that clears it.

Test tenants are deliberately NOT reused: the assertions in review_spaces/review_pair
count rows ("1 in the inbox", "3 in the space"), which only holds for a fresh list.
`bin/live-test-reset.sh` is what keeps the device cap from filling up: it drops devices
belonging to tenants with a handful of captures and no account link.
"""
import json
import urllib.error
import urllib.request

BASE = "https://inbox-lite.echolike.app"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"


def _call(path, token=None, body=None, method=None):
    h = {"content-type": "application/json", "user-agent": UA}
    if token:
        h["authorization"] = "Bearer " + token
    req = urllib.request.Request(
        BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        method=method or ("POST" if body is not None else "GET"),
        headers=h,
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def tenant(label="test"):
    """A fresh {token, user} tenant, or a clear stop when the inbox says no."""
    code, claim = _call("/api/claim", method="POST")
    if code != 200 or not claim.get("token"):
        raise SystemExit(
            "could not claim a test tenant for %r (%s: %s)\n"
            "run bin/live-test-reset.sh — it clears the claim window and the devices of test tenants"
            % (label, code, claim.get("error"))
        )
    return {"token": claim["token"], "user": claim["user"]}
