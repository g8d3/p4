#!/usr/bin/env python3
"""Read-only wallet snapshot. Stdlib only. Never uses private keys.

- Hyperliquid public API: spot + perp clearinghouse state for WALLET_ADDRESS.
- EVM USDC balance: tries public Arbitrum RPCs (read-only eth_call balanceOf).
- Never prints WALLET_PRIVATE_KEY / HL_API_KEY. Missing address -> unknown.
Writes log/balance.json.
"""
import json
import os
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "log" / "balance.json"
HL = "https://api.hyperliquid.xyz"  # public info API; never the DRPC env URL
ADDR = os.environ.get("WALLET_ADDRESS", "")

USDC_ARB = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
BAL_OF = "70a08231"  # balanceOf(address)
RPCS = [
    "https://arbitrum-one-rpc.publicnode.com",
    "https://arb1.arbitrum.io/rpc",
    "https://arbitrum.llamarpc.com",
]


def post_info(payload, timeout=15):
    req = urllib.request.Request(
        HL + "/info", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def evm_usdc(address):
    if not address or not address.startswith("0x"):
        return {"ok": False, "reason": "no_address"}
    addr_pad = address[2:].lower().rjust(64, "0")
    data = "0x" + BAL_OF + addr_pad
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                       "params": [{"to": USDC_ARB, "data": data}, "latest"]}).encode()
    last_err = ""
    for rpc in RPCS:
        try:
            req = urllib.request.Request(rpc, data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as r:
                res = json.loads(r.read().decode())
            val = int(res.get("result", "0x0"), 16) / 1e6
            return {"ok": True, "usdc": round(val, 2), "rpc": rpc}
        except Exception as e:  # noqa: BLE001 - report, keep trying
            last_err = str(e)[:120]
    return {"ok": False, "reason": last_err or "rpc_unreachable"}


def main():
    snap = {"address_prefix": (ADDR[:6] + "..." + ADDR[-4:]) if ADDR else None}
    if ADDR:
        for key, typ in (("perp", {"type": "clearinghouseState", "user": ADDR}),
                         ("spot", {"type": "spotClearinghouseState", "user": ADDR})):
            try:
                st = post_info(typ)
                m = st.get("marginSummary", {})
                snap[key] = {"ok": True,
                             "accountValue": m.get("accountValue"),
                             "totalMarginUsed": m.get("totalMarginUsed")}
            except Exception as e:  # noqa: BLE001
                snap[key] = {"ok": False, "reason": str(e)[:120]}
    else:
        snap["perp"] = snap["spot"] = {"ok": False, "reason": "WALLET_ADDRESS unset"}
    snap["evm_arbitrum_usdc"] = evm_usdc(ADDR)
    snap["live_orders_placed"] = 0  # v0 never places orders; honest counter
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snap, indent=2))
    print(f"BALANCE spot={snap.get('spot')} perp_account={snap.get('perp', {}).get('accountValue')} "
          f"evm={snap['evm_arbitrum_usdc']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
