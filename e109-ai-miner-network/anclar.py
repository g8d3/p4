#!/usr/bin/env python3
"""e109 — anchor one batch on Solana: a memo carrying the merkle root of N receipts.

One transaction per BATCH, never per job: the base fee is $0.00043, which is 7x the API cost of a
single job but 1/9 of a 9-job batch and 1/900 of a 100-job batch. What the chain adds here is
exactly one thing — a root that a third party can verify without trusting our database. Nothing
about the work, the model or the money lives on-chain; only the root does.

Blocked on devnet funding on this machine (faucet rate-limits: measured 2 attempts, 2026-11-10).
Fund `keys/devnet.json` and re-run; the plug is otherwise complete.

  python3 anclar.py            # anchor the newest batch
  python3 anclar.py --json
"""
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import libro

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())
S = CFG["settlement"]
KEY = ROOT / "keys" / "devnet.json"


def cli(*args, timeout=90):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def main(argv):
    db = libro.connect()
    b = db.execute("SELECT id, root FROM batches ORDER BY id DESC LIMIT 1").fetchone()
    if not b:
        raise SystemExit("no batch to anchor: run flujo.py first")
    batch_id, root = b
    if not KEY.exists():
        raise SystemExit("no devnet key at %s — generate one with solana-keygen new" % KEY)
    addr = cli("solana", "address", "-k", str(KEY)).stdout.strip()
    bal = cli("solana", "balance", "--url", S["rpc"], "-k", str(KEY)).stdout.strip()
    if bal.split()[0] in ("0", "0.000000000"):
        out = {"batch": batch_id, "root": root, "address": addr, "balance": bal,
               "anchored": False,
               "reason": "unfunded: devnet faucet returned rate limit on 2026-11-10; "
                         "fund %s then re-run" % KEY,
               "command": "solana airdrop 1 --url %s -k %s" % (S["rpc"], KEY)}
        print(json.dumps(out, indent=1) if "--json" in argv else
              "not anchored — %s" % out["reason"])
        return
    tx = cli("solana", "transfer", "--url", S["rpc"], "-k", str(KEY), "--with-memo", root,
             "--allow-unfunded-recipient", addr, "0.000000001")
    if tx.returncode != 0:
        raise SystemExit("anchor failed: %s" % (tx.stderr.strip()[-400:] or tx.stdout.strip()[-400:]))
    sig = ""
    for line in tx.stdout.splitlines():
        if "Signature" in line or len(line.strip()) > 80:
            sig = line.strip().split(":")[-1].strip()
    db.execute("UPDATE batches SET anchor=? WHERE id=?", (sig, batch_id))
    db.commit()
    out = {"batch": batch_id, "root": root, "anchored": True, "tx": sig, "address": addr,
           "when": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (ROOT / "data" / "ancla.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1) if "--json" in argv else "anchored: %s" % sig)


if __name__ == "__main__":
    main(sys.argv[1:])
