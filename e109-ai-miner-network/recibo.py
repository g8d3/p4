#!/usr/bin/env python3
"""e109 — the receipt: the only thing a miner, a client and a verifier all agree on.

A job is a spec. A miner answers it and returns a receipt: what it was asked, what came back
(hash, never the text), which model, how many tokens, how many joules, and a signature over the
canonical bytes. Payment, reputation and spot-checks all hang off this object — which is why it
is defined here once, and why nothing in it is optional.

No chain involved: ed25519 + sha256 are enough to prove *who* submitted *what*, and to make a
batch root that a settlement layer (Solana, or a plain database) can anchor later.

Keys live in `keys/` (0600, gitignored), never in env or in a file we commit.
"""
import base64
import hashlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parent
KEYS = ROOT / "keys"


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def job_id(spec):
    return sha(canon(spec))[:16]


def keypair(name):
    """Load or create `<name>`'s ed25519 key. Returns (private, public_hex)."""
    KEYS.mkdir(exist_ok=True)
    p = KEYS / (name + ".key")
    if p.exists():
        raw = base64.b64decode(p.read_text().strip())
        priv = Ed25519PrivateKey.from_private_bytes(raw)
    else:
        priv = Ed25519PrivateKey.generate()
        p.write_text(base64.b64encode(priv.private_bytes(
            serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
            serialization.NoEncryption())).decode())
        os.chmod(p, 0o600)
    pub = priv.public_key().public_bytes(serialization.Encoding.Raw,
                                         serialization.PublicFormat.Raw).hex()
    return priv, pub


def sign(priv, obj):
    body = dict(obj)
    body.pop("sig", None)
    return base64.b64encode(priv.sign(canon(body))).decode()


def verify(pub_hex, obj, sig_b64):
    body = dict(obj)
    body.pop("sig", None)
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(
            base64.b64decode(sig_b64), canon(body))
        return True
    except Exception:
        return False


def make(spec, *, worker_pub, output, model, tokens_in, tokens_out, joules, price_usd):
    """A receipt binds the spec, the answer (by hash) and the work done."""
    r = {
        "job": job_id(spec),
        "spec_sha": sha(canon(spec)),
        "out_sha": sha(output.encode()),
        "worker": worker_pub,
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "joules": round(joules or 0, 1),
        "price_usd": round(price_usd, 8),
    }
    return r


def merkle(leaves):
    """Root over receipt hashes: one 32-byte value anchors a whole batch."""
    layer = [sha(canon(x)) for x in leaves]
    if not layer:
        return sha(b"")
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [sha(bytes.fromhex(layer[i]) + bytes.fromhex(layer[i + 1]))
                 for i in range(0, len(layer), 2)]
    return layer[0]
