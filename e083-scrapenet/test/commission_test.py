#!/usr/bin/env python3
"""Commission math tests for ScrapeNet earnings (incl. caps).

Pure function test: no server, no fixtures. Run: python3 test/commission_test.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
import app


def check(name, cond, detail=""):
    print(("ok  " if cond else "FAIL") + f" {name} {detail}")
    if not cond:
        check.failed = True


check.failed = False

# basic: 100 records x 0.01 = 1.00 gross, 10% -> fee 0.10, net 0.90
nodes, totals = app.compute_earnings({"n1": 100}, "SCRAPE", 0.01, 10, 1000, None)
check("basic gross", nodes[0]["gross"] == 1.0, nodes[0])
check("basic commission", nodes[0]["commission"] == 0.1, nodes[0])
check("basic net", nodes[0]["net"] == 0.9, nodes[0])
check("basic totals", totals == {"records": 100, "billable_records": 100,
                                 "gross": 1.0, "commission": 0.1, "net": 0.9}, totals)

# totals add up across nodes
nodes, totals = app.compute_earnings({"a": 10, "b": 30}, "SCRAPE", 0.01, 10, 1000, None)
check("multi-node totals", totals["gross"] == 0.4 and totals["net"] == 0.36, totals)

# spam: per-node record cap stops payout growth
nodes, _ = app.compute_earnings({"spam": 5000}, "SCRAPE", 0.01, 10, 1000, None)
check("record cap enforced", nodes[0]["billable_records"] == 1000 and nodes[0]["capped"] is True, nodes[0])
check("capped gross", nodes[0]["gross"] == 10.0, nodes[0])

# net payout cap
nodes, _ = app.compute_earnings({"whale": 900}, "SCRAPE", 0.01, 10, 1000, 5.0)
check("net cap enforced", nodes[0]["net"] == 5.0 and nodes[0]["capped"] is True, nodes[0])

# under caps: no flag
nodes, _ = app.compute_earnings({"ok": 50}, "SCRAPE", 0.01, 10, 1000, 5.0)
check("no false cap", nodes[0]["capped"] is False and nodes[0]["net"] == 0.45, nodes[0])

# zero commission edge
nodes, _ = app.compute_earnings({"z": 7}, "T", 0.5, 0, 1000, None)
check("zero commission", nodes[0]["net"] == 3.5 and nodes[0]["commission"] == 0.0, nodes[0])

print("PASS" if not check.failed else "FAIL")
sys.exit(1 if check.failed else 0)
