#!/usr/bin/env python3
"""Track B alert-shipper DRY RUN (paper-only).

Reads e058 funding signals read-only, composes the Telegram alert text
that WOULD be sent for the top persistent executable spread(s).

Hard rules: stdlib only, read-only DB access (URI mode=ro), no network,
no sends, no writes outside stdout. Exit 0 on success.
"""
import sqlite3
import sys
from datetime import datetime, timezone

E058_DB = "/home/vuos/code/p4/e058-funding-scanner/data.db"
TOP_N = 3
OI_RANK_CUTOFF = 500  # e058 convention: rank 500+ = mirage


def parse_ts(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def freshness_badge(sent_ts, now):
    dt = parse_ts(sent_ts)
    if dt is None:
        return "FRESHNESS UNKNOWN", "?"
    hours = (now - dt).total_seconds() / 3600
    if hours < 1:
        return "FRESH", "%dm" % int(hours * 60)
    if hours < 6:
        return "AGING", "%.1fh" % hours
    return "STALE", "%.0fh (~%.1fd)" % (hours, hours / 24)


def main():
    now = datetime.now(timezone.utc)
    con = sqlite3.connect("file:%s?mode=ro" % E058_DB, uri=True)
    try:
        cur = con.cursor()
        row = cur.execute("SELECT MAX(sent_ts) FROM signals").fetchone()
        if not row or not row[0]:
            print("PAPER DRY-RUN: no signals in e058 data. Nothing would send.")
            return 0
        latest = row[0]
        rows = cur.execute(
            "SELECT coin, median_apy, spread_bps, long_v, short_v, persist, oi_rank"
            " FROM signals WHERE sent_ts = ? AND persist = '4/4'"
            " AND oi_rank < ? ORDER BY median_apy DESC LIMIT ?",
            (latest, OI_RANK_CUTOFF, TOP_N),
        ).fetchall()
    finally:
        con.close()

    badge, age = freshness_badge(latest, now)
    lines = []
    lines.append("[PAPER — DRY RUN, NOT SENT]")
    lines.append("FUNDING SPREAD x%d (persist 4/4, OI rank < %d)" % (len(rows), OI_RANK_CUTOFF))
    lines.append("snapshot %s | freshness: %s (%s old)" % (latest, badge, age))
    lines.append("")
    if not rows:
        lines.append("No executable spread at latest snapshot. Nothing would send.")
    for i, (coin, apy, spread, long_v, short_v, persist, oi) in enumerate(rows, 1):
        lines.append(
            "%d. %s: LONG %s / SHORT %s | spread %.2f bps/8h | ~%.0f%% APY"
            " | OI rk %d | persist %s" % (i, coin, long_v, short_v, spread, apy, oi, persist)
        )
    lines.append("")
    lines.append("PAPER watermark: simulated, no position taken. OI+depth gated; verify live before pilot.")
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
