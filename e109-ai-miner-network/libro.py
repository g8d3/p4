#!/usr/bin/env python3
"""e109 — the ledger: who did the work, what it was worth, and who brought the client.

This is the part that answers "is a blockchain needed?" Honestly: for the *accounting* of a
network that we operate, a signed ledger in SQLite is enough, and it is 1000x cheaper than a
chain. A chain becomes necessary the moment someone other than us must verify the books without
trusting us (a miner checking its own payouts, a referrer checking its commission, a buyer
checking a receipt root). Until then, put a merkle root in a table and keep going.

So: the ledger is the source of truth; `batches.root` is the anchor that a settlement layer
(Solana memo, or a published daily file) can carry. Swapping in a chain changes *who can verify*,
never the numbers.

Tables: agents (keys, kind), jobs (spec), receipts (signed work), commissions (first-touch, %),
batches (one merkle root per settlement). Money is USD everywhere; crypto is only the rail.
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "libro.db"
NETWORK_FEE = 0.10          # what the network keeps on a sale
COMMISSION_PCT = 0.15       # what the agent that brought the client earns, forever, first touch

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY, kind TEXT, pubkey TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, spec TEXT, workflow TEXT, client TEXT,
  ref TEXT, price_usd REAL, created TEXT);
CREATE TABLE IF NOT EXISTS receipts(job TEXT PRIMARY KEY, worker TEXT, out_sha TEXT, model TEXT,
  tokens_in INT, tokens_out INT, joules REAL, price_usd REAL, sig TEXT, verified INT, spot INT,
  match TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS commissions(sale_job TEXT, referrer TEXT, pct REAL, usd REAL,
  paid INT DEFAULT 0);
CREATE TABLE IF NOT EXISTS batches(id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT,
  n_jobs INT, root TEXT, anchor TEXT);
CREATE TABLE IF NOT EXISTS contracts(id TEXT PRIMARY KEY, client TEXT, ref TEXT, workflow TEXT,
  tier TEXT, price_usd REAL, royalty_share REAL, model TEXT, feed_at TEXT, spec TEXT,
  client_sig TEXT, scout_sig TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS components(id TEXT PRIMARY KEY, kind TEXT, spec TEXT, sponsor TEXT,
  builder TEXT, tier TEXT, royalty_share REAL, created TEXT);
CREATE TABLE IF NOT EXISTS reuses(id INTEGER PRIMARY KEY AUTOINCREMENT, component TEXT, buyer TEXT,
  fee_usd REAL, sponsor_usd REAL, builder_usd REAL, network_usd REAL, created TEXT);
"""


def connect():
    DB.parent.mkdir(exist_ok=True)
    db = sqlite3.connect(DB)
    db.executescript(SCHEMA)
    return db


def register(db, agent_id, kind, pubkey, now):
    db.execute("INSERT OR IGNORE INTO agents VALUES (?,?,?,?)", (agent_id, kind, pubkey, now))
    db.commit()


def add_job(db, spec, jid, now):
    db.execute("INSERT OR IGNORE INTO jobs VALUES (?,?,?,?,?,?,?)",
               (jid, json.dumps(spec, sort_keys=True), spec["workflow"], spec["client"],
                spec.get("ref", ""), spec["price_usd"], now))
    db.commit()


def add_receipt(db, jid, r, sig, verified, spot, match, now):
    db.execute("INSERT OR REPLACE INTO receipts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (jid, r["worker"], r["out_sha"], r["model"], r["tokens_in"], r["tokens_out"],
                r["joules"], r["price_usd"], sig, int(verified), int(spot), match, now))
    db.commit()


def owe_commission(db, jid, ref):
    """First touch only: the ref recorded on the job is the only one that ever gets paid."""
    if not ref:
        return 0.0
    row = db.execute("SELECT price_usd FROM jobs WHERE id=?", (jid,)).fetchone()
    usd = round(row[0] * COMMISSION_PCT, 8)
    db.execute("INSERT INTO commissions VALUES (?,?,?,?,0)", (jid, ref, COMMISSION_PCT, usd))
    db.commit()
    return usd


