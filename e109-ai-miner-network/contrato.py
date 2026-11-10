#!/usr/bin/env python3
"""e109 — the contract a scout agent closes, and the registry that keeps paying afterwards.

The scout's job is not "sell software": it is to find a business with a problem, talk to the person
who owns it, and put a number in front of them that is impossible to refuse because a human doing
the same work costs a hundred times more. Two axes, quoted live from the market feed:

  · the work, priced at the cheapest model that passes the quality floor (never a typed constant);
  · ownership, as a ladder: cost / co-build / owner. More money up front buys a bigger share of
    every future reuse of the component.

That is the abundance mechanic: the client is not buying a licence, it is buying a position. If the
same piece is later used by another business — alone or inside a bigger product — the registry pays
the sponsor (the client), the builder (the agent that built it) and the network, forever.

  python3 contrato.py quote quote-by-text [tier]
  python3 contrato.py close quote-by-text owner  biz_dana  agent_ref_3  scout_a
  python3 contrato.py reuse comp_quote-by-text_dana  biz_other  0.50
  python3 contrato.py show
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import libro
import precios
import recibo

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())
BUILDER_SHARE = CFG["royalty"]["builder_share"]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def quote(workflow, tier="cobuild"):
    feed = precios.fetch_feed()
    q = precios.quote(feed, workflow, tier)[tier]
    tokens = q["tokens"]
    cheapest = min((m for m in feed["models"] if m.endswith(":batch")),
                   key=lambda m: precios.cost_usd(feed, m, tokens[0], tokens[1]))
    return {
        "id": "c_%s_%s_%s" % (workflow, q["tier"] if "tier" in q else tier,
                              feed["_fetched_at"][:10]),
        "workflow": workflow, "tier": tier,
        "price_usd": q["price_usd"], "royalty_share": q["royalty_share"],
        "model": q["model"], "cost_usd": q["cost_usd"], "tokens": q["tokens"],
        "feed_at": feed["_fetched_at"],
        "cheapest_on_market": cheapest,
        "spread_vs_cheapest": round(q["cost_usd"] / precios.cost_usd(feed, cheapest, *tokens), 2),
        "note": "price is the market price of the tokens x the tier multiple; the spread is shown "
                "so nobody has to ask what we are paying for the same work.",
    }


def close(workflow, tier, client, ref, scout):
    q = quote(workflow, tier)
    spec = {"workflow": workflow, "client": client, "ref": ref, "tier": tier,
            "deliverable": "%s component, reusable by other businesses" % workflow}
    scout_priv, scout_pub = recibo.keypair(scout)
    client_priv, client_pub = recibo.keypair(client)
    body = {"id": q["id"], "spec": spec, "price_usd": q["price_usd"],
            "royalty_share": q["royalty_share"], "model": q["model"]}
    c = dict(q, spec=spec, client=client, ref=ref, scout=scout,
             client_pub=client_pub, scout_pub=scout_pub,
             client_sig=recibo.sign(client_priv, body), scout_sig=recibo.sign(scout_priv, body))
    db = libro.connect()
    libro.register(db, client, "client", client_pub, now())
    libro.register(db, scout, "scout", scout_pub, now())
    libro.add_contract(db, c, now())
    libro.register_component(db, q["id"], workflow, spec, client, scout, tier,
                             q["royalty_share"], now())
    return c


def show():
    db = libro.connect()
    rows = db.execute("SELECT id, client, tier, price_usd, royalty_share, created FROM contracts "
                      "ORDER BY created DESC LIMIT 10").fetchall()
    print("contracts: %d" % libro.report(db)["contracts"])
    for r in rows:
        print("  %-34s %-10s %-8s $%.8f  royalty %.0f%%  %s"
              % (r[0], r[1], r[2], r[3], r[4] * 100, r[5]))


def main(argv):
    if not argv:
        return show()
    cmd = argv[0]
    if cmd == "quote":
        q = quote(argv[1], argv[2] if len(argv) > 2 else "cobuild")
        print(json.dumps(q, indent=1, ensure_ascii=False))
    elif cmd == "close":
        c = close(*argv[1:6])
        print(json.dumps({k: c[k] for k in ("id", "client", "tier", "price_usd",
                                            "royalty_share", "model")}, indent=1))
        print("signed by client and scout; component registered")
    elif cmd == "reuse":
        db = libro.connect()
        out = libro.pay_reuse(db, argv[1], argv[2], float(argv[3]), BUILDER_SHARE, now())
        print(json.dumps(out, indent=1))
    else:
        show()


if __name__ == "__main__":
    main(sys.argv[1:])
