#!/usr/bin/env python3
"""e109 — what a job costs right now, from a live market feed. No invented numbers.

The first version of this experiment priced a job with a constant copied out of one vendor's
pricing page. That is stale the moment the market moves, and it was **5.7x too expensive**:
the live feed prices the same model (`z-ai/glm-5.3-flash:batch`) at $0.033/M in and $0.061/M out,
not the $0.15 / $0.50 the coding-plan page lists.

So cost is never a constant here: it is a function of (live price, actual token counts). The feed
is OpenRouter's public model catalogue (465 models, per-token prices, no key), cached with a
timestamp; token counts are what the network already records on every receipt. A quote is
`tokens x price` plus the network fee — recomputable by anyone, at any moment.

  python3 precios.py                 # quote the three workflows, three tiers each
  python3 precios.py --json          # the full dict
  python3 precios.py --refresh       # force a feed refresh
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text())
P = CFG["pricing"]
FEED = ROOT / "data" / "precios.json"
FEED_TTL_S = 3600


def fetch_feed(force=False):
    now = datetime.now(timezone.utc).timestamp()
    if FEED.exists() and not force:
        cached = json.loads(FEED.read_text())
        if now - cached.get("_fetched_ts", 0) < FEED_TTL_S:
            return cached
    req = urllib.request.Request(P["feed_url"], headers={"User-Agent": "e109-precios"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = json.load(r)["data"]
    models = {}
    for m in raw:
        pr = m.get("pricing") or {}
        try:
            pin, pout = float(pr.get("prompt", 0)), float(pr.get("completion", 0))
        except (TypeError, ValueError):
            continue
        if pin <= 0 and pout <= 0:
            continue
        models[m["id"]] = {"in_per_m": pin * 1e6, "out_per_m": pout * 1e6,
                           "ctx": m.get("context_length")}
    feed = {"_fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "_fetched_ts": now, "models": models}
    FEED.parent.mkdir(exist_ok=True)
    FEED.write_text(json.dumps(feed, indent=1))
    return feed


def cost_usd(feed, model_id, tokens_in, tokens_out):
    """The only cost formula in the network: price comes from the feed, tokens from the receipt."""
    m = feed["models"].get(model_id)
    if not m:
        raise KeyError("model not in feed: %s" % model_id)
    return (tokens_in * m["in_per_m"] + tokens_out * m["out_per_m"]) / 1_000_000


def quote(feed, workflow, tier=None):
    """One workflow -> one price per ownership tier, all on the cheapest model that passes quality.

    Two axes kept apart on purpose: the model is a quality decision (cheapest that works), the
    tier is an ownership decision (how much of the reuse the client buys). Mixing them produced a
    ladder where the "plus" tier cost 40x the "owner" tier — the client could not tell what it was
    buying.
    """
    tokens_in, tokens_out = CFG["expected_tokens"][workflow]
    model = P["model_by_workflow"][workflow]
    base = cost_usd(feed, model, tokens_in, tokens_out)
    out = {}
    for name, spec in P["tiers"].items():
        if tier and name != tier:
            continue
        out[name] = {
            "model": model,
            "cost_usd": round(base, 8),
            "price_usd": round(base * spec["multiple"], 8),
            "royalty_share": spec["royalty_share"],
            "tokens": [tokens_in, tokens_out],
        }
    return out


def margin_vs_energy(feed, workflow, joules_per_job, kwh_usd):
    """What a local miner keeps: the sale price minus its own energy. This is the miner's P&L."""
    tokens_in, tokens_out = CFG["expected_tokens"][workflow]
    energy = joules_per_job / 3_600_000 * kwh_usd
    rows = {}
    for name, spec in P["tiers"].items():
        market = cost_usd(feed, P["model_by_workflow"][workflow], tokens_in, tokens_out)
        price = market * spec["multiple"]
        rows[name] = {"price_usd": round(price, 8), "energy_usd": round(energy, 10),
                      "miner_margin_usd": round(price * (1 - P["network_fee"]) - energy, 8),
                      "basis": "sold at the market price of the same tokens, paid its own energy"}
    return rows


def main(argv):
    feed = fetch_feed("--refresh" in argv)
    out = {"feed": {"fetched_at": feed["_fetched_at"], "models": len(feed["models"])},
           "workflows": {}}
    for wf in CFG["expected_tokens"]:
        out["workflows"][wf] = quote(feed, wf)
    out["miner"] = {wf: margin_vs_energy(feed, wf, CFG["machine_joules_per_job"],
                                         CFG["machine"]["usd_per_kwh"])
                    for wf in CFG["expected_tokens"]}
    if "--json" in argv:
        print(json.dumps(out, indent=1, ensure_ascii=False))
        return
    print("feed: %s (%d models, prices are $/1M tokens)" % (out["feed"]["fetched_at"],
                                                            out["feed"]["models"]))
    for wf, tiers in out["workflows"].items():
        print("\n%s  (tokens %s)" % (wf, tiers[next(iter(tiers))]["tokens"]))
        for name, t in tiers.items():
            print("  %-8s %-34s cost $%.8f -> price $%.8f  royalty %.0f%%"
                  % (name, t["model"], t["cost_usd"], t["price_usd"],
                     t["royalty_share"] * 100))
            m = out["miner"][wf][name]
            print("           miner: energy $%.8f  keeps $%.8f" % (m["energy_usd"],
                                                                   m["miner_margin_usd"]))


if __name__ == "__main__":
    main(sys.argv[1:])
