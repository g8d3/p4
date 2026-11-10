#!/usr/bin/env python3
"""e109 — the worker: a machine joins the network, answers a job, signs a receipt.

This is what "people join their computers to run inference" looks like at the smallest useful
size: an HTTP endpoint, a local model, a signed receipt, no chain, no node, no consensus.

  POST /job  {"spec": {...}}  ->  {"output": "...", "receipt": {...}, "sig": "...", "pub": "..."}
  GET  /health                ->  {"worker": "<pub>", "model": "..."}

Determinism is the contract: temperature 0, fixed seed, fixed options. The verifier re-runs the
same spec and compares hashes; if the model is not reproducible, the receipt says so instead of
pretending (that is what `flujo.py` measures).

  python3 worker.py [port]
"""
import json
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import energia
import recibo

ROOT = Path(__file__).resolve().parent
M = json.loads((ROOT / "config.json").read_text())["machine"]
SEED = 42
WORKER_ID = "w_" + sys.argv[2] if len(sys.argv) > 2 else "w_local"


def infer(spec):
    body = {
        "model": M["model"],
        "messages": [{"role": "system", "content": spec["system"]},
                     {"role": "user", "content": spec["user"]}],
        "stream": False,
        "options": {"temperature": 0, "seed": SEED, "num_predict": M["max_tokens"]},
    }
    req = urllib.request.Request(M["url"].rstrip("/") + "/api/chat",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.load(r)
    return out


def handle(spec):
    out, joules = energia.joules_between(M["energy_counter"], lambda: infer(spec))
    text = (out.get("message") or {}).get("content", "")
    priv, pub = recibo.keypair(WORKER_ID)
    r = recibo.make(spec, worker_pub=pub, output=text, model=M["model"],
                    tokens_in=out.get("prompt_eval_count", 0),
                    tokens_out=out.get("eval_count", 0),
                    joules=joules, price_usd=spec["price_usd"])
    return {"output": text, "receipt": r, "sig": recibo.sign(priv, r), "pub": pub}


class H(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            _, pub = recibo.keypair(WORKER_ID)
            self._json(200, {"worker": pub, "model": M["model"], "id": WORKER_ID})
        else:
            self._json(404, {"error": "no such path"})

    def do_POST(self):
        if self.path != "/job":
            return self._json(404, {"error": "no such path"})
        n = int(self.headers.get("Content-Length", 0))
        try:
            spec = json.loads(self.rfile.read(n))["spec"]
            if not all(k in spec for k in ("system", "user", "price_usd", "workflow", "client")):
                raise ValueError("spec needs system, user, price_usd, workflow, client")
        except Exception as e:
            return self._json(400, {"error": str(e)})
        try:
            self._json(200, handle(spec))
        except Exception as e:
            self._json(500, {"error": "inference failed: %s" % e})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 11500
    print("worker on 127.0.0.1:%d — model %s" % (port, M["model"]), flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