def add_contract(db, c, now):
    db.execute("INSERT OR REPLACE INTO contracts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (c["id"], c["client"], c["ref"], c["workflow"], c["tier"], c["price_usd"],
                c["royalty_share"], c["model"], c["feed_at"], json.dumps(c["spec"], sort_keys=True),
                c["client_sig"], c["scout_sig"], now))
    db.commit()


def register_component(db, component_id, kind, spec, sponsor, builder, tier, share, now):
    """A delivered piece enters the registry with its owners. Reuse pays them, forever."""
    db.execute("INSERT OR REPLACE INTO components VALUES (?,?,?,?,?,?,?,?)",
               (component_id, kind, json.dumps(spec, sort_keys=True), sponsor, builder, tier,
                share, now))
    db.commit()


def pay_reuse(db, component_id, buyer, fee_usd, builder_share, now):
    """One reuse event: sponsor gets its contracted share, builder its share, network the rest."""
    row = db.execute("SELECT sponsor, royalty_share FROM components WHERE id=?",
                     (component_id,)).fetchone()
    if not row:
        raise KeyError("unknown component: %s" % component_id)
    sponsor, share = row
    sponsor_usd = round(fee_usd * share, 8)
    builder_usd = round(fee_usd * builder_share, 8)
    network_usd = round(fee_usd - sponsor_usd - builder_usd, 8)
    db.execute("INSERT INTO reuses(component,buyer,fee_usd,sponsor_usd,builder_usd,network_usd,"
               "created) VALUES (?,?,?,?,?,?,?)",
               (component_id, buyer, fee_usd, sponsor_usd, builder_usd, network_usd, now))
    db.commit()
    return {"sponsor": sponsor, "sponsor_usd": sponsor_usd, "builder_usd": builder_usd,
            "network_usd": network_usd}


def close_batch(db, root, now):
    n = db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
    db.execute("INSERT INTO batches(created,n_jobs,root,anchor) VALUES (?,?,?,NULL)",
               (now, n, root))
    db.commit()
    return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def report(db):
    q = db.execute
    return {
        "jobs": q("SELECT COUNT(*) FROM jobs").fetchone()[0],
        "receipts": q("SELECT COUNT(*) FROM receipts").fetchone()[0],
        "verified": q("SELECT COUNT(*) FROM receipts WHERE verified=1").fetchone()[0],
        "spot_checked": q("SELECT COUNT(*) FROM receipts WHERE spot=1").fetchone()[0],
        "exact_match": q("SELECT COUNT(*) FROM receipts WHERE match='exact'").fetchone()[0],
        "fuzzy_match": q("SELECT COUNT(*) FROM receipts WHERE match='fuzzy'").fetchone()[0],
        "sales_usd": round(q("SELECT COALESCE(SUM(price_usd),0) FROM receipts").fetchone()[0], 8),
        "commission_usd": round(q("SELECT COALESCE(SUM(usd),0) FROM commissions").fetchone()[0], 8),
        "joules": round(q("SELECT COALESCE(SUM(joules),0) FROM receipts").fetchone()[0], 1),
        "workers": [r[0] for r in q("SELECT DISTINCT worker FROM receipts").fetchall()],
        "referrers": [r[0] for r in q("SELECT DISTINCT referrer FROM commissions").fetchall()],
        "network_fee_usd": round(q("SELECT COALESCE(SUM(price_usd),0) FROM receipts")
                                 .fetchone()[0] * NETWORK_FEE, 8),
        "contracts": q("SELECT COUNT(*) FROM contracts").fetchone()[0],
        "components": q("SELECT COUNT(*) FROM components").fetchone()[0],
        "reuse_fees_usd": round(q("SELECT COALESCE(SUM(fee_usd),0) FROM reuses").fetchone()[0], 8),
        "royalties_paid_usd": round(q("SELECT COALESCE(SUM(sponsor_usd+builder_usd),0) FROM reuses")
                                    .fetchone()[0], 8),
    }
