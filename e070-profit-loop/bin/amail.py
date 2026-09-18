#!/usr/bin/env python3
"""AgentMail helper: agent-owned inbox. Key from AGENTMAIL_API_KEY env. Never prints key.
Usage:
  python3 bin/amail.py inbox                       # show inbox address
  python3 bin/amail.py recent [n]                  # latest messages
  python3 bin/amail.py read <message_id>           # full message
  python3 bin/amail.py send <to> <subject> <body>  # send (plain text)
"""
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = "https://api.agentmail.to/v0"
INBOX = "zcash_cat@agentmail.to"


def call(method, path, data=None):
    key = os.environ.get("AGENTMAIL_API_KEY", "")
    if not key:
        return {"error": "AGENTMAIL_API_KEY missing"}
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"},
        method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "inbox"
    if cmd == "inbox":
        print(json.dumps({"inbox": INBOX}))
    elif cmd == "recent":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        d = call("GET", "/inboxes/%s/messages?limit=%d"
                 % (urllib.parse.quote(INBOX), n))
        for m in d.get("messages", []):
            print(json.dumps({"id": m.get("message_id", m.get("id")),
                              "from": m.get("from", "?"),
                              "subject": (m.get("subject") or "")[:120],
                              "date": m.get("date", m.get("created_at", ""))}))
    elif cmd == "read":
        mid = sys.argv[2]
        m = call("GET", "/inboxes/%s/messages/%s"
                 % (urllib.parse.quote(INBOX), urllib.parse.quote(mid)))
        print(json.dumps(m, indent=1)[:3000])
    elif cmd == "send":
        to, subject, body = sys.argv[2], sys.argv[3], sys.argv[4]
        print(json.dumps(call("POST", "/inboxes/%s/messages/send"
                              % urllib.parse.quote(INBOX),
                              {"to": to, "subject": subject, "body": body}))[:300])
    else:
        print(json.dumps({"error": "unknown cmd"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
