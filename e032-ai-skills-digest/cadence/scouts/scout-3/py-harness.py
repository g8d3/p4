import json, os, urllib.request, urllib.error

base = os.environ["OPENCODE_GO_BASE_URL"]
key = os.environ["OPENCODE_GO_API_KEY"]
model = os.environ.get("OPENCODE_GO_MODEL", "deepseek-v4-flash")
req = urllib.request.Request(
    base + "chat/completions",
    data=json.dumps({"model": model, "messages": [{"role": "user", "content": "Reply with exactly: ok"}], "max_tokens": 200}).encode(),
    headers={"content-type": "application/json", "authorization": "Bearer " + key, "user-agent": "curl/8.0"},
)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.load(r)
        msg = j.get("choices", [{}])[0].get("message", {}).get("content")
        print("OK status=%s model=%s reply=%r" % (r.status, j.get("model", "?"), msg))
except urllib.error.HTTPError as e:
    print("HTTP_ERROR status=%s body=%s" % (e.code, e.read()[:200]))
except Exception as e:
    print("ERROR %s: %s" % (type(e).__name__, e))